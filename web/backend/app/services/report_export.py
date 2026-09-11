"""Report export in CSV, JSON, PDF, and Markdown formats.

Every format that can carry prose — MD, PDF, and JSON — surfaces the *full*
engine-generated document (``penetration_test_report.md`` + each
``vulnerabilities/*.md``) so a user who downloads the PDF gets the same content
they'd see in the Markdown export, not a one-page summary. CSV stays tabular
(findings only) because it exists for spreadsheet/pipeline consumers.
"""

import csv
import io
import json
import re
from datetime import UTC, datetime
from pathlib import Path

from app.core.config import settings
from app.models.assessment import Assessment


def _run_dir(assessment: Assessment) -> Path | None:
    run_id = getattr(assessment, "strix_run_id", None)
    if not run_id or not settings.STRIX_REPO_PATH:
        return None
    d = Path(settings.STRIX_REPO_PATH) / "strix_runs" / run_id
    return d if d.exists() else None


def read_strix_report(assessment: Assessment) -> dict:
    """Read the engine-generated report + per-vuln markdown from the run dir.

    Returns ``{"has_report", "report_md", "vulnerabilities": [{id,title,severity,md}]}``.
    ``has_report`` is False for simulations or runs without a run dir.
    """
    run_dir = _run_dir(assessment)
    if run_dir is None:
        return {"has_report": False, "report_md": "", "vulnerabilities": []}

    report_md = ""
    report_path = run_dir / "penetration_test_report.md"
    if report_path.exists():
        try:
            report_md = report_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            report_md = ""

    vulns: list[dict] = []
    csv_path = run_dir / "vulnerabilities.csv"
    if csv_path.exists():
        try:
            rows = list(csv.DictReader(csv_path.open(encoding="utf-8", errors="replace")))
        except OSError:
            rows = []
        for row in rows:
            vid = (row.get("id") or "").strip()
            rel = (row.get("file") or f"vulnerabilities/{vid}.md").strip()
            md = ""
            vpath = run_dir / rel
            if vpath.exists():
                try:
                    md = vpath.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    md = ""
            vulns.append({
                "id": vid,
                "title": (row.get("title") or "").strip(),
                "severity": (row.get("severity") or "").strip(),
                "md": md,
            })

    return {
        "has_report": bool(report_md or vulns),
        "report_md": report_md,
        "vulnerabilities": vulns,
    }


def to_markdown(assessment: Assessment) -> bytes:
    """Full engine report + all vulnerability details as one markdown document.

    Falls back to a minimal generated header when the run dir has no report
    (e.g. simulation), so the export always produces something coherent.
    """
    data = read_strix_report(assessment)
    parts: list[str] = []
    if data["report_md"].strip():
        parts.append(data["report_md"].rstrip())
    else:
        parts.append(f"# Security Assessment Report — {assessment.name}\n")
        parts.append(f"**Target:** {assessment.target}  ")
        parts.append(f"**Status:** {assessment.status}  ")
        parts.append(f"**Generated:** {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}\n")

    if data["vulnerabilities"]:
        parts.append("\n\n---\n\n# Vulnerability Details\n")
        for v in data["vulnerabilities"]:
            if v["md"].strip():
                parts.append("\n" + v["md"].rstrip() + "\n")
            else:
                parts.append(f"\n## {v['title'] or v['id']} ({v['severity'].upper()})\n")

    return ("\n".join(parts).rstrip() + "\n").encode("utf-8")


def _findings_rows(assessment: Assessment) -> list[dict]:
    return [
        {
            "id": f.id,
            "title": f.title,
            "severity": f.severity,
            "cve": f.cve or "",
            "description": f.description,
            "recommendation": f.recommendation,
        }
        for f in assessment.findings
    ]


def to_csv(assessment: Assessment) -> bytes:
    buf = io.StringIO()
    writer = csv.DictWriter(
        buf, fieldnames=["id", "title", "severity", "cve", "description", "recommendation"]
    )
    writer.writeheader()
    writer.writerows(_findings_rows(assessment))
    return buf.getvalue().encode("utf-8")


def to_json(assessment: Assessment) -> bytes:
    strix = read_strix_report(assessment)
    payload = {
        "assessment": {
            "id": assessment.id,
            "name": assessment.name,
            "target": assessment.target,
            "status": assessment.status,
            "created_at": assessment.created_at.isoformat() if assessment.created_at else None,
        },
        "generated_at": datetime.now(UTC).isoformat(),
        "findings": _findings_rows(assessment),
        # The full engine document, so automation consumers get the same content
        # a human sees in the Markdown/PDF export.
        "strix_report_md": strix["report_md"],
        "vulnerability_details": [
            {"id": v["id"], "title": v["title"], "severity": v["severity"], "md": v["md"]}
            for v in strix["vulnerabilities"]
        ],
    }
    return json.dumps(payload, indent=2).encode("utf-8")


_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$")
_LIST_RE = re.compile(r"^(\s*)([-*+]|\d+\.)\s+(.+)$")
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_CODE_RE = re.compile(r"`([^`]+)`")


def _md_inline(text: str) -> str:
    """Escape XML metacharacters, then apply **bold** and `inline code` markup.

    reportlab's Paragraph uses an XML-ish mini-language, so raw ``&<>`` must be
    escaped before we introduce our own ``<b>``/``<font>`` tags — otherwise a
    stray ``<`` in the source text (very common in shell payloads or exploit
    code) blows up the whole document build.
    """
    s = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    s = _BOLD_RE.sub(r"<b>\1</b>", s)
    s = _CODE_RE.sub(r'<font face="Courier">\1</font>', s)
    return s


def _md_to_flowables(md: str, styles, code_style) -> list:
    """Best-effort markdown → reportlab flowables.

    Supports the subset the Strix engine actually emits: ATX headings, ``**bold**``
    and ``` `inline code` ```, fenced code blocks (```` ```lang ... ``` ````),
    ``-``/``*``/``1.`` lists, horizontal rules, and blank-line paragraph breaks.
    Anything unrecognized falls through as a plain paragraph so no content is
    dropped.
    """
    from reportlab.lib import colors as _colors
    from reportlab.lib.units import mm
    from reportlab.platypus import HRFlowable, Paragraph, Preformatted, Spacer

    story: list = []
    lines = md.splitlines()
    para_buf: list[str] = []

    heading_style = {1: "Heading1", 2: "Heading2", 3: "Heading3"}

    def flush_para() -> None:
        if not para_buf:
            return
        text = " ".join(ln.strip() for ln in para_buf if ln.strip())
        if text:
            story.append(Paragraph(_md_inline(text), styles["BodyText"]))
        para_buf.clear()

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Fenced code block — take verbatim; escape XML metachars only.
        if stripped.startswith("```"):
            flush_para()
            i += 1
            code_lines: list[str] = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            i += 1  # skip closing fence (or fall off end)
            if code_lines:
                code_txt = "\n".join(code_lines)
                # Preformatted respects newlines and monospacing; escape only.
                safe = code_txt.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                story.append(Preformatted(safe, code_style))
                story.append(Spacer(1, 2 * mm))
            continue

        # Horizontal rule
        if stripped in ("---", "***", "___"):
            flush_para()
            story.append(
                HRFlowable(width="100%", thickness=0.5, color=_colors.HexColor("#cbd5e1"))
            )
            story.append(Spacer(1, 3 * mm))
            i += 1
            continue

        # Heading
        m = _HEADING_RE.match(stripped)
        if m:
            flush_para()
            level = min(len(m.group(1)), 3)
            story.append(Spacer(1, 3 * mm))
            story.append(Paragraph(_md_inline(m.group(2)), styles[heading_style[level]]))
            i += 1
            continue

        # List item — bullet or numbered; preserve indentation loosely.
        li = _LIST_RE.match(line)
        if li:
            flush_para()
            indent_spaces = len(li.group(1))
            marker = li.group(2)
            bullet = "•" if marker in ("-", "*", "+") else marker
            content = _md_inline(li.group(3))
            left = 6 + indent_spaces * 3  # in points, roughly
            para = (
                f'<para leftIndent="{left + 10}" firstLineIndent="-10">'
                f"<b>{bullet}</b> {content}</para>"
            )
            story.append(Paragraph(para, styles["BodyText"]))
            i += 1
            continue

        # Blank line → paragraph break.
        if not stripped:
            flush_para()
            i += 1
            continue

        para_buf.append(line)
        i += 1

    flush_para()
    return story


def to_pdf(assessment: Assessment) -> bytes:
    """Full engine report as PDF.

    Renders the engine's ``penetration_test_report.md`` and each per-vuln
    markdown as proper PDF content (headings, lists, code blocks), not just a
    summary table. Falls back to the metadata + findings table when the run dir
    has no report (simulation runs), so the export never produces a blank PDF.
    """
    # Lazy import so the app still runs if reportlab isn't installed.
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        HRFlowable,
        PageBreak,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    strix = read_strix_report(assessment)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        title=f"{assessment.name} Report",
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
    )
    styles = getSampleStyleSheet()
    code_style = ParagraphStyle(
        "MdCode",
        parent=styles["Code"],
        fontName="Courier",
        fontSize=8,
        leading=10,
        backColor=colors.HexColor("#f1f5f9"),
        borderPadding=4,
        leftIndent=4,
        rightIndent=4,
        spaceBefore=3,
        spaceAfter=3,
    )
    story: list = []

    # --- Cover ---
    story.append(Paragraph(f"Security Assessment Report — {assessment.name}", styles["Title"]))
    story.append(Spacer(1, 6 * mm))
    for m in (
        f"<b>Target:</b> {assessment.target}",
        f"<b>Status:</b> {assessment.status}",
        f"<b>Scan type:</b> {assessment.scan_type}",
        f"<b>Generated:</b> {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}",
    ):
        story.append(Paragraph(m, styles["Normal"]))
    story.append(Spacer(1, 6 * mm))

    # --- Findings summary table (always present) ---
    sev_color = {
        "critical": colors.HexColor("#b91c1c"),
        "high": colors.HexColor("#ea580c"),
        "medium": colors.HexColor("#ca8a04"),
        "low": colors.HexColor("#2563eb"),
        "info": colors.HexColor("#64748b"),
    }
    story.append(Paragraph(f"Findings ({len(assessment.findings)})", styles["Heading2"]))
    if assessment.findings:
        data = [["Severity", "Title", "CVE"]]
        for f in assessment.findings:
            data.append([f.severity.upper(), f.title, f.cve or "-"])
        table = Table(data, colWidths=[26 * mm, 118 * mm, 30 * mm])
        style = [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ]
        for i, f in enumerate(assessment.findings, start=1):
            style.append(("TEXTCOLOR", (0, i), (0, i), sev_color.get(f.severity, colors.black)))
        table.setStyle(TableStyle(style))
        story.append(table)
    else:
        story.append(Paragraph("No findings recorded.", styles["Normal"]))

    # --- Full engine report body ---
    if strix["report_md"].strip():
        story.append(PageBreak())
        story.extend(_md_to_flowables(strix["report_md"], styles, code_style))

    # --- Per-vulnerability details ---
    if strix["vulnerabilities"]:
        story.append(PageBreak())
        story.append(Paragraph("Vulnerability Details", styles["Heading1"]))
        for idx, v in enumerate(strix["vulnerabilities"]):
            if idx > 0:
                story.append(Spacer(1, 4 * mm))
                story.append(
                    HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#94a3b8"))
                )
                story.append(Spacer(1, 3 * mm))
            if v["md"].strip():
                story.extend(_md_to_flowables(v["md"], styles, code_style))
            else:
                story.append(
                    Paragraph(
                        f"<b>{v['title'] or v['id']}</b> ({v['severity'].upper()})",
                        styles["Heading2"],
                    )
                )

    doc.build(story)
    return buf.getvalue()


EXPORTERS = {
    "csv": (to_csv, "text/csv"),
    "json": (to_json, "application/json"),
    "pdf": (to_pdf, "application/pdf"),
    "md": (to_markdown, "text/markdown"),
}

"""Report export in CSV, JSON, and PDF formats."""

import csv
import io
import json
from datetime import UTC, datetime

from app.models.assessment import Assessment


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
    }
    return json.dumps(payload, indent=2).encode("utf-8")


def to_pdf(assessment: Assessment) -> bytes:
    # Lazy import so the app still runs if reportlab isn't installed.
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, title=f"{assessment.name} Report")
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph(f"Security Assessment Report — {assessment.name}", styles["Title"]))
    story.append(Spacer(1, 6 * mm))
    meta = [
        f"<b>Target:</b> {assessment.target}",
        f"<b>Status:</b> {assessment.status}",
        f"<b>Scan type:</b> {assessment.scan_type}",
        f"<b>Generated:</b> {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}",
    ]
    for m in meta:
        story.append(Paragraph(m, styles["Normal"]))
    story.append(Spacer(1, 6 * mm))

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
        table = Table(data, colWidths=[28 * mm, 110 * mm, 30 * mm])
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

    doc.build(story)
    return buf.getvalue()


EXPORTERS = {
    "csv": (to_csv, "text/csv"),
    "json": (to_json, "application/json"),
    "pdf": (to_pdf, "application/pdf"),
}

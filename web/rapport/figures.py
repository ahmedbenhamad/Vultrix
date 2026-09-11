# -*- coding: utf-8 -*-
"""Génère toutes les figures du rapport PFE (diagrammes + graphiques)."""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Ellipse
import matplotlib.font_manager as fm

FIG = os.path.join(os.path.dirname(__file__), "figures")
os.makedirs(FIG, exist_ok=True)

PRIMARY = "#2563eb"; DARK = "#0f172a"; SLATE = "#334155"; LIGHT = "#e2e8f0"
GREEN = "#16a34a"; RED = "#dc2626"; ORANGE = "#ea580c"; AMBER = "#d97706"; INFO = "#64748b"
plt.rcParams.update({"font.size": 10, "font.family": "DejaVu Sans"})
# Les titres sont gérés comme légendes dans le document Word (style académique).
matplotlib.axes.Axes.set_title = lambda self, *a, **k: None


def box(ax, x, y, w, h, text, fc=PRIMARY, tc="white", fs=9, r=0.02):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0.01,rounding_size={r}",
                                fc=fc, ec="none", zorder=2))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", color=tc, fontsize=fs,
            weight="bold", zorder=3, wrap=True)


def arrow(ax, p1, p2, color=SLATE, style="-|>", lw=1.6, ls="-"):
    ax.add_patch(FancyArrowPatch(p1, p2, arrowstyle=style, mutation_scale=14,
                                 color=color, lw=lw, linestyle=ls, zorder=1))


def save(fig, name):
    fig.savefig(os.path.join(FIG, name), dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("wrote", name)


# ── 1. Architecture globale ───────────────────────────────────────────────────
def architecture():
    fig, ax = plt.subplots(figsize=(9, 6)); ax.axis("off"); ax.set_xlim(0, 10); ax.set_ylim(0, 10)
    box(ax, 0.5, 8.4, 9, 1.1, "Client (Navigateur) — Next.js 16 · React 19 · Tailwind\nDashboard · Assessments · Reports · Assistant IA · ⌘K", DARK, fs=9)
    # frontend proxy
    box(ax, 0.5, 6.7, 9, 0.9, "Serveur Next.js  —  proxy /api/* (cookies httpOnly + CSRF)", "#1e3a8a", fs=9)
    arrow(ax, (5, 8.4), (5, 7.6))
    # backend
    box(ax, 0.5, 3.7, 9, 2.6, "", "#f1f5f9", tc=DARK)
    ax.text(5, 6.05, "Backend  —  FastAPI (async) + SQLAlchemy 2.0", ha="center", color=DARK, weight="bold", fontsize=10)
    for i, t in enumerate(["Auth / RBAC\nMFA · Sessions", "Assessments\nPipeline · WS", "Findings\nTriage · Diff",
                            "Schedules\nAPScheduler", "Reports\nPDF/CSV/JSON", "Assistant\n+ RAG"]):
        box(ax, 0.7 + i * 1.5, 4.5, 1.35, 1.1, t, PRIMARY, fs=7.5)
    box(ax, 0.7, 3.9, 8.6, 0.45, "Middlewares : En-têtes de sécurité · CSRF · Rate-limit · Request-ID · Audit inaltérable", INFO, fs=7.5)
    arrow(ax, (5, 6.7), (5, 6.3))
    # data + engine
    box(ax, 0.5, 2.1, 2.7, 1.2, "PostgreSQL\n(asyncpg / SQLite dev)", "#0e7490", fs=8.5)
    box(ax, 3.6, 2.1, 2.7, 1.2, "Redis\n(files / cache)", "#b91c1c", fs=8.5)
    box(ax, 6.7, 2.1, 2.8, 1.2, "Moteur Strix (CLI)\nDocker sandbox (Kali)", DARK, fs=8.5)
    arrow(ax, (2, 3.7), (2, 3.3)); arrow(ax, (5, 3.7), (5, 3.3)); arrow(ax, (8, 3.7), (8, 3.3))
    # engine externals
    box(ax, 6.7, 0.4, 1.35, 1.1, "Metasploit\nFramework", "#7c3aed", fs=8)
    box(ax, 8.15, 0.4, 1.35, 1.1, "Pentest RAG\n(FastAPI)", GREEN, fs=8)
    arrow(ax, (7.4, 2.1), (7.4, 1.5)); arrow(ax, (8.8, 2.1), (8.8, 1.5))
    ax.set_title("Figure — Architecture globale de la plateforme Strix Console", fontsize=11, weight="bold")
    save(fig, "architecture.png")


# ── 2. Diagramme de cas d'utilisation ─────────────────────────────────────────
def usecase():
    fig, ax = plt.subplots(figsize=(9, 6.5)); ax.axis("off"); ax.set_xlim(0, 10); ax.set_ylim(0, 10)
    actors = [("Administrateur", 0.6, 8.4), ("Manager", 0.6, 6.2), ("Analyste", 0.6, 4.0), ("Observateur", 0.6, 1.8)]
    for name, x, y in actors:
        ax.plot(x + 0.25, y + 0.55, "o", ms=13, color=DARK)
        ax.plot([x + 0.25, x + 0.25], [y + 0.45, y - 0.05], color=DARK, lw=2)
        ax.plot([x, x + 0.5], [y + 0.25, y + 0.25], color=DARK, lw=2)
        ax.plot([x + 0.25, x], [y - 0.05, y - 0.4], color=DARK, lw=2)
        ax.plot([x + 0.25, x + 0.5], [y - 0.05, y - 0.4], color=DARK, lw=2)
        ax.text(x + 0.25, y - 0.7, name, ha="center", fontsize=8.5, weight="bold")
    ax.add_patch(FancyBboxPatch((3.1, 0.6), 6.6, 8.9, boxstyle="round,pad=0.02,rounding_size=0.1",
                                fc="#f8fafc", ec=SLATE, lw=1.2))
    ax.text(6.4, 9.15, "Strix Console", ha="center", fontsize=9, weight="bold", color=SLATE)
    uc = ["S'authentifier (MFA)", "Gérer utilisateurs & rôles", "Créer / lancer un test",
          "Suivre le pipeline (live)", "Visualiser la sortie du moteur", "Trier les vulnérabilités",
          "Comparer deux scans", "Planifier des tests récurrents", "Exporter des rapports",
          "Consulter l'assistant IA", "Consulter le journal d'audit"]
    ys = [8.9, 8.15, 7.4, 6.65, 5.9, 5.15, 4.4, 3.65, 2.9, 2.15, 1.4]
    for t, y in zip(uc, ys):
        ax.add_patch(Ellipse((6.4, y), 5.6, 0.62, fc="white", ec=PRIMARY, lw=1.3))
        ax.text(6.4, y, t, ha="center", va="center", fontsize=8)
    # a few association lines
    for (ax0, ay0), y in [((1.1, 8.65), 8.9), ((1.1, 8.65), 8.15), ((1.1, 6.45), 7.4),
                          ((1.1, 6.45), 3.65), ((1.1, 4.25), 6.65), ((1.1, 4.25), 4.4),
                          ((1.1, 2.05), 5.9), ((1.1, 2.05), 1.4)]:
        ax.plot([ax0, 3.6], [ay0, y], color=LIGHT, lw=1, zorder=0)
    ax.set_title("Figure — Diagramme de cas d'utilisation", fontsize=11, weight="bold")
    save(fig, "usecase.png")


# ── 3. Pipeline d'évaluation (5 phases) ───────────────────────────────────────
def pipeline():
    fig, ax = plt.subplots(figsize=(10, 2.6)); ax.axis("off"); ax.set_xlim(0, 10.5); ax.set_ylim(0, 2.4)
    phases = [("1", "Reconnaissance", PRIMARY), ("2", "Éval. des\nvulnérabilités", PRIMARY),
              ("3", "Exploitation", ORANGE), ("4", "Post-\nexploitation", RED), ("5", "Reporting", GREEN)]
    x = 0.4
    for i, (n, t, c) in enumerate(phases):
        ax.add_patch(plt.Circle((x + 0.5, 1.6), 0.42, color=c, zorder=2))
        ax.text(x + 0.5, 1.6, n, ha="center", va="center", color="white", weight="bold", fontsize=13, zorder=3)
        ax.text(x + 0.5, 0.55, t, ha="center", va="center", fontsize=9)
        if i < 4:
            arrow(ax, (x + 0.95, 1.6), (x + 1.55, 1.6), color=SLATE, lw=2)
        x += 2.0
    ax.set_title("Figure — Pipeline d'évaluation en 5 phases", fontsize=11, weight="bold")
    save(fig, "pipeline.png")


# ── 4. Handoff d'exploitation (exploit_research) ──────────────────────────────
def exploit_handoff():
    fig, ax = plt.subplots(figsize=(9, 4.6)); ax.axis("off"); ax.set_xlim(0, 10); ax.set_ylim(0, 6)
    box(ax, 0.4, 4.7, 2.4, 1.0, "Recon : service,\nversion, CVE", DARK, fs=9)
    box(ax, 3.6, 4.7, 2.8, 1.0, "exploit_research\n(un seul appel)", PRIMARY, fs=9)
    arrow(ax, (2.8, 5.2), (3.6, 5.2))
    box(ax, 7.0, 5.3, 2.6, 0.8, "1) RAG /retrieve\n→ portail de pertinence", GREEN, fs=8)
    box(ax, 7.0, 4.3, 2.6, 0.8, "2) RAG /query\n(guidage exploit)", GREEN, fs=8)
    box(ax, 7.0, 3.3, 2.6, 0.8, "3) msfconsole search\n(module Metasploit)", "#7c3aed", fs=8)
    arrow(ax, (6.4, 5.2), (7.0, 5.7)); arrow(ax, (6.4, 5.2), (7.0, 4.7)); arrow(ax, (6.4, 5.2), (7.0, 3.7))
    box(ax, 3.2, 2.2, 3.6, 0.9, "Recommandation déterministe\n(décision côté Python)", "#1e3a8a", fs=9)
    arrow(ax, (5, 4.7), (5, 3.1))
    box(ax, 0.4, 0.5, 4.2, 1.0, "Module Metasploit trouvé →\nUTILISER LE MODULE (check, exploit -j)", "#7c3aed", fs=8.5)
    box(ax, 5.2, 0.5, 4.4, 1.0, "Sinon → payload RAG\n(actionable_commands / exploit_code)", GREEN, fs=8.5)
    arrow(ax, (4, 2.2), (2.5, 1.5)); arrow(ax, (6, 2.2), (7.4, 1.5))
    ax.set_title("Figure — Handoff d'exploitation : RAG + Metasploit (priorité au module)", fontsize=10.5, weight="bold")
    save(fig, "exploit_handoff.png")


# ── 5. Matrice RBAC (rôles × permissions) ─────────────────────────────────────
def rbac():
    import numpy as np
    roles = ["Observateur", "Analyste", "Manager", "Admin"]
    perms = ["stats:read", "assessment:read", "assessment:create/run", "finding:triage",
             "schedule:manage", "report:export", "assessment:read:all", "user:read",
             "audit:read", "user:manage", "role:manage", "settings:manage"]
    M = np.array([
        [1,1,0,0,0,0,0,0,0,0,0,0],
        [1,1,1,1,1,1,0,0,0,0,0,0],
        [1,1,1,1,1,1,1,1,1,0,0,0],
        [1,1,1,1,1,1,1,1,1,1,1,1],
    ])
    fig, ax = plt.subplots(figsize=(9, 3.2))
    ax.imshow(M, cmap="Blues", vmin=0, vmax=1.4, aspect="auto")
    ax.set_xticks(range(len(perms))); ax.set_xticklabels(perms, rotation=40, ha="right", fontsize=7.5)
    ax.set_yticks(range(len(roles))); ax.set_yticklabels(roles, fontsize=9)
    for i in range(len(roles)):
        for j in range(len(perms)):
            ax.text(j, i, "✓" if M[i, j] else "", ha="center", va="center",
                    color="white" if M[i, j] else "#cbd5e1", fontsize=10, weight="bold")
    ax.set_title("Figure — Matrice RBAC : permissions par rôle système", fontsize=11, weight="bold")
    save(fig, "rbac.png")


# ── 6. Diagramme de séquence : lancer un test ─────────────────────────────────
def seq_run():
    fig, ax = plt.subplots(figsize=(9.5, 5.2)); ax.axis("off"); ax.set_xlim(0, 10); ax.set_ylim(0, 10)
    lanes = ["Utilisateur", "Frontend", "API FastAPI", "Moteur Strix", "PostgreSQL"]
    xs = [1, 3, 5, 7, 9]
    for name, x in zip(lanes, xs):
        box(ax, x - 0.75, 9.1, 1.5, 0.7, name, DARK, fs=8)
        ax.plot([x, x], [0.5, 9.1], color=LIGHT, lw=1.2, zorder=0)
    steps = [
        (1, 3, "Créer + Lancer", 8.4),
        (3, 5, "POST /assessments/{id}/run  (cookie+CSRF)", 7.7),
        (5, 9, "INSERT assessment (queued)", 7.0),
        (5, 7, "launch()  →  strix --target --non-interactive", 6.3),
        (7, 7, "Docker sandbox : recon → exploit → post-ex", 5.4),
        (7, 5, "événements WS (state / log / finding)", 4.6),
        (5, 3, "WebSocket /ws/assessments/{id}", 3.9),
        (3, 1, "Console live + pipeline + findings", 3.2),
        (5, 9, "UPDATE status=completed, findings", 2.4),
    ]
    for a, b, t, y in steps:
        if a == b:
            ax.add_patch(FancyBboxPatch((a - 0.25, y - 0.25), 0.5, 0.5, boxstyle="round,pad=0.01",
                                        fc="#eff6ff", ec=PRIMARY))
            ax.text(a, y + 0.45, t, ha="center", fontsize=7.5, style="italic")
        else:
            arrow(ax, (a, y), (b, y), color=PRIMARY if a < b else SLATE,
                  style="-|>", ls="-" if a < b else "--")
            ax.text((a + b) / 2, y + 0.12, t, ha="center", fontsize=7.5)
    ax.set_title("Figure — Diagramme de séquence : exécution d'un test", fontsize=11, weight="bold")
    save(fig, "seq_run.png")


# ── 7. Gantt / planning des phases ────────────────────────────────────────────
def gantt():
    tasks = [
        ("Intégration Metasploit + RAG (exploit_research)", 0, 2, PRIMARY),
        ("Phase 0 — Fondations (async, migrations, tests)", 2, 1.2, "#1e3a8a"),
        ("Phase 1 — Auth (cookies, MFA, RBAC, audit)", 3.2, 1.3, "#1e3a8a"),
        ("Phase 2 — Temps réel (WebSocket, orphelins)", 4.5, 0.9, "#1e40af"),
        ("Phase 3 — Écran de sortie du moteur", 5.4, 0.9, ORANGE),
        ("Phase 4 — Phase de post-exploitation", 6.3, 0.9, RED),
        ("Phase 5 — Triage, diff, alertes, planification", 7.2, 1.5, GREEN),
        ("Phase 6 — ⌘K, observabilité, qualité", 8.7, 1.1, INFO),
        ("Tests, vérification & rédaction du rapport", 9.8, 1.2, DARK),
    ]
    fig, ax = plt.subplots(figsize=(10, 4.4))
    for i, (name, start, dur, c) in enumerate(tasks):
        ax.barh(len(tasks) - i - 1, dur, left=start, height=0.55, color=c, edgecolor="white")
        ax.text(start + dur + 0.1, len(tasks) - i - 1, name, va="center", fontsize=8)
    ax.set_yticks([]); ax.set_xlabel("Semaines (calendaire relatif)")
    ax.set_xlim(0, 16); ax.spines[["top", "right", "left"]].set_visible(False)
    ax.set_title("Figure — Planning du projet (méthodologie itérative par phases)", fontsize=11, weight="bold")
    save(fig, "gantt.png")


# ── 8. Répartition des vulnérabilités par sévérité ────────────────────────────
def severity():
    labels = ["Critique", "Élevée", "Moyenne", "Faible", "Info"]
    vals = [3, 2, 5, 3, 1]; cols = [RED, ORANGE, AMBER, PRIMARY, INFO]
    fig, ax = plt.subplots(figsize=(5.2, 4.2))
    w, _, at = ax.pie(vals, colors=cols, autopct=lambda p: f"{p*sum(vals)/100:.0f}",
                      startangle=90, wedgeprops=dict(width=0.42, edgecolor="white"), pctdistance=0.79)
    for t in at:
        t.set_color("white"); t.set_fontweight("bold")
    ax.legend(labels, loc="center", fontsize=8, frameon=False)
    ax.set_title("Figure — Répartition des vulnérabilités par sévérité", fontsize=10.5, weight="bold")
    save(fig, "severity.png")


# ── 9. Couverture de tests par module ─────────────────────────────────────────
def tests_chart():
    mods = ["Smoke\n(core)", "Sécurité\n(auth/MFA)", "WebSocket", "Sortie\nmoteur", "Post-\nexpl.",
            "Triage /\ndiff", "Ops\n(alertes)", "Planif."]
    counts = [8, 7, 3, 3, 4, 4, 6, 4]
    fig, ax = plt.subplots(figsize=(9, 3.6))
    bars = ax.bar(mods, counts, color=PRIMARY, edgecolor="white", width=0.6)
    ax.bar_label(bars, fontsize=9, weight="bold")
    ax.set_ylabel("Nombre de tests"); ax.set_ylim(0, 10)
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_title(f"Figure — Couverture de tests par module (total : {sum(counts)} tests, 100 % réussis)",
                 fontsize=10.5, weight="bold")
    save(fig, "tests.png")


# ── 10. Comparaison approche manuelle vs plateforme ───────────────────────────
def comparison():
    cats = ["Temps de\nmise en place", "Suivi\ntemps réel", "Traçabilité\n(audit)",
            "Reproductibilité", "Reporting", "Collaboration\n(RBAC)"]
    manual = [3, 2, 2, 2, 3, 1]; platform = [8, 9, 10, 9, 9, 9]
    import numpy as np
    x = np.arange(len(cats)); w = 0.38
    fig, ax = plt.subplots(figsize=(9, 3.8))
    ax.bar(x - w/2, manual, w, label="Pentest manuel", color=INFO)
    ax.bar(x + w/2, platform, w, label="Strix Console", color=PRIMARY)
    ax.set_xticks(x); ax.set_xticklabels(cats, fontsize=8)
    ax.set_ylabel("Score qualitatif (/10)"); ax.set_ylim(0, 11)
    ax.legend(frameon=False); ax.spines[["top", "right"]].set_visible(False)
    ax.set_title("Figure — Analyse comparative : approche manuelle vs plateforme", fontsize=10.5, weight="bold")
    save(fig, "comparison.png")


for f in [architecture, usecase, pipeline, exploit_handoff, rbac, seq_run, gantt, severity, tests_chart, comparison]:
    f()
print("DONE")

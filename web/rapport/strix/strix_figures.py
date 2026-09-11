# -*- coding: utf-8 -*-
"""Figures du rapport technique sur le projet open-source Strix."""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Ellipse

FIG = os.path.join(os.path.dirname(__file__), "figures")
os.makedirs(FIG, exist_ok=True)
PRIMARY = "#2563eb"; DARK = "#0f172a"; SLATE = "#334155"; LIGHT = "#e2e8f0"
GREEN = "#16a34a"; RED = "#dc2626"; ORANGE = "#ea580c"; PURPLE = "#7c3aed"; INFO = "#64748b"
plt.rcParams.update({"font.size": 10, "font.family": "DejaVu Sans"})
matplotlib.axes.Axes.set_title = lambda self, *a, **k: None


def box(ax, x, y, w, h, text, fc=PRIMARY, tc="white", fs=9):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.01,rounding_size=0.02",
                                fc=fc, ec="none", zorder=2))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", color=tc, fontsize=fs,
            weight="bold", zorder=3)


def arrow(ax, p1, p2, color=SLATE, lw=1.6, ls="-", style="-|>"):
    ax.add_patch(FancyArrowPatch(p1, p2, arrowstyle=style, mutation_scale=13, color=color,
                                 lw=lw, linestyle=ls, zorder=1))


def save(fig, name):
    fig.savefig(os.path.join(FIG, name), dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig); print("wrote", name)


def architecture():
    fig, ax = plt.subplots(figsize=(9.2, 6.2)); ax.axis("off"); ax.set_xlim(0, 10); ax.set_ylim(0, 10)
    # Host
    box(ax, 0.4, 8.2, 9.2, 1.3, "Hôte (poste / CI-CD)  —  CLI Strix (Python)\nOrchestrateur d'agents · TUI Textual · Boucle agentique", DARK, fs=9)
    # LLM
    box(ax, 0.4, 6.4, 3.0, 1.1, "Fournisseur LLM\n(via LiteLLM)\nGPT-5 / Claude / local", PURPLE, fs=8.5)
    arrow(ax, (1.9, 8.2), (1.9, 7.5), color=PURPLE, style="<|-|>")
    ax.text(0.55, 7.85, "prompts / actions", fontsize=7, color=PURPLE, va="center")
    # sandbox
    box(ax, 3.8, 3.2, 5.8, 4.3, "", "#f1f5f9", tc=DARK)
    ax.text(6.7, 7.2, "Bac à sable Docker (image Kali)", ha="center", weight="bold", color=DARK, fontsize=9.5)
    box(ax, 4.1, 6.3, 5.2, 0.7, "Serveur d'outils (tool_server) — exécute les appels d'outils", SLATE, fs=8)
    arrow(ax, (5, 8.2), (5, 7.0), color=PRIMARY, style="<|-|>")
    ax.text(5.2, 7.55, "appels d'outils (HTTP)", fontsize=7, color=PRIMARY, va="center")
    for i, (t, c) in enumerate([("Proxy\nCaido", RED), ("Navigateur", PRIMARY), ("Terminal", DARK),
                                ("Python", GREEN), ("Recon /\nOutils", ORANGE), ("Metasploit\n+ RAG", PURPLE)]):
        box(ax, 4.1 + (i % 3) * 1.75, 5.4 - (i // 3) * 0.95, 1.6, 0.8, t, c, fs=7.5)
    box(ax, 4.1, 3.35, 5.2, 0.55, "Outils Kali : nmap · nuclei · sqlmap · ffuf\nhttpx · subfinder · naabu · katana · wapiti", INFO, fs=6.8)
    # output
    box(ax, 0.4, 3.2, 3.0, 1.2, "Sorties  —  strix_runs/<run>\nvulnerabilities.csv · run.json\nstrix.log · rapport .md", GREEN, fs=8)
    arrow(ax, (3.8, 5.0), (3.4, 4.2), color=GREEN)
    save(fig, "architecture.png")


def agents():
    fig, ax = plt.subplots(figsize=(9, 5.2)); ax.axis("off"); ax.set_xlim(0, 10); ax.set_ylim(0, 6)
    box(ax, 3.7, 4.9, 2.6, 0.9, "Agent racine\n(orchestrateur)", DARK, fs=9)
    subs = [("Agent Recon", ORANGE, 0.4), ("Agent Injection\n(SQLi/XSS)", RED, 2.6),
            ("Agent Auth /\nIDOR", PRIMARY, 4.8), ("Agent SSRF /\nXXE", PURPLE, 7.0),
            ("Agent Rapport", GREEN, 9.2 - 1.6)]
    for t, c, x in subs:
        box(ax, x, 3.0, 1.7, 0.95, t, c, fs=7.5)
        arrow(ax, (5, 4.9), (x + 0.85, 3.95), color=SLATE)
    # validation subagent under injection
    box(ax, 2.6, 1.4, 1.7, 0.8, "Agent validation\n(PoC)", "#1e3a8a", fs=7.5)
    arrow(ax, (3.45, 3.0), (3.45, 2.2), color=SLATE)
    ax.text(5, 5.75, "Graphe d'agents — création dynamique, exécution parallèle, partage des découvertes",
            ha="center", fontsize=8.5, style="italic", color=SLATE)
    save(fig, "agents.png")


def workflow():
    fig, ax = plt.subplots(figsize=(10, 2.6)); ax.axis("off"); ax.set_xlim(0, 11); ax.set_ylim(0, 2.2)
    steps = [("Cible", INFO), ("Recon &\ncartographie", ORANGE), ("Éval. des\nvulnérabilités", PRIMARY),
             ("Exploitation", RED), ("Validation\n(PoC)", PURPLE), ("Rapport &\nfix", GREEN)]
    x = 0.2
    for i, (t, c) in enumerate(steps):
        box(ax, x, 0.7, 1.5, 0.9, t, c, fs=8)
        if i < len(steps) - 1:
            arrow(ax, (x + 1.5, 1.15), (x + 1.75, 1.15), color=SLATE, lw=2)
        x += 1.75
    save(fig, "workflow.png")


def tools_chart():
    cats = ["Proxy HTTP\n(Caido)", "Navigateur", "Terminal", "Python", "Recon", "Graphe\nd'agents",
            "Reporting", "Notes /\nTodo", "Recherche\nweb", "exploit_\nresearch"]
    vals = [1] * len(cats)
    colors = [RED, PRIMARY, DARK, GREEN, ORANGE, SLATE, GREEN, INFO, PRIMARY, PURPLE]
    fig, ax = plt.subplots(figsize=(9.2, 2.6))
    ax.bar(cats, vals, color=colors, edgecolor="white")
    ax.set_yticks([]); ax.set_ylim(0, 1.3)
    for i, c in enumerate(cats):
        ax.text(i, 0.5, "●", ha="center", va="center", color="white", fontsize=14)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(axis="x", labelsize=8)
    save(fig, "tools.png")


def vulns():
    groups = {
        "Contrôle d'accès": ["IDOR", "BFLA", "Mass assignment"],
        "Injection": ["SQLi", "RCE", "Path trav./LFI"],
        "Côté serveur": ["SSRF", "XXE", "Open redirect"],
        "Côté client": ["XSS", "CSRF"],
        "Logique / Auth": ["Business logic", "Race cond.", "JWT/Auth"],
        "Exposition": ["Info disclosure", "File upload", "Subdomain TO"],
    }
    fig, ax = plt.subplots(figsize=(9, 3.6))
    labels = list(groups.keys())
    counts = [len(v) for v in groups.values()]
    colors = [RED, ORANGE, PURPLE, PRIMARY, GREEN, INFO]
    bars = ax.bar(labels, counts, color=colors, edgecolor="white", width=0.62)
    ax.bar_label(bars, fontsize=9, weight="bold")
    ax.set_ylabel("Nombre de classes"); ax.set_ylim(0, 4)
    ax.tick_params(axis="x", labelsize=8.5)
    ax.spines[["top", "right"]].set_visible(False)
    save(fig, "vulns.png")


for f in [architecture, agents, workflow, tools_chart, vulns]:
    f()
print("DONE")

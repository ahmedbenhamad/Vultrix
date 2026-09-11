# -*- coding: utf-8 -*-
"""Figures du rapport technique sur le projet Pentest RAG."""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

FIG = os.path.join(os.path.dirname(__file__), "figures")
os.makedirs(FIG, exist_ok=True)
PRIMARY = "#2563eb"; DARK = "#0f172a"; SLATE = "#334155"; LIGHT = "#e2e8f0"
GREEN = "#16a34a"; RED = "#dc2626"; ORANGE = "#ea580c"; PURPLE = "#7c3aed"; INFO = "#64748b"; TEAL = "#0d9488"
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
    fig, ax = plt.subplots(figsize=(9.2, 6.0)); ax.axis("off"); ax.set_xlim(0, 10); ax.set_ylim(0, 10)
    # Clients
    box(ax, 0.4, 8.4, 4.3, 1.1, "Client / Agent Strix\ncurl · HTTP POST", DARK, fs=8.5)
    box(ax, 5.3, 8.4, 4.3, 1.1, "Testeur (humain)\nCLI rag_manager · Swagger /docs", SLATE, fs=8.5)
    # Docker compose boundary
    box(ax, 0.4, 2.0, 6.4, 5.6, "", "#f1f5f9", tc=DARK)
    ax.text(3.6, 7.3, "Docker Compose — réseau pentest_net", ha="center", weight="bold", color=DARK, fontsize=9)
    # pentest-rag service
    box(ax, 0.7, 5.4, 5.8, 1.5, "Service pentest-rag  (FastAPI / uvicorn)\n/query · /retrieve · /ingest  — port 8000",
        PRIMARY, fs=8.3)
    arrow(ax, (2.5, 8.4), (2.5, 6.9), color=PRIMARY, style="<|-|>")
    ax.text(2.7, 7.6, "HTTP JSON", fontsize=7, color=PRIMARY, va="center")
    # RAG core
    box(ax, 0.9, 4.35, 2.6, 0.8, "Embeddings\nnomic-embed-text", TEAL, fs=7.5)
    box(ax, 3.7, 4.35, 2.6, 0.8, "Reranker\nms-marco MiniLM", PURPLE, fs=7.5)
    arrow(ax, (3.6, 5.4), (2.2, 5.15), color=SLATE)
    arrow(ax, (3.9, 5.4), (5.0, 5.15), color=SLATE)
    # Qdrant
    box(ax, 0.7, 2.5, 5.8, 1.3, "Qdrant — base vectorielle\ncollection pentest_rag · distance COSINE · ports 6333/6334",
        RED, fs=8)
    arrow(ax, (3.6, 4.35), (3.6, 3.8), color=RED, style="<|-|>")
    # External LLM
    box(ax, 7.2, 5.4, 2.5, 1.5, "Backend LLM\nOllama (local)\nou OpenRouter (cloud)", ORANGE, fs=8)
    arrow(ax, (6.5, 6.15), (7.2, 6.15), color=ORANGE, style="<|-|>")
    ax.text(6.85, 6.4, "génération", fontsize=6.8, color=ORANGE, ha="center")
    # Volumes
    box(ax, 7.2, 2.5, 2.5, 1.9, "Volumes\n./data (corpus)\n./.env (config)\nhuggingface_cache", GREEN, fs=8)
    arrow(ax, (6.5, 3.1), (7.2, 3.3), color=GREEN)
    save(fig, "architecture.png")


def pipeline():
    fig, ax = plt.subplots(figsize=(10, 2.7)); ax.axis("off"); ax.set_xlim(0, 12); ax.set_ylim(0, 2.4)
    steps = [("1. Ingestion\ndonnées → vecteurs", TEAL), ("2. Retrieval\n+ Reranking", PURPLE),
             ("3. Generation\npayloads JSON", ORANGE)]
    x = 0.6
    for i, (t, c) in enumerate(steps):
        box(ax, x, 0.7, 3.0, 1.0, t, c, fs=9)
        if i < len(steps) - 1:
            arrow(ax, (x + 3.0, 1.2), (x + 3.6, 1.2), color=SLATE, lw=2.2)
        x += 3.6
    ax.text(6, 0.25, "Qdrant (base vectorielle) — socle partagé entre les trois phases",
            ha="center", fontsize=8.5, style="italic", color=SLATE)
    save(fig, "pipeline.png")


def retrieval():
    fig, ax = plt.subplots(figsize=(9.2, 4.6)); ax.axis("off"); ax.set_xlim(0, 10); ax.set_ylim(0, 6)
    box(ax, 0.3, 5.0, 2.4, 0.9, "Requête + expansion\n(RCE, LFI, SQLi…)", DARK, fs=7.8)
    box(ax, 3.4, 5.0, 2.9, 0.9, "Recherche sémantique\nQdrant (top-100)", PRIMARY, fs=8)
    box(ax, 7.0, 5.0, 2.7, 0.9, "Cross-Encoder\nreranking", PURPLE, fs=8)
    arrow(ax, (2.7, 5.45), (3.4, 5.45)); arrow(ax, (6.3, 5.45), (7.0, 5.45))
    # scoring composite
    box(ax, 2.3, 3.1, 5.4, 1.1, "Score composite\nsémantique + lexical\n+ signaux techniques + contexte cible",
        TEAL, fs=7.8)
    arrow(ax, (8.3, 5.0), (6.5, 4.2), color=SLATE)
    for i, (t, c) in enumerate([("payload / CVE\nexploit", ORANGE), ("service / version\nfindings", RED),
                                ("curl / python\nreverse shell", INFO)]):
        box(ax, 0.5 + i * 3.2, 1.5, 2.9, 0.85, t, c, fs=7.3)
        arrow(ax, (2.0 + i * 3.2, 2.35), (4.2, 3.1) if i == 0 else ((5.0, 3.1) if i == 1 else (5.8, 3.1)),
              color=SLATE, ls=":")
    box(ax, 3.4, 0.2, 3.2, 0.85, "Top-5 chunks → contexte", GREEN, fs=8.5)
    arrow(ax, (5.0, 3.1), (5.0, 1.05), color=GREEN, lw=2)
    save(fig, "retrieval.png")


def tiers():
    fig, ax = plt.subplots(figsize=(9.2, 5.0)); ax.axis("off"); ax.set_xlim(0, 10); ax.set_ylim(0, 6)
    box(ax, 3.0, 5.1, 4.0, 0.8, "Résultat RAG (JSON structuré)", DARK, fs=8.5)
    box(ax, 0.4, 3.5, 2.9, 1.1, "Tier 1 — MSF natif\nmodule validé via RPC", GREEN, fs=8)
    box(ax, 3.55, 3.5, 2.9, 1.1, "Tier 2 — SearchSploit\nimport → MSF → exec", ORANGE, fs=8)
    box(ax, 6.7, 3.5, 2.9, 1.1, "Tier 3 — RAG direct\ncurl · script · commandes", RED, fs=8)
    arrow(ax, (4.2, 5.1), (1.85, 4.6), color=SLATE)
    arrow(ax, (5.0, 5.1), (5.0, 4.6), color=SLATE)
    arrow(ax, (5.8, 5.1), (8.15, 4.6), color=SLATE)
    ax.text(1.85, 2.95, "trouvé ?", fontsize=7, color=INFO, ha="center", style="italic")
    arrow(ax, (3.3, 4.05), (3.55, 4.05), color=INFO, ls=":")
    arrow(ax, (6.45, 4.05), (6.7, 4.05), color=INFO, ls=":")
    # HIL gate
    box(ax, 2.8, 1.6, 4.4, 0.95, "Gate HIL / dry-run\nstatut « approved » requis", PURPLE, fs=8.5)
    for x in (1.85, 5.0, 8.15):
        arrow(ax, (x, 3.5), (5.0, 2.55), color=SLATE, ls=":")
    box(ax, 3.4, 0.2, 3.2, 0.9, "Exécution contrôlée", DARK, fs=8.5)
    arrow(ax, (5.0, 1.6), (5.0, 1.1), color=PURPLE, lw=2)
    save(fig, "tiers.png")


def strix_integration():
    fig, ax = plt.subplots(figsize=(10, 3.0)); ax.axis("off"); ax.set_xlim(0, 13); ax.set_ylim(0, 2.6)
    steps = [("Recon Strix\nservice+version", DARK), ("POST /retrieve\ncontexte", PRIMARY),
             ("Gate\n>100c · ≥3 lignes", PURPLE), ("POST /query\nplan JSON", TEAL),
             ("Exécution\npayloads", RED)]
    x = 0.3
    for i, (t, c) in enumerate(steps):
        box(ax, x, 1.0, 2.15, 1.0, t, c, fs=7.8)
        if i < len(steps) - 1:
            arrow(ax, (x + 2.15, 1.5), (x + 2.55, 1.5), color=SLATE, lw=2)
        x += 2.55
    ax.text(6.4, 0.45, "confidence_score : >0.7 exploiter · 0.4–0.7 vérifier · <0.4 recon · timeout 120 s",
            ha="center", fontsize=8, style="italic", color=SLATE)
    save(fig, "strix_integration.png")


for f in [architecture, pipeline, retrieval, tiers, strix_integration]:
    f()
print("DONE")

# -*- coding: utf-8 -*-
"""Construit le rapport PFE (français) — Vultrix Console."""
import os
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

HERE = os.path.dirname(__file__)
FIG = os.path.join(HERE, "figures")
SHOTS = os.path.join(HERE, "screenshots")
NAVY = RGBColor(0x0F, 0x24, 0x2E)
BLUE = RGBColor(0x1E, 0x3A, 0x8A)
GREY = RGBColor(0x47, 0x55, 0x69)

doc = Document()

# ── Styles de base ────────────────────────────────────────────────────────────
normal = doc.styles["Normal"]
normal.font.name = "Calibri"
normal.font.size = Pt(11)
normal.paragraph_format.space_after = Pt(6)
normal.paragraph_format.line_spacing = 1.3
for lvl, sz, col in [("Heading 1", 18, BLUE), ("Heading 2", 14, NAVY), ("Heading 3", 12, GREY)]:
    st = doc.styles[lvl]
    st.font.name = "Calibri"; st.font.size = Pt(sz); st.font.color.rgb = col; st.font.bold = True

# section margins
sec = doc.sections[0]
sec.left_margin = sec.right_margin = Inches(1.0)
sec.top_margin = sec.bottom_margin = Inches(1.0)

_fig_ctr = {}
_tbl_ctr = [0]


def p(text="", size=11, bold=False, italic=False, align=None, color=None, after=6, before=0):
    para = doc.add_paragraph()
    para.paragraph_format.space_after = Pt(after)
    para.paragraph_format.space_before = Pt(before)
    if align:
        para.alignment = align
    r = para.add_run(text)
    r.font.size = Pt(size); r.bold = bold; r.italic = italic
    if color:
        r.font.color.rgb = color
    return para


def h1(text):
    doc.add_page_break()
    doc.add_heading(text, level=1)


def h2(text):
    doc.add_heading(text, level=2)


def h3(text):
    doc.add_heading(text, level=3)


def bullets(items):
    for it in items:
        para = doc.add_paragraph(style="List Bullet")
        para.paragraph_format.space_after = Pt(3)
        if isinstance(it, tuple):
            r = para.add_run(it[0]); r.bold = True
            para.add_run(" " + it[1])
        else:
            para.add_run(it)


def figure(name, chap, caption, width=6.3, base=FIG):
    _fig_ctr[chap] = _fig_ctr.get(chap, 0) + 1
    doc.add_picture(os.path.join(base, name), width=Inches(width))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap = doc.add_paragraph()
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = cap.add_run(f"Figure {chap}.{_fig_ctr[chap]} — {caption}")
    r.italic = True; r.font.size = Pt(9.5); r.font.color.rgb = GREY
    cap.paragraph_format.space_after = Pt(12)


def table(headers, rows, caption=None, widths=None):
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = "Light Grid Accent 1"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr = t.rows[0].cells
    for i, htext in enumerate(headers):
        run = hdr[i].paragraphs[0].add_run(htext)
        run.bold = True; run.font.size = Pt(10)
    for row in rows:
        cells = t.add_row().cells
        for i, val in enumerate(row):
            para = cells[i].paragraphs[0]
            para.add_run(str(val)).font.size = Pt(9.5)
    if widths:
        for row in t.rows:
            for i, w in enumerate(widths):
                row.cells[i].width = Inches(w)
    if caption:
        _tbl_ctr[0] += 1
        cp = doc.add_paragraph()
        cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = cp.add_run(f"Tableau {_tbl_ctr[0]} — {caption}")
        r.italic = True; r.font.size = Pt(9.5); r.font.color.rgb = GREY
    doc.add_paragraph().paragraph_format.space_after = Pt(4)
    return t


def toc_field(title):
    doc.add_heading(title, level=1)
    para = doc.add_paragraph()
    run = para.add_run()
    fldChar = OxmlElement("w:fldChar"); fldChar.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText"); instr.set(qn("xml:space"), "preserve")
    instr.text = 'TOC \\o "1-3" \\h \\z \\u'
    fldSep = OxmlElement("w:fldChar"); fldSep.set(qn("w:fldCharType"), "separate")
    t = OxmlElement("w:t"); t.text = "Faites un clic droit ici → « Mettre à jour les champs » pour générer la table."
    fldEnd = OxmlElement("w:fldChar"); fldEnd.set(qn("w:fldCharType"), "end")
    for el in (fldChar, instr, fldSep, t, fldEnd):
        run._r.append(el)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE DE GARDE
# ══════════════════════════════════════════════════════════════════════════════
p("République Tunisienne", 12, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, after=0)
p("Ministère de l'Enseignement Supérieur et de la Recherche Scientifique", 11, align=WD_ALIGN_PARAGRAPH.CENTER, after=0)
p("Université / École d'Ingénieurs", 11, align=WD_ALIGN_PARAGRAPH.CENTER, after=2)
p("[Nom de l'établissement]", 11, italic=True, align=WD_ALIGN_PARAGRAPH.CENTER, after=18)
p("RAPPORT DE PROJET DE FIN D'ÉTUDES", 15, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, color=BLUE, after=2)
p("En vue de l'obtention du Diplôme National d'Ingénieur", 11, align=WD_ALIGN_PARAGRAPH.CENTER, after=0)
p("Spécialité : Sécurité des Systèmes Informatiques et des Réseaux", 11, italic=True, align=WD_ALIGN_PARAGRAPH.CENTER, after=24)
p("Automatisation avancée des tests d'intrusion par un système d'IA",
  16, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, color=NAVY, after=0)
p("agentique : intégration de Metasploit & RAG et conception d'une",
  16, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, color=NAVY, after=0)
p("console web d'opérations de sécurité (Vultrix Console)",
  16, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, color=NAVY, after=28)
p("Réalisé par : [Nom et Prénom de l'étudiant]", 12, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, after=18)
p("Encadrant académique : [Nom]", 11, align=WD_ALIGN_PARAGRAPH.CENTER, after=0)
p("Encadrant professionnel : [Nom]", 11, align=WD_ALIGN_PARAGRAPH.CENTER, after=24)
p("Année Universitaire 2025 – 2026", 12, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)

# ── Dédicace ──────────────────────────────────────────────────────────────────
doc.add_page_break()
doc.add_heading("Dédicace", level=1)
p("À mes chers parents, pour leur amour inconditionnel, leurs sacrifices et leur confiance "
  "indéfectible qui ont été ma plus grande source de force tout au long de ce parcours.", italic=True)
p("À ma famille et à mes proches, pour leur soutien constant et leurs encouragements.", italic=True)
p("À mes enseignants et encadrants, pour la qualité de leur accompagnement et la rigueur "
  "qu'ils m'ont transmise.", italic=True)
p("À mes amis et camarades, pour tous les moments partagés qui ont donné du sens à cette expérience.", italic=True)

# ── Remerciements ─────────────────────────────────────────────────────────────
doc.add_page_break()
doc.add_heading("Remerciements", level=1)
p("Au terme de ce travail, je tiens à exprimer ma profonde gratitude à toutes les personnes qui "
  "ont contribué, de près ou de loin, à l'aboutissement de ce projet de fin d'études.")
p("Je remercie chaleureusement mon encadrant académique pour sa disponibilité, ses conseils "
  "avisés et son suivi rigoureux, ainsi que mon encadrant professionnel pour la confiance "
  "qu'il m'a accordée et pour le cadre technique stimulant qu'il a su instaurer.")
p("Mes remerciements s'adressent également aux membres du jury pour l'honneur qu'ils me font "
  "en acceptant d'évaluer ce travail, ainsi qu'à l'ensemble du corps enseignant pour la "
  "formation de qualité dont j'ai bénéficié.")

# ── Résumé / Abstract ─────────────────────────────────────────────────────────
doc.add_page_break()
doc.add_heading("Résumé", level=1)
p("Ce projet de fin d'études porte sur l'automatisation avancée des tests d'intrusion à l'aide "
  "d'un système d'intelligence artificielle agentique fondé sur des grands modèles de langage "
  "(LLM). Le travail s'articule autour de deux contributions complémentaires. La première consiste "
  "à enrichir le moteur agentique open-source Strix en y intégrant le framework d'exploitation "
  "Metasploit et un service de connaissances RAG (Retrieval-Augmented Generation) : un outil "
  "unique et déterministe, exploit_research, interroge la base RAG puis recherche un module "
  "Metasploit et produit une recommandation « module d'abord », réduisant la charge de décision "
  "confiée au modèle. La seconde contribution est la conception et la réalisation d'une console "
  "web professionnelle, Vultrix Console, offrant l'authentification forte "
  "(cookies httpOnly, CSRF, MFA TOTP), un contrôle d'accès par rôles (RBAC), le pilotage et le "
  "suivi temps réel des campagnes (WebSocket), la visualisation de la sortie du moteur, une phase "
  "de post-exploitation, le triage des vulnérabilités, la comparaison de scans, la planification "
  "récurrente, l'export de rapports et un journal d'audit inaltérable. La plateforme, développée "
  "avec Next.js et FastAPI, a été validée par 39 tests automatisés et vérifiée de bout en bout.")
p("Mots-clés : ", bold=True, after=0)
p("tests d'intrusion, IA agentique, LLM, Metasploit, RAG, Strix, RBAC, MFA, FastAPI, Next.js, "
  "sécurité applicative.", italic=True)
doc.add_heading("Abstract", level=1)
p("This graduation project addresses the advanced automation of penetration testing using an "
  "agentic AI system based on Large Language Models (LLMs). It delivers two complementary "
  "contributions. First, it augments the open-source Strix agentic engine with the Metasploit "
  "exploitation framework and a Retrieval-Augmented Generation (RAG) knowledge service: a single "
  "deterministic tool, exploit_research, queries the RAG, searches Metasploit and returns a "
  "module-first recommendation, offloading decision complexity from the model. Second, it designs "
  "and builds a professional, Vultrix Console, providing strong "
  "authentication (httpOnly cookies, CSRF, TOTP MFA), role-based access control, real-time "
  "assessment orchestration (WebSocket), engine-output visualisation, a post-exploitation phase, "
  "findings triage, scan diffing, recurring scheduling, report export and a tamper-evident audit "
  "trail. Built with Next.js and FastAPI, the platform is covered by 39 automated tests and "
  "verified end-to-end.")
p("Keywords: ", bold=True, after=0)
p("penetration testing, agentic AI, LLM, Metasploit, RAG, Strix, RBAC, MFA, FastAPI, Next.js.", italic=True)

# ── Table des matières + listes ───────────────────────────────────────────────
doc.add_page_break()
toc_field("Table des matières")

doc.add_page_break()
doc.add_heading("Liste des figures", level=1)
figs = [
    "Figure 1.1 — Planning du projet (méthodologie itérative par phases)",
    "Figure 2.1 — Handoff d'exploitation : RAG + Metasploit (priorité au module)",
    "Figure 3.1 — Architecture globale de la plateforme Vultrix Console",
    "Figure 3.2 — Diagramme de cas d'utilisation",
    "Figure 3.3 — Diagramme de séquence : exécution d'un test",
    "Figure 3.4 — Matrice RBAC : permissions par rôle système",
    "Figure 4.1 — Pipeline d'évaluation en 5 phases",
    "Figure 5.1 — Page de connexion sécurisée (MFA)",
    "Figure 5.2 — Tableau de bord",
    "Figure 5.3 — Détail d'une campagne : pipeline, post-exploitation et triage",
    "Figure 5.4 — Écran de sortie du moteur (arbre d'agents, télémétrie, console)",
    "Figure 5.5 — Planification de tests récurrents",
    "Figure 5.6 — Gestion des rôles et permissions (RBAC)",
    "Figure 5.7 — Couverture de tests par module",
    "Figure 5.8 — Répartition des vulnérabilités par sévérité",
    "Figure 5.9 — Analyse comparative : approche manuelle vs plateforme",
]
for f in figs:
    doc.add_paragraph(f, style="List Bullet").paragraph_format.space_after = Pt(2)

doc.add_heading("Liste des tableaux", level=1)
for t in ["Tableau 1 — Besoins fonctionnels principaux",
          "Tableau 2 — Besoins non fonctionnels",
          "Tableau 3 — Pile technologique du projet",
          "Tableau 4 — Modèle de données (principales tables)",
          "Tableau 5 — Synthèse des résultats de validation"]:
    doc.add_paragraph(t, style="List Bullet").paragraph_format.space_after = Pt(2)

doc.add_heading("Liste des abréviations", level=1)
table(["Abréviation", "Signification"], [
    ["LLM", "Large Language Model (grand modèle de langage)"],
    ["RAG", "Retrieval-Augmented Generation"],
    ["RBAC", "Role-Based Access Control (contrôle d'accès par rôles)"],
    ["MFA / TOTP", "Multi-Factor Authentication / Time-based One-Time Password"],
    ["CSRF", "Cross-Site Request Forgery"],
    ["API", "Application Programming Interface"],
    ["WS", "WebSocket"],
    ["CVE", "Common Vulnerabilities and Exposures"],
    ["ORM", "Object-Relational Mapping"],
    ["CI/CD", "Continuous Integration / Continuous Deployment"],
], widths=[1.6, 4.7])

# ══════════════════════════════════════════════════════════════════════════════
# INTRODUCTION GÉNÉRALE
# ══════════════════════════════════════════════════════════════════════════════
h1("Introduction générale")
p("La transformation numérique des organisations s'accompagne d'une surface d'attaque en "
  "expansion permanente. Les tests d'intrusion (penetration testing) constituent l'un des "
  "moyens les plus efficaces pour évaluer, de façon offensive et contrôlée, la robustesse "
  "d'un système d'information. Toutefois, réalisés manuellement, ils demeurent coûteux en "
  "temps, difficilement reproductibles et fortement dépendants de l'expertise de l'opérateur.")
p("L'émergence des grands modèles de langage (LLM) et des architectures dites « agentiques » "
  "ouvre la voie à une automatisation intelligente de ce processus : des agents autonomes "
  "planifient, exécutent et enchaînent des actions offensives en s'appuyant sur des outils "
  "réels. Le moteur open-source Strix illustre cette approche. Néanmoins, deux limites "
  "subsistent : d'une part, la phase d'exploitation reste fragile lorsqu'elle est entièrement "
  "confiée au raisonnement du modèle ; d'autre part, l'usage en équipe manque d'une interface "
  "d'opérations sécurisée offrant gouvernance, traçabilité et pilotage.")
p("Ce projet répond à ces deux limites. Il intègre au moteur Strix le framework Metasploit et "
  "un service de connaissances RAG au travers d'un outil déterministe unique, puis conçoit et "
  "réalise une console web professionnelle, Vultrix Console, dédiée à l'orchestration et au suivi "
  "des campagnes de sécurité.")
p("Le présent rapport est organisé en cinq chapitres. Le premier présente le cadre général du "
  "projet et la méthodologie adoptée. Le deuxième dresse un état de l'art des tests d'intrusion "
  "et de leur automatisation par IA. Le troisième détaille la conception et l'architecture. Le "
  "quatrième décrit les technologies et la réalisation. Le cinquième expose les tests et "
  "l'évaluation. Une conclusion générale synthétise les apports et ouvre des perspectives.")

# ══════════════════════════════════════════════════════════════════════════════
# CHAPITRE 1
# ══════════════════════════════════════════════════════════════════════════════
h1("Chapitre 1 — Cadre général du projet")
h2("1.1 Introduction")
p("Ce chapitre situe le projet dans son contexte, formule la problématique, présente la solution "
  "proposée et décrit la méthodologie de gestion adoptée pour mener le développement.")

h2("1.2 Contexte et problématique")
p("Le pentest manuel souffre de plusieurs limites structurelles : durée d'exécution élevée, "
  "dépendance à l'expertise humaine, faible reproductibilité et difficulté de traçabilité. "
  "Les plateformes d'automatisation par IA agentique, comme Strix, apportent une réponse "
  "prometteuse mais présentent, en l'état, deux insuffisances :")
bullets([
    ("Exploitation fragile — ", "en confiant l'intégralité de la décision d'exploitation au LLM, "
     "l'agent peut échouer à sélectionner ou paramétrer correctement un exploit, faute d'accès "
     "structuré à une base de connaissances et à un arsenal éprouvé."),
    ("Absence d'interface d'opérations — ", "l'outil est piloté en ligne de commande, sans "
     "gestion des utilisateurs, sans contrôle d'accès, sans suivi temps réel ni gouvernance, "
     "ce qui limite l'usage collaboratif et la valeur opérationnelle en entreprise."),
])
p("La problématique retenue peut ainsi se formuler : comment fiabiliser la phase d'exploitation "
  "d'un agent de pentest fondé sur un LLM, et comment en faire un service d'opérations de "
  "sécurité sûr, gouverné et exploitable en équipe ?")

h2("1.3 Solution proposée")
p("La solution se décline en deux volets complémentaires :")
bullets([
    ("Volet 1 — Fiabilisation de l'exploitation. ", "Intégration de Metasploit et d'un service "
     "RAG dans le moteur Strix via un outil unique et déterministe, exploit_research, qui "
     "interroge le RAG, recherche un module Metasploit et renvoie une recommandation « module "
     "d'abord ». La logique de décision est déplacée du modèle vers du code Python vérifiable."),
    ("Volet 2 — Console d'opérations. ", "Conception d'une application web, Vultrix Console, "
     "offrant authentification forte, RBAC, pilotage et suivi temps réel des campagnes, "
     "visualisation de la sortie du moteur, post-exploitation, triage, comparaison de scans, "
     "planification récurrente, reporting et audit inaltérable."),
])

h2("1.4 Méthodologie de gestion de projet")
p("Le développement a suivi une démarche itérative et incrémentale, organisée en phases "
  "successives livrant chacune un incrément fonctionnel testé et vérifié. Cette approche, "
  "proche de Scrum/Kanban, a permis de sécuriser les fondations avant d'empiler les "
  "fonctionnalités, tout en conservant une application exécutable à chaque étape.")
bullets([
    ("Intégration Metasploit + RAG — ", "outil exploit_research, playbooks et tests."),
    ("Phase 0 (Fondations) — ", "couche de données asynchrone, migrations, files et harnais de tests."),
    ("Phase 1 (Authentification) — ", "cookies httpOnly, CSRF, MFA TOTP, RBAC, sessions, audit."),
    ("Phase 2 (Temps réel) — ", "WebSocket, réconciliation des exécutions orphelines."),
    ("Phase 3 (Sortie moteur) — ", "arbre d'agents, console live, télémétrie (jetons, coût)."),
    ("Phase 4 (Post-exploitation) — ", "5ᵉ phase du pipeline et événements typés."),
    ("Phase 5 (Domaine) — ", "triage, comparaison de scans, alertes, planification récurrente."),
    ("Phase 6 (Qualité) — ", "palette de commandes ⌘K, observabilité, durcissement."),
])
figure("gantt.png", 1, "Planning du projet (méthodologie itérative par phases).")

h2("1.5 Conclusion")
p("Ce chapitre a défini le cadre, la problématique et la trajectoire du projet. Le chapitre "
  "suivant établit l'état de l'art sur lequel s'appuient les choix de conception.")

# ══════════════════════════════════════════════════════════════════════════════
# CHAPITRE 2
# ══════════════════════════════════════════════════════════════════════════════
h1("Chapitre 2 — État de l'art")
h2("2.1 Introduction")
p("Ce chapitre présente les fondements des tests d'intrusion, les approches d'automatisation "
  "par IA agentique et les briques techniques mobilisées (Strix, Metasploit, RAG), afin de "
  "positionner la contribution du projet.")

h2("2.2 Tests d'intrusion et Red Teaming")
p("Un test d'intrusion reproduit, de manière autorisée et méthodique, le comportement d'un "
  "attaquant afin d'identifier et de démontrer des vulnérabilités exploitables. Le cycle de vie "
  "standard comprend la reconnaissance, l'évaluation des vulnérabilités, l'exploitation, la "
  "post-exploitation puis la rédaction du rapport. Le Red Teaming étend cette démarche à une "
  "simulation d'adversaire plus réaliste et furtive.")

h2("2.3 Automatisation par IA agentique et LLM")
p("Un système « agentique » orchestre un ou plusieurs agents fondés sur un LLM capables de "
  "raisonner, de décomposer une tâche, d'appeler des outils et d'itérer à partir des retours "
  "d'exécution. Appliqué au pentest, ce paradigme automatise la planification et l'enchaînement "
  "des actions offensives. Des travaux comme PentestGPT ou AutoGPT ont démontré la faisabilité "
  "de cette approche, tout en révélant ses limites : hallucinations, décisions d'exploitation "
  "peu fiables et besoin d'un ancrage dans des connaissances vérifiées.")

h2("2.4 Briques mobilisées")
bullets([
    ("Strix — ", "moteur multi-agent open-source de pentest ; un CLI côté hôte orchestre des "
     "agents qui exécutent des outils dans un bac à sable Docker (Kali)."),
    ("Metasploit Framework — ", "arsenal d'exploitation de référence ; ses modules apportent "
     "vérification non destructive (check), gestion des cas limites et sessions structurées."),
    ("RAG (Retrieval-Augmented Generation) — ", "service qui indexe des connaissances "
     "d'exploitation et fournit, sur requête, un contexte et un guidage ancrés dans des "
     "documents réels plutôt que dans la seule mémoire du modèle."),
])
p("La combinaison de ces briques permet d'ancrer le raisonnement de l'agent (RAG) tout en "
  "privilégiant un exécuteur éprouvé (Metasploit) lorsqu'un module existe.")
figure("exploit_handoff.png", 2, "Handoff d'exploitation : RAG puis Metasploit, avec priorité au module.")

h2("2.5 Positionnement du projet")
p("Par rapport à l'existant, la contribution est double : (i) rendre l'exploitation déterministe "
  "en collapsant le protocole RAG + Metasploit dans un outil unique dont la décision est codée "
  "en Python ; (ii) doter la plateforme d'une console d'opérations sécurisée, absente des outils "
  "comparables, apportant gouvernance, temps réel et traçabilité.")

h2("2.6 Conclusion")
p("L'état de l'art confirme la pertinence d'une approche hybride « IA agentique + arsenal "
  "éprouvé » et l'intérêt d'une interface d'opérations. Le chapitre suivant en présente la "
  "conception.")

# ══════════════════════════════════════════════════════════════════════════════
# CHAPITRE 3
# ══════════════════════════════════════════════════════════════════════════════
h1("Chapitre 3 — Conception & Architecture")
h2("3.1 Introduction")
p("Ce chapitre décrit l'architecture globale, les besoins fonctionnels et non fonctionnels, "
  "les diagrammes UML, le modèle de données et la conception de la sécurité.")

h2("3.2 Architecture globale")
p("La plateforme adopte une architecture trois tiers. Le client (Next.js) communique en même "
  "origine avec un serveur Next.js qui relaie les appels /api/* vers un backend FastAPI "
  "asynchrone. Ce dernier expose les services métier, persiste les données dans PostgreSQL "
  "(SQLite en développement) et pilote le moteur Strix, lequel s'appuie sur Metasploit et le "
  "service RAG. Redis fournit files et cache.")
figure("architecture.png", 3, "Architecture globale de la plateforme Vultrix Console.")

h2("3.3 Besoins")
h3("3.3.1 Acteurs")
p("Quatre rôles système sont définis, du moins au plus privilégié : Observateur (lecture seule), "
  "Analyste (création et exécution de tests, triage, export), Manager (supervision de toutes les "
  "campagnes, audit, lecture des utilisateurs) et Administrateur (accès complet).")
h3("3.3.2 Besoins fonctionnels")
table(["Réf.", "Besoin fonctionnel"], [
    ["BF1", "S'authentifier avec cookies sécurisés et second facteur (MFA TOTP)"],
    ["BF2", "Gérer les utilisateurs, les rôles et les permissions (RBAC)"],
    ["BF3", "Créer, lancer, annuler et supprimer un test d'intrusion"],
    ["BF4", "Suivre en temps réel le pipeline (état, phases, journal)"],
    ["BF5", "Visualiser la sortie du moteur (arbre d'agents, télémétrie, console)"],
    ["BF6", "Trier les vulnérabilités (statut, gravité, assignation)"],
    ["BF7", "Comparer deux scans d'une même cible (nouveaux / corrigés)"],
    ["BF8", "Planifier des tests récurrents (cron)"],
    ["BF9", "Exporter des rapports (PDF, CSV, JSON)"],
    ["BF10", "Consulter l'assistant IA et le journal d'audit"],
], caption="Besoins fonctionnels principaux.", widths=[0.9, 5.4])
h3("3.3.3 Besoins non fonctionnels")
table(["Réf.", "Besoin non fonctionnel"], [
    ["BNF1", "Sécurité : jetons httpOnly, protection CSRF, MFA, en-têtes de sécurité"],
    ["BNF2", "Performance : backend asynchrone, temps réel via WebSocket"],
    ["BNF3", "Traçabilité : journal d'audit inaltérable (chaîné par hachage)"],
    ["BNF4", "Fiabilité : réconciliation des exécutions, tests automatisés"],
    ["BNF5", "Maintenabilité : migrations versionnées, séparation claire des couches"],
    ["BNF6", "Observabilité : identifiants de requête, sondes /readyz et /livez"],
], caption="Besoin non fonctionnels.", widths=[0.9, 5.4])

h2("3.4 Diagrammes UML")
h3("3.4.1 Diagramme de cas d'utilisation")
figure("usecase.png", 3, "Diagramme de cas d'utilisation de la plateforme.")
h3("3.4.2 Diagramme de séquence — exécution d'un test")
p("Le scénario nominal d'exécution d'un test illustre l'enchaînement entre l'utilisateur, le "
  "frontend, l'API, le moteur et la base de données, ainsi que la diffusion des événements "
  "temps réel via WebSocket.")
figure("seq_run.png", 3, "Diagramme de séquence : exécution d'un test.")

h2("3.5 Modèle de données")
p("Le modèle relationnel s'organise autour des entités suivantes, gérées via l'ORM SQLAlchemy "
  "2.0 et versionnées par Alembic.")
table(["Table", "Rôle"], [
    ["users / roles / role_permissions", "Comptes, rôles et permissions (RBAC)"],
    ["user_sessions", "Sessions serveur (rotation, détection de réutilisation)"],
    ["assessments / findings", "Campagnes et vulnérabilités découvertes"],
    ["post_ex_events", "Événements de post-exploitation (session, privesc, exfil…)"],
    ["schedules", "Définitions de tests récurrents (cron)"],
    ["log_entries / audit_events", "Journaux d'exécution et journal d'audit chaîné"],
    ["reports / chat_sessions / chat_messages", "Rapports et conversations de l'assistant"],
], caption="Modèle de données (principales tables).", widths=[2.6, 3.7])

h2("3.6 Conception de la sécurité")
p("La sécurité repose sur une authentification par cookies httpOnly (jeton d'accès non lisible "
  "en JavaScript), une protection CSRF par double soumission, un second facteur TOTP obligatoire "
  "pour les rôles à privilèges, une rotation des jetons de rafraîchissement avec détection de "
  "réutilisation, ainsi qu'un contrôle d'accès par rôles appliqué à chaque endpoint.")
figure("rbac.png", 3, "Matrice RBAC : permissions accordées par rôle système.")

h2("3.7 Conclusion")
p("La conception établit une base sûre et modulaire. Le chapitre suivant décrit les technologies "
  "retenues et la réalisation.")

# ══════════════════════════════════════════════════════════════════════════════
# CHAPITRE 4
# ══════════════════════════════════════════════════════════════════════════════
h1("Chapitre 4 — Technologies & Réalisation")
h2("4.1 Introduction")
p("Ce chapitre présente la pile technologique, l'intégration Metasploit + RAG et la réalisation "
  "du backend et du frontend.")

h2("4.2 Pile technologique")
table(["Couche", "Technologies"], [
    ["Frontend", "Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS, Recharts"],
    ["Backend", "FastAPI (async), SQLAlchemy 2.0, Pydantic v2, Uvicorn"],
    ["Sécurité", "Argon2, PyJWT, pyotp (TOTP), slowapi (rate-limit)"],
    ["Données", "PostgreSQL (asyncpg) / SQLite (aiosqlite), Alembic, Redis"],
    ["Planification", "APScheduler, croniter"],
    ["Moteur", "Strix (CLI multi-agent), Docker, Kali Linux, Metasploit, RAG"],
    ["Qualité", "pytest, ruff, GitHub Actions (CI)"],
], caption="Pile technologique du projet.", widths=[1.7, 4.6])

h2("4.3 Intégration Metasploit & RAG (exploit_research)")
p("L'intégration transforme un protocole multi-étapes en un unique appel d'outil déterministe. "
  "Dès que la reconnaissance fournit un service, une version ou une CVE, l'agent invoque "
  "exploit_research, qui : (1) interroge le RAG (/retrieve puis, après un portail de pertinence, "
  "/query) en contournant le proxy et avec un délai adapté ; (2) recherche un module via "
  "msfconsole ; (3) détecte l'adresse LHOST du bac à sable ; (4) produit une recommandation "
  "déterministe privilégiant le module Metasploit lorsqu'il existe, et retombant sur le payload "
  "RAG sinon. La logique de décision est ainsi codée et testée, et non laissée au modèle.")
p("Extrait — construction de la commande du moteur avec instruction optionnelle :", after=2)
code = doc.add_paragraph()
code.paragraph_format.left_indent = Inches(0.3)
cr = code.add_run('cmd = ["strix", "--target", target, "--non-interactive",\n'
                  '       "--scan-mode", mode]\n'
                  'if instruction:\n'
                  '    cmd += ["--instruction", instruction]')
cr.font.name = "Consolas"; cr.font.size = Pt(9.5)

h2("4.4 Réalisation du backend")
bullets([
    ("Authentification & RBAC — ", "connexion par cookies, MFA TOTP, sessions serveur avec "
     "rotation et détection de réutilisation, permissions resource:action vérifiées par dépendance."),
    ("Pipeline d'évaluation — ", "création, lancement, annulation ; exécution en tâche de fond "
     "et diffusion d'événements d'état, de journaux et de vulnérabilités."),
    ("Temps réel — ", "bus d'événements interne pontant le runner (thread) vers les abonnés "
     "WebSocket ; réconciliation au démarrage des exécutions orphelines."),
    ("Triage & comparaison — ", "mise à jour du statut, de la gravité et de l'assignation d'une "
     "vulnérabilité ; comparaison des vulnérabilités entre deux scans d'une même cible."),
    ("Planification — ", "APScheduler déclenche des tests récurrents selon une expression cron ; "
     "calcul de la prochaine occurrence via croniter."),
    ("Observabilité — ", "middleware d'identifiant de requête, sondes /readyz (base + moteur) et "
     "/livez ; journal d'audit inaltérable chaîné par hachage."),
])
figure("pipeline.png", 4, "Pipeline d'évaluation en 5 phases (dont la post-exploitation).", width=6.5)

h2("4.5 Réalisation du frontend")
p("Le frontend, en Next.js (App Router), propose des modules dédiés : tableau de bord (statistiques "
  "et graphiques), campagnes et vue de détail (pipeline live, console, post-exploitation, triage, "
  "comparaison), rapports, journaux, audit, utilisateurs, rôles, planification, assistant IA et "
  "paramètres. Une palette de commandes (⌘K) offre une navigation rapide filtrée par permissions. "
  "L'interface est responsive, thématisable (clair/sombre) et cohérente grâce à un système de "
  "composants réutilisables.")

h2("4.6 Conclusion")
p("La réalisation couvre l'ensemble des besoins définis, du moteur enrichi à la console "
  "d'opérations. Le chapitre suivant en évalue la qualité.")

# ══════════════════════════════════════════════════════════════════════════════
# CHAPITRE 5
# ══════════════════════════════════════════════════════════════════════════════
h1("Chapitre 5 — Tests & Évaluation")
h2("5.1 Introduction")
p("Ce chapitre présente l'environnement de test, la validation fonctionnelle, la couverture de "
  "tests et une analyse comparative avec l'approche manuelle.")

h2("5.2 Environnement de test")
p("Les essais ont été menés sur un poste Windows 11 avec Docker Desktop, l'intégration ayant été "
  "validée sur une image de bac à sable Kali contenant Metasploit, contre une cible vulnérable "
  "de type application Drupal. Le backend a été exécuté en mode asynchrone (SQLite en "
  "développement, PostgreSQL en cible), le frontend via le serveur de développement Next.js.")

h2("5.3 Validation fonctionnelle")
p("Chaque incrément a fait l'objet d'une vérification de bout en bout : connexion par cookies et "
  "MFA, application effective du RBAC (retour 403 pour un observateur sur une action "
  "d'administration), exécution et suivi temps réel d'une campagne, visualisation de la sortie du "
  "moteur avec télémétrie réelle (par exemple 6 requêtes LLM et 68 542 jetons sur une exécution), "
  "triage d'une vulnérabilité, comparaison de scans, planification récurrente et export de "
  "rapports. Côté intégration moteur, exploit_research a produit, sur une cible Drupal, une "
  "recommandation ancrée (CVE-2018-7600, Drupalgeddon2) avec sélection du module Metasploit.")
p("Les captures d'écran ci-dessous illustrent les principales vues de l'interface réalisée.", after=8)

figure("login.png", 5, "Page de connexion sécurisée (cookies httpOnly, étape MFA).", width=4.4, base=SHOTS)
figure("dashboard.png", 5, "Tableau de bord : statistiques, activité et répartition des vulnérabilités.", width=6.5, base=SHOTS)
figure("assessment_detail.png", 5, "Détail d'une campagne : pipeline en 5 phases, post-exploitation et triage des vulnérabilités.", width=5.3, base=SHOTS)
figure("engine_output.png", 5, "Écran de sortie du moteur : arbre d'agents, télémétrie (jetons, coût) et console live.", width=6.5, base=SHOTS)
figure("schedules.png", 5, "Planification de tests récurrents (expression cron, prochaine exécution).", width=6.5, base=SHOTS)
figure("roles.png", 5, "Gestion des rôles et des permissions (RBAC).", width=6.5, base=SHOTS)

h2("5.4 Couverture de tests")
p("La plateforme est couverte par un harnais de tests automatisés (pytest) exécuté en intégration "
  "continue, complété par des vérifications navigateur. L'ensemble des tests est au vert.")
figure("tests.png", 5, "Couverture de tests par module (39 tests, 100 % réussis).", width=6.2)

h2("5.5 Résultats et analyse comparative")
p("À titre illustratif, la répartition des vulnérabilités par gravité sur une campagne de "
  "démonstration est présentée ci-dessous, suivie d'une analyse comparative qualitative entre "
  "un pentest manuel et l'usage de la plateforme.")
figure("severity.png", 5, "Répartition des vulnérabilités par sévérité (campagne de démonstration).", width=4.4)
figure("comparison.png", 5, "Analyse comparative : approche manuelle vs plateforme.", width=6.3)
table(["Critère", "Résultat"], [
    ["Tests automatisés", "39 tests, 100 % réussis"],
    ["Analyse statique (ruff)", "Aucune erreur"],
    ["Build frontend", "14+ routes compilées, 0 vulnérabilité npm"],
    ["Sécurité", "Cookies httpOnly, CSRF, MFA, RBAC, audit chaîné vérifiés"],
    ["Temps réel", "WebSocket : état, journaux et vulnérabilités diffusés"],
    ["Intégration moteur", "exploit_research validé (RAG + module Metasploit)"],
], caption="Synthèse des résultats de validation.", widths=[2.5, 3.8])

h2("5.6 Limites et perspectives")
bullets([
    ("Ordonnanceur mono-processus — ", "APScheduler s'exécute en processus unique ; un "
     "déploiement multi-workers nécessiterait un processus d'ordonnancement dédié."),
    ("Runner en thread — ", "l'exécution des scans s'appuie sur un thread interne ; une "
     "extraction vers un worker RQ dédié améliorerait la durabilité."),
    ("Perspectives — ", "pièces jointes de preuve, scans multi-cibles, intégrations "
     "(Jira, SIEM), cartographie CVSS/CWE/OWASP, client TypeScript généré depuis l'OpenAPI."),
])

h2("5.7 Conclusion")
p("L'évaluation confirme la robustesse fonctionnelle et la qualité de la plateforme, ainsi que "
  "la valeur de l'intégration Metasploit + RAG. Les limites identifiées ouvrent des pistes "
  "d'amélioration claires.")

# ══════════════════════════════════════════════════════════════════════════════
# CONCLUSION GÉNÉRALE
# ══════════════════════════════════════════════════════════════════════════════
h1("Conclusion générale")
p("Ce projet de fin d'études a abordé l'automatisation avancée des tests d'intrusion par un "
  "système d'IA agentique fondé sur des LLM, en apportant deux contributions complémentaires. "
  "La première fiabilise la phase la plus délicate — l'exploitation — en intégrant Metasploit et "
  "un service RAG au moteur Strix via un outil déterministe unique, exploit_research, qui déplace "
  "la décision du modèle vers du code vérifiable et privilégie un exécuteur éprouvé.")
p("La seconde transforme un outil en ligne de commande en une véritable console "
  "d'opérations de sécurité, Vultrix Console, dotée d'une authentification forte, "
  "d'un contrôle d'accès par rôles, d'un suivi temps réel, d'une visualisation de la sortie du "
  "moteur, d'une phase de post-exploitation, du triage des vulnérabilités, de la comparaison de "
  "scans, de la planification récurrente, du reporting et d'un journal d'audit inaltérable. "
  "L'ensemble, développé avec Next.js et FastAPI, a été validé par 39 tests automatisés et "
  "vérifié de bout en bout.")
p("Au-delà des résultats obtenus, ce travail confirme la pertinence d'une approche hybride "
  "associant l'autonomie des agents IA à la robustesse d'outils éprouvés, encadrée par une "
  "plateforme sûre et gouvernée. Les perspectives — extraction du runner vers une file durable, "
  "intégrations métier (Jira, SIEM), cartographie normative des vulnérabilités et génération "
  "automatique du client d'API — dessinent une évolution naturelle vers un produit d'entreprise.")

# ── Bibliographie / Webographie ───────────────────────────────────────────────
h1("Bibliographie & Webographie")
refs = [
    "Strix — Moteur multi-agent open-source de tests d'intrusion. https://github.com/usestrix/strix",
    "Rapid7 — Metasploit Framework. https://www.metasploit.com",
    "OWASP — Web Security Testing Guide et OWASP Top 10. https://owasp.org",
    "PentestGPT — LLM-driven penetration testing. Travaux de recherche associés.",
    "FastAPI — Framework web asynchrone Python. https://fastapi.tiangolo.com",
    "Next.js — Framework React (App Router). https://nextjs.org",
    "SQLAlchemy 2.0 — ORM Python. https://www.sqlalchemy.org",
    "APScheduler — Ordonnancement de tâches en Python. https://apscheduler.readthedocs.io",
    "MITRE — Common Vulnerabilities and Exposures (CVE). https://cve.mitre.org",
    "Retrieval-Augmented Generation (RAG) — Lewis et al., 2020.",
]
for i, r in enumerate(refs, 1):
    para = doc.add_paragraph()
    para.paragraph_format.space_after = Pt(4)
    para.add_run(f"[{i}] ").bold = True
    para.add_run(r)

out = os.path.join(HERE, "Rapport_PFE_Vultrix_Console.docx")
doc.save(out)
print("SAVED:", out)
print("Paragraphs:", len(doc.paragraphs))

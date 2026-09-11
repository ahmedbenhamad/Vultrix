# -*- coding: utf-8 -*-
"""DOCX -> PDF (LibreOffice) puis rend des pages en PNG (PyMuPDF) pour vérification."""
import os
import subprocess
import sys

HERE = os.path.dirname(__file__)
DOCX = os.path.join(HERE, "Rapport_Technique_Pentest_RAG.docx")
PDF = os.path.join(HERE, "Rapport_Technique_Pentest_RAG.pdf")
SOFFICE = r"C:\Program Files\LibreOffice\program\soffice.exe"

subprocess.run([SOFFICE, "--headless", "--convert-to", "pdf", "--outdir", HERE, DOCX],
               check=True, timeout=180)
print("PDF:", PDF, "exists:", os.path.exists(PDF))

import fitz  # noqa: E402
doc = fitz.open(PDF)
print("PDF pages:", doc.page_count)
outdir = os.path.join(HERE, "preview")
os.makedirs(outdir, exist_ok=True)
pages = [int(x) for x in (sys.argv[1:] or ["1", "7", "9", "13"])]
for pno in pages:
    if 1 <= pno <= doc.page_count:
        doc[pno - 1].get_pixmap(dpi=110).save(os.path.join(outdir, f"page-{pno:02d}.png"))
        print("wrote page", pno)

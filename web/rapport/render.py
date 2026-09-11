# -*- coding: utf-8 -*-
"""Convertit le rapport .docx en PDF (LibreOffice) puis rend quelques pages en PNG (PyMuPDF)."""
import os
import subprocess
import sys

HERE = os.path.dirname(__file__)
DOCX = os.path.join(HERE, "Rapport_PFE_Strix_Console.docx")
PDF = os.path.join(HERE, "Rapport_PFE_Strix_Console.pdf")
SOFFICE = r"C:\Program Files\LibreOffice\program\soffice.exe"

# 1) DOCX -> PDF via LibreOffice headless
subprocess.run(
    [SOFFICE, "--headless", "--convert-to", "pdf", "--outdir", HERE, DOCX],
    check=True, timeout=180,
)
print("PDF:", PDF, "exists:", os.path.exists(PDF))

# 2) PDF -> PNG (pages demandées) via PyMuPDF
import fitz  # noqa: E402

pages = [int(x) for x in (sys.argv[1:] or ["1", "9", "15", "21"])]
doc = fitz.open(PDF)
print("PDF pages:", doc.page_count)
outdir = os.path.join(HERE, "preview")
os.makedirs(outdir, exist_ok=True)
for pno in pages:
    if 1 <= pno <= doc.page_count:
        pix = doc[pno - 1].get_pixmap(dpi=110)
        out = os.path.join(outdir, f"page-{pno:02d}.png")
        pix.save(out)
        print("wrote", out)

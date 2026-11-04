"""Render report/report.md to report/report.pdf with Chrome (Arabic-capable fonts)."""
import os
import shutil
import subprocess
import sys
from pathlib import Path

import markdown

here = Path(__file__).resolve().parent
html = markdown.markdown((here / "report.md").read_text(encoding="utf-8"), extensions=["tables"])
css = """
@page { size: A4; margin: 16mm 15mm; }
body { font-family: 'Noto Sans','DejaVu Sans',sans-serif; font-size: 9.6pt; line-height: 1.38; color: #111; }
h1 { font-size: 17pt; margin: 0 0 4pt; } h2 { font-size: 11.5pt; margin: 12pt 0 3pt; border-bottom: 1px solid #bbb; }
table { border-collapse: collapse; width: 100%; margin: 5pt 0; font-size: 8.6pt; }
th, td { border: 1px solid #bbb; padding: 2.5pt 4pt; vertical-align: top; } th { background: #eef1f4; text-align: left; }
code { font-size: 8.6pt; background: #f2f2f2; padding: 0 2pt; } p { margin: 4pt 0; } ul { margin: 3pt 0 3pt 14pt; padding: 0; }
"""
out = here / "report.html"
out.write_text(f"<!doctype html><meta charset='utf-8'><style>{css}</style>{html}", encoding="utf-8")
# Chrome's name differs by OS; CHROME=<path> overrides
chrome = os.getenv("CHROME") or next(
    (c for c in ("google-chrome", "chromium", "chrome", r"C:\Program Files\Google\Chrome\Application\chrome.exe")
     if shutil.which(c) or Path(c).exists()), "google-chrome")
subprocess.run([chrome, "--headless=new", "--no-sandbox", "--disable-gpu", "--no-pdf-header-footer",
                f"--print-to-pdf={here / 'report.pdf'}", out.as_uri()], check=True, capture_output=True)
out.unlink()
print("wrote", here / "report.pdf")

#!/usr/bin/env python3
"""Converte os HTML de out/<data>/ em PDF (A4 paisagem) com o Chromium do Playwright e grava as cópias datadas
em ../04_PDFs_Semanais/ (AAAA-MM-DD_<Dealer>_Avance_Semanal.pdf e AAAA-MM-DD_Consolidado_Interno.pdf).
Uso: python3 pdf.py [data]"""
import sys, glob, json, pathlib, shutil
from playwright.sync_api import sync_playwright
BASE = pathlib.Path(__file__).parent
cfg = json.loads((BASE / 'config.json').read_text(encoding='utf-8'))
date = sys.argv[1] if len(sys.argv) > 1 else sorted(p.name for p in (BASE / 'out').iterdir())[-1]
files = [f for f in glob.glob(str(BASE / 'out' / date / '*.html')) if not f.endswith('_email.html')]
PDFS = BASE.parent / '04_PDFs_Semanais'; PDFS.mkdir(exist_ok=True)
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page()
    for f in files:
        pg.goto('file://' + f); pg.wait_for_load_state('networkidle')
        pdf = f[:-5] + '.pdf'
        pg.pdf(path=pdf, format='A4', landscape=True, print_background=True, margin={'top': '10mm', 'bottom': '10mm', 'left': '10mm', 'right': '10mm'})
        stem = pathlib.Path(f).stem
        nome = 'Consolidado_Interno' if stem == 'consolidado' else cfg['dealers'][stem]['nome'] + '_Avance_Semanal'
        dest = PDFS / f'{date}_{nome}.pdf'; shutil.copy(pdf, dest); print('pdf', dest.name)
    b.close()

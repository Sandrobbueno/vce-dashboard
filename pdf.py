#!/usr/bin/env python3
"""Converte os HTML de out/<lang>/<data>/ em PDF (A4 paisagem) e grava as cópias datadas em 04_PDFs_Semanais/.
Uso: python3 pdf.py --lang es|pt [data]"""
import sys, glob, json, pathlib, shutil
from playwright.sync_api import sync_playwright
BASE = pathlib.Path(__file__).parent
LANG = sys.argv[sys.argv.index('--lang') + 1] if '--lang' in sys.argv else 'es'
args = [a for i, a in enumerate(sys.argv[1:]) if a != '--lang' and sys.argv[i] != '--lang']
cfg = json.loads((BASE / f'config_{LANG}.json').read_text(encoding='utf-8'))
date = args[0] if args else sorted(p.name for p in (BASE / 'out' / LANG).iterdir())[-1]
files = [f for f in glob.glob(str(BASE / 'out' / LANG / date / '*.html')) if not f.endswith('_email.html')]
PDFS = (BASE if (BASE / '.github').exists() else BASE.parent) / '04_PDFs_Semanais'; PDFS.mkdir(exist_ok=True)
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page()
    for f in files:
        pg.goto('file://' + f); pg.wait_for_load_state('networkidle')
        pdf = f[:-5] + '.pdf'
        pg.pdf(path=pdf, format='A4', landscape=True, print_background=True, margin={'top': '10mm', 'bottom': '10mm', 'left': '10mm', 'right': '10mm'})
        stem = pathlib.Path(f).stem
        nome = cfg.get('sufixo_consolidado', 'Consolidado_Interno') if stem == 'consolidado' else cfg['dealers'][stem]['nome'].replace(' ', '_') + '_' + cfg.get('sufixo_pdf', 'Avance_Semanal')
        dest = PDFS / f'{date}_{nome}.pdf'; shutil.copy(pdf, dest); print('pdf', dest.name)
    b.close()

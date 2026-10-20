#!/usr/bin/env python3
"""Retira do curso os alunos de um programa do roster (ex.: especialistas fora do curso de liderança).
Guarda: só retira quem está matriculado E tem 0% no curso; quem tem progresso é pulado e listado.
Uso: HOTSCOOL_KEY_PT=... python3 retirar.py --lang pt --curso 21427 --programa especialistas"""
import json, os, sys, pathlib, argparse, datetime, time, urllib.request, urllib.error
ap = argparse.ArgumentParser(); ap.add_argument('--lang', required=True); ap.add_argument('--curso', required=True); ap.add_argument('--programa', required=True)
a = ap.parse_args(); BASE = pathlib.Path(__file__).parent; key = os.environ[f'HOTSCOOL_KEY_{a.lang.upper()}']; API = 'https://api.hotscool.com/v1/'; cid = int(a.curso)
def call(m, p, body=None):
    r = urllib.request.Request(API + p, method=m, headers={'x-access-token': key, 'Content-Type': 'application/json'}, data=json.dumps(body).encode() if body is not None else None)
    try:
        with urllib.request.urlopen(r, timeout=60) as x: return x.status, json.loads(x.read().decode() or 'null')
    except urllib.error.HTTPError as e: return e.code, e.read().decode()[:200]
cfg = json.loads((BASE / f'config_{a.lang}.json').read_text(encoding='utf-8'))
alvo = [p for p in cfg['roster'] if p['programa'] == a.programa]
ok, pulados, falhas = [], [], []
for p in alvo:
    s, d = call('POST', 'leads/search/0', {'email': p['email']}); lst = (d.get('data') or []) if s == 200 and isinstance(d, dict) else []
    if not lst: pulados.append((p['email'], 'não encontrado')); continue
    sid = lst[0]['id']
    s, rep = call('GET', f'students/{sid}/report/course/{cid}')
    rc = (rep.get('relatorio_curso') or {}) if s == 200 and isinstance(rep, dict) else None
    if not rc: pulados.append((p['email'], 'não matriculado')); continue
    pct = int(str(rc.get('percentual_visto') or '0').rstrip('%') or 0)
    if pct > 0 or rc.get('curso_concluido'): pulados.append((p['email'], f'tem progresso {pct}%: mantido')); continue
    s, d = call('DELETE', f'students/withdraw/{sid}/{cid}')
    (ok if s == 200 else falhas).append((p['email'], sid, s))
time.sleep(10)
conf = 0
for e, sid, s in ok:
    s2, rep = call('GET', f'students/{sid}/report/course/{cid}')
    rc = (rep.get('relatorio_curso') or {}) if s2 == 200 and isinstance(rep, dict) else None
    conf += 0 if rc else 1
resumo = f'{datetime.datetime.now(datetime.timezone.utc):%Y-%m-%d %H:%M} UTC | {a.lang.upper()} | RETIRADA DO CURSO {cid} | programa {a.programa} | alvo {len(alvo)} | retirados {len(ok)} (confirmados fora do relatório: {conf}) | pulados {len(pulados)} | falhas {len(falhas)} | pedido do Sandro no chat (matrícula indevida)\n'
(BASE / 'acoes.log').open('a', encoding='utf-8').write(resumo); print(resumo); print('pulados:', pulados); print('falhas:', falhas)
sys.exit(1 if falhas else 0)

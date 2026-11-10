#!/usr/bin/env python3
"""Bloqueia o acesso de um aluno à escola Hotscool (a pedido do Sandro, uma pessoa por execução). Não apaga nada: o cadastro e o progresso ficam.
Uso: HOTSCOOL_KEY_<LANG>=... python3 bloquear.py --lang es --email x@y [--nome "X"] [--status 1|0] [--aplicar sim]
Sem --aplicar só inspeciona: mostra o cadastro, procura os campos de acesso e tenta ler a especificação do endpoint no api-docs."""
import json, os, sys, pathlib, argparse, datetime, time, re, urllib.request, urllib.error
ap = argparse.ArgumentParser(); ap.add_argument('--lang', required=True); ap.add_argument('--email', required=True)
ap.add_argument('--nome', default=''); ap.add_argument('--status', default=''); ap.add_argument('--aplicar', default='')
a = ap.parse_args(); BASE = pathlib.Path(__file__).parent; key = os.environ[f'HOTSCOOL_KEY_{a.lang.upper()}']; ROOT = 'https://api.hotscool.com/'; API = ROOT + 'v1/'
def call(m, p, body=None, root=API, auth=True):
    h = {'Content-Type': 'application/json'}
    if auth: h['x-access-token'] = key
    r = urllib.request.Request(root + p, method=m, headers=h, data=json.dumps(body).encode() if body is not None else None)
    try:
        with urllib.request.urlopen(r, timeout=60) as x:
            t = x.read().decode()
            try: return x.status, json.loads(t or 'null')
            except Exception: return x.status, t
    except urllib.error.HTTPError as e: return e.code, e.read().decode()[:300]
def achar():
    s, d = call('POST', 'leads/search/0', {'email': a.email.strip().lower()})
    return (d.get('data') or []) if s == 200 and isinstance(d, dict) else []
def campos_acesso(o, pref=''):
    out = {}
    if isinstance(o, dict):
        for k, v in o.items():
            if re.search(r'bloq|bloc|acesso|access|ativo|active|status|situa', k, re.I) and not isinstance(v, (dict, list)): out[pref + k] = v
            elif isinstance(v, dict): out.update(campos_acesso(v, pref + k + '.'))
    return out
lst = achar()
if not lst: print('NÃO ENCONTRADO:', a.email); sys.exit(1)
sid = lst[0]['id']; print('id', sid, '| nome', lst[0].get('nome'), '| e-mail', lst[0].get('email'))
print('campos de acesso (lead):', json.dumps(campos_acesso(lst[0]), ensure_ascii=False))
s, st = call('GET', f'students/{sid}'); print('GET students/{id}:', s, json.dumps(campos_acesso(st), ensure_ascii=False)[:500] if s == 200 else str(st)[:200])
if not a.aplicar:
    s, d = call('GET', 'v1/api-docs/swagger-ui-init.js', root=ROOT, auth=False)
    print('swagger-ui-init.js', s, len(d) if isinstance(d, str) else type(d).__name__)
    if s == 200 and isinstance(d, str):
        for m in re.finditer(r'block-access|students/access', d):
            i = m.start(); print('TRECHO:', re.sub(r'\s+', ' ', d[max(0, i-200):i+1600])); break
    for u in ('v1/api-docs/swagger.json', 'v1/api-docs.json', 'v1/swagger.json', 'api-docs/swagger.json', 'swagger.json', 'v1/api-docs/'):
        s, d = call('GET', u, root=ROOT, auth=False)
        if s == 200 and isinstance(d, dict) and 'paths' in d:
            for p, v in d['paths'].items():
                if 'block' in p or p.endswith('/access/{id}/{curso}/{status}') or '/access/' in p: print('SPEC', u, p, json.dumps(v, ensure_ascii=False)[:900])
            break
        print('spec', u, s, (str(d)[:80] if s == 200 else ''))
    sys.exit(0)
if a.status == '': print('informe --status'); sys.exit(1)
s, d = call('PUT', f'students/block-access/school/{sid}/{a.status}'); print('PUT block-access:', s, str(d)[:300])
time.sleep(5)
s2, st2 = call('GET', f'students/{sid}'); depois = campos_acesso(st2) if s2 == 200 else {}
print('depois:', json.dumps(depois, ensure_ascii=False))
linha = f'{datetime.datetime.now(datetime.timezone.utc):%Y-%m-%d %H:%M} UTC | {a.lang.upper()} | BLOQUEIO DE ACESSO À ESCOLA | {a.nome or lst[0].get("nome")} <{a.email.strip().lower()}> | id_aluno {sid} | status enviado {a.status} | HTTP {s} | campos de acesso depois: {json.dumps(depois, ensure_ascii=False)} | pedido do Sandro no chat (saiu da empresa); cadastro e progresso mantidos\n'
(BASE / 'acoes.log').open('a', encoding='utf-8').write(linha); print(linha)
sys.exit(0 if s == 200 else 1)

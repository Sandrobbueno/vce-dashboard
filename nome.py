#!/usr/bin/env python3
"""Corrige o nome de um aluno na Hotscool (a pedido do Sandro, um por execução).
Sem --aplicar só inspeciona: mostra o cadastro e lista no api-docs os endpoints PUT/PATCH de alunos e leads com seus parâmetros.
Uso: HOTSCOOL_KEY_<LANG>=... python3 nome.py --lang pt --email x@y --nome "Nome Completo" [--aplicar sim --metodo PUT --caminho 'students/{id}']"""
import json, os, sys, re, pathlib, argparse, datetime, time, urllib.request, urllib.error
ap = argparse.ArgumentParser()
for k in ('lang', 'email', 'nome'): ap.add_argument('--' + k, required=True)
ap.add_argument('--aplicar', default=''); ap.add_argument('--metodo', default='PUT'); ap.add_argument('--caminho', default='')
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
lst = achar()
if not lst: print('NÃO ENCONTRADO:', a.email); sys.exit(1)
sid = lst[0]['id']; print('id', sid, '| nome atual:', lst[0].get('nome'), '| e-mail', lst[0].get('email'))
if not a.aplicar:
    s, d = call('GET', 'v1/api-docs/swagger-ui-init.js', root=ROOT, auth=False)
    m = re.search(r'"swaggerDoc":\s*(\{.*\})\s*,\s*"customOptions"', d, re.S) if isinstance(d, str) else None
    if not m: print('spec não encontrada', s); sys.exit(0)
    spec = json.loads(m.group(1))
    for p, ops in spec.get('paths', {}).items():
        for meth, op in ops.items():
            if meth.lower() in ('put', 'patch') and re.search(r'student|lead|aluno|user', p, re.I):
                params = [(x.get('name'), x.get('in')) for x in op.get('parameters', [])]
                body = op.get('requestBody', {}).get('content', {}).get('application/json', {}).get('schema', {})
                ref = body.get('$ref', '')
                props = list(spec.get('components', {}).get('schemas', {}).get(ref.split('/')[-1], {}).get('properties', {}).keys()) if ref else list(body.get('properties', {}).keys())
                print('ENDPOINT', meth.upper(), p, '|', op.get('summary'), '| params', params, '| corpo', props[:25])
    sys.exit(0)
caminho = a.caminho.replace('{id}', str(sid))
CAMPOS = ('codigo_externo', 'nome', 'email', 'ddd', 'telefone', 'id_pais')  # reenviados com o valor atual para o PUT não apagar nada
corpo = {k: lst[0].get(k) for k in CAMPOS if lst[0].get(k) not in (None, '')}; corpo['nome'] = a.nome
print('campos reenviados:', sorted(corpo))
s, d = call(a.metodo, caminho, corpo); print(a.metodo, caminho, s, str(d)[:300])
time.sleep(5); dep = (achar() or [{}])[0]; depois = dep.get('nome'); print('nome depois:', depois, '| e-mail depois:', dep.get('email'), '| código depois:', dep.get('codigo_externo'))
ok = s == 200 and depois == a.nome and (dep.get('email') or '').lower() == a.email.strip().lower()
linha = f'{datetime.datetime.now(datetime.timezone.utc):%Y-%m-%d %H:%M} UTC | {a.lang.upper()} | CORREÇÃO DE NOME | <{a.email.strip().lower()}> | id_aluno {sid} | "{lst[0].get("nome")}" -> "{a.nome}" | {a.metodo} {a.caminho} HTTP {s} | conferência: {"ok" if ok else "FALHOU (nome na busca: " + str(depois) + ")"} | pedido do Sandro no chat\n'
(BASE / 'acoes.log').open('a', encoding='utf-8').write(linha); print(linha); sys.exit(0 if ok else 1)

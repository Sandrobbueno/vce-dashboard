#!/usr/bin/env python3
"""Ação administrativa na Hotscool, a pedido do Sandro (uma ação por execução).
Uso: HOTSCOOL_KEY_<LANG>=... python3 acao.py --lang pt --nome "X" --email x@y --unidade 2314 --departamento 1799 --cargo 4479 --codigo LID-BR-019 --curso 21427 --programa lideranca --dealer tracbel [--ddd 19 --telefone 995929257]
Passos: (1) busca por e-mail; (2) cadastra se não existir; (3) matricula no curso; (4) confere; (5) registra em acoes.log e no roster do config.
Telefone vai à plataforma mas nunca ao log nem ao repositório."""
import json, os, sys, pathlib, argparse, datetime, time, urllib.request, urllib.error
ap = argparse.ArgumentParser()
for a in ('lang','nome','email','unidade','departamento','cargo','codigo','curso','programa','dealer'): ap.add_argument('--'+a, required=True)
ap.add_argument('--verificar', default=''); ap.add_argument('--boasvindas', default='1'); ap.add_argument('--ddd', default=''); ap.add_argument('--telefone', default=''); ap.add_argument('--senha', default='123456')
a = ap.parse_args()
BASE = pathlib.Path(__file__).parent; API = 'https://api.hotscool.com/v1/'
key = os.environ[f'HOTSCOOL_KEY_{a.lang.upper()}']
def call(method, path, body=None):
    req = urllib.request.Request(API + path, method=method, headers={'x-access-token': key, 'Content-Type': 'application/json'},
                                 data=json.dumps(body).encode() if body is not None else None)
    try:
        with urllib.request.urlopen(req, timeout=60) as r: return r.status, json.loads(r.read().decode() or 'null')
    except urllib.error.HTTPError as e: return e.code, e.read().decode()[:300]
def find():
    s, d = call('POST', 'leads/search/0', {'email': a.email})
    return (d.get('data') or []) if s == 200 and isinstance(d, dict) else []
email = a.email.strip().lower()
ja = find(); resultado = []
if ja:
    resultado.append(f'já existia (id {ja[0]["id"]}); cadastro não alterado')
else:
    b = dict(nome=a.nome, email=email, id_pais=1, id_unidade=int(a.unidade), id_departamento=int(a.departamento), id_cargo=int(a.cargo),
             codigo_externo=a.codigo, senha=a.senha, enviar_email_notificacao=1 if a.boasvindas == '1' else 0)
    if a.ddd and a.telefone: b.update(ddd=int(a.ddd), telefone=int(a.telefone))
    s, d = call('POST', 'leads/enrollment/groups', b); resultado.append(f'cadastro HTTP {s}')
    if s != 200: print(resultado, d); sys.exit(1)
    time.sleep(3); ja = find()
    if not ja: print('cadastro não apareceu na busca'); sys.exit(1)
sid = ja[0]['id']
if a.verificar:
    resultado.append('verificação posterior')
else:
    s, d = call('POST', 'students/enrollment', {'nome': a.nome, 'email': email, 'id_curso': int(a.curso), 'id_pais': 1, 'enviar_email_notificacao': 1 if a.boasvindas == '1' else 0}); resultado.append(f'matrícula HTTP {s}')
    if s != 200: print(resultado, d); sys.exit(1)
    time.sleep(20)
se, de = call('GET', f'students/external_code/{a.codigo}')
print('external_code:', se, json.dumps([{k: x.get(k) for k in ('id', 'email', 'codigo_externo', 'cursos_matriculados', 'trilhas')} for x in (de if isinstance(de, list) else [])], ensure_ascii=False)[:800])
s, rep = call('GET', f'students/{sid}/report/course/{a.curso}'); print('report:', s, str(rep)[:300] if s != 200 else 'ok')
ok = s == 200 and isinstance(rep, dict) and (rep.get('relatorio_curso') or {}).get('id_curso') == int(a.curso)
resultado.append('conferência: ' + ('curso aparece no relatório do aluno' if ok else f'FALHOU (HTTP {s})'))
cat = (ja[0].get('categorizacao') or {})
resultado.append(f'categorização: {cat.get("nome_unidade")} / {cat.get("nome_departamento")} / {cat.get("nome_cargo")}')
linha = f'{datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M")} UTC | {a.lang.upper()} | CADASTRO + MATRICULA | {a.nome} <{email}> | id_aluno {sid} | curso {a.curso} | código {a.codigo} | ' + ' | '.join(resultado) + ' | pedido do Sandro no chat | boas-vindas ' + ('solicitado à plataforma (só vale para cadastro novo)' if a.boasvindas == '1' else 'desligado') + '\n'
(BASE / 'acoes.log').open('a', encoding='utf-8').write(linha); print(linha)
cp = BASE / f'config_{a.lang}.json'; cfg = json.loads(cp.read_text(encoding='utf-8'))
if email not in {p['email'].lower() for p in cfg['roster']}:
    cfg['roster'].append({'email': email, 'nome': a.nome, 'dealer': a.dealer, 'programa': a.programa})
    cp.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + '\n', encoding='utf-8'); print('roster atualizado')
sys.exit(0 if ok else 1)

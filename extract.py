#!/usr/bin/env python3
"""
Extrai da API da Hotscool (api.hotscool.com) o progresso da turma e grava history/dump_<lang>_<AAAA-MM-DD>.json.

Uso:  HOTSCOOL_KEY_ES=<chave> python3 extract.py [--lang es]
      (ou deixe a chave em ../00_Chaves_API/chave_api_es.txt; esse arquivo nunca sai de lá)

Só funciona onde api.hotscool.com é alcançável. No ambiente em nuvem do Claude isso depende de
liberar o domínio na política de rede da organização (Admin → Capabilities). Enquanto não liberar,
usar extract.js pelo navegador interno do app (ver ROTINA.md).

Quem entra no dump: todo aluno cujo e-mail está no roster do config.json, mais quem está nas trilhas
do config (id_trilha) ou tem cargo "Especialistas Lean"/"Lidenrança Lean". O build.py decide quem
aparece nos dashboards (só o roster); o resto vai para a lista de extras do consolidado.
Privacidade: do cadastro só saem id, código, nome, e-mail, datas de cadastro/login, unidade, cargo,
trilhas, cursos e progresso. CPF, telefone, endereço e nascimento nunca entram no dump.
"""
import json, os, sys, pathlib, datetime, urllib.request, urllib.error, concurrent.futures as cf

BASE = pathlib.Path(__file__).parent
LANG = sys.argv[sys.argv.index('--lang') + 1] if '--lang' in sys.argv else 'es'
cfg = json.loads((BASE / 'config.json').read_text(encoding='utf-8'))
key = os.environ.get(f'HOTSCOOL_KEY_{LANG.upper()}') or (BASE.parent / '00_Chaves_API' / f'chave_api_{LANG}.txt').read_text().strip()
API = 'https://api.hotscool.com/v1/'

def get(path):
    req = urllib.request.Request(API + path, headers={'x-access-token': key})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode('utf-8'))

def get_all(prefix):
    out, p = [], 0
    while True:
        d = get(f'{prefix}{p}')
        if not isinstance(d, list) or not d: break
        out += d
        if len(d) < 25: break
        p += 1
    return out

def arr(x): return x if isinstance(x, list) else (list(x.values()) if isinstance(x, dict) else [])

courses = get_all('courses/all/')
students = get_all('students/3/all/')
roster = {p['email'].lower() for p in cfg['roster']}
trail_ids = {t['id_trilha'] for t in cfg['trilhas'].values()}
cargos = {'especialistas lean', 'lidenrança lean', 'liderança lean'}
cohort = [s for s in students if (s.get('email') or '').lower() in roster
          or any(t.get('id_trilha') in trail_ids for t in arr(s.get('trilhas')))
          or ((s.get('categorizacao') or {}).get('nome_cargo') or '').strip().lower() in cargos]
course_ids = [c['id'] for c in courses]

def one(s):
    cat = s.get('categorizacao') or {}; c, cert = {}, {}
    for cid in course_ids:
        try:
            rc = (get(f'students/{s["id"]}/report/course/{cid}') or {}).get('relatorio_curso') or {}
        except urllib.error.HTTPError:
            continue
        pv = int(str(rc.get('percentual_visto') or '0').rstrip('%') or 0); done = bool(rc.get('curso_concluido'))
        if pv or done:
            c[str(cid)] = 100 if done else pv
            if done and rc.get('certificado'): cert[str(cid)] = (rc['certificado'][0].get('data') or '')[:10]
    return {'id': s['id'], 'code': s.get('codigo_externo') or '', 'n': (s.get('nome') or '').strip(), 'em': (s.get('email') or '').lower(),
            'cad': (s.get('data_cadastro') or '')[:10], 'l': (s.get('ultimo_login') or '')[:10],
            'u': (cat.get('nome_unidade') or '').strip(), 'r': (cat.get('nome_cargo') or '').strip(),
            't': [t.get('id_trilha') for t in arr(s.get('trilhas'))], 'enr': [x.get('id_curso') for x in arr(s.get('cursos_matriculados'))], 'c': c, 'cert': cert}

with cf.ThreadPoolExecutor(6) as ex:
    rows = list(ex.map(one, cohort))

ts = datetime.datetime.now(datetime.timezone.utc)
dump = {'ts': ts.strftime('%Y-%m-%dT%H:%M:%SZ'), 'escola': cfg['escola'], 'idioma': LANG,
        'courses': [[c['id'], c['nome'].strip(), (c.get('categoria') or '').strip()] for c in courses], 'rows': rows}
out = BASE / 'history' / f'dump_{LANG}_{ts.strftime("%Y-%m-%d")}.json'
out.write_text(json.dumps(dump, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
print(f'{out.name}: {len(rows)} alunos de {len(students)} cadastrados; {len(courses)} cursos')

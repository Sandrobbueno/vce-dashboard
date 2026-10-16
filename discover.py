#!/usr/bin/env python3
"""Descoberta da estrutura de uma escola Hotscool (cursos, unidades, cargos, trilhas vistas, cadastros por unidade/cargo).
Uso: HOTSCOOL_KEY_<LANG>=<chave> python3 discover.py --lang pt  -> grava discovery_<lang>.json (sem dados pessoais além de nome/e-mail/unidade/cargo)."""
import json, os, sys, pathlib, urllib.request, collections
LANG = sys.argv[sys.argv.index('--lang') + 1] if '--lang' in sys.argv else 'es'
key = os.environ[f'HOTSCOOL_KEY_{LANG.upper()}']
API = 'https://api.hotscool.com/v1/'
def get(p):
    r = urllib.request.Request(API + p, headers={'x-access-token': key})
    with urllib.request.urlopen(r, timeout=60) as x: return json.loads(x.read().decode())
def get_all(pfx):
    out, p = [], 0
    while True:
        d = get(f'{pfx}{p}')
        if not isinstance(d, list) or not d: break
        out += d
        if len(d) < 25: break
        p += 1
    return out
arr = lambda x: x if isinstance(x, list) else (list(x.values()) if isinstance(x, dict) else [])
courses, units, deps, roles, students = (get_all(p) for p in ('courses/all/', 'groups/units/all/', 'groups/departments/all/', 'groups/roles/all/', 'students/3/all/'))
trails, by_unit_role, enroll = {}, collections.Counter(), collections.Counter()
rows = []
for s in students:
    for t in arr(s.get('trilhas')): trails[t.get('id_trilha')] = t.get('nome_trilha')
    c = s.get('categorizacao') or {}
    by_unit_role[(c.get('nome_unidade') or '-') + ' | ' + (c.get('nome_cargo') or '-')] += 1
    for x in arr(s.get('cursos_matriculados')): enroll[x.get('id_curso')] += 1
    rows.append({'code': s.get('codigo_externo') or '', 'n': (s.get('nome') or '').strip(), 'em': (s.get('email') or '').lower(), 'cad': (s.get('data_cadastro') or '')[:10],
                 'l': (s.get('ultimo_login') or '')[:10], 'u': c.get('nome_unidade') or '', 'r': c.get('nome_cargo') or '', 't': [t.get('id_trilha') for t in arr(s.get('trilhas'))], 'enr': [x.get('id_curso') for x in arr(s.get('cursos_matriculados'))]})
out = {'escola': (students[0].get('escola') if students else ''), 'n_students': len(students),
       'courses': [[c['id'], c['nome'].strip(), (c.get('categoria') or '').strip(), enroll.get(c['id'], 0)] for c in courses],
       'units': [[u['id'], u['nome'].strip()] for u in units], 'departments': [[d['id'], d['nome'].strip()] for d in deps], 'roles': [[r['id'], r['nome'].strip()] for r in roles],
       'trails_seen': trails, 'by_unit_role': dict(by_unit_role), 'students': rows}
pathlib.Path(f'discovery_{LANG}.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
print(f'discovery_{LANG}.json: {len(students)} cadastros, {len(courses)} cursos, {len(units)} unidades, trilhas {trails}')

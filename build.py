#!/usr/bin/env python3
"""
Gera os dashboards semanais da Formación Lean Volvo CE (um por dealer + consolidado interno).

Uso:  python3 build.py [--date AAAA-MM-DD] [--lang es]
Lê:   config.json, history/dump_<lang>_*.json (o mais recente é a semana corrente; o anterior é a base do Δ)
Grava: out/<data>/<dealer>.html        dashboard completo (impressão/PDF)
       out/<data>/<dealer>_email.html  corpo de e-mail (só tags aceitas pelo conector do Outlook: sem CSS, sem imagens)
       out/<data>/consolidado.html     visão interna (todos os dealers, extras, ausentes)
       out/<data>/resumen.json         números por dealer (para o texto do e-mail, o doc do projeto e conferência)
Regras de cálculo: ver ROTINA.md.
"""
import json, sys, glob, os, re, html, datetime, pathlib, unicodedata

BASE = pathlib.Path(__file__).parent
LANG = sys.argv[sys.argv.index('--lang') + 1] if '--lang' in sys.argv else 'es'
cfg = json.loads((BASE / f'config_{LANG}.json').read_text(encoding='utf-8'))
L = cfg.get('idioma', LANG)  # idioma das saídas para os dealers

# ---------- dumps ----------
dumps = sorted(glob.glob(str(BASE / 'history' / f'dump_{LANG}_*.json')))
if not dumps: sys.exit('nenhum dump em history/')
if '--date' in sys.argv:
    d = sys.argv[sys.argv.index('--date') + 1]
    dumps = [x for x in dumps if x.split('_')[-1][:10] <= d]
cur = json.loads(open(dumps[-1], encoding='utf-8').read())
prev = json.loads(open(dumps[-2], encoding='utf-8').read()) if len(dumps) > 1 else None
hist = [json.loads(open(x, encoding='utf-8').read()) for x in dumps]
DATE = dumps[-1].split('_')[-1][:10]
OUT = BASE / 'out' / LANG / DATE
OUT.mkdir(parents=True, exist_ok=True)

INICIO = cfg['inicio_turma']
TR = cfg['trilhas']
DEALERS = cfg['dealers']
EXCL = set(cfg['excluir_dominios'])
COURSE_NAME = {str(c[0]): c[1] for c in cur['courses']}

MESES_ES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']
MESES_PT = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez']

def fdate(s, lang='es'):
    if not s: return '—'
    y, m, d = s[:10].split('-')
    return f"{int(d)} {(MESES_ES if lang == 'es' else MESES_PT)[int(m) - 1]} {y}"

def norm(s):
    return unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode().lower().strip()

def semana():
    d0 = datetime.date.fromisoformat(INICIO); d1 = datetime.date.fromisoformat(DATE)
    return (d1 - d0).days // 7 + 1

# ---------- cálculo por pessoa ----------
def index(dump):
    return {r['em'].lower(): r for r in dump['rows']}

def avance(row, prog):
    """% da trilha = média dos cursos da trilha; curso sem relatório = 0. None se não cadastrado."""
    if row is None: return None
    ids = [str(c) for c in TR[prog]['cursos']]
    return round(sum(int(row['c'].get(c, 0)) for c in ids) / len(ids))

def estado(row, av):
    if row is None: return 'sin_registro'
    if av == 100: return 'concluido'
    if av > 0: return 'en_curso'
    return 'no_inicio' if (row.get('l') or '')[:10] >= INICIO else 'sin_acceso'

ETIQUETA = {
    'es': {'sin_registro': '✖ Sin registro', 'sin_acceso': '○ Sin acceso', 'no_inicio': '◔ No inició', 'en_curso': '◑ En curso', 'concluido': '● Concluido'},
    'pt': {'sin_registro': '✖ Sem cadastro', 'sin_acceso': '○ Sem acesso', 'no_inicio': '◔ Não iniciou', 'en_curso': '◑ Em curso', 'concluido': '● Concluiu'},
}
CSS_EST = {'sin_registro': 'crit', 'sin_acceso': 'ser', 'no_inicio': 'warn', 'en_curso': 'prog', 'concluido': 'good'}

cur_ix, prev_ix = index(cur), (index(prev) if prev else {})
people = []  # uma linha por pessoa do roster
for p in cfg['roster']:
    em = p['email'].lower(); row = cur_ix.get(em); pr = p['programa']
    av = avance(row, pr); pav = avance(prev_ix.get(em), pr) if prev else None
    ids = [str(c) for c in TR[pr]['cursos']]
    extra = None
    if pr == 'liderazgo' and row and any(str(c) in row['c'] for c in TR['expertos']['cursos']):
        extra = avance(row, 'expertos')  # líder que também percorre a trilha Expertos
    people.append({
        'email': em, 'nome': (row['n'] if row else p['nome']), 'dealer': p['dealer'], 'programa': pr,
        'registrado': row is not None, 'ultimo_acceso': (row.get('l') or '')[:10] if row else '',
        'cursos': {c: int(row['c'].get(c, 0)) if row else 0 for c in ids},
        'avance': av, 'delta': (None if (pav is None or av is None) else av - pav),
        'estado': estado(row, av if av is not None else 0), 'certificados': sum(1 for c in ids if row and c in row.get('cert', {})),
        'extra_expertos': extra, 'nota': p.get('nota', ''),
    })

# extras: na plataforma, nas trilhas, fora do roster e fora dos domínios excluídos
roster_emails = {p['email'].lower() for p in cfg['roster']}
# extras relevantes: fora do roster, mas de um dos dealers configurados e cadastrados a partir do início da turma
# (as turmas de 2025 de outros dealers ficam de fora: não são objeto deste acompanhamento)
dealer_units = {d['nome'].lower() for d in DEALERS.values()}
dealer_doms = {dom for d in DEALERS.values() for dom in d['dominios']}
extras = [r for r in cur['rows'] if r['em'].lower() not in roster_emails and r['em'].split('@')[-1] not in EXCL
          and (r['u'].lower() in dealer_units or r['em'].split('@')[-1] in dealer_doms) and (r.get('cad') or '') >= INICIO[:7]]

# ---------- agregados ----------
def resumo(rows_p):
    n = len(rows_p)
    if n == 0: return None
    avs = [x['avance'] or 0 for x in rows_p]
    return {
        'inscritos': n,
        'registrados': sum(1 for x in rows_p if x['registrado']),
        'con_acceso': sum(1 for x in rows_p if x['ultimo_acceso'] >= INICIO),
        'iniciaron': sum(1 for x in rows_p if (x['avance'] or 0) > 0),
        'concluyeron': sum(1 for x in rows_p if x['avance'] == 100),
        'avance_prom': round(sum(avs) / n),
        'certificados': sum(x['certificados'] for x in rows_p),
    }

def serie(dealer, prog):
    """avanço médio por semana (uma entrada por dump) para o dealer/programa"""
    pts = []
    for dmp in hist:
        ix = index(dmp); vals = []
        for p in cfg['roster']:
            if p['dealer'] == dealer and p['programa'] == prog:
                vals.append(avance(ix.get(p['email'].lower()), prog) or 0)
        pts.append((dmp['ts'][:10], round(sum(vals) / len(vals)) if vals else 0))
    return pts

resumen = {'fecha': DATE, 'semana': semana(), 'inicio': INICIO, 'dealers': {}}
for dk in DEALERS:
    resumen['dealers'][dk] = {}
    for pk in TR:
        rp = [x for x in people if x['dealer'] == dk and x['programa'] == pk]
        r = resumo(rp)
        if r: r['serie'] = serie(dk, pk); resumen['dealers'][dk][pk] = r
red = {pk: resumo([x for x in people if x['programa'] == pk]) for pk in TR}
resumen['red'] = red
(OUT / 'resumen.json').write_text(json.dumps(resumen, ensure_ascii=False, indent=1), encoding='utf-8')

# ---------- HTML completo (impressão / PDF) ----------
STYLE = """
:root{--ink:#0b0b0b;--ink2:#52514e;--mute:#8a8984;--line:#e6e4df;--surf:#fcfcfb;--card:#ffffff;
--seq:#2a78d6;--seq-l:#cde2fb;--good:#008300;--warn:#c98500;--ser:#d95926;--crit:#c0302f;--prog:#2a78d6}
*{box-sizing:border-box}body{margin:0;background:var(--surf);color:var(--ink);font:14px/1.45 -apple-system,"Segoe UI",Inter,Roboto,Helvetica,Arial,sans-serif}
.page{max-width:1080px;margin:0 auto;padding:36px 40px}
.brandbar{height:6px;background:linear-gradient(90deg,#c0302f 0 34%,#eb6834 34% 67%,#008300 67%)}
header{display:flex;justify-content:space-between;align-items:flex-end;gap:24px;margin-bottom:22px}
h1{font-size:26px;margin:0 0 4px;letter-spacing:-.01em}h2{font-size:17px;margin:30px 0 10px}
.sub{color:var(--ink2)}.meta{text-align:right;color:var(--ink2);font-size:13px}.meta b{color:var(--ink);font-size:15px}
.tiles{display:grid;grid-template-columns:repeat(6,1fr);gap:10px}
.tile{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 14px}
.tile .v{font-size:26px;font-weight:650;letter-spacing:-.02em;line-height:1.1}.tile .l{color:var(--ink2);font-size:12px;margin-top:3px}
.tile .s{color:var(--mute);font-size:11px;margin-top:2px}
table{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--line);border-radius:10px;overflow:hidden}
th{font-size:11px;text-transform:uppercase;letter-spacing:.04em;color:var(--ink2);text-align:left;padding:9px 10px;border-bottom:1px solid var(--line);background:#f6f5f2;font-weight:600}
td{padding:8px 10px;border-bottom:1px solid var(--line);vertical-align:middle}tr:last-child td{border-bottom:0}
td.n{white-space:nowrap}td.r,th.r{text-align:right}td.c,th.c{text-align:center}
.bar{display:inline-block;width:110px;height:8px;background:var(--seq-l);border-radius:4px;vertical-align:middle;margin-right:8px;overflow:hidden}
.bar i{display:block;height:100%;background:var(--seq);border-radius:4px}
.pct{display:inline-block;min-width:34px;font-variant-numeric:tabular-nums}
.est{font-size:12px;white-space:nowrap}.good{color:var(--good)}.warn{color:var(--warn)}.ser{color:var(--ser)}.crit{color:var(--crit)}.prog{color:var(--prog)}
.d{font-variant-numeric:tabular-nums;font-size:12px}.d.up{color:var(--good)}.d.zero{color:var(--mute)}
.cell{font-variant-numeric:tabular-nums;font-size:12px;color:var(--ink2)}.cell.done{color:var(--good);font-weight:600}
.note{color:var(--ink2);font-size:12px;margin-top:8px}
footer{margin-top:34px;padding-top:12px;border-top:1px solid var(--line);color:var(--mute);font-size:11px;display:flex;justify-content:space-between}
.two{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.chart{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 14px}
@media print{body{background:#fff}.page{padding:18px 22px;max-width:none}.tile,.chart,tr{break-inside:avoid}thead{display:table-header-group}h2{break-after:avoid}@page{size:A4 landscape;margin:12mm}}
"""

T = {
    'es': dict(titulo='Avance semanal', prog='Programa', nombre='Participante', acceso='Último acceso', avance='Avance', delta='Δ sem.', estado='Situación',
               inscritos='Inscritos', registrados='Con registro', con_acceso='Accedieron', iniciaron='Iniciaron', concluyeron='Concluyeron', avance_prom='Avance medio',
               desde='desde el inicio', de_la_trilha='de la ruta', red='Promedio de la red', semana='Semana', actualizado='Datos de', evol='Evolución semanal del avance medio',
               cursos='Avance por curso', personas_curso='Personas que concluyeron cada curso', nota_calc='El avance de la ruta es el promedio de sus cursos. Una persona sin registro en la plataforma cuenta como 0 %. "Accedieron" considera accesos desde el inicio del programa',
               extra='También en Expertos', pie='Generado por Lean Dealers · datos de la plataforma Lean Dealers Academy', sin_datos='Sin datos todavía'),
    'pt': dict(titulo='Avanço semanal', prog='Programa', nombre='Participante', acceso='Último acesso', avance='Avanço', delta='Δ sem.', estado='Situação',
               inscritos='Inscritos', registrados='Com cadastro', con_acceso='Acessaram', iniciaron='Iniciaram', concluyeron='Concluíram', avance_prom='Avanço médio',
               desde='desde o início', de_la_trilha='da trilha', red='Média da rede', semana='Semana', actualizado='Dados de', evol='Evolução semanal do avanço médio',
               cursos='Avanço por curso', personas_curso='Pessoas que concluíram cada curso', nota_calc='O avanço da trilha é a média dos cursos. Pessoa sem cadastro na plataforma conta como 0%. "Acessaram" considera acessos desde o início do programa',
               extra='Também em Expertos', pie='Gerado por Lean Dealers · dados da plataforma Lean Dealers Academy', sin_datos='Sem dados ainda'),
}

def esc(s): return html.escape(str(s))

def tiles(r, t):
    if not r: return ''
    def tile(v, l, s=''): return f'<div class="tile"><div class="v">{v}</div><div class="l">{l}</div><div class="s">{s}</div></div>'
    return '<div class="tiles">' + tile(r['inscritos'], t['inscritos']) + tile(r['registrados'], t['registrados']) + \
        tile(r['con_acceso'], t['con_acceso'], t['desde']) + tile(r['iniciaron'], t['iniciaron']) + \
        tile(r['concluyeron'], t['concluyeron'], t['de_la_trilha']) + tile(f"{r['avance_prom']}%", t['avance_prom']) + '</div>'

def delta_html(d):
    if d is None: return '<span class="d zero">—</span>'
    if d == 0: return '<span class="d zero">0</span>'
    return f'<span class="d up">+{d} pp</span>' if d > 0 else f'<span class="d">{d} pp</span>'

def tabela_pessoas(rows_p, prog, t, lang, mostrar_dealer=False):
    ids = [str(c) for c in TR[prog]['cursos']]
    curto = TR[prog]['cursos_curto']
    h = '<table><thead><tr>' + (f'<th>Dealer</th>' if mostrar_dealer else '') + f'<th>{t["nombre"]}</th><th>{t["acceso"]}</th>'
    if len(ids) > 1: h += ''.join(f'<th class="c" title="{esc(COURSE_NAME.get(c, c))}">{esc(curto[c])}</th>' for c in ids)
    h += f'<th>{t["avance"]}</th><th class="r">{t["delta"]}</th><th>{t["estado"]}</th>'
    if prog == 'liderazgo': h += f'<th class="r">{t["extra"]}</th>'
    h += '</tr></thead><tbody>'
    for x in sorted(rows_p, key=lambda z: (-(z['avance'] or 0), norm(z['nome']))):
        av = x['avance'] or 0
        h += '<tr>' + (f'<td class="n">{esc(DEALERS[x["dealer"]]["nome"])}</td>' if mostrar_dealer else '') + f'<td class="n">{esc(x["nome"])}</td><td class="n">{fdate(x["ultimo_acceso"], lang)}</td>'
        if len(ids) > 1:
            for c in ids:
                v = x['cursos'][c]; h += f'<td class="c"><span class="cell{" done" if v == 100 else ""}">{v if v else "·"}{"%" if v else ""}</span></td>'
        h += f'<td><span class="bar"><i style="width:{av}%"></i></span><span class="pct">{av}%</span></td><td class="r">{delta_html(x["delta"])}</td>'
        h += f'<td class="est {CSS_EST[x["estado"]]}">{ETIQUETA[lang][x["estado"]]}</td>'
        if prog == 'liderazgo': h += f'<td class="r cell">{(str(x["extra_expertos"]) + "%") if x["extra_expertos"] is not None else "—"}</td>'
        h += '</tr>'
    return h + '</tbody></table>'

def tabela_cursos(rows_p, prog, t, lang='es'):
    ids = [str(c) for c in TR[prog]['cursos']]
    if len(ids) < 2: return ''
    n = len(rows_p)
    h = f'<div class="chart"><div class="sub" style="font-size:12px;margin-bottom:8px">{t["personas_curso"]}</div><table>'
    for c in ids:
        done = sum(1 for x in rows_p if x['cursos'][c] == 100); started = sum(1 for x in rows_p if 0 < x['cursos'][c] < 100)
        w = round(100 * done / n) if n else 0
        h += f'<tr><td class="n" style="width:38%">{esc(COURSE_NAME.get(c, c))}</td><td><span class="bar" style="width:160px"><i style="width:{w}%"></i></span><span class="pct">{done}</span> <span class="cell">/ {n} · {started} {"en curso" if lang == "es" else "em curso"}</span></td></tr>'
    return h + '</table></div>'

def tabela_evol(dk, prog, t, lang):
    pts = resumen['dealers'].get(dk, {}).get(prog, {}).get('serie', [])
    h = f'<div class="chart"><div class="sub" style="font-size:12px;margin-bottom:8px">{t["evol"]}</div><table><tr><th></th>' + ''.join(f'<th class="c">{fdate(d, lang)}</th>' for d, _ in pts) + '</tr>'
    h += f'<tr><td class="n"><b>{esc(DEALERS[dk]["nome"])}</b></td>' + ''.join(f'<td class="c"><b>{v}%</b></td>' for _, v in pts) + '</tr></table>'
    # REGRA FIXA (14/10/2026): nenhuma saída individual de dealer mostra média da rede nem dado de outro dealer.
    if len(pts) < 2: h += (f'<div class="note">{t["sin_datos"]}: la serie se construye semana a semana.</div>' if lang == 'es' else f'<div class="note">{t["sin_datos"]}: a série se constrói semana a semana.</div>')
    return h + '</div>'

def pagina(titulo, subtitulo, corpo, lang):
    t = T[lang]
    return f'''<!doctype html><html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><title>{esc(titulo)}</title><style>{STYLE}</style></head>
<body><div class="brandbar"></div><div class="page"><header><div><h1>{esc(titulo)}</h1><div class="sub">{esc(subtitulo)}</div></div>
<div class="meta"><b>{t["semana"]} {resumen["semana"]}</b><br>{t["actualizado"]} {fdate(DATE, lang)}</div></header>{corpo}
<footer><span>{t["pie"]}</span><span>{esc(cfg["marca"])} · {fdate(DATE, lang)}</span></footer></div></body></html>'''

def dashboard_dealer(dk):
    t = T[L]; d = DEALERS[dk]; corpo = ''
    for pk in TR:
        rp = [x for x in people if x['dealer'] == dk and x['programa'] == pk]
        if not rp: continue
        r = resumen['dealers'][dk][pk]
        corpo += f'<h2>{esc(TR[pk]["nome"])}</h2>' + tiles(r, t)
        corpo += '<div class="two" style="margin-top:12px">' + tabela_evol(dk, pk, t, L) + tabela_cursos(rp, pk, t, L) + '</div>'
        corpo += '<h2 style="font-size:15px">' + t['nombre'] + 's</h2>' + tabela_pessoas(rp, pk, t, L)
    corpo += f'<p class="note">{t["nota_calc"]} ({fdate(INICIO, L)}).</p>'
    return pagina(f'{cfg["programa"]} · {d["nome"]}', f'{d["pais"]} · {t["titulo"]}', corpo, L)

for dk in DEALERS:
    (OUT / f'{dk}.html').write_text(dashboard_dealer(dk), encoding='utf-8')

# ---------- consolidado interno (PT) ----------
t = T['pt']; corpo = ''
for pk in TR:
    corpo += f'<h2>{esc(TR[pk]["nome"])} · rede</h2>' + tiles(red[pk], t)
    corpo += '<table style="margin-top:12px"><thead><tr><th>Dealer</th><th class="r">Inscritos</th><th class="r">Cadastro</th><th class="r">Acessaram</th><th class="r">Iniciaram</th><th class="r">Concluíram</th><th class="r">Avanço médio</th><th class="r">Certificados</th></tr></thead><tbody>'
    for dk in DEALERS:
        r = resumen['dealers'][dk].get(pk)
        if not r: continue
        corpo += f'<tr><td class="n"><b>{esc(DEALERS[dk]["nome"])}</b> <span class="cell">{esc(DEALERS[dk]["pais"])}</span></td><td class="r">{r["inscritos"]}</td><td class="r">{r["registrados"]}</td><td class="r">{r["con_acceso"]}</td><td class="r">{r["iniciaron"]}</td><td class="r">{r["concluyeron"]}</td><td class="r"><span class="bar"><i style="width:{r["avance_prom"]}%"></i></span><span class="pct">{r["avance_prom"]}%</span></td><td class="r">{r["certificados"]}</td></tr>'
    corpo += '</tbody></table>'
    corpo += '<h2 style="font-size:15px">Participantes</h2>' + tabela_pessoas([x for x in people if x['programa'] == pk], pk, t, 'pt', mostrar_dealer=True)
aus = [x for x in people if not x['registrado']]
if aus:
    corpo += '<h2>Inscritos sem cadastro na plataforma</h2><table>' + ''.join(f'<tr><td class="n">{esc(DEALERS[x["dealer"]]["nome"])}</td><td>{esc(x["nome"])}</td><td class="cell">{esc(x["email"])}</td><td class="cell">{esc(TR[x["programa"]]["nome"])}</td></tr>' for x in aus) + '</table>'
if extras:
    corpo += '<h2>Na plataforma, fora do roster (não entram nos dashboards)</h2><table>' + ''.join(f'<tr><td class="n">{esc(r["u"])}</td><td>{esc(r["n"])}</td><td class="cell">{esc(r["em"])}</td><td class="cell">cadastro {fdate(r["cad"], "pt")} · trilhas {",".join(map(str, r["t"])) or "—"}</td></tr>' for r in extras) + '</table>'
notas = [x for x in people if x['nota']]
if notas: corpo += '<p class="note">Notas do roster: ' + '; '.join(f'{esc(x["nome"])}: {esc(x["nota"])}' for x in notas) + '</p>'
corpo += f'<p class="note">{t["nota_calc"]} ({fdate(INICIO, "pt")}). Excluídos dos indicadores: domínios {", ".join(sorted(EXCL))}.</p>'
(OUT / 'consolidado.html').write_text(pagina(f'{cfg["programa"]} · Consolidado interno', 'Lean Dealers · todos os dealers · uso interno', corpo, 'pt'), encoding='utf-8')

# ---------- corpo de e-mail (allowlist do conector Outlook: h2,h3,p,b,i,table,tr,th,td,ul,li,br,hr,a,div) ----------
def barra_txt(p):
    n = round(p / 10); return '▰' * n + '▱' * (10 - n)

EMAIL = {
    'es': dict(sauda='Estimado equipo de <b>{d}</b>,', intro='Adjunto el avance semanal de sus participantes en la <b>{p}</b> (semana {w}, datos del {dt}).',
               linha='{t}: {i} inscritos, {s} ya iniciaron, {c} concluyeron, avance medio {a}%', fecho='El detalle por participante está en el PDF. Quedamos a disposición para apoyar a quienes aún no iniciaron.', ass='Saludos,', asunto='Asunto: Formación Lean Volvo CE · Avance semanal {d} · {dt}', anexar='anexar'),
    'pt': dict(sauda='Prezada equipe da <b>{d}</b>,', intro='Segue em anexo o avanço semanal dos seus participantes na <b>{p}</b> (semana {w}, dados de {dt}).',
               linha='{t}: {i} inscritos, {s} já iniciaram, {c} concluíram, avanço médio {a}%', fecho='O detalhe por participante está no PDF. Ficamos à disposição para apoiar quem ainda não iniciou.', ass='Abraço,', asunto='Assunto: Formação Lean Volvo CE · Avanço semanal {d} · {dt}', anexar='anexar'),
}
def email_dealer(dk):
    """Texto curto de acompanhamento (o Sandro envia o e-mail à mão com o PDF anexo). Sem tabelas, sem dados de outros dealers."""
    d = DEALERS[dk]; e = EMAIL[L]; h = ''
    h += '<p>' + e['sauda'].format(d=esc(d['nome'])) + '</p>'
    h += '<p>' + e['intro'].format(p=esc(cfg['programa']), w=resumen['semana'], dt=fdate(DATE, L)) + '</p>'
    frases = []
    for pk in TR:
        r = resumen['dealers'][dk].get(pk)
        if not r: continue
        frases.append(e['linha'].format(t=esc(TR[pk]['nome']), i=r['inscritos'], s=r['iniciaron'], c=r['concluyeron'], a=r['avance_prom']))
    h += '<p>' + '.<br>'.join(frases) + '.</p>'
    h += '<p>' + e['fecho'] + '</p>'
    h += f'<p>{e["ass"]}<br>{esc(cfg["remetente_nome"])}</p>'
    return h

for dk in DEALERS:
    (OUT / f'{dk}_email.html').write_text(email_dealer(dk), encoding='utf-8')

# textos de e-mail em arquivo único (texto puro) para o envio manual com o PDF anexo
import re as _re
def _txt(h): return _re.sub(r'\n{3,}', '\n\n', _re.sub(r'<[^>]+>', lambda m: '\n' if m.group(0) in ('<br>', '</p>') else '', h)).strip()
blocos = []
for dk in DEALERS:
    nome_pdf = f"{DATE}_{DEALERS[dk]['nome'].replace(' ', '_')}_{cfg.get('sufixo_pdf', 'Avance_Semanal')}.pdf"
    blocos.append(f"=== {DEALERS[dk]['nome']} · {EMAIL[L]['anexar']} {nome_pdf} ===\n" + EMAIL[L]['asunto'].format(d=DEALERS[dk]['nome'], dt=fdate(DATE, L)) + "\n\n" + html.unescape(_txt(email_dealer(dk))))
(OUT / 'textos_email.txt').write_text('\n\n\n'.join(blocos) + '\n', encoding='utf-8')

# ---------- guarda de confidencialidade ----------
# Nenhuma saída individual pode citar a rede, a média da rede ou o nome de outro dealer. Se citar, o build falha.
PROIBIDO = ['promedio de la red', 'média da rede', 'media da rede', 'la red', 'da rede', 'toda la red', 'toda a rede']
for dk in DEALERS:
    outros = [DEALERS[o]['nome'].lower() for o in DEALERS if o != dk]
    for f in (OUT / f'{dk}.html', OUT / f'{dk}_email.html'):
        txt = f.read_text(encoding='utf-8').lower()
        achados = [w for w in PROIBIDO + outros if w in txt]
        if achados: sys.exit(f'CONFIDENCIALIDADE: {f.name} menciona {achados}. Saída não gerada.')

# ---------- validação impressa ----------
print(f'[{LANG}] {DATE} · semana {resumen["semana"]} · dump {os.path.basename(dumps[-1])} · anterior {os.path.basename(dumps[-2]) if prev else "—"}')
for dk in DEALERS:
    for pk, r in resumen['dealers'][dk].items():
        print(f'  {DEALERS[dk]["nome"]:9s} {TR[pk]["nome_curto"]:15s} inscritos {r["inscritos"]:2d} cadastro {r["registrados"]:2d} acessaram {r["con_acceso"]:2d} iniciaram {r["iniciaron"]:2d} concluíram {r["concluyeron"]:2d} avanço {r["avance_prom"]:3d}% cert {r["certificados"]}')
print('  rede:', {TR[k]['nome_curto']: f'{v["avance_prom"]}% ({v["inscritos"]} inscritos)' for k, v in red.items()})
print('  sem cadastro:', [x['nome'] for x in aus], '| extras:', [r['n'] for r in extras])

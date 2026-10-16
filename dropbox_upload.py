#!/usr/bin/env python3
"""
Envia as saídas da rodada para a pasta do Dropbox "Brazil LEAN/Universidades Lean/VCE/Turmas 2026".

Uso (no GitHub Actions): DROPBOX_APP_KEY, DROPBOX_APP_SECRET, DROPBOX_REFRESH_TOKEN no ambiente; python3 dropbox_upload.py [data]
O que vai:
  04_PDFs_Semanais/<data>_*.pdf                      -> Turmas 2026/04_PDFs_Semanais/
  out/<data>/*.html, resumen.json                     -> Turmas 2026/03_Dashboard/out/<data>/
  history/dump_es_<data>.json                         -> Turmas 2026/03_Dashboard/history/
Arquivo já existente com o mesmo nome é sobrescrito (mode=overwrite), pois a rodada do dia pode ser refeita.
Contas Dropbox de equipe: se o caminho não for encontrado a partir da raiz do usuário, tenta com o namespace raiz da equipe
(cabeçalho Dropbox-API-Path-Root), que é onde ficam as pastas compartilhadas.
"""
import os, sys, json, glob, pathlib, urllib.request, urllib.parse, urllib.error, base64

BASE = pathlib.Path(__file__).parent
DEST = '/Brazil LEAN/Universidades Lean/VCE/Turmas 2026'
LANG = sys.argv[sys.argv.index('--lang') + 1] if '--lang' in sys.argv else 'es'
args = [a for i, a in enumerate(sys.argv[1:]) if a != '--lang' and sys.argv[i] != '--lang']
cfg = json.loads((BASE / f'config_{LANG}.json').read_text(encoding='utf-8'))
date = args[0] if args else sorted(p.name for p in (BASE / 'out' / LANG).iterdir())[-1]

key, secret, refresh = (os.environ.get(k) for k in ('DROPBOX_APP_KEY', 'DROPBOX_APP_SECRET', 'DROPBOX_REFRESH_TOKEN'))
if not (key and secret and refresh):
    sys.exit('Segredos DROPBOX_APP_KEY / DROPBOX_APP_SECRET / DROPBOX_REFRESH_TOKEN não configurados; envio ao Dropbox pulado.')

def post(url, data=None, headers=None, raw=None):
    req = urllib.request.Request(url, data=raw if raw is not None else (urllib.parse.urlencode(data).encode() if data else None), headers=headers or {}, method='POST')
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode() or '{}')

# 1) access token a partir do refresh token
auth = base64.b64encode(f'{key}:{secret}'.encode()).decode()
tok = post('https://api.dropboxapi.com/oauth2/token', {'grant_type': 'refresh_token', 'refresh_token': refresh}, {'Authorization': f'Basic {auth}'})['access_token']
H = {'Authorization': f'Bearer {tok}', 'Content-Type': 'application/json'}

# 2) descobrir se precisa do namespace raiz da equipe
acct = post('https://api.dropboxapi.com/2/users/get_current_account', raw=b'null', headers=H)
root = acct.get('root_info', {})
path_root = None
if root.get('.tag') == 'team' and root.get('root_namespace_id') != root.get('home_namespace_id'):
    path_root = json.dumps({'.tag': 'root', 'root': root['root_namespace_id']})

def exists(path, hdr):
    try:
        post('https://api.dropboxapi.com/2/files/get_metadata', raw=json.dumps({'path': path}).encode(), headers=hdr); return True
    except urllib.error.HTTPError as e:
        return False

hdr = dict(H)
if not exists(DEST, hdr) and path_root:
    hdr['Dropbox-API-Path-Root'] = path_root
if not exists(DEST, hdr):
    sys.exit(f'Pasta de destino não encontrada no Dropbox: {DEST} (conta {acct.get("email")})')

def upload(local, remote):
    data = pathlib.Path(local).read_bytes()
    h = dict(hdr); h['Content-Type'] = 'application/octet-stream'
    h['Dropbox-API-Arg'] = json.dumps({'path': remote, 'mode': 'overwrite', 'autorename': False, 'mute': True}, ensure_ascii=True)
    # caracteres não ASCII no caminho precisam de escape \\uXXXX no cabeçalho; json.dumps(ensure_ascii=True) já faz isso
    r = post('https://content.dropboxapi.com/2/files/upload', raw=data, headers=h)
    print('enviado', r.get('path_display'), f'{len(data)//1024} KB')

files = []
nomes_pdf = [f"{date}_{d['nome'].replace(' ', '_')}_{cfg.get('sufixo_pdf', 'Avance_Semanal')}.pdf" for d in cfg['dealers'].values()] + [f"{date}_{cfg.get('sufixo_consolidado', 'Consolidado_Interno')}.pdf"]
files += [(str(BASE / '04_PDFs_Semanais' / n), f'{DEST}/04_PDFs_Semanais/{n}') for n in nomes_pdf if (BASE / '04_PDFs_Semanais' / n).exists()]
files += [(f, f'{DEST}/03_Dashboard/out/{LANG}/{date}/{os.path.basename(f)}') for f in glob.glob(str(BASE / 'out' / LANG / date / '*')) if not f.endswith('.pdf')]
files += [(f, f'{DEST}/03_Dashboard/history/{os.path.basename(f)}') for f in glob.glob(str(BASE / 'history' / f'dump_{LANG}_{date}.json'))]
if (BASE / 'out' / LANG / date / 'textos_email.txt').exists():
    files.append((str(BASE / 'out' / LANG / date / 'textos_email.txt'), f"{DEST}/04_PDFs_Semanais/{date}_{cfg.get('sufixo_textos', 'Textos_Email')}.txt"))
files += [(str(BASE / n), f'{DEST}/03_Dashboard/{n}') for n in ('ROTINA.md', 'README.md', 'config_es.json', 'config_pt.json', 'build.py', 'extract.py', 'pdf.py', 'dropbox_upload.py') if (BASE / n).exists()]
if not files: sys.exit(f'nada para enviar para a data {date}')
for local, remote in files: upload(local, remote)
print(f'{len(files)} arquivos enviados ao Dropbox ({acct.get("email")})')

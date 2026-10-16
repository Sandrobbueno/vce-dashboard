# vce-dashboard · Formação Lean Volvo CE (escolas ES e PT)

Repositório privado da Lean Dealers. Toda segunda às 07:30 (Brasília) o GitHub Actions:
1. testa o alcance de `api.hotscool.com`;
2. para cada escola (`es` = dealers hispânicos, `pt` = dealers brasileiros), roda `extract.py --lang` (chaves nos segredos `HOTSCOOL_KEY_ES` / `HOTSCOOL_KEY_PT`) e grava `history/dump_<lang>_<data>.json`;
3. roda `build.py --lang` e grava `out/<lang>/<data>/` (dashboard HTML e texto de e-mail por dealer, consolidado interno, `resumen.json`, `textos_email.txt`);
4. tenta gerar os PDFs datados em `04_PDFs_Semanais/`;
5. passa pela guarda de confidencialidade;
6. **envia os PDFs datados e as saídas para a pasta do Dropbox** `Brazil LEAN/Universidades Lean/VCE/Turmas 2026` (`04_PDFs_Semanais/` com `<data>_<Dealer>_Avance_Semanal.pdf` (ES) e `<data>_<Dealer>_Avanco_Semanal.pdf` (PT), consolidados `_ES`/`_PT`, textos `Textos_Email_ES/PT`; e `03_Dashboard/`), via API do Dropbox com os segredos `DROPBOX_APP_KEY`, `DROPBOX_APP_SECRET`, `DROPBOX_REFRESH_TOKEN`;
7. faz o commit.

O e-mail aos dealers é enviado **pelo Sandro, à mão**, com o PDF do dealer anexado; `out/<data>/<dealer>_email.html` traz um texto curto em espanhol para copiar. Às 07:51 a tarefa agendada do Claude só confere a rodada, registra os números no doc do projeto e manda um resumo ao Sandro. Regras de cálculo e de confidencialidade: `ROTINA.md`.

**Fonte de verdade** do pipeline: este repositório. `config_es.json` e `config_pt.json` têm roster, dealers e composição das trilhas de cada escola. O Dropbox recebe cópias das saídas.

Rodar à mão: aba **Actions** → "Extração e dashboards semanais (Volvo CE)" → **Run workflow**.

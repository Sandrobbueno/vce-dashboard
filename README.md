# vce-dashboard · Formación Lean Volvo CE

Repositório privado da Lean Dealers. Toda segunda às 07:30 (Brasília) o GitHub Actions:
1. testa o alcance de `api.hotscool.com`;
2. roda `extract.py` (chave no segredo `HOTSCOOL_KEY_ES`) e grava `history/dump_es_<data>.json`;
3. roda `build.py` e grava `out/<data>/` (dashboard HTML e corpo de e-mail por dealer, consolidado interno, `resumen.json`);
4. tenta gerar os PDFs datados em `04_PDFs_Semanais/`;
5. passa pela guarda de confidencialidade;
6. **envia os PDFs datados e as saídas para a pasta do Dropbox** `Brazil LEAN/Universidades Lean/VCE/Turmas 2026` (`04_PDFs_Semanais/` e `03_Dashboard/`), via API do Dropbox com os segredos `DROPBOX_APP_KEY`, `DROPBOX_APP_SECRET`, `DROPBOX_REFRESH_TOKEN`;
7. faz o commit.

O e-mail aos dealers é enviado **pelo Sandro, à mão**, com o PDF do dealer anexado; `out/<data>/<dealer>_email.html` traz um texto curto em espanhol para copiar. Às 07:51 a tarefa agendada do Claude só confere a rodada, registra os números no doc do projeto e manda um resumo ao Sandro. Regras de cálculo e de confidencialidade: `ROTINA.md`.

**Fonte de verdade** do pipeline (config, roster, destinatários, scripts): este repositório. O Dropbox recebe cópias das saídas.

Rodar à mão: aba **Actions** → "Extração e dashboards semanais (Volvo CE)" → **Run workflow**.

# vce-dashboard · Formación Lean Volvo CE

Repositório privado da Lean Dealers. Toda segunda às 07:30 (Brasília) o GitHub Actions:
1. testa o alcance de `api.hotscool.com`;
2. roda `extract.py` (chave no segredo `HOTSCOOL_KEY_ES`) e grava `history/dump_es_<data>.json`;
3. roda `build.py` e grava `out/<data>/` (dashboard HTML e corpo de e-mail por dealer, consolidado interno, `resumen.json`);
4. tenta gerar os PDFs datados em `04_PDFs_Semanais/`;
5. passa pela guarda de confidencialidade e faz o commit.

Às 07:51 a tarefa agendada do Claude ("Dashboard semanal Volvo CE (segundas)") clona este repositório, pega a rodada mais recente em `out/`, grava as saídas no Dropbox (`Brazil LEAN/Universidades Lean/VCE/Turmas 2026`) e cria os rascunhos de e-mail no Outlook do Sandro. Regras de cálculo e de confidencialidade: `ROTINA.md`.

**Fonte de verdade** do pipeline (config, roster, destinatários, scripts): este repositório. O Dropbox recebe cópias das saídas.

Rodar à mão: aba **Actions** → "Extração e dashboards semanais (Volvo CE)" → **Run workflow**.

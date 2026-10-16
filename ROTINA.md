# Dashboard semanal · Formación Lean Volvo CE (dealers hispânicos)

Fonte de verdade: repositório privado GitHub `Sandrobbueno/vce-dashboard` (desde 16/10/2026). Cópia das saídas no Dropbox: `Brazil LEAN/Universidades Lean/VCE/Turmas 2026`. Criado em 14/10/2026.

## Arquitetura (16/10/2026)
A rede das tarefas agendadas do Claude bloqueia `api.hotscool.com` e a liberação feita no ambiente de nuvem "Default" não se aplica a elas (testado em 14 e 16/10). Por isso o trabalho é dividido:
1. **GitHub Actions** (`.github/workflows/semanal.yml`), segunda 07:30 Brasília: testa a API, extrai, gera HTML/e-mail/PDF, passa pela guarda de confidencialidade e faz commit em `history/`, `out/` e `04_PDFs_Semanais/`. A chave da Hotscool fica no segredo `HOTSCOOL_KEY_ES` do repositório, nunca no código.
2. **Tarefa agendada do Claude**, segunda 07:51: clona este repositório, pega a rodada mais recente, grava as saídas no Dropbox e cria os rascunhos no Outlook. Não chama a API.
Se a rodada do Actions falhar, a tarefa do Claude encontra `out/` sem a data do dia e para, avisando o Sandro. Alternativa manual: rodada no chat com o Mac ligado (extract.js pelo navegador interno).

## Estrutura da pasta Turmas 2026 (reorganizada em 14/10/2026)
| Pasta | Conteúdo |
|---|---|
| `00_Chaves_API/` | `chave_api_es.txt` (escola em espanhol) e, quando existir, `chave_api_pt.txt`. Só a chave, nada mais. Não copiar para outro lugar. |
| `01_Inscricoes/` | Planilha de interessados e lista de bloqueio. |
| `02_Importacao_Plataforma/` | CSVs importados na Hotscool por programa e idioma, e os não importáveis. **É a origem do roster.** |
| `03_Dashboard/` | Este pipeline (abaixo). |
| `04_PDFs_Semanais/` | Um PDF por dealer e por semana, nome `AAAA-MM-DD_<Dealer>_Avance_Semanal.pdf`, mais `AAAA-MM-DD_Consolidado_Interno.pdf`. Para enviar, pegar sempre a data mais recente. |

## O que é
Um e-mail por dealer (CDM, Ascendum, Rieder), em espanhol, toda segunda, com inscritos, situação e avanço de cada participante nas duas formações (Expertos Lean 2026 e Liderazgo Lean), mais a evolução semanal. Cada dealer vê **só a sua gente**. Há também um consolidado interno (português) com todos os dealers, os inscritos sem cadastro e quem está na plataforma fora do roster.

## Arquivos
| Arquivo | Para quê |
|---|---|
| `config.json` | A fonte de verdade: trilhas (cursos que compõem cada uma), dealers, **destinatários**, roster (quem é da turma) e exclusões. É o único arquivo que o Sandro edita. |
| `extract.py` | Extração direta da API (quando `api.hotscool.com` for alcançável). Grava `history/dump_es_AAAA-MM-DD.json`. |
| `extract.js` | Mesma extração pelo navegador interno do app Claude (caminho atual, API bloqueada no ambiente em nuvem). |
| `build.py` | Gera `out/<data>/`: `<dealer>.html` (dashboard completo), `<dealer>_email.html` (corpo do e-mail), `consolidado.html`, `resumen.json`. |
| `build.py.b64` | Cópia do `build.py` em base64. **Em sessão na nuvem, ler esta e decodificar**: o `fetch` do conector do Dropbox apaga as tags HTML de dentro das strings do `.py` e quebra o gerador. |
| `pdf.py` | Converte os HTML em PDF (A4 paisagem) com o Chromium do Playwright e grava as cópias datadas em `../04_PDFs_Semanais/`. |
| `history/` | Um dump por semana. É daqui que sai a coluna Δ (vs. dump anterior) e a série "Evolução semanal". **Nunca apagar.** |
| `out/<data>/` | Saídas de cada semana (HTML, e-mail, PDF, resumen.json). |

A chave da API está em `../00_Chaves_API/chave_api_es.txt` (só a chave, 96 caracteres hexadecimais). `extract.py` lê a variável `HOTSCOOL_KEY_ES` ou esse arquivo. Nunca entra em HTML, dump ou e-mail.

## Regras de cálculo (decididas em 14/10/2026)
1. **Roster manda.** Quem é da turma vem das planilhas de importação (16 e 18/09), transcritas no `config.json`. A plataforma só informa progresso. Motivo: 6 líderes de Costa Rica e Rieder já existiam com cadastro de 2025 e cargos antigos; Katherina Bolaños (CDM) não existe na plataforma. Pessoa na trilha mas fora do roster aparece só no consolidado interno ("extras").
2. **Expertos Lean 2026 = 5 cursos**: Valor (24185), 5S (24475), Gemba (25040), Kanban (25757), Herramientas (25792). A API não expõe a composição da trilha (403). Os alunos de 2025 também fizeram Fundamentos e Planteando Problemas; esses cursos não contam.
3. **Liderazgo Lean = só o curso Liderazgo Lean (25023)**. Líder que também percorre a trilha Expertos aparece com o % dela numa coluna à parte ("También en Expertos"), sem entrar no avanço do programa.
4. **% da trilha = média simples dos cursos**; curso sem relatório = 0; concluído = 100.
5. **Avanço médio do dealer = média sobre os inscritos** (sem cadastro conta 0). Denominador estável semana a semana.
6. **"Accedieron" = último login a partir de 18/09/2026** (início da turma). Login de 2025 não conta.
7. Situação: Sin registro (não está na plataforma) · Sin acceso (sem login desde o início e 0%) · No inició (acessou, 0%) · En curso · Concluido (100%).
8. Δ sem. = avanço de hoje menos o do dump anterior, em pontos percentuais. Na primeira semana fica "—".
9. Excluídos de tudo: domínios `leandealers.com` e `hotscool.com` (Sandro e Nei têm cadastro na plataforma).
10. Privacidade: dump e HTML só carregam nome, e-mail, unidade, cargo, datas de acesso e progresso. A API expõe CPF, telefone, endereço e nascimento; nada disso entra.
11. **Confidencialidade entre dealers (regra fixa, 14/10/2026).** Nenhuma saída individual (dashboard, PDF ou e-mail de um dealer) mostra média da rede, ranking, total da turma ou qualquer dado de outro dealer. O dealer só vê e sabe do dele por nós; se a Volvo CE quiser comparar, a responsabilidade é dela. Só o consolidado interno (uso Lean Dealers) junta todos. O `build.py` tem uma guarda que aborta a geração se uma saída individual citar a rede ou o nome de outro dealer; não remover.

## Rotina de segunda
### A. Extrair
- **Se `api.hotscool.com` estiver liberado na rede do Claude** (Admin → Capabilities): `python3 extract.py` (lê a chave de `../00_Chaves_API/chave_api_es.txt` ou de `HOTSCOOL_KEY_ES`).
- **Se não**: abrir `https://api.hotscool.com/v1/api-docs/` no navegador interno do app, rodar `extract.js` (com a chave e o roster do `config.json`), conferir a soma de controle (linhas, soma dos %, nº de certificados) depois de transferir, gravar `history/dump_es_AAAA-MM-DD.json`. Exige o Mac ligado e o app aberto.
- Nos dois casos, teste rápido antes de prosseguir: `curl -sS -o /dev/null -w "%{http_code}" https://api.hotscool.com/v1/api-docs/` tem que dar 200.

### B. Gerar
`python3 build.py` e depois `python3 pdf.py` (gera os PDFs datados em `04_PDFs_Semanais/`). O terminal imprime os números por dealer: comparar com a semana anterior antes de enviar. Movimento brusco (avanço médio caindo, inscritos mudando) é motivo para parar e investigar, não para enviar.

### C. Enviar
- Um e-mail por dealer para os `destinatarios` do `config.json`, com `copia` em cópia. Assunto: `Formación Lean Volvo CE · Avance semanal <Dealer> · <data>`.
- O corpo é o `<dealer>_email.html`. O conector do Outlook **não anexa arquivos** e só aceita HTML básico (sem CSS, sem imagem): o dashboard viaja como tabelas no corpo. O PDF completo é para quando a rodada é feita no chat com o Sandro (enviar à mão se quiser).
- Enquanto a lista de destinatários estiver vazia ou o Sandro não autorizar envio automático: **criar rascunho** no Outlook do Sandro (ele revisa e envia), nunca enviar direto.
- Não enviar nada se a extração falhou ou se o dump é o mesmo da semana anterior.

### D. Guardar e registrar
- `history/dump_es_<data>.json` e `out/<data>/` ficam nesta pasta; os PDFs datados em `../04_PDFs_Semanais/`.
- Registrar os números do `resumen.json` no doc do projeto Volvo CE no Claude (`claude/painel-vce-status-semanal.md`).

## Pendências abertas (14/10/2026)
- Destinatários por dealer (nome + e-mail) ainda não informados → `config.json` → `dealers.*.destinatarios`.
- Liberação de `api.hotscool.com` na política de rede do Claude (decide se a tarefa agendada roda sozinha).
- Katherina Bolaños (CDM, Liderazgo) sem cadastro na plataforma: cadastrar ou tirar do roster.
- Turma em português (Brasil): mesma estrutura; precisa da chave da escola em português (`00_Chaves_API/chave_api_pt.txt`) e do roster das planilhas `02_Importacao_Plataforma/*/Portugues - Brasil/importacao_BRASIL_*.csv`.
- Primeiro envio: Ascendum (1%) e Rieder (1%, 2 de 10 acessaram) vão receber um retrato ruim. Recomendação: o Sandro envia a primeira semana pessoalmente com uma mensagem de contexto; a automação assume da segunda em diante.

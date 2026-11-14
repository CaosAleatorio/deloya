# Verificação técnica

Executar os testes em PostgreSQL **isolado**, sem dados reais. Resultados concretos deste ambiente são registados em [VALIDATION.md](VALIDATION.md). Não afirmar sucesso por ter instalado dependências ou escrito testes.

## Frontend

Em `frontend/`, após `npm ci`:

```powershell
npm run lint
npx tsc --noEmit
npm test
npm run build
```

Lint e TypeScript verificam problemas estáticos; build confirma a compilação. Testes essenciais devem validar o contrato HTTP/CSRF e a apresentação de demonstração quando aplicável. Estes comandos não demonstram, por si só, que a navegação móvel funciona num browser.

## Backend

Instalar dependências de `backend/requirements.txt` num ambiente Python 3.13. Criar explicitamente a base dedicada; o helper lê o `.env` em memória, deriva `deloya_test` a partir da configuração local e não imprime credenciais. A partir da raiz:

```powershell
docker compose exec -T db createdb -U deloya deloya_test
./.venv/Scripts/python.exe scripts/test-backend.py -q
```

Se `deloya_test` já existir, não repetir `createdb`. Para PostgreSQL nativo, criar a base com as ferramentas locais e manter as URLs correctas. `TEST_DATABASE_URL`, quando definida explicitamente, substitui a derivação; tanto o helper como a fixture exigem PostgreSQL e nome terminado em `_test`. **As tabelas da base indicada são limpas entre testes.** Nunca apontar esta variável a dados a preservar. O comando directo `python -m pytest -q` em `backend/` requer a variável correctamente exportada; sem ela, os testes de integração podem ser ignorados, o que não demonstra sucesso.

Os testes de segurança/negócio abrangem registo, login/logout, JWT inválido/expirado, refresh replay, CSRF, loja pendente, IDOR cliente/vendedor, total no servidor, carrinho multivendedor, stock concorrente, cancelamento e pagamentos repetidos/falhados conforme os ficheiros da suite. Concorrência precisa de transacções PostgreSQL reais; SQLite ou mocks não comprovam bloqueio de stock.

O teste de relatórios deve incluir encomendas junto da meia-noite de Maputo: 22:00 UTC do dia anterior pertence ao dia local seguinte. Validar também autorização da loja, filtro de categoria sem duplicações e intervalo invertido.

## Ensaio manual de interface

### Testes opcionais no navegador

Com a API, PostgreSQL e frontend locais em execução, num ambiente de demonstração com o seed carregado, executar na raiz:

```powershell
npm install --prefix .local/browser-qa --no-audit --no-fund playwright @axe-core/playwright
$env:PLAYWRIGHT_BROWSERS_PATH = Join-Path (Get-Location) '.local/browsers'
./.local/browser-qa/node_modules/.bin/playwright.cmd install chromium
node scripts/browser-smoke.mjs
node scripts/accessibility-smoke.mjs
```

O teste funcional cria uma conta e uma encomenda **demonstrativas**, percorre as áreas de cliente, vendedor e administrador, e verifica a navegação móvel. Recusa produtos sem o indicador demonstrativo. Usa `DEMO_PASSWORD` apenas do `.env` privado, sem a imprimir. `--panels-only` permite rever as páginas de gestão sem repetir a compra. Capturas e relatórios ficam em `.local/browser-results/`, fora do Git. `QA_BASE_URL` permite mudar a origem de testes explicitamente.

A análise axe verifica quatro páginas em larguras de 1440 e 390 px. Um resultado sem violações automáticas não substitui avaliação manual de acessibilidade ou os testes de utilizadores da monografia.

| Cenário | Verificação | Evidência a recolher |
| --- | --- | --- |
| Telemóvel 360 px | Menu, pesquisa, cards, formulários e checkout sem scroll horizontal indevido | Capturas e problemas observados |
| Tablet/desktop | Filtros, grelhas e painéis legíveis | Capturas 768/1440 px |
| Teclado | Skip link, foco, labels, modal e botões operáveis | Grelha de tarefas |
| API indisponível | Erro honesto e opção de tentar novamente | Captura sem fixtures artificiais |
| Catálogo vazio | Mensagem de estado vazio | Base sem seed |
| Compra duas lojas | Duas parcelas e totais coerentes | Encomenda demonstrativa anonimizada |
| Pagamento | Rótulo inequívoco, sucesso/falha/expiração | Estado no browser e API |
| Vendedor/admin | Acesso correcto e moderação | Tentativas permitidas/rejeitadas |

Não confundir estes ensaios técnicos com os cinco testes de utilizadores da monografia. Consentimento académico e recolha de investigação seguem [ACADEMIC_EVALUATION.md](ACADEMIC_EVALUATION.md).

## Registo

Registar data, comando, versão/SHA, ambiente, quantidade de testes executados, falhas/skips e bloqueios. Guardar artefactos locais em pasta ignorada e sem tokens/passwords. Repetir uma verificação depois de alterar os ficheiros a que ela se refere. Publicar resultados apenas do que foi efectivamente executado.

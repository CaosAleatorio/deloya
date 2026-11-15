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

Lint e TypeScript verificam problemas estáticos; build confirma a compilação. Testes essenciais devem validar o contrato HTTP/CSRF e a identificação de dados de teste quando aplicável. A navegação móvel é verificada separadamente num browser.

## Backend

Instalar dependências de `backend/requirements.txt` num ambiente Python 3.13. Criar explicitamente a base dedicada; o helper lê o `.env` em memória, deriva `deloya_test` a partir da configuração local e não imprime credenciais. A partir da raiz:

```powershell
docker compose exec -T db createdb -U deloya deloya_test
./.venv/Scripts/python.exe scripts/test-backend.py -q
```

Se `deloya_test` já existir, não repetir `createdb`. Para PostgreSQL nativo, criar a base com as ferramentas locais e manter as URLs correctas. `TEST_DATABASE_URL`, quando definida explicitamente, substitui a derivação; tanto o helper como a fixture exigem PostgreSQL e nome terminado em `_test`. **As tabelas da base indicada são limpas entre testes.** Nunca apontar esta variável a dados a preservar. O comando directo `python -m pytest -q` em `backend/` requer a variável correctamente exportada; sem ela, os testes de integração podem ser ignorados, o que não comprova sucesso.

Os testes de segurança/negócio abrangem registo, login/logout, JWT inválido/expirado, refresh replay, CSRF, loja pendente, IDOR cliente/vendedor, total no servidor, carrinho multivendedor, stock concorrente, cancelamento e pagamentos repetidos/falhados conforme os ficheiros da suite. Concorrência precisa de transacções PostgreSQL reais; SQLite ou mocks não comprovam bloqueio de stock.

`test_manual_payments.py` cobre destinatários privados, snapshot, total/taxa no servidor, confirmação por loja, pagamento parcial, idempotência, referências repetidas, concorrência e loja suspensa. O runner fixa `PAYMENT_MODE=demo` para regressões legadas; os testes manuais configuram o seu próprio modo sem alterar `.env`. `test_private_attachments.py` verifica titularidade, ficheiros inválidos, quotas e falhas de armazenamento; chamadas Blob são simuladas. `test_blob_sessions.py` exercita o SDK instalado com transporte HTTP controlado. `test_request_limits.py` verifica limites antes do parser, incluindo corpos sem Content-Length.

O teste de relatórios deve incluir encomendas junto da meia-noite de Maputo: 22:00 UTC do dia anterior pertence ao dia local seguinte. Validar também autorização da loja, filtro de categoria sem duplicações e intervalo invertido.

## Ensaio manual de interface

### Testes opcionais no navegador

Com a API, PostgreSQL e frontend locais em execução, num ambiente de teste com o seed carregado, executar na raiz:

```powershell
npm install --prefix .local/browser-qa --no-audit --no-fund playwright @axe-core/playwright
$env:PLAYWRIGHT_BROWSERS_PATH = Join-Path (Get-Location) '.local/browsers'
./.local/browser-qa/node_modules/.bin/playwright.cmd install chromium
node scripts/browser-smoke.mjs
node scripts/accessibility-smoke.mjs
node scripts/auth-form-regression.mjs
```

O teste funcional cria uma conta e uma encomenda **de teste**, percorre as áreas de cliente, vendedor e administrador, e verifica a navegação móvel. Recusa produtos sem o indicador interno `is_demo`. Usa `DEMO_PASSWORD` apenas do `.env` privado, sem a imprimir. `--panels-only` permite rever as páginas de gestão sem repetir a compra. Capturas e relatórios ficam em `.local/browser-results/`, fora do Git. `QA_BASE_URL` permite mudar a origem de testes explicitamente.

`browser-smoke.mjs` é o roteiro legado do simulador e requer `PAYMENT_MODE=demo` num ambiente de teste próprio. O fluxo manual e os anexos têm regressões adicionais, executadas na raiz com o frontend disponível e as ferramentas Playwright acima instaladas:

```powershell
node frontend/tests/manual-payments.browser.mjs
node frontend/tests/support-attachments.browser.mjs
```

Estas duas regressões interceptam as respostas API no browser: não criam transferências, encomendas ou ficheiros remotos. Exercitam desktop/telemóvel, estados parciais, referências por loja, confirmação/recusa e anexos privados. A suite backend complementa a UI com transacções PostgreSQL reais. Nenhuma destas verificações locais confirma armazenamento ou publicação online.

A análise axe verifica quatro páginas em larguras de 1440 e 390 px. Um resultado sem violações automáticas deve ser complementado por avaliação manual de acessibilidade.

A regressão dos formulários verifica login e registo com JavaScript activo e desactivado, incluindo uma submissão nativa forçada que deve usar POST e nunca credenciais na query string. As respostas de autenticação deste script são simuladas e não criam contas na base de dados. Para testar a hidratação num IP da rede, configurar as origens conforme o README e definir `QA_BASE_URL` para esse endereço antes de executar o script.

| Cenário | Verificação | Evidência a recolher |
| --- | --- | --- |
| Telemóvel 360 px | Menu, pesquisa, cards, formulários e checkout sem scroll horizontal indevido | Capturas e problemas observados |
| Tablet/desktop | Filtros, grelhas e painéis legíveis | Capturas 768/1440 px |
| Teclado | Skip link, foco, labels, modal e botões operáveis | Grelha de tarefas |
| API indisponível | Erro honesto e opção de tentar novamente | Captura sem fixtures artificiais |
| Catálogo vazio | Mensagem de estado vazio | Base sem seed |
| Compra duas lojas | Duas parcelas e totais coerentes | Encomenda de teste anonimizada |
| Pagamento | Rótulo inequívoco, sucesso/falha/expiração | Estado no browser e API |
| Vendedor/admin | Acesso correcto e moderação | Tentativas permitidas/rejeitadas |

Executar as tarefas com dados de teste e registar os problemas observados, sem incluir contactos, moradas ou credenciais pessoais nos artefactos.

## Registo

Registar data, comando, versão/SHA, ambiente, quantidade de testes executados, falhas/skips e bloqueios. Guardar artefactos locais em pasta ignorada e sem tokens/passwords. Repetir uma verificação depois de alterar os ficheiros a que ela se refere. Publicar resultados apenas do que foi efectivamente executado.

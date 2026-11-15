# Publicação — Neon, FastAPI, Blob e Next.js

Deloya Marketplace — Adelino Fonseca João, 2026.

Revisto em **15/11/2026**. Registar execução e evidências em [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md). Este guia não confirma recursos criados ou URLs publicados.

## Contas, planos e região

Usar contas do proprietário e confirmar o plano. Não activar subscrições, períodos experimentais pagos ou cobranças sem autorização.

| Serviço | Capacidade gratuita consultada | Limitação relevante |
| --- | --- | --- |
| Neon Free | 100 projectos; 100 CU-h/mês e 1 GB PostgreSQL por projecto; 10 branches; 5 GB/mês de transferência pública por projecto | 20 GB PostgreSQL totais por conta/organização; compute suspende ao esgotar CU-h ou transferência. |
| Vercel Hobby | Dois projectos cabem no limite de 200; Functions Fluid com 2 GB e até 300 s; uma região por projecto | Termos reservam Hobby a uso pessoal ou não comercial. Operação comercial requer plano apropriado e autorização de custos. |
| Blob Hobby | 1 GB-mês; 10 000 operações simples; 2 000 avançadas; 10 GB de transferência | Quotas partilhadas; exceder pode interromper acesso. Armazenamento privado disponível em todos os planos. |

Estes valores não garantem capacidade para tráfego contínuo ou comércio real. No Neon Free o compute desliga após cinco minutos sem actividade; evitar monitores que mantenham a base permanentemente activa. Fontes: [Neon](https://neon.com/pricing), [Hobby](https://vercel.com/docs/plans/hobby), [termos Vercel, secção 4](https://vercel.com/legal/terms), [Blob](https://vercel.com/docs/vercel-blob/usage-and-pricing).

Ponto de partida recomendado: Neon **`aws-eu-central-1`**, Functions dos dois projectos e Blob em **`fra1`**, Frankfurt. Mantém API, base e armazenamento na mesma região; recomendação de arquitectura, sem medição de latência a partir de Maputo. Neon não lista região africana. Confirmar disponibilidade na conta antes da criação; a região Neon e a região Blob não podem mudar posteriormente. Fontes: [regiões Neon](https://neon.com/docs/introduction/regions), [Vercel](https://vercel.com/docs/regions), [Functions](https://vercel.com/docs/functions/configuring-functions/region), [Blob](https://vercel.com/docs/vercel-blob#choosing-your-blob-store-region).

## Ferramentas e autenticação

Para criar contas, abrir [Neon Console](https://console.neon.tech/) e [Vercel Sign Up](https://vercel.com/signup); é possível usar o GitHub como identidade. Autorizar no navegador, sem copiar tokens para o chat. A instalação local das ferramentas fica em `.local/deploy-cli`, ignorada pelo Git.

No PowerShell, cada comando abre o fluxo de autorização do respectivo serviço:

```powershell
npx --yes neon@9.5.0 login
npx --yes vercel@65.16.0 login
```

Concluir um login antes de iniciar o outro. Criar conta e autorizar a CLI não cria automaticamente a base nem publica o site. Confirmar plano/scope antes dos passos seguintes. Fontes: [Neon login](https://neon.com/docs/cli/login), [Vercel login](https://vercel.com/docs/cli/login).

Versões publicadas consultadas no registo npm em 15/11/2026: `vercel@65.16.0` (Node >=20), `neon@9.5.0` (Node >=20.19.0). `neonctl@9.5.0` oferece ambos os comandos `neon` e `neonctl`. Node 22.19 satisfaz ambos. Registar as versões efectivamente instaladas. Fontes: [CLI Neon](https://neon.com/docs/cli), [pacote Vercel](https://www.npmjs.com/package/vercel), [pacote Neon](https://www.npmjs.com/package/neon).

```powershell
vercel --version
neon --version
vercel whoami
neon me
```

Se necessário, usar `vercel login` e `neon login` no browser. Nunca colocar tokens no Git, chat ou argumentos guardados no histórico. Neon também aceita `NEON_API_KEY`; contas geridas pela integração Vercel podem precisar dessa chave. `neon me` indica sessão sem iniciar login automático. Fonte: [login Neon](https://neon.com/docs/cli/login).

Neon documenta `~/.config/neon/credentials.json`; instalações antigas usavam `~/.config/neonctl/credentials.json`. Vercel mantém `auth.json`/`config.json` no directório global `com.vercel.cli`, determinado por XDG/Windows ou `--global-config`. Não copiar nem imprimir estes ficheiros. Fontes: [configuração Vercel](https://vercel.com/docs/project-configuration/global-configuration), [CLI Neon antigo](https://github.com/neondatabase/neonctl/blob/main/src/config.ts).

Projectos temporários sem login e bases Neon não reclamadas não substituem recursos permanentes do proprietário.

## 1. Neon — criar base e tabelas

Confirmar a organização Free, listar projectos e reutilizar o correcto quando existir. Criar uma base vazia, isolada da base local/testes:

```powershell
neon projects list
neon projects create --name deloya --database deloya --role deloya_owner --pg-version 17 --region-id aws-eu-central-1 --cu 0.25 --no-secrets
```

PostgreSQL 17 corresponde ao ambiente de testes. `--no-secrets` impede impressão da password. Registar IDs de projecto/branch devolvidos; não inventar hosts/credenciais. Fonte: [projectos Neon](https://neon.com/docs/cli/projects).

Obter ligações **em memória**, indicando IDs reais. Os valores contêm passwords e não devem aparecer nos logs:

```powershell
$deloyaPooledUrl = (neon connection-string $deloyaNeonBranchId --project-id $deloyaNeonProjectId --database-name deloya --role-name deloya_owner --pooled --ssl require).Trim()
$deloyaDirectUrl = (neon connection-string $deloyaNeonBranchId --project-id $deloyaNeonProjectId --database-name deloya --role-name deloya_owner --ssl require).Trim()
```

Guardar pooled em `DATABASE_URL` e directa em `DATABASE_DIRECT_URL` pelo mecanismo privado de segredos. Preservar `sslmode=require` e os restantes parâmetros Neon. Host pooled inclui `-pooler`. Fontes: [connection-string](https://neon.com/docs/cli/connection-string), [pooling](https://neon.com/docs/connect/connection-pooling).

A API tem `pool_pre_ping`, timeout de 10 s e até dez ligações por processo (`pool_size=5`, `max_overflow=5`). O limite multiplica-se pelas instâncias: observar conexões/utilização ao escalar. Alembic usa ligação directa e `NullPool`. Não executar migrações por import/startup das Functions.

Carregar variáveis num processo de release isolado e confirmar que apontam para o Neon correcto. A partir de `backend`:

```powershell
..\.venv\Scripts\python.exe -m alembic heads
..\.venv\Scripts\python.exe -m alembic upgrade head
..\.venv\Scripts\python.exe -m alembic current
```

`current` deve coincidir com a única `head`, incluindo `private_attachments`. Não executar seed ou copiar a base local. Base existente exige backup antes da migração; base nova recebe apenas esquema e registos operacionais explicitamente autorizados.

## 2. Vercel — publicar FastAPI

Criar dois projectos no mesmo scope, associados a `CaosAleatorio/deloya`. Nomes abaixo são propostas, sujeitos à disponibilidade; obter URLs reais da plataforma.

| Projecto | Root Directory | Framework/runtime | Configuração |
| --- | --- | --- | --- |
| `deloya-api` | `backend` | FastAPI; Python 3.13 | `index.py` exporta `app`; instalação detectada; sem migrações no build. |
| `deloya` | `frontend` | Next.js; Node 22.x | `npm ci`; `npm run build`; saída Next.js detectada. |

Reservar projectos e confirmar domínio canónico frontend antes de configurar `FRONTEND_ORIGIN`. Isto prepara configuração sem alterar a ordem de publicação.

```powershell
vercel project create deloya-api --scope $deloyaVercelScope
vercel project update deloya-api --root-directory backend --framework fastapi --scope $deloyaVercelScope --yes
vercel project create deloya --scope $deloyaVercelScope
vercel project update deloya --root-directory frontend --framework nextjs --node-version 22.x --install-command "npm ci" --build-command "npm run build" --scope $deloyaVercelScope --yes
```

Executar CLI na **raiz do repositório**, seleccionando um projecto por vez com `vercel link --project ... --scope ...`. Root Directory é relativo a essa raiz. Seleccionar `fra1` nas configurações de Functions dos dois projectos. Fontes: [monorepos](https://vercel.com/docs/monorepos), [project create/update](https://vercel.com/docs/cli/project), [link](https://vercel.com/docs/cli/link).

Variáveis **Production** do backend:

| Nome | Valor/uso |
| --- | --- |
| `ENVIRONMENT` | `production` |
| `DATABASE_URL` | Neon pooled com TLS; segredo. |
| `DATABASE_DIRECT_URL` | Directa com TLS para release; segredo. |
| `JWT_SECRET` | Aleatório próprio desta instalação, mínimo 32 caracteres; segredo. |
| `FRONTEND_ORIGIN` | Origem HTTPS canónica real frontend, sem caminho/wildcard. |
| `COOKIE_SECURE` | `true` |
| `PAYMENT_MODE` | `manual` permite transferências directas declaradas e confirmadas pelo vendedor; `disabled` impede novos pagamentos; `demo` restringe ao simulador de teste. Nenhum activa APIs das operadoras. |
| `BLOB_PRIVATE_READ_WRITE_TOKEN` | Credencial store privado após passo 3; segredo. |
| `BLOB_READ_WRITE_TOKEN` / `BLOB_PUBLIC_BASE_URL` | Credencial/origem store público se forem activados uploads de catálogo. |

Browser usa `/api/v1` no domínio frontend; Next encaminha para API. Cookies/CSRF exigem domínio canónico correcto. `DEVELOPMENT_FRONTEND_ORIGINS` e `DEV_ALLOWED_HOSTS` não são necessárias em produção. Nenhum segredo usa `NEXT_PUBLIC_`.

Confirmar Python **3.13** nos logs: `requires-python = ">=3.13"` isoladamente não fixa versão menor, pois Vercel também suporta 3.14. `backend/index.py` exporta a aplicação existente; FastAPI torna-se uma Function. Fontes: [FastAPI](https://vercel.com/docs/frameworks/backend/fastapi), [Python](https://vercel.com/docs/functions/runtimes/python).

Com API seleccionada, executar `vercel deploy --prod`. Confirmar Ready e testar `https://<dominio-real-api>/health`: `status: ok` e `database: ok`. Guardar URL real para passo 4. Excluir `.env`, credenciais, `.local`, `.venv`, dumps e bases locais do upload.

## 3. Vercel Blob — anexos privados

Store privado serve anexos de suporte; imagens do catálogo usam store público separado. Private Blob tem disponibilidade geral em todos os planos desde Junho de 2026. Fonte: [anúncio oficial](https://vercel.com/changelog/vercel-private-blob-is-now-generally-available).

Com projecto API seleccionado:

```powershell
vercel blob list-stores --all --json
vercel blob create-store deloya-anexos --access private --region fra1 --environment production
```

Identificar store antes de criar outro. CLI solicita ligação ao projecto; `--yes` auto-conecta e, sem `--environment`, inclui todos ambientes. Não partilhar anexos/credenciais de produção com Preview/Development. Capturar saídas sem expor credenciais. `--json` não está documentado para `create-store`. Fonte: [CLI Blob](https://vercel.com/docs/cli/blob).

Configurar credencial privada em **`BLOB_PRIVATE_READ_WRITE_TOKEN`** no backend. Integração pode criar `BLOB_READ_WRITE_TOKEN` automaticamente: conferir mapeamento, pois aqui esse nome pertence ao catálogo público. Prefixo pode ser escolhido nas opções avançadas da ligação. Não substituir um token pelo outro. Fontes: [ligação de stores](https://vercel.com/docs/vercel-blob/client-upload), [SDK Python](https://vercel.com/docs/vercel-blob/python-sdk-reference).

Publicar API novamente após configurar segredo. Verificar upload/lista/download/remoção pelas rotas autenticadas, com controlo de titular/admin. Acesso directo ao objecto privado sem credencial e acesso por terceiro devem falhar.

Limites da aplicação: **3 MiB** por anexo e dez por pedido de suporte, com validação de conteúdo. Payload das Functions: 4.5 MB incluindo multipart. Bundle Python padrão: 500 MB descomprimidos. Não elevar limites sem rever percurso nos dois projectos. Fonte: [limites Functions](https://vercel.com/docs/functions/limitations).

Desde Setembro de 2026 número de stores não tem limite antigo; cada criação conta como operação avançada e não aumenta quotas gratuitas. Fonte: [limites de stores](https://vercel.com/changelog/unlimited-vercel-blob-stores-on-every-plan).

## 4. Vercel — publicar Next.js

Seleccionar frontend e configurar **`BACKEND_URL`** em Production com origem HTTPS real/estável da API, sem `/api/v1` no fim. Rewrite acrescenta esse caminho. Variável fica no servidor e não precisa de `NEXT_PUBLIC_`.

Confirmar `npm ci`, testes, lint, TypeScript e `npm run build` antes de `vercel deploy --prod`. Alterar `BACKEND_URL` exige novo build para actualizar rewrite.

No domínio final, verificar registo/login sem credenciais na URL, logout, renovação, catálogo, carrinho, encomenda, painéis e anexos. Testar pelo frontend: healthcheck da API não verifica cookies/proxy/CSRF. Preview tem outra origem; usar ambiente/dados isolados.

Confirmar que Deployment Protection não apresenta login Vercel ao proxy em vez da API. Endpoints privados mantêm autenticação da aplicação.

## Operação e rollback

Registar SHA Git, deployment IDs/URLs, região, revisão Alembic e verificações na checklist, sem segredos/dados pessoais. Criar primeiro administrador pelo procedimento privado `python -m app.bootstrap_admin --email <email-do-proprietario>`, com `ADMIN_PASSWORD` fora do código. Não inventar identidade ou reutilizar passwords de teste.

Preparar backup e ensaiar restauro antes de dados operacionais. Rollback da aplicação pode exigir compatibilidade com esquema actualizado. Não executar `alembic downgrade` destrutivo automaticamente; preferir migração correctiva quando apropriado. Não eliminar bases/stores numa repetição do deploy.

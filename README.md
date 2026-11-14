# Deloya Marketplace

Marketplace multivendedor de produtos e serviços para a **Deloya Serviços e Comércios**, Nampula, Moçambique. Projecto de **Adelino Fonseca João — 2026**.

Next.js 16 / React 19 / TypeScript / Tailwind 4; FastAPI / SQLAlchemy / Alembic / Psycopg 3 / PostgreSQL. Os dados operacionais vêm da API e da base de dados.

Inclui catálogo, contas de cliente, candidaturas de vendedores, gestão de lojas, carrinho multivendedor, encomendas, administração e relatórios. Consulte o [guia de utilização](docs/USER_GUIDE.md).

**PAGAMENTO DE TESTE — SEM MOVIMENTAÇÃO DE DINHEIRO.** M-Pesa e e-Mola reais permanecem desactivados. Os dados opcionais de teste são fictícios. Consulte o [estado das integrações e limites operacionais](docs/LIMITATIONS.md).

## Arranque com Docker — Windows / PowerShell

Pré-requisitos: Git, Docker Desktop com motor Linux activo e Docker Compose. Na raiz:

```powershell
./scripts/setup-env.ps1
docker compose up -d db
docker compose build backend frontend
docker compose run --rm backend alembic upgrade head
docker compose up -d backend frontend
```

O script cria `.env` com segredos aleatórios e preserva configuração existente. Nunca versionar `.env`. A migração é explícita; não corre por cada pedido. A instalação inicial precisa de acesso às imagens e aos registos de dependências.

Abrir [aplicação](http://localhost:3000), [healthcheck](http://127.0.0.1:8000/health) e [OpenAPI](http://127.0.0.1:8000/docs). PostgreSQL fica em `127.0.0.1:5433`. Sem seed ou dados criados pela API, o catálogo apresenta estado vazio.

### Onde abrir cada área

O site, a conta e os painéis pertencem todos ao frontend, na porta **3000**. Iniciar sessão com uma conta do papel correspondente antes de abrir:

- [Conta do cliente](http://localhost:3000/conta).
- [Painel do vendedor](http://localhost:3000/vendedor/dashboard).
- [Painel do administrador](http://localhost:3000/admin/dashboard).

A porta **8000** serve a API; não apresenta um segundo painel de gestão. Abrir a sua raiz encaminha para a documentação em `/docs`. O frontend comunica com a API através de `/api/v1`.

### Dados de teste opcionais

```powershell
docker compose run --rm backend python -m app.seed --demo
```

Contas de teste: `admin@demo.deloya.example.com`, `cliente@demo.deloya.example.com`, `vendedor1@demo.deloya.example.com` e `vendedor2@demo.deloya.example.com`. A palavra-passe é `DEMO_PASSWORD` no `.env` local. Não existe palavra-passe pública. Consultar apenas no editor; nunca incluir em capturas ou commits.

O seed é explícito e idempotente, sem apagar dados ou substituir contas existentes. Numa conta já criada, preserva a palavra-passe; alterar `DEMO_PASSWORD` não redefine essa conta. Não o executar em produção. Para criar uma conta administrativa própria, consultar [segurança](docs/SECURITY.md).

```powershell
docker compose logs --tail 100 backend frontend
docker compose stop
```

`stop` conserva dados. Não remover o volume para resolver problemas de arranque; inspeccionar logs e efectuar backup.

## Desenvolvimento sem Docker para a aplicação

Instalar Python **3.13**, Node.js **22 LTS** ou versão compatível com Next 16, e PostgreSQL. Pode manter apenas PostgreSQL no Docker com `docker compose up -d db`, ou usar uma instalação nativa e ajustar ambas as URLs no `.env`. SQLite não é suportado.

Terminal PowerShell para o backend, a partir da raiz:

```powershell
./scripts/setup-env.ps1
python --version
python -m venv .venv
./.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
Set-Location backend
../.venv/Scripts/python.exe -m alembic upgrade head
../.venv/Scripts/python.exe -m app.seed --demo
../.venv/Scripts/python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

O seed é opcional. O backend lê o `.env` da raiz; conferir as URLs antes de executar. Não usar uma base de produção numa sessão de desenvolvimento.

Noutro terminal, a partir da raiz:

```powershell
Set-Location frontend
npm ci
$env:BACKEND_URL = 'http://127.0.0.1:8000'
npm run dev
```

O browser usa `/api/v1` na mesma origem e Next encaminha para FastAPI. Não expor segredos em `NEXT_PUBLIC_*`.

### Se o site abre mas o login ou os dados falham

1. Abrir [o estado da API](http://127.0.0.1:8000/health): deve devolver `status: ok` e `database: ok`. Se não responder, verificar o terminal do backend e se o PostgreSQL está activo.
2. Abrir [o catálogo através do frontend](http://localhost:3000/api/v1/products?page_size=1). Deve devolver JSON. Um erro de ligação aqui indica problema no destino `BACKEND_URL` ou no processo da API.
3. Em desenvolvimento local, `localhost:3000` e `127.0.0.1:3000` são aceites para a mesma porta. Para um IP da rede, configurar os dois lados conforme o exemplo abaixo e reiniciar ambos os servidores. Em produção permanece obrigatória a origem HTTPS configurada; as origens adicionais de desenvolvimento são ignoradas.
4. Manter os terminais dos dois servidores abertos. `npm run build` apenas compila; para servir a compilação, executar `npm run start` em `frontend/`. Para desenvolvimento, usar `npm run dev`.

Exemplo de acesso pela rede, substituindo `192.168.1.10` pelo IP realmente utilizado no browser:

```dotenv
# .env na raiz: origem completa, incluindo protocolo e porta.
DEVELOPMENT_FRONTEND_ORIGINS=["http://192.168.1.10:3000"]
```

```dotenv
# frontend/.env.local: apenas o hostname/IP, sem protocolo ou porta.
DEV_ALLOWED_HOSTS=192.168.1.10
```

Iniciar o frontend com `npm run dev -- --hostname 0.0.0.0 --port 3000`. A API pode continuar ligada a `127.0.0.1:8000`, porque o proxy do frontend encaminha os pedidos. Não utilizar wildcards para autorizar origens.

Os formulários de autenticação requerem JavaScript e ficam bloqueados até a página estar pronta. Sem JavaScript apresentam um aviso; a submissão nativa usa POST e nunca deve colocar palavras-passe na URL. O registo exige pelo menos 12 caracteres.

## Verificação

Em `frontend/`:

```powershell
npm run lint
npx tsc --noEmit
npm test
npm run build
```

Na raiz, com Python configurado, criar **uma vez** a base PostgreSQL de testes isolada e executar:

```powershell
docker compose exec -T db createdb -U deloya deloya_test
./.venv/Scripts/python.exe scripts/test-backend.py -q
```

O auxiliar `./scripts/check.ps1` reúne as verificações locais. `python -m pytest -q` em `backend/` também funciona quando `TEST_DATABASE_URL` está correctamente exportada. Consultar [TESTING.md](docs/TESTING.md): as tabelas da base dedicada são limpas entre testes. Não apontar testes a dados a preservar. Resultados efectivos: [VALIDATION.md](docs/VALIDATION.md). A existência de um teste não significa que tenha sido executado neste ambiente.

## Organização e documentação

| Caminho | Conteúdo |
| --- | --- |
| `frontend/` | App Router, componentes, formulários e cliente HTTP |
| `backend/` | API, domínio, PostgreSQL, migrações e testes |
| `scripts/` | Configuração e verificação local |
| `docs/` | Arquitectura, operação, requisitos e utilização |

- [Requisitos e fluxos](docs/REQUIREMENTS.md), [arquitectura](docs/ARCHITECTURE.md), [base de dados](docs/DATABASE.md), [API](docs/API.md).
- [Segurança](docs/SECURITY.md), [pagamentos](docs/PAYMENTS.md), [backup](docs/BACKUP.md), [deploy](docs/DEPLOYMENT.md).
- [Rastreabilidade](docs/REQUIREMENTS_TRACEABILITY.md), [guia de utilização](docs/USER_GUIDE.md), [testes](docs/TESTING.md) e [resultados](docs/VALIDATION.md).

O repositório reúne aplicação, API e documentação operacional. A publicação e as integrações externas seguem a [preparação de deploy](docs/DEPLOYMENT.md); o envio de código para GitHub, por si só, não activa alojamento ou pagamentos.

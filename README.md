# Deloya Marketplace

Protótipo académico multivendedor de produtos e serviços para a **Deloya Serviços e Comércios**, Nampula, Moçambique. Projecto de Adelino Fonseca João, Licenciatura em Informática Aplicada, Universidade Rovuma; avaliação de investigação prevista para 2027. Marca e logótipo provisórios.

Next.js 16 / React 19 / TypeScript / Tailwind 4; FastAPI / SQLAlchemy / Alembic / Psycopg 3 / PostgreSQL. Os dados operacionais vêm da API e da base de dados.

**PAGAMENTO SIMULADO — SEM TRANSACÇÃO REAL.** M-Pesa e e-Mola reais permanecem desactivados. Os dados opcionais de demonstração são fictícios, sem resultados de investigação ou prova de aumento de vendas. Consulte [limitações](docs/LIMITATIONS.md).

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

Abrir [aplicação](http://localhost:3000), [healthcheck](http://localhost:8000/health) e [OpenAPI](http://localhost:8000/docs). PostgreSQL fica em `127.0.0.1:5433`. Sem seed ou dados criados pela API, o catálogo apresenta estado vazio.

### Seed opcional

```powershell
docker compose run --rm backend python -m app.seed --demo
```

Contas demonstrativas: `admin@demo.deloya.example.com`, `cliente@demo.deloya.example.com`, `vendedor1@demo.deloya.example.com` e `vendedor2@demo.deloya.example.com`. A palavra-passe é `DEMO_PASSWORD` no `.env` local. Não existe palavra-passe pública. Consultar apenas no editor; nunca incluir em capturas ou commits.

O seed é explícito e idempotente, sem apagar dados ou substituir contas reais. Não o executar em produção. Para administração fora da demonstração, consultar [segurança](docs/SECURITY.md).

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
| `docs/` | Arquitectura, operação e plano académico |

- [Requisitos e fluxos](docs/REQUIREMENTS.md), [arquitectura](docs/ARCHITECTURE.md), [base de dados](docs/DATABASE.md), [API](docs/API.md).
- [Segurança](docs/SECURITY.md), [pagamentos](docs/PAYMENTS.md), [backup](docs/BACKUP.md), [deploy](docs/DEPLOYMENT.md).
- [Rastreabilidade](docs/REQUIREMENTS_TRACEABILITY.md), [avaliação académica](docs/ACADEMIC_EVALUATION.md), [demonstração](docs/DEMO_SCRIPT.md).

O esqueleto Next original foi reorganizado em `frontend/`, preservando `/sobre`. Enviar código para GitHub não activa Vercel, Neon, Blob ou pagamentos reais. Operação comercial exige revisão institucional do branding, termos, privacidade e integrações.

# Auditoria inicial e plano de execução

Data de referência: 14/11/2026, Africa/Maputo.

## Situação encontrada

A pasta continha um esqueleto Next.js com `app`, `public`, configurações, dependências locais e página `/sobre`. Não havia repositório Git inicializado na raiz nem backend/base de dados de marketplace. O frontend foi reorganizado em `frontend/`, preservando o conteúdo existente; `/sobre` permanece disponível. Não foram apagados dados de negócio para criar o protótipo.

Requisitos recebidos: marketplace académico multivendedor de produtos **e** serviços, API FastAPI/PostgreSQL, segurança por titularidade, pagamentos de demonstração e documentação da monografia. O envio para `https://github.com/CaosAleatorio/deloya.git` foi solicitado. Publicação Vercel/Neon e uso de serviços pagos não integram esta autorização.

## Sequência de trabalho

| Fase | Resultado verificável |
| --- | --- |
| 1 Auditoria/requisitos | Este registo, REQUIREMENTS e fluxos |
| 2 Base técnica | Monorepo, Compose, Next/FastAPI/PostgreSQL e healthcheck |
| 3 Identidade/dados | Modelo, Alembic, sessões, candidatura e aprovação |
| 4 Marketplace | Catálogo, carrinho, encomenda e isolamento por loja |
| 5 Pagamentos | Simulação persistida/idempotente; real desactivado |
| 6 Administração | Moderação, métricas, reclamações e relatórios |
| 7 Validação | Testes técnicos, revisão e protocolo académico |
| 8 Entrega | GitHub e preparação de deploy; sem publicação comercial implícita |

Cada fase é avaliada pela implementação final e pelos resultados em VALIDATION; esta tabela não declara automaticamente sucesso. Dependências externas ausentes são registadas em LIMITATIONS.

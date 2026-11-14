# Registo de validação técnica

Data: **14/11/2026**, referência Africa/Maputo. Este registo descreve verificações técnicas efectivamente comunicadas durante a implementação. Não contém resultados de investigação académica, participantes ou métricas de impacto comercial.

## Ambiente

Windows; Python 3.13.9; Node.js 22.19; Next.js 16.4.6; React 19.3.1; PostgreSQL 17 em Docker. Testes backend executados numa base PostgreSQL isolada, distinta dos dados de demonstração. Segredos locais não integram este documento.

## Verificações executadas

| Verificação | Resultado observado |
| --- | --- |
| Backend, `scripts/test-backend.py` / Pytest | **55 passed**, 36,67 segundos |
| Frontend, `npm test` | **9 testes passaram** |
| Frontend, ESLint | Passou no código final |
| Frontend, TypeScript | Passou no código final |
| Frontend, build Next.js | Passou no código final, incluindo Button shadcn/ui |
| Dependências Python, `pip check` | Sem conflitos |
| Migrações, `alembic check` | Sem operações de upgrade pendentes |
| Dependências JavaScript, `npm audit` | 0 vulnerabilidades reportadas na execução registada |
| Seed explícito, primeira execução | 11 anúncios novos |
| Seed explícito, repetição | 0 anúncios novos; idempotência observada |

Uma auditoria de dependências sem ocorrências não equivale a certificação de segurança. A suite usa PostgreSQL real para as verificações de domínio e isolamento; a contagem acima não inclui testes de utilizadores da monografia.

## Browser e acessibilidade

No servidor de desenvolvimento foram concluídos os fluxos de registo, pesquisa, carrinho com duas lojas, pagamento simulado, histórico, logout e novo login. Foram verificadas as nove páginas administrativas e sete páginas de vendedor. A verificação móvel a 390 px não apresentou overflow horizontal nos cenários inspeccionados.

A repetição final com `npm run start`, sobre a compilação de produção, passou as **9 verificações funcionais** de `scripts/browser-smoke.mjs`. Incluiu o download autenticado do PDF da encomenda, validando resposta PDF e `Cache-Control: no-store`, sem erros inesperados do browser/API.

Uma auditoria Axe na compilação final de produção executou **8 scans**, correspondentes a quatro páginas nas larguras de 1440 e 390 px, com **zero violações reportadas**. Este resultado automatizado tem o alcance das páginas e regras verificadas; não demonstra conformidade integral de todas as interacções ou substitui avaliação manual com pessoas.

## Código e rastreabilidade

A validação corresponde à versão inicial 0.1.0. O commit que contém este registo identifica os ficheiros validados. Os artefactos locais de navegador ficam em `.local/browser-results/`, ignorados pelo Git.

Destino Git autorizado: `CaosAleatorio/deloya`, ramo `main`. Conferir a sincronização com `git rev-parse HEAD` e `git ls-remote origin refs/heads/main`: os identificadores devem coincidir. O envio de código não representa publicação da aplicação.

A revisão dos ficheiros candidatos não encontrou os segredos do `.env` local. `.env`, ambientes instalados, ficheiros de base de dados e artefactos de teste não são versionados. `docker compose config --quiet` passou; o PostgreSQL do Compose foi executado, enquanto frontend e API foram validados como processos locais, sem construir as respectivas imagens Docker neste ambiente.

## Limites de validação

- Não houve publicação verificada em Vercel nem criação/validação de produção no Neon.
- Não houve cobrança real por M-Pesa/e-Mola, liquidação a vendedores ou teste com credenciais financeiras de produção.
- O upload remoto Vercel Blob não foi validado com armazenamento e credenciais reais; testes locais não comprovam operação remota.
- Não há serviço real de email configurado ou envio de recuperação validado.
- Os cerca de 15 questionários e cinco testes de usabilidade previstos para 2027 **não foram realizados como parte desta validação técnica**.
- Dados seed e pagamentos simulados não comprovam vendas, dinheiro recebido ou resultados da investigação.

Consultar [TESTING.md](TESTING.md) para repetir os comandos, [LIMITATIONS.md](LIMITATIONS.md) para limites operacionais e [ACADEMIC_EVALUATION.md](ACADEMIC_EVALUATION.md) para o protocolo de investigação ainda por executar.

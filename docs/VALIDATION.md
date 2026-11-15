# Registo de validação técnica

Data: **14/11/2026**, referência Africa/Maputo. Este registo descreve verificações técnicas executadas durante a implementação e a correcção de acesso local do Deloya Marketplace, projecto de Adelino Fonseca João.

## Ambiente

Windows; Python 3.13.9; Node.js 22.19; Next.js 16.4.6; React 19.3.1; PostgreSQL 17 em Docker. Testes backend executados numa base PostgreSQL isolada. Segredos locais não integram este documento.

## Actualização de 15/11/2026 — transferências directas e anexos privados

| Verificação actual | Resultado observado |
| --- | --- |
| Backend completo, runner na base dedicada `deloya_test` | **159 passaram**, 35,23 s |
| Frontend unitário | **32 passaram** |
| ESLint / TypeScript / build Next.js | Passaram |
| Browser de pagamentos manuais, compilação de produção local | Desktop 1440 px e telemóvel 390 px: destinatários separados, valor do servidor, pendência, confirmação, pagamento parcial, rejeição/reenvio, loja suspensa e aviso de teste passaram |
| Browser de anexos privados, compilação de produção local | Cliente/admin em 1440/390 px: upload, download, remoção, tamanho excedido, indisponibilidade e autorização passaram |
| Axe nos dois roteiros novos | 6 scans, zero violações reportadas; sem erros JavaScript ou overflow nos cenários verificados |
| Migração local / `alembic check` / `pip check` | Head `c381dafe204b`; sem diferenças de esquema nem conflitos de dependências |
| Neon novo, PostgreSQL 17, Frankfurt | Head `c381dafe204b`, 19 tabelas; sem copiar contas ou seed local |
| Store Blob privado Frankfurt | Marcador sem dados pessoais carregado/lido autenticado; acesso anónimo devolveu 403; marcador removido |

As chamadas API dos dois roteiros novos de browser são simuladas; testes de domínio usam PostgreSQL real. A prova Blob acima usa o armazenamento real, mas a validação das rotas da aplicação publicada fica registada separadamente em [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md). Os resultados abaixo preservam o histórico de 14/11/2026.

## Verificações executadas

| Verificação | Resultado observado |
| --- | --- |
| Backend, `scripts/test-backend.py` / Pytest | **105 passed**, 40,69 segundos, após correcções de acesso e revisão dos textos |
| Frontend, `npm test` | **15 testes passaram**, incluindo origens locais e geração de chaves em HTTP |
| Frontend, ESLint | Passou na revisão de acesso e autenticação |
| Frontend, TypeScript | Passou na revisão de acesso e autenticação |
| Frontend, build Next.js | Passou na revisão de acesso e autenticação |
| Dependências Python, `pip check` | Sem conflitos |
| Migrações, `alembic check` | Sem operações de upgrade pendentes |
| Dependências JavaScript, `npm audit` | 0 vulnerabilidades reportadas na execução registada |
| Seed explícito, primeira execução | 11 anúncios novos |
| Seed explícito, repetição | 0 anúncios novos; idempotência observada |

Os registos de dependências, migrações e seed referem-se à entrega inicial; os restantes indicam a revisão de acesso descrita na tabela. Uma auditoria de dependências sem ocorrências não equivale a certificação de segurança. A suite usa PostgreSQL real para verificar domínio e isolamento.

## Browser e acessibilidade

Na entrega inicial, no servidor de desenvolvimento, foram concluídos os fluxos de registo, pesquisa, carrinho com duas lojas, pagamento de teste, histórico, logout e novo login. Foram verificadas as nove páginas administrativas e sete páginas de vendedor. A verificação móvel a 390 px não apresentou overflow horizontal nos cenários inspeccionados.

A repetição dessa entrega com `npm run start`, sobre a compilação de produção, passou as **9 verificações funcionais** de `scripts/browser-smoke.mjs`. Incluiu o download autenticado do PDF da encomenda, validando resposta PDF e `Cache-Control: no-store`, sem erros inesperados do browser/API.

Uma auditoria Axe nessa compilação executou **8 scans**, correspondentes a quatro páginas nas larguras de 1440 e 390 px, com **zero violações reportadas**. Este resultado automatizado abrange as páginas e regras verificadas; não confirma a acessibilidade de todas as interacções.

Na revisão de acesso, passaram **4 verificações com os serviços locais activos**, cobrindo registo, login e logout nos endereços de desenvolvimento configurados, incluindo IP da rede e os aliases `localhost`/`127.0.0.1`. Não foram observadas credenciais na query string. A regressão `scripts/auth-form-regression.mjs` passou **4 cenários de login/registo com JavaScript activo e desactivado**; este script usa respostas HTTP simuladas e não cria contas na base de dados.

Após a revisão da apresentação para 2026, o fluxo completo foi repetido no IP da rede através de HTTP: **9 verificações passaram**, incluindo encomenda de duas lojas, pagamento de teste, PDF privado, painéis e navegação móvel. A geração das chaves de idempotência usa `crypto.getRandomValues` quando `crypto.randomUUID` não existe nesse contexto; os testes confirmam UUIDv4 e ausência de fallback aleatório inseguro. Os quatro cenários de protecção dos formulários voltaram a passar no mesmo IP.

## Código e rastreabilidade

Os resultados distinguem a entrega inicial 0.1.0 da revisão de acesso e autenticação. O commit que contém este registo identifica a revisão da documentação; executar novamente os comandos relevantes após alterações posteriores. Os artefactos locais de navegador ficam em `.local/browser-results/`, ignorados pelo Git.

Repositório: `CaosAleatorio/deloya`, ramo `main`. Conferir a sincronização com `git rev-parse HEAD` e `git ls-remote origin refs/heads/main`: os identificadores devem coincidir. O envio de código não representa publicação da aplicação.

A revisão dos ficheiros candidatos não encontrou os segredos do `.env` local. `.env`, ambientes instalados, ficheiros de base de dados e artefactos de teste não são versionados. `docker compose config --quiet` passou; o PostgreSQL do Compose foi executado, enquanto frontend e API foram validados como processos locais. A construção das imagens Docker da aplicação não foi executada neste ambiente.

## Workflow de integração contínua

O log do job inicial confirmou `unknown shorthand flag: 'U' in -U` ao criar o serviço PostgreSQL. O comando do healthcheck passou a usar aspas duplas, adequadas à passagem dos argumentos pelo executor. A configuração corrigida foi verificada num contentor PostgreSQL temporário que atingiu o estado `healthy`, sem portas publicadas e sem alterar a base local do projecto.

As actions `checkout`, `setup-node` e `setup-python` usam a versão `v7`, com runtime interno Node 24. A aplicação continua a usar Node 22 e Python 3.13. O resultado remoto de cada revisão pode ser consultado em [GitHub Actions](https://github.com/CaosAleatorio/deloya/actions/workflows/ci.yml), identificando o commit correspondente.

## Limites de validação

- A actualização de 15/11/2026 publicou e verificou Vercel/Neon; IDs, URLs e alcance das verificações estão em [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md).
- Não houve cobrança real por M-Pesa/e-Mola, liquidação a vendedores ou teste com credenciais financeiras de produção.
- O SDK validou o Blob privado real com marcador, leitura autenticada, acesso anónimo 403 e remoção. O utilizador dispensou o ensaio adicional pelas rotas da aplicação com contas técnicas de produção; não o apresentar como executado.
- Não há serviço real de email configurado ou envio de recuperação validado.
- Dados de teste e pagamentos simulados não comprovam vendas ou dinheiro recebido.

Consultar [TESTING.md](TESTING.md) para repetir os comandos e [LIMITATIONS.md](LIMITATIONS.md) para os limites operacionais.

# Registo de publicação

Deloya Marketplace — Adelino Fonseca João, 2026.

Publicação verificada em **15/11/2026**. Os dois deployments Production atingiram `READY`. O utilizador optou por concluir com as verificações realizadas e dispensou o ensaio adicional com contas temporárias na base publicada. Caixas desmarcadas identificam limites de validação ou preparação operacional, não uma alegação de execução. [Guia de publicação](DEPLOYMENT.md).

## Acessos e plano

- [x] Sessão Neon na conta do proprietário; organização/plano Free confirmados.
- [x] Sessão Vercel identificada; scope/plano Hobby confirmados; nenhum extra pago activado.
- [ ] Elegibilidade no plano confirmada; uso comercial exige plano apropriado autorizado.
- [x] Python 3.13 confirmado nos logs Vercel; Node 22.x configurado; CLIs Neon 9.5.0 / Vercel 65.16.0.
- [x] Plano de upload revisto: 137 ficheiros, 938500 bytes, sem segredos, dumps ou ficheiros locais.

## Neon — base e tabelas

- [x] Projecto PostgreSQL 17 criado; Frankfurt, plano Free.
- [x] Base/branch de publicação próprias; nenhuma cópia/seed local.
- [x] Ligações pooled/directa com TLS; API usa pooled, migração usou directa.
- [x] Migrações aplicadas explicitamente; revisão actual coincide com única head.
- [x] Tabela `private_attachments` presente entre 19 tabelas; consulta bem-sucedida.
- [ ] Backup/restauro estabelecido antes de dados operacionais.

| Evidência | Valor confirmado |
| --- | --- |
| Data da verificação | 15/11/2026 |
| ID projecto / branch | `rough-smoke-78419741` / `br-green-forest-baky2crn` (`production`) |
| Região / PostgreSQL | `aws-eu-central-1` / 17 |
| Base | `deloya` |
| Revisão Alembic | `c381dafe204b` |

Não registar strings de conexão, passwords ou tokens.

## Vercel — FastAPI

- [x] API ligada a `CaosAleatorio/deloya`, Root Directory `backend`, FastAPI.
- [x] Log: `Using Python 3.13 from backend/.python-version`; Functions `fra1`.
- [x] Production configurado: JWT próprio, TLS, cookies Secure, origem `https://deloya.vercel.app`.
- [x] Nenhuma migração/seed executada por import/startup.
- [x] Deployment Ready; `/health` devolveu HTTP 200, `status: ok`, `database: ok`.
- [x] Primeira conta administrativa criada após autorização explícita; acesso apenas em `.local/production-admin.env`, ignorado por Git/Vercel. Sem senha nesta documentação.

## Vercel Blob — anexos privados

- [x] Store `deloya-anexos`, privado, região `fra1`.
- [x] Credencial privada em `BLOB_PRIVATE_READ_WRITE_TOKEN` apenas no backend Production, após autorização explícita.
- [x] Token privado não ocupa `BLOB_READ_WRITE_TOKEN`; catálogo público remoto não configurado.
- [x] Credenciais Production não copiadas para Preview/Development.
- [ ] Upload até 3 MiB, validação e limite por pedido verificados online.
- [ ] Titular/admin lista/descarrega; acesso anónimo e de terceiro bloqueado.
- [x] Marcador remoto: leitura autenticada correcta; URL privado sem credencial devolveu 403.
- [x] Marcadores técnicos removidos pelo SDK; nenhum documento pessoal utilizado.

## Vercel — Next.js e integração

- [x] Frontend com Root Directory `frontend`, Next.js e Node 22.x, ligado ao GitHub.
- [x] `BACKEND_URL=https://deloya-api.vercel.app` apenas no servidor.
- [x] Build concluído após configuração backend; deployment Ready.
- [x] Domínio canónico `https://deloya.vercel.app` coincide com `FRONTEND_ORIGIN`.
- [ ] Registo/login/logout/renovação verificados sem credenciais na URL.
- [ ] Cookies HttpOnly/Secure, CSRF e autorização verificados.
- [x] Página inicial HTTP 200, marca presente; catálogo pelo proxy HTTP 200 e vazio, conforme base nova.
- [x] Endpoint de sessão pelo domínio frontend HTTP 200 com cookie CSRF Secure.
- [ ] Carrinho, encomenda e painéis com dados operacionais no domínio final.
- [ ] Suporte testado com anexo persistente e acesso negado a terceiro.
- [x] `PAYMENT_MODE=manual`; APIs das operadoras desactivadas.
- [ ] Carteiras por loja, referência pendente e confirmação pelo vendedor verificadas; sem dinheiro em dados de teste.
- [ ] Logs/relatórios sem divulgação de segredos/dados pessoais.

| Artefacto | Identificador/URL confirmado |
| --- | --- |
| SHA funcional publicado | `326bfa1840ac69244b72eda127a201256205ab31` |
| Projecto / deployment API | `prj_S9Y1nfhNG7n5kDlAS5jUMULYYJBX` / `dpl_5BUvuaE2Pj7Akvu7jj54WLVrnTWc` |
| URL canónico API | [deloya-api.vercel.app](https://deloya-api.vercel.app/health) |
| Store privado / região | `store_KxdmGpN0PX9Lz0pQ` / `fra1` |
| Projecto / deployment frontend | `prj_r6Ak33mYi15v3q6Wve1UXwRO6yoY` / `dpl_6wwFZHkT13KdfvVjqAAo3eyVWgUX` |
| URL canónico frontend | [deloya.vercel.app](https://deloya.vercel.app) |
| Data/resultado CI | 15/11/2026; [backend e frontend aprovados](https://github.com/CaosAleatorio/deloya/actions/runs/43739736376) |
| Rollback | Preservar os deployment IDs acima; promover versão anterior na Vercel. Migrações aditivas não se revertem automaticamente. |

## Limites desta entrega

**Actualização de 20/11/2026:** a pedido do proprietário, foram adicionadas 16 categorias (oito principais/oito subcategorias) e três lojas ilustrativas: Adelino Tecnologia, Adelino Moda & Acessórios e Adelino Serviços. As lojas MetaB e Guy's Beauty existentes não foram alteradas. As novas lojas estão identificadas como exemplos e não têm carteiras de pagamento configuradas. O rodapé apresenta o contacto fornecido e perfis sociais explicitamente ilustrativos. A correcção do formulário foi validada conforme [VALIDATION.md](VALIDATION.md).

A publicação é persistente nas contas autorizadas, com API/base e proxy verificados. O utilizador dispensou testes adicionais que criariam contas e um pedido de apoio temporários na base Production; esses dados não foram criados. Os fluxos de login, anexos e isolamento entre utilizadores têm testes locais, sem repetição com contas de produção. O Blob real foi testado directamente pelo SDK com marcador sem dados pessoais.

O catálogo está vazio e não recebeu seed. Upload público de imagens exige store público separado. O plano Vercel Hobby está documentado para uso pessoal/não comercial; confirmar plano apropriado antes de operação comercial. Backup/restauro e acompanhamento de quotas continuam como preparação operacional. Não houve transferência financeira real.

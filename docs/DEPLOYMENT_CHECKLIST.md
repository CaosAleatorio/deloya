# Registo de publicação

Deloya Marketplace — Adelino Fonseca João, 2026.

Preparação revista em **15/11/2026**. Preencher apenas com evidência da conta/URL real. Caixa desmarcada significa **verificação pendente neste registo**, mesmo que recurso exista. [Guia de publicação](DEPLOYMENT.md).

## Acessos e plano

- [ ] Sessão Neon na conta do proprietário; organização/plano Free confirmados.
- [ ] Sessão Vercel identificada; scope/plano confirmados; nenhum extra pago activado.
- [ ] Elegibilidade no plano confirmada; uso comercial exige plano apropriado autorizado.
- [ ] Versões efectivamente utilizadas dos runtimes/CLIs registadas.
- [ ] Artefacto revisto para excluir segredos, dumps e ficheiros locais.

## Neon — base e tabelas

- [ ] Projecto PostgreSQL 17 criado/identificado; região/plano confirmados.
- [ ] Base/branch isoladas de testes; nenhuma cópia/seed local inadvertida.
- [ ] Ligações pooled/directa verificadas com TLS.
- [ ] Migrações aplicadas explicitamente; revisão actual coincide com única head.
- [ ] Tabela `private_attachments` presente; consulta bem-sucedida.
- [ ] Backup/restauro estabelecido antes de dados operacionais.

| Evidência | Valor confirmado |
| --- | --- |
| Data/hora da verificação | Pendente |
| ID projecto / branch | Pendente |
| Região / PostgreSQL | Pendente |
| Base | Pendente |
| Revisão Alembic | Pendente |

Não registar strings de conexão, passwords ou tokens.

## Vercel — FastAPI

- [ ] API ligada ao repositório com Root Directory `backend` e framework FastAPI.
- [ ] Python 3.13/região confirmados nos logs/configuração reais.
- [ ] Production configurado: JWT próprio, TLS, cookies Secure, origem HTTPS exacta.
- [ ] Nenhuma migração/seed executada por import/startup.
- [ ] Deployment Ready; healthcheck indica API/base disponíveis.
- [ ] Primeira conta administrativa criada privadamente, se necessária.

## Vercel Blob — anexos privados

- [ ] Store privado identificado; região/access mode confirmados.
- [ ] Credencial privada em `BLOB_PRIVATE_READ_WRITE_TOKEN` apenas no backend.
- [ ] Credencial do catálogo público separada, se configurada.
- [ ] Production isolado de Preview/Development.
- [ ] Upload até 3 MiB, validação e limite por pedido verificados online.
- [ ] Titular/admin lista/descarrega; acesso anónimo e de terceiro bloqueado.
- [ ] URL directo sem credencial bloqueado; token/URL interno ausentes das respostas.
- [ ] Remoção autorizada verificada; quotas observadas na conta.

## Vercel — Next.js e integração

- [ ] Frontend com Root Directory `frontend`, Next.js e Node 22.x.
- [ ] `BACKEND_URL` usa domínio HTTPS real/estável API.
- [ ] Build concluído após configuração backend.
- [ ] Domínio canónico coincide com `FRONTEND_ORIGIN`.
- [ ] Registo/login/logout/renovação verificados sem credenciais na URL.
- [ ] Cookies HttpOnly/Secure, CSRF e autorização verificados.
- [ ] Catálogo, carrinho, encomenda e painéis verificados no domínio final.
- [ ] Suporte testado com anexo persistente e acesso negado a terceiro.
- [ ] Modo de pagamento configurado; APIs das operadoras desactivadas.
- [ ] Carteiras por loja, referência pendente e confirmação pelo vendedor verificadas; sem dinheiro em dados de teste.
- [ ] Logs/relatórios sem divulgação de segredos/dados pessoais.

| Artefacto | Identificador/URL confirmado |
| --- | --- |
| SHA Git publicado | Pendente |
| Projecto / deployment API | Pendente |
| URL canónico API | Pendente |
| Store privado / região | Pendente |
| Projecto / deployment frontend | Pendente |
| URL canónico frontend | Pendente |
| Data/resultado testes publicados | Pendente |
| Responsável / rollback | Pendente |

Só concluir após obter URLs reais e executar fluxos essenciais. Testes locais e recursos temporários não confirmam publicação persistente.

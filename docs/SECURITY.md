# Segurança e operação responsável

Controlos do protótipo não constituem certificação ou teste de intrusão externo.

| Ameaça | Controlo | Verificação |
| --- | --- | --- |
| Recursos de outra pessoa | Backend filtra por titular e papel | IDOR cliente/vendedor |
| Password exposta | Argon2, sem password em logs | Login inválido e hash |
| Token reutilizado | Acesso curto, sessão persistida, rotação/revogação de refresh | Expiração, replay e logout |
| Pedido forjado com cookies | HttpOnly/SameSite, origem e token CSRF | CSRF ausente/inválido |
| Força bruta | Rate limiting persistido em PostgreSQL | Limite e janela |
| Preço adulterado | Recalcular na API | Payload manipulado |
| Venda acima do stock | Transacção e bloqueio de linhas | Concorrência PostgreSQL |
| Pagamento duplicado | Idempotência e estado transaccional | Repetição/fora de ordem |
| Confirmação falsa | Provedores reais desactivados; retorno não confirma | Webhook não autorizado |
| Upload malicioso | Tipo/conteúdo/tamanho/titularidade e acesso público/privado | Validar fluxo configurado |
| Segredo no browser/Git | `.env` ignorado; sem `NEXT_PUBLIC_*` privado | Revisão dos ficheiros rastreados |

## Sessões e origens

Produção exige HTTPS, `ENVIRONMENT=production`, `COOKIE_SECURE=true` e `FRONTEND_ORIGIN` exacta. A configuração recusa ligações PostgreSQL de produção sem `sslmode=require`, `verify-ca` ou `verify-full`, incluindo a URL directa quando definida. Não aceitar wildcard com credenciais. Tokens refresh aleatórios são guardados por hash, rotacionados e revogados. A verificação da sessão complementa a assinatura JWT.

A dependência de desenvolvimento `minimatch` usada por `@typescript-eslint/typescript-estree` tem uma substituição específica para a versão 11.0.1, correcção indicada no [aviso do projecto](https://github.com/advisories/GHSA-g3hv-75wg-m249). As restantes dependências mantêm as versões do lockfile; validar novamente a auditoria ao actualizá-las.

O cliente envia CSRF nas mutações conforme a API. Cookies de autenticação são HttpOnly; somente o token CSRF, incapaz de autenticar sozinho, precisa de ser legível. Não guardar tokens de autenticação em localStorage.

## Administração e segredos

Seed cria apenas contas demonstrativas. Para bootstrap controlado, a partir de `backend/`, fornecer `ADMIN_PASSWORD` por ambiente privado e executar:

```powershell
python -m app.bootstrap_admin --email administrador@dominio-autorizado.example
```

O email acima é placeholder. Não colocar passwords na linha de comando, documentação, histórico ou código. Remover a variável da sessão quando terminar. Conferir o comportamento do bootstrap para contas existentes; não promover uma conta real silenciosamente.

## Dados e pagamentos

Nunca recolher PIN de carteira móvel ou dados de cartão. Uma referência demonstrativa não é comprovativo bancário. O simulador não movimenta fundos; callbacks reais exigem validação segundo documentação oficial específica.

Minimizar contactos/moradas, expor apenas contacto comercial autorizado e fornecer ao vendedor somente a informação necessária à sua subencomenda. Auditoria identifica actor/acção/recurso sem passwords, tokens, chaves ou números financeiros completos. Relatórios também exigem autorização e revisão de dados expostos.

## Ficheiros

Separar catálogo público de anexos privados. Validar conteúdo real, extensão e limites; gerar nomes seguros e verificar titularidade ao alterar/remover referências. Bloquear conteúdo activo arbitrário de utilizadores. Sem armazenamento autorizado, não prometer upload persistente. Não servir documentos privados por URLs públicos nem usar filesystem efémero para persistência.

## Produção

Rever dependências, cabeçalhos, TLS, limites de infraestrutura, monitorização e backup/restauro. Termos e privacidade demonstrativos requerem revisão institucional. Rate limiting da aplicação não substitui toda a gestão de abuso. Ver [limitações](LIMITATIONS.md) e [deploy](DEPLOYMENT.md).

Referência técnica: [FastAPI — Argon2 e JWT](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/). O domínio acrescenta autorização por recurso e sessões ao exemplo de autenticação.

# Segurança e operação responsável

Os controlos de segurança da aplicação abrangem identidade, autorização e consistência dos dados. A validação interna deve ser complementada por revisão e teste de intrusão externo antes da operação pública.

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
| Confirmação falsa | Referência do cliente fica pendente; só dono da loja aprovada confirma após conferência da carteira | IDOR, duplicação e retorno sem autorização |
| Upload malicioso | Tipo/conteúdo/tamanho/titularidade e acesso público/privado | Validar fluxo configurado |
| Segredo no browser/Git | `.env` ignorado; sem `NEXT_PUBLIC_*` privado | Revisão dos ficheiros rastreados |

## Sessões e origens

Produção exige HTTPS, `ENVIRONMENT=production`, `COOKIE_SECURE=true` e `FRONTEND_ORIGIN` exacta. A configuração recusa ligações PostgreSQL de produção sem `sslmode=require`, `verify-ca` ou `verify-full`, incluindo a URL directa quando definida. Não aceitar wildcard com credenciais. Tokens refresh aleatórios são guardados por hash, rotacionados e revogados. A verificação da sessão complementa a assinatura JWT.

A dependência de desenvolvimento `minimatch` usada por `@typescript-eslint/typescript-estree` tem uma substituição específica para a versão 11.0.1, correcção indicada no [aviso do projecto](https://github.com/advisories/GHSA-g3hv-75wg-m249). As restantes dependências mantêm as versões do lockfile; validar novamente a auditoria ao actualizá-las.

O cliente envia CSRF nas mutações conforme a API. Cookies de autenticação são HttpOnly; somente o token CSRF, incapaz de autenticar sozinho, precisa de ser legível. Não guardar tokens de autenticação em localStorage.

Trocar senha ou email requer a senha actual, limite de tentativas e revogação de todas as sessões anteriores. A sessão actual recebe novos cookies. Login, refresh e mudanças de credenciais serializam primeiro na conta, evitando emissão de acesso após encerramento ou alteração concorrente. Logs não incluem senhas ou novos emails.

Eliminar conta anonimiza o perfil e remove moradas/carrinho; conserva referências e registos transaccionais. São exigidas senha actual e confirmação explícita, sem permitir encerramento com compromissos pendentes ou da última administração activa. A loja é suspensa e os anúncios arquivados, com guards para impedir reactivação de titular encerrado. O histórico e os anexos privados não são apagados por uma eliminação lógica.

Em desenvolvimento, o backend aceita o alias exacto `localhost`/`127.0.0.1` com o mesmo protocolo e porta. Outros endereços exigem autorização explícita em `DEVELOPMENT_FRONTEND_ORIGINS`; esta lista é ignorada em produção e nos testes. O Next.js autoriza hosts de desenvolvimento adicionais através de `DEV_ALLOWED_HOSTS` em `frontend/.env.local`, sem wildcards. A mesma lista de origens backend é aplicada a CORS e CSRF, e um token CSRF válido continua obrigatório.

Formulários de login/registo usam POST explícito e controlos desactivados antes da hidratação. A falha ou desactivação de JavaScript não deve provocar navegação GET com credenciais na query string. A regressão de navegador testa os dois modos com dados fictícios.

## Administração e segredos

O seed cria apenas contas de teste. Para criar uma conta administrativa própria, a partir de `backend/`, fornecer `ADMIN_PASSWORD` por ambiente privado e executar:

```powershell
python -m app.bootstrap_admin --email administrador@dominio-autorizado.example
```

O email acima é um exemplo e deve ser substituído pelo endereço do administrador. Não colocar passwords na linha de comando, documentação, histórico ou código. Remover a variável da sessão quando terminar. O bootstrap recusa promover uma conta existente; escolher uma conta administrativa própria e verificar o resultado.

## Dados e pagamentos

Nunca recolher PIN de carteira móvel ou dados de cartão. Uma referência de teste não é comprovativo bancário. O simulador não movimenta fundos; callbacks reais exigem validação segundo documentação oficial específica.

Minimizar contactos/moradas, expor apenas contacto comercial autorizado e fornecer ao vendedor somente a informação necessária à sua subencomenda. Auditoria identifica actor/acção/recurso sem passwords, tokens, chaves ou números financeiros completos. Relatórios também exigem autorização e revisão de dados expostos.

## Ficheiros

Separar catálogo público de anexos privados. Validar conteúdo real, extensão e limites; gerar nomes seguros e verificar titularidade ao alterar/remover referências. Bloquear conteúdo activo arbitrário de utilizadores. Sem armazenamento autorizado, não prometer upload persistente. Não servir documentos privados por URLs públicos nem usar filesystem efémero para persistência.

Anexos de apoio usam `BLOB_PRIVATE_READ_WRITE_TOKEN`, separado do token público de catálogo. A API devolve metadados sem URL/caminho de armazenamento; download autenticado com `no-store` e disposição `attachment`. Só o titular do pedido e administradores podem listar, enviar, descarregar e remover; ser vendedor de uma encomenda não concede acesso a estes documentos. Limites: 3 MiB por ficheiro, 10 por pedido e PDF não encriptado até 100 páginas. Imagens são reprocessadas para remover metadados.

## Produção

Rever dependências, cabeçalhos, TLS, limites de infraestrutura, monitorização e backup/restauro. Conferir os contactos, prazos de retenção e condições de utilização nos termos e na política de privacidade para a instalação concreta. Rate limiting da aplicação deve ser complementado por monitorização de abuso. Ver [limitações](LIMITATIONS.md) e [deploy](DEPLOYMENT.md).

Referência técnica: [FastAPI — Argon2 e JWT](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/). O domínio acrescenta autorização por recurso e sessões ao exemplo de autenticação.

# Preparação de deploy — Vercel, Neon e Blob

**Este documento não significa que a aplicação foi publicada.** O envio de código para o GitHub foi solicitado. Criação de recursos externos, activação financeira e publicação comercial são etapas separadas e não executadas automaticamente.

## Arquitectura de destino

Dois projectos Vercel a partir do mesmo monorepo: frontend com Root Directory `frontend`; backend com Root Directory `backend`. Base PostgreSQL no Neon, imagens públicas de catálogo em armazenamento público e anexos sensíveis em armazenamento privado. A aplicação não persiste dados no filesystem efémero de funções.

### Backend

O runtime Python da Vercel suporta Python 3.13 e reconhece uma instância ASGI chamada `app` em entrypoints suportados, incluindo `index.py`. O repositório reutiliza a aplicação FastAPI em vez de a recriar por pedido. Verificar novamente o contrato da plataforma antes de publicar: [FastAPI na Vercel](https://vercel.com/docs/frameworks/backend/fastapi), [runtime Python](https://vercel.com/docs/functions/runtimes/python).

Configurar `DATABASE_URL` pooled com SSL, `DATABASE_DIRECT_URL` directa para tarefas administrativas, segredo JWT forte, origem HTTPS exacta do frontend e cookies Secure. As restantes variáveis devem corresponder a `.env.example` e à configuração do backend. Manter os provedores reais desactivados. Variáveis privadas não usam prefixo `NEXT_PUBLIC_`.

### Frontend

Seleccionar Next.js e instalar a partir do lockfile. Configurar a origem privada da API na variável usada pelo proxy do projecto, sem incluir segredos no cliente. As chamadas do browser usam `/api/v1`; o proxy encaminha para o backend. Validar cookies, cabeçalhos CSRF e origem com os dois domínios reais. Next.js requer Node.js compatível, no mínimo 20.9 conforme a [documentação oficial](https://nextjs.org/docs/app/getting-started/installation).

## Neon e migrações

Usar uma base distinta para desenvolvimento, testes e produção. Copiar os endereços do painel autorizado; não inventar hosts ou credenciais. A ligação pooled serve a API. Migrações e `pg_dump` usam a ligação directa porque dependem de características de sessão; a [documentação de pooling do Neon](https://neon.com/docs/connect/connection-pooling) distingue estes casos.

Executar `alembic upgrade head` uma vez no processo de release autorizado, depois de backup e revisão da migração. Não executar migração ou seed durante import da aplicação, startup de cada função ou por cada invocação. Nunca carregar seed numa base real inadvertidamente.

## Vercel Blob

O armazenamento deve distinguir catálogo público e documentos privados. Um URL difícil de adivinhar não substitui autorização. Antes de activar uploads, ligar um armazenamento autorizado, configurar token apenas no servidor e verificar limites/tipos/tamanho e controlo de titularidade. Documentos privados devem ser servidos por acesso autenticado. Fontes: [Blob](https://vercel.com/docs/vercel-blob), [armazenamento privado](https://vercel.com/docs/vercel-blob/private-storage).

Sem credenciais e configuração verificadas, não anunciar upload persistente como disponível. Não usar disco local de Vercel Functions para imagens de utilizadores, comprovativos ou anexos.

## Checklist de release

- [ ] Branding provisório e textos institucionais revistos.
- [ ] Testes e build executados; resultados registados com data e ambiente.
- [ ] Base de produção e backup preparados; restauração ensaiada.
- [ ] Migração revista e aplicada explicitamente à base correcta.
- [ ] Segredos configurados no servidor; `.env` fora do Git.
- [ ] Origem HTTPS exacta, CORS restrito, cookies Secure e CSRF verificados.
- [ ] Conta administrativa criada por procedimento privado, sem palavra-passe partilhada em código.
- [ ] Dados de demonstração isolados dos reais; pagamentos reais desactivados.
- [ ] Política e custos de Vercel/Neon/Blob conferidos no plano autorizado.
- [ ] Healthcheck, registo/login, catálogo, carrinho e encomenda verificados no URL final.
- [ ] Logs e relatórios revistos para evitar exposição de dados pessoais.
- [ ] Procedimento de rollback e responsável definidos.

Preços e elegibilidade comercial variam; não se assume que qualquer plano gratuito cobre operação comercial ou todo o armazenamento. Conferir [planos Vercel](https://vercel.com/pricing), [preços Neon](https://neon.com/pricing) e [custos Blob](https://vercel.com/docs/vercel-blob/usage-and-pricing) no momento da autorização, sem activar planos pagos automaticamente.

## Verificação e rollback

Uma publicação só fica confirmada depois de obter o URL real e verificar healthcheck e fluxo essencial. Guardar identificador da versão, SHA Git e revisão Alembic. Rollback de aplicação pode exigir compatibilidade com o esquema actualizado; não executar `downgrade` destrutivo automaticamente. Se a migração não for reversível com segurança, corrigir por migração adicional e seguir o plano de restauro aprovado.

# API REST v1

Base: `/api/v1`. Healthcheck fora da versão: `GET /health`. A documentação OpenAPI interactiva está em `/docs` no backend; o esquema exacto está em `/openapi.json`. Em desenvolvimento: API `http://localhost:8000`; o browser usa o proxy Next em `http://localhost:3000/api/v1`.

## Convenções

UUIDs identificam recursos privados; slugs identificam detalhes públicos. Campos usam `snake_case`; dinheiro usa strings decimais (`"1250.00"`) em MZN. Datas completas incluem fuso; o armazenamento é UTC e a apresentação é Africa/Maputo. Listagens paginadas devolvem `{items,total,page,page_size}`, com `page_size` até 100; categorias e moradas têm respostas próprias finitas.

Mutações exigem cookie `csrf_token` e cabeçalho `X-CSRF-Token` iguais, além da origem autorizada quando fornecida. Primeiro chamar `GET /auth/session` para obter cookie/token. Autenticação usa cookies `access_token` e `refresh_token`, ambos HttpOnly; o browser envia credenciais. Não há token de autenticação em localStorage. O webhook externo é excepção ao CSRF, mas está desactivado e não confirma pagamentos.

## Identidade e perfil

| Método / rota | Conteúdo / comportamento |
| --- | --- |
| GET `/auth/session` | `{user,csrf_token}`; user nulo se não autenticado |
| POST `/auth/register` | `name,email,password,phone`; password 12–128 caracteres, phone string opcional |
| POST `/auth/login` | `email,password`; cria sessão e cookies |
| POST `/auth/refresh` | Rotaciona refresh; reutilização revoga família |
| POST `/auth/logout` | Revoga sessão/família e remove cookies |
| GET / PATCH `/me` | Consulta perfil; actualização parcial de `name,phone,email`; alterar email exige `current_password` |
| POST `/me/password` | `current_password,new_password` (12–128 caracteres); troca a senha e renova a sessão actual |
| DELETE `/me` | `current_password,confirmation="ELIMINAR"`; encerra acesso e anonimiza o perfil, conservando histórico |
| GET / POST `/me/addresses` | Moradas próprias; criar com `label,address,province,district,phone` |
| PATCH / DELETE `/me/addresses/{id}` | Actualizar/remover apenas morada própria |

O registo não aceita `role`, `is_demo` ou campos extra. O backend determina o indicador de conta de teste conforme a configuração. Não existe recuperação por email sem serviço real configurado.

Alterar email ou senha exige a senha actual e revoga todas as sessões anteriores, incluindo os refresh tokens. A resposta emite novos cookies para a sessão que realizou a alteração. Email é normalizado e único; duplicados devolvem 409. A alteração de email não envia uma confirmação fictícia. Papel, titular e estado não são editáveis pelo próprio perfil.

Eliminar conta exige confirmação explícita e fica bloqueado enquanto existirem encomendas, transferências manuais ou solicitações de serviço por concluir. A última conta administrativa activa também é protegida. O perfil perde nome/email/telefone e acesso; moradas e carrinho são removidos. Uma loja própria é suspensa e os seus anúncios arquivados. Encomendas, pagamentos, apoio, anexos e auditoria permanecem associados aos IDs históricos; a operação não promete apagar todos os registos transaccionais.

## Catálogo público

| Método / rota | Filtros / resultado |
| --- | --- |
| GET `/categories` | Categorias activas, incluindo `parent_id` |
| GET `/products` e `/services` | `q,category,store,province,min_price,max_price,sort,page,page_size` |
| GET `/products/{slug}` e `/services/{slug}` | Só anúncios publicados em loja aprovada e categoria activa |
| GET `/stores` | `q,province,page,page_size`; só lojas aprovadas |
| GET `/stores/{slug}` | Loja pública e contacto comercial |

`category` e `store` aceitam slug/UUID conforme o filtro. Ordenação: `recent`, `price_asc`, `price_desc`. `price=null` significa sob consulta. Serviço tem `stock=null`. O payload do anúncio inclui loja e categoria.

## Cliente autenticado

| Método / rota | Conteúdo / comportamento |
| --- | --- |
| GET `/cart` | Itens próprios, preços actuais e total servidor |
| POST `/cart` | `listing_id,quantity`; soma à quantidade existente |
| PATCH `/cart/{item_id}` | `quantity`, positiva e válida para stock/tipo |
| DELETE `/cart/{item_id}` | Remove item próprio |
| GET / POST `/orders` | Histórico próprio / checkout transaccional |
| GET `/orders/{id}` | Detalhe próprio com subencomendas |
| GET `/orders/{id}/receipt.pdf` | Documento PDF privado do titular, com snapshots por loja e aviso de teste quando aplicável |
| POST `/orders/{id}/cancel` | Cancela apenas encomenda ainda por pagar |
| GET / POST `/payments` | Tentativas próprias / inicia tentativa elegível |
| GET `/payment-settings` | Modo actual (`manual`, `demo`, `disabled`) e disponibilidade do simulador; sem credenciais |
| POST `/orders/{id}/vendor-orders/{vendor_order_id}/payments` | Declara transferência própria: `provider=mpesa|emola,reference,idempotency_key,notes?` |
| POST `/payments/{id}/simulate` | `outcome=success|failure|expired`; somente pagamentos de teste próprios |
| POST `/payment-webhooks/{provider}` | Desactivado: 503, sem alterar recursos |
| GET / POST `/service-requests` | Solicitações próprias; criar com `listing_id,message,requested_date?` |
| GET / POST `/support` | Reclamações próprias; `subject,message,order_id?` |
| GET / POST `/support/{ticket_id}/attachments` | Lista metadados / multipart `file`, até 3 MiB; titular/admin |
| GET / DELETE `/attachments/{id}` | Download autenticado / remoção; titular/admin |

Checkout aceita `delivery_method=pickup|arranged`, `address`, `notes`, `requested_date` e `idempotency_key` (8–120 caracteres). Não aceita preço/total do browser. Entrega combinada exige morada e tarifa explícita de cada loja; serviço sob consulta exige solicitação em vez de compra arbitrária.

No modo `manual`, declarar uma transferência usa a rota da subencomenda: o servidor obtém montante e destinatário do snapshot, cria estado `pending` e aguarda revisão pelo vendedor. Encomendas devolvem `payment_mode`, `can_cancel` e, por loja, `payment_destinations` e `payments`. `parcialmente_paga` identifica parcelas já confirmadas enquanto outras aguardam. Informar referência não confirma dinheiro recebido. A chave de idempotência preserva o resultado; reutilizá-la com dados diferentes devolve 409.

A rota legada `POST /payments` aceita `order_id,provider=demo,idempotency_key` apenas no modo de teste elegível. Os adaptadores automáticos `mpesa`/`emola` permanecem indisponíveis; a rota manual não os invoca. O simulador não altera uma tentativa já finalizada para outro resultado.

O PDF individual usa nome/preço dos snapshots, totais e condições de recepção, sem guardar ficheiro no disco. O titular é o único autorizado; outro cliente, vendedor de uma parcela ou administrador que não seja titular recebe 404 nesta rota. Encomenda por pagar gera «Registo da encomenda», nunca comprovativo de pagamento. Documento de teste conserva «PAGAMENTO DE TESTE — SEM MOVIMENTAÇÃO DE DINHEIRO» e «NÃO CONSTITUI PROVA DE DINHEIRO RECEBIDO», mesmo depois de uma simulação de sucesso.

Cada item do carrinho inclui `available`. Artigos eliminados, de loja suspensa ou categoria desactivada ficam identificados como indisponíveis e podem ser removidos pelo cliente. O checkout valida novamente a disponibilidade, mesmo que o browser seja contornado.

## Vendedor

| Método / rota | Comportamento |
| --- | --- |
| POST `/vendor/application` | Candidatura: dados da loja; estado pendente |
| GET / PATCH `/vendor/store` | Consulta loja própria / edita após aprovação |
| GET `/vendor/dashboard` | Métricas da base e totais reais/simulados separados |
| GET / POST `/vendor/products` e `/vendor/services` | Listar/criar anúncios próprios |
| PATCH / DELETE `/vendor/products/{id}` e `/vendor/services/{id}` | Actualizar/arquivar anúncio próprio |
| GET `/vendor/orders` | Subencomendas próprias, filtro `status` |
| PATCH `/vendor/orders/{id}` | `status` e/ou `service_status` conforme transição |
| GET `/vendor/payments` | Declarações das próprias subencomendas; filtro `status` e paginação |
| POST `/vendor/orders/{id}/payments/{payment_id}/review` | `decision=confirm|reject,wallet_verified,notes?`; confirmar exige conferência explícita, rejeitar exige motivo |
| GET `/vendor/service-requests` | Solicitações da loja |
| PATCH `/vendor/service-requests/{id}` | `confirmed`, `declined` ou `completed` conforme estado |
| POST `/vendor/uploads` | Multipart imagem JPEG/PNG/WebP até 3 MB; Blob configurado obrigatório |
| DELETE `/vendor/uploads/{image_id}` | Remove imagem própria sem referências activas/arquivadas; Blob configurado obrigatório |

Dados da loja: `name,description,province,district,address,phone,nuit?,logo_url?,delivery_fee?`, mais pares opcionais `mpesa_phone,mpesa_account_name` e `emola_phone,emola_account_name`. Cada carteira exige número e nome juntos; nove dígitos locais normalizam para `+258`. Respostas públicas de loja/anúncio excluem estes quatro campos. `delivery_fee=null` significa tarifa não definida, não entrega gratuita. Anúncio: `name,description,category_id,price,stock,sku,image_url,images,service_location,estimated_duration,status`. Edição usa `expected_updated_at` devolvido no anúncio para detectar conflito, especialmente em stock alterado desde a leitura. Vendedor envia `draft`/`pending`; publicação exige moderação. Imagens devem pertencer à própria loja no armazenamento autorizado ou ser imagens ilustrativas locais de teste. Remover referências de logo, imagem principal e galeria antes de apagar os bytes; anúncios arquivados também contam.

DELETE de produto/serviço elimina-o do catálogo por arquivo lógico, preservando os snapshots e referências das encomendas. Repetições não duplicam a auditoria. PATCH de anúncio arquivado devolve 409, impedindo a republicação por edição. O isolamento por loja também se aplica à eliminação.

## Administração

| Método / rota | Comportamento |
| --- | --- |
| GET `/admin/dashboard` | Utilizadores, lojas, encomendas, pagamentos e apoio |
| GET / PATCH `/admin/stores` / `/{id}` | Listar e aprovar/suspender; decisão auditada |
| GET / PATCH `/admin/catalog` / `/{id}` | Listar/moderar anúncios |
| GET / POST `/admin/categories` | Listar/criar categorias e subcategorias |
| PATCH / DELETE `/admin/categories/{id}` | Editar/desactivar, sem ciclos de hierarquia |
| GET `/admin/orders` e `/admin/payments` | Filtros `status,is_demo` e paginação |
| GET / PATCH `/admin/payment-config` | Consultar e activar/desactivar pagamentos de teste quando o ambiente permite |
| GET `/admin/audit` | Registos críticos paginados |
| GET / PATCH `/admin/support` / `/{id}` | Consulta e resolução de reclamações |

## Relatórios

`GET /reports/orders.csv` e `/reports/orders.pdf`, autenticados: administrador consulta todas as lojas autorizadas; vendedor apenas a própria. Filtros: `start,end,status,store_id,is_demo,category_id`, com datas `aaaa-mm-dd` interpretadas em Africa/Maputo. Categoria usa UUID e o estado refere-se à subencomenda. Intervalo invertido devolve 422. Máximo de 5000 subencomendas por exportação. Os registos identificam simulação e não constituem comprovativos bancários. PDF é gerado em memória; não exige persistência no filesystem da função.

## Erros

| Código | Situação |
| --- | --- |
| 401 | Sessão ausente, inválida, expirada ou revogada |
| 403 | Papel, origem ou CSRF sem autorização |
| 404 | Recurso inexistente ou não pertencente ao titular |
| 409 | Stock, estado, unicidade ou disponibilidade incompatível |
| 413 | Upload acima do limite |
| 422 | Campos inválidos, tipo errado ou transição/intervalo inválido |
| 429 | Limite de tentativas atingido |
| 502/503 | Armazenamento/base/integração indisponível |

Erros devolvem `detail`; validação inclui campos/mensagens sem reenviar valores sensíveis. Nunca tratar parâmetro de retorno do browser como confirmação financeira. Consultar [PAYMENTS.md](PAYMENTS.md).

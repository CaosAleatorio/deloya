# Matriz de rastreabilidade

Esta matriz relaciona os requisitos de software com a implementação e a verificação técnica. A descrição de um teste indica o comportamento a verificar; os resultados executados ficam em [VALIDATION.md](VALIDATION.md). Capturas e artefactos devem excluir passwords, tokens e dados pessoais.

| ID / requisito | Implementação | Verificação |
| --- | --- | --- |
| R01 Requisitos e papéis | REQUIREMENTS.md e USER_GUIDE.md | Conferir permissões e fluxos de cliente, vendedor e administrador |
| R02 Monorepo e API | frontend, backend, Compose e /health | Arranque local, healthcheck e catálogo pela API |
| R03 Registo/sessão/logout | Rotas auth, JWT e AuthSession | Registo, token inválido/expirado, refresh rotativo e logout |
| R04 Candidatura/aprovação | Store.status e rotas vendor/admin | Loja pendente não publica; aprovação autoriza só o titular |
| R05 Isolamento do vendedor | Filtros por store.owner_id | Vendedor A não altera anúncio nem parcela da loja B |
| R06 Isolamento do cliente | Filtros por customer_id/user_id | Cliente A não consulta encomenda nem morada do cliente B |
| R07 Catálogo de produtos/serviços | Listing.kind, pesquisa e páginas de detalhe | Filtros, paginação, estado vazio e ocultação de loja suspensa |
| R08 Regras de serviços | Stock nulo, ServiceRequest e preço sob consulta | Serviço não decrementa stock; solicitação depende do vendedor |
| R09 Carrinho persistente | CartItem por utilizador | Quantidade válida, alteração/remoção e autorização |
| R10 Total no servidor | create_order e Numeric/Decimal | Payload do browser não altera o total; snapshot preservado |
| R11 Compra multivendedor | Order + VendorOrder + OrderItem | Itens de duas lojas geram duas parcelas correctas |
| R12 Stock transaccional | Checkout com bloqueio PostgreSQL | Dois clientes disputam a última unidade; apenas um consegue |
| R13 Cancelamento/falha | release_stock e transições de estado | Cancelamento não torna a encomenda paga; stock reposto uma vez |
| R14 Pagamentos de teste | PaymentService / DemoPaymentProvider | Aviso explícito e bloqueio de encomendas sem indicador de teste |
| R15 Idempotência | Unicidade e transacções de tentativa | Repetição sem duplicar pagamento ou reserva de stock |
| R16 M-Pesa/e-Mola desactivados | Adaptadores bloqueiam chamadas reais | Pedido real devolve indisponibilidade sem confirmar pagamento |
| R17 Logística explícita | Método/morada e tarifa por loja | Entrega sem tarifa bloqueada; levantamento disponível |
| R18 Indicadores persistentes | Agregações SQL por titular e modo de dados | Comparar contagens/somas com PostgreSQL; separar testes |
| R19 CSV/PDF | Relatórios e PDF individual privado | Autorização, snapshots e aviso de ausência de cobrança nos testes |
| R20 Reclamações/auditoria | SupportTicket e AuditLog | Reclamação privada e acções críticas rastreáveis |
| R21 Segurança de sessão | CSRF, cookies, Argon2 e rate limiting | CSRF inválido rejeitado, replay de refresh e limite de login |
| R22 Imagens persistentes | Vercel Blob condicionado à configuração | Sem credenciais: indisponibilidade; validar bytes, tamanho e titular |
| R23 Interface responsiva/acessível | Layout, labels, foco e teclado | Capturas em diferentes larguras e fluxo com teclado |
| R24 Autenticação no browser | POST explícito, hidratação e origens de desenvolvimento | Login/registo com e sem JavaScript; nenhuma credencial na URL |
| R25 Operação e recuperação | DEPLOYMENT.md, SECURITY.md e BACKUP.md | Ensaio de backup/restauro e verificação de release |

## Registo de evidências

Para cada execução, guardar data, SHA/revisão, configuração sem segredos, comando, resultado e referência do artefacto. Os testes de navegador guardam resultados em `.local/browser-results/`, ignorada pelo Git. Capturas com seed devem manter a identificação de dados de teste.

Assinalar «não executado» quando faltar ambiente ou configuração. Resultados automatizados não substituem a avaliação manual de todos os fluxos, uma auditoria externa ou a validação de integrações com serviços reais.

# Matriz de rastreabilidade

Esta matriz relaciona implementação e verificações previstas; **não representa resultados de investigação**. «Teste» refere-se a teste automatizado ou cenário a executar. Resultados efectivos ficam em [VALIDATION.md](VALIDATION.md). Evidências com capturas devem evitar passwords, tokens e dados pessoais.

Objectivos específicos: OE1 organizar requisitos; OE2 projectar arquitectura multivendedor; OE3 implementar protótipo móvel com pagamentos previstos; OE4 permitir avaliação de viabilidade/usabilidade; OE5 documentar logística, segurança, confiança e fiabilidade.

| ID / requisito | Objectivo | Implementação/evidência no código | Verificação e evidência a guardar |
| --- | --- | --- | --- |
| R01 Requisitos e actores | OE1 | REQUIREMENTS.md e fluxos | Revisão com representante autorizado, ainda por realizar |
| R02 Monorepo e API real | OE2, OE3 | frontend, backend, compose e /health | Arranque local, healthcheck e catálogo API |
| R03 Registo/sessão/logout | OE3, OE5 | auth router, JWT, AuthSession | Registo, token inválido/expirado, refresh rotativo e logout |
| R04 Candidatura/aprovação | OE2, OE3 | Store.status e rotas vendor/admin | Pendente não publica; aprovação autoriza só titular |
| R05 Isolamento vendedor | OE2, OE5 | Filtros por store.owner_id | Vendedor A não altera anúncio nem subencomenda B |
| R06 Isolamento cliente | OE3, OE5 | Filtros por customer_id/user_id | Cliente A não consulta encomenda/morada B |
| R07 Catálogo produtos/serviços | OE3 | Listing.kind, pesquisa e páginas de detalhe | Filtros, paginação, estado vazio e loja suspensa oculta |
| R08 Serviço não é stock | OE2, OE3 | Stock nulo, ServiceRequest, preço sob consulta | Serviço não decrementa stock; solicitação confirmada pelo titular |
| R09 Carrinho persistente | OE3 | CartItem por utilizador | Quantidade válida, alteração/remoção e IDOR |
| R10 Total no servidor | OE3, OE5 | create_order e Numeric/Decimal | Preço enviado pelo browser não altera total; snapshot conservado |
| R11 Compra multivendedor | OE2, OE3 | Order + VendorOrder + OrderItem | Itens de duas lojas geram duas parcelas correctas |
| R12 Stock transaccional | OE3, OE5 | Checkout com bloqueio PostgreSQL | Dois clientes disputam última unidade; apenas um consegue |
| R13 Cancelamento/falha | OE3, OE5 | release_stock e estados | Nunca torna paga; repõe stock uma vez |
| R14 Pagamento demonstrativo | OE3, OE5 | PaymentService / DemoPaymentProvider | Rótulo explícito e bloqueio de encomendas reais |
| R15 Idempotência/repetições | OE3, OE5 | Unicidade e transacções de tentativa | Mesma chave/repetição sem duplicar pagamento ou stock |
| R16 M-Pesa/e-Mola preparados | OE3, OE5 | Adaptadores fail closed | Chamadas reais devolvem indisponível; não há URL inventado |
| R17 Logística explícita | OE3, OE5 | Método/morada e tarifa definida pela loja | Entrega sem tarifa bloqueada; levantamento disponível |
| R18 Dashboards reais | OE3 | Agregações SQL por titular e demonstração | Comparar contagens/somas com registos PostgreSQL |
| R19 CSV/PDF | OE3, OE5 | Relatórios e documento individual privado da encomenda | Autorização, IDOR, snapshots e aviso de que simulação não prova recebimento |
| R20 Reclamações/auditoria | OE3, OE5 | SupportTicket e AuditLog | Pedido privado e acção crítica rastreáveis |
| R21 Segurança de sessão | OE5 | CSRF, cookies, Argon2 e rate limit | CSRF inválido rejeitado, replay refresh e limite de login |
| R22 Imagens persistentes | OE3, OE5 | Integração Blob condicionada à configuração | Sem credenciais: erro explícito; validar tipos/tamanho/titular |
| R23 Interface móvel/acessível | OE3, OE4 | Layout responsivo, labels, foco e teclado | Capturas 360/768/1440 e fluxo completo com teclado |
| R24 Usabilidade/H1–H3 | OE4 | ACADEMIC_EVALUATION.md | Plano para 15 questionários/5 testes; recolha ainda não efectuada |
| R25 Documentação operacional | OE5 | DEPLOYMENT, SECURITY, BACKUP | Ensaio de backup/restauro e checklist de release |

## Registo de evidências

Para cada execução, guardar data, SHA/revisão, configuração sem segredos, comando, resultado e referência do artefacto. Sugestão de pasta local ignorada: `artifacts/validation/`. Os ficheiros de resultados não devem conter credenciais. Capturas de catálogo com seed têm de conservar a identificação de demonstração.

As capturas e avaliações manuais não foram preenchidas automaticamente nesta matriz. Assinalar «não executado» quando faltarem ambiente, participantes, credenciais ou autorização; nunca substituir observações por dados inventados.

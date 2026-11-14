# Demonstração académica — 10 a 15 minutos

Este é um guião previsto. Não afirma que a apresentação, os testes de usabilidade ou a recolha de questionários ocorreram. Preparar uma base isolada com seed explícito, API activa e credenciais locais, sem exibir a palavra-passe.

| Tempo aproximado | Acção | Mensagem/evidência |
| --- | --- | --- |
| 0:00–1:00 | Apresentar contexto e página inicial | Deloya, Nampula; marca provisória; protótipo académico |
| 1:00–2:30 | Pesquisar e filtrar catálogo | Dados da API/PostgreSQL; produtos e serviços separados |
| 2:30–3:30 | Abrir produto, loja e serviço sob consulta | Identidade da loja, preço MT, stock só em produtos, sem agenda em tempo real |
| 3:30–4:30 | Registar conta de teste ou entrar como cliente demo | Dados fictícios e sessão protegida |
| 4:30–6:00 | Adicionar itens de duas lojas e alterar quantidade | Carrinho persistente; total calculado pelo backend |
| 6:00–7:30 | Confirmar levantamento e criar encomenda | Duas subencomendas; custo explícito e snapshots |
| 7:30–8:30 | Simular sucesso, repetir confirmação e descarregar registo PDF | PAGAMENTO SIMULADO — SEM TRANSACÇÃO REAL; PDF não prova recebimento; repetição não duplica |
| 8:30–10:00 | Entrar como vendedor e processar a sua parcela | Isolamento por loja, transições permitidas e métricas demonstrativas |
| 10:00–11:30 | Entrar como administrador | Aprovação de loja, moderação e relatório autenticado |
| 11:30–12:30 | Mostrar cenário separado de falha/expiração | Encomenda não paga e stock restituído uma vez |
| 12:30–15:00 | Mostrar documentação e limitações | Plano 2027, 15 questionários/5 testes ainda por executar; integrações reais desactivadas |

## Preparação

1. Executar migração e seed conforme README. Confirmar `/health` e catálogo antes de apresentar.
2. Usar browser/perfis separados ou terminar sessão entre papéis. Não mostrar cookies, `.env` ou terminal com segredos.
3. Confirmar que há stock para dois cenários diferentes. O cenário de falha utiliza uma encomenda nova; não alterar o resultado final de um pagamento já concluído.
4. Preparar uma candidatura pendente real na base de demonstração para exemplificar aprovação, caso o seed não inclua uma.
5. Se Blob não estiver configurado, explicar a indisponibilidade de upload em vez de simular um ficheiro carregado.

## Pontos a explicar

- A listagem não mostra vendas, descontos ou avaliações inventados.
- O vendedor A não recebe a parcela B; essa regra está no backend.
- Preço sob consulta gera solicitação; não se cobra zero nem se inventa cotação.
- Levantamento e entrega combinada exigem informação explícita; não há GPS.
- O comprovativo demonstrativo não prova recebimento de dinheiro.
- A existência dos adaptadores M-Pesa/e-Mola não significa integração financeira autorizada.
- O protocolo académico permite avaliação futura; não se apresentam resultados inexistentes.

## Contingência

Se a API ou a base estiver indisponível, mostrar o erro e explicar a falha técnica. Não substituir por screenshots como se fossem uma sessão activa. Se se usar uma gravação de uma execução anterior, identificar data, versão e natureza da gravação. Não contornar autorização para completar a apresentação.

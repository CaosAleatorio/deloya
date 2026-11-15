# Limitações e condições de utilização

Este documento descreve o estado das integrações e as condições de operação do Deloya Marketplace. Resultados de execução ficam em [VALIDATION.md](VALIDATION.md).

| Área | Estado e consequência |
| --- | --- |
| M-Pesa/e-Mola | Transferência directa para número e titular declarados pelo vendedor; cliente informa referência e vendedor verifica a carteira. Sem cobrança, verificação de titular ou confirmação automática pelas APIs das operadoras. |
| Pagamentos de teste | Sucesso/falha/expiração são cenários explícitos, restritos a encomendas de teste. Não comprovam recebimento de dinheiro. |
| Liquidação | Cada loja recebe directamente a sua parcela. A plataforma não guarda fundos, divide transferências nem executa reembolsos. Confirmações do vendedor e referências ficam registadas para conciliação manual. |
| Email | Sem provedor real de email; recuperação de palavra-passe e confirmação por email não estão disponíveis. Não existe uma recuperação fictícia que afirme envio. |
| Imagens | Upload público de catálogo depende de Vercel Blob configurado. Sem token/origem autorizados devolve indisponibilidade. A execução local sem credenciais não valida upload remoto. |
| Anexos privados | Pedidos de apoio aceitam JPEG, PNG, WebP e PDF até 3 MiB, no máximo 10 por pedido, com Vercel Blob privado configurado. Apenas titular e administrador podem aceder; sem credencial privada, upload/download/remoção devolvem indisponibilidade. Acesso remoto só fica validado após publicar e testar o store. PDFs de encomendas são gerados em memória. |
| Serviços | Solicitação e confirmação pelo vendedor; sem agenda em tempo real. Serviço sob consulta não entra no checkout com um preço inventado. |
| Logística | Levantamento e entrega combinada com tarifa explícita definida pela loja; sem GPS, transportadoras ou tarifas automáticas inventadas. |
| Avaliações | Não há reputação pública, classificações de estrelas ou testemunhos fictícios. Avaliação de compra verificada pode ser extensão futura. |
| Deploy | Preparação Vercel/Neon/Blob não significa publicação ou recursos criados. Só comunicar URLs depois de verificação real. |

## Limites operacionais

Stock é reservado quando a encomenda é criada. Rejeitar uma referência manual não cancela a encomenda nem repõe stock; o cliente pode corrigir a referência. Uma declaração pendente ou um recebimento confirmado impede cancelamento global para evitar ignorar uma transferência. Não existe um worker permanente que expire encomendas por relógio; encomendas abandonadas podem manter reservas até resolução operacional.

As exportações limitam o resultado a 5000 subencomendas para evitar relatórios sem limite. Filtrar por categoria usa a categoria actual do anúncio; snapshots de compra preservam nome/preço, não uma taxonomia histórica completa.

A documentação de segurança e a existência de testes não substituem auditoria externa, validação comercial ou ensaios com utilizadores. O vendedor é responsável pelos dados da carteira e pela conferência do recebimento. Manter os dados de teste separados dos dados de operação e excluir pagamentos de teste das receitas reais.

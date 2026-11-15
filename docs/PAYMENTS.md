# Pagamentos directos aos vendedores

M-Pesa e e-Mola funcionam por transferência feita pelo cliente na sua carteira, fora da Deloya. A plataforma apresenta os dados declarados pelo vendedor, regista a referência e aguarda confirmação do recebimento pelo próprio vendedor. Não chama APIs das operadoras, não cobra dinheiro nem solicita PIN.

## Configurar a loja

Na candidatura de vendedor ou na edição da loja, preencher os pares que a loja aceita:

| Carteira | Campos |
| --- | --- |
| M-Pesa / Vodacom | Número e nome do titular tal como aparece na carteira |
| e-Mola / Movitel | Número e nome do titular tal como aparece na carteira |

Cada método exige os dois campos preenchidos. Números moçambicanos são normalizados para `+258` seguido de nove dígitos. Esta validação verifica formato; não consulta a operadora nem certifica titularidade. O vendedor deve conferir os dados antes de os guardar. Os campos financeiros não aparecem no catálogo público; o comprador autenticado recebe os destinatários da própria encomenda.

Os dados ficam copiados na subencomenda no checkout. Alterar a carteira da loja afecta compras futuras e preserva o destinatário apresentado nas encomendas já criadas.

## Comprar e confirmar

1. O servidor calcula artigos, entrega e total de cada loja. O browser não envia o valor a cobrar.
2. No detalhe da encomenda, o cliente escolhe M-Pesa ou e-Mola entre os métodos configurados e confere número, titular e valor.
3. O cliente faz a transferência na carteira, verifica o nome apresentado pela operadora e guarda a referência.
4. Na Deloya, informa referência e uma nota opcional. Isto cria uma declaração **pendente de confirmação**; não torna a encomenda paga.
5. O vendedor consulta o saldo/extracto da sua carteira, confere referência e valor, e confirma o recebimento na sua área. Pode rejeitar com motivo quando não encontrar o pagamento.

Uma compra de duas lojas exige duas transferências e duas confirmações independentes. O estado da encomenda pode ficar `parcialmente_paga` até todas as parcelas serem confirmadas. Cada vendedor processa apenas a sua parcela confirmada.

Rejeitar uma referência não cancela a encomenda nem repõe o stock. O cliente pode corrigir e reenviar. Uma declaração pendente ou recebimento confirmado bloqueia cancelamento global; resolver qualquer divergência com o vendedor e o apoio. A Deloya não executa estornos ou reembolsos automáticos.

## Controlo e histórico

As rotas validam titularidade da encomenda, propriedade e aprovação da loja, estado e montante no servidor. Operações usam bloqueios transaccionais e chaves de idempotência; repetir um pedido não duplica recebimentos. Uma confirmação final não pode ser convertida em rejeição por um novo clique.

Cada declaração conserva provedor, referência, parcela, valor, estado, datas e responsável pela revisão. Apenas o vendedor da parcela pode confirmar ou rejeitar. A auditoria regista a decisão sem incluir tokens ou PIN. Os relatórios identificam recebimentos confirmados pelo vendedor; não afirmam validação bancária pela Deloya.

O PDF da encomenda reflecte o estado registado, incluindo parcelas pendentes. Não substitui o comprovativo emitido pela operadora. Reclamações podem receber anexos privados na área de apoio; apenas titular e administradores acedem a esses ficheiros.

## Modos de operação

| `PAYMENT_MODE` | Comportamento |
| --- | --- |
| `manual` | Transferência directa M-Pesa/e-Mola e revisão pelo vendedor; modo habitual. |
| `demo` | Simulador legado de sucesso/falha/expiração, apenas em dados de teste elegíveis. |
| `disabled` | Novos pagamentos indisponíveis. |

Dados de teste preservam o indicador interno `is_demo` e o aviso **PAGAMENTO DE TESTE — SEM MOVIMENTAÇÃO DE DINHEIRO**. Nunca enviar dinheiro para esses destinatários. Confirmar um cenário de teste não representa dinheiro recebido e não integra receitas reais. Mudar de modo não converte contas, lojas ou encomendas antigas em dados reais.

Os adaptadores automáticos M-Pesa/e-Mola e o webhook permanecem desactivados. Uma página de retorno ou uma referência declarada pelo cliente nunca confirma recebimento por si só. Uma futura integração automática exigiria documentação e autorização próprias; não é necessária para este fluxo manual.

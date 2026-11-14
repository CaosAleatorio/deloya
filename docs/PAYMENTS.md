# Pagamentos e conciliação

## Modos

| Modo | Comportamento | Condições |
| --- | --- | --- |
| Teste | Simula sucesso, falha e expiração; persiste tentativa e estado | Dados de teste elegíveis e rótulo obrigatório |
| Sandbox oficial | Não activado | Documentação técnica aprovada, credenciais e testes do provedor |
| Produção real | Não activada | Contrato comercial, credenciais, segurança, reconciliação e autorização |

O rótulo obrigatório é **PAGAMENTO DE TESTE — SEM MOVIMENTAÇÃO DE DINHEIRO**. «Pago» num registo de teste significa apenas que a simulação teve sucesso. Relatórios e documentos de teste não provam recebimento de dinheiro. Nunca informar ou recolher PIN da carteira móvel.

## Provedores e fontes oficiais

A Vodacom apresenta uma API Aberta M-Pesa com C2B para recebimentos e métodos síncronos/assíncronos. O portal oficial menciona ambiente de testes. Isto confirma a existência da oferta, mas não concede à Deloya credenciais ou autorização. O adaptador real permanece desactivado até serem verificados os contratos técnicos e comerciais da conta autorizada. Fontes consultadas em 14/11/2026: [API Aberta M-Pesa](https://www.vm.co.mz/m-pesa/artigo/api-aberta-do-m-pesa) e [portal de desenvolvimento](https://developer.mpesa.vm.co.mz/).

Para e-Mola, a consulta ao [site oficial da Movitel](https://www.movitel.co.mz/) não disponibilizou uma especificação técnica pública utilizável nesta implementação. Não se conclui que uma API não exista. Solicitar documentação e acesso comercial à Movitel ou a um integrador autorizado e verificar a sua autorização antes de implementar chamadas. Não se adoptam URLs ou assinaturas de terceiros como contrato oficial.

## Desenho do serviço

`PaymentService` coordena regras de domínio; `DemoPaymentProvider`, `MPesaProvider` e `EMolaProvider` implementam uma interface de provedor. Os dois últimos falham de forma explícita enquanto não houver integração autorizada. O servidor calcula o montante a partir da encomenda; o browser não determina o total.

Cada tentativa guarda identidade própria, encomenda, referência interna única, provedor, montante Decimal, estado, chave de idempotência e timestamps. O isolamento impede um cliente de iniciar ou consultar pagamentos de encomendas de outro cliente. Operações que mudam o estado são transaccionais. Repetir a mesma chave devolve o resultado associado, sem criar outra tentativa ou aplicar a mesma transição duas vezes.

O fluxo de teste só pode actuar em dados identificados pelo indicador interno `is_demo`. Uma encomenda cancelada, falhada ou expirada não pode receber posteriormente uma confirmação simulada que a torne paga. A reposição de stock deve ocorrer no máximo uma vez quando o fluxo a exigir. O valor de provedor `demo` e o nome `DemoPaymentProvider` são identificadores técnicos preservados no contrato da API.

## Integração real futura

Antes de activar qualquer provedor:

1. Obter a especificação oficial aplicável, identidade do comerciante e condições de liquidação.
2. Implementar autenticação e validação de callbacks exactamente conforme esse contrato; rejeitar assinaturas inválidas e referências desconhecidas.
3. Definir timeouts, repetição segura, tratamento de estados indeterminados e reconciliação autorizada.
4. Testar eventos repetidos, fora de ordem, conflito de montante/moeda, entrega atrasada e falha após débito externo.
5. Separar credenciais e dados sandbox/produção; rever logs para excluir segredos e números financeiros completos.
6. Validar termos, privacidade, custos e limites antes de publicar.

Uma página de retorno nunca confirma pagamento. Um webhook não autenticado nunca altera a encomenda. Não existe aqui um mecanismo genérico inventado de assinatura para M-Pesa/e-Mola: a autenticação terá de seguir documentação oficial específica.

## Liquidação e relatórios

O sistema regista valores por vendedor através das subencomendas. Não executa transferências, split settlement, reembolso financeiro ou desembolsos automáticos. A conciliação comercial futura exige procedimento manual autorizado, registo do responsável e comparação com os extractos do provedor. Métricas de teste não devem ser somadas a receitas reais.

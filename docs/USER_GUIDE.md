# Guia de utilização

Deloya Marketplace, projecto de Adelino Fonseca João, 2026. A aplicação permite pesquisar produtos e serviços, comprar a várias lojas e gerir a actividade de vendedores e administradores.

## Aceder à aplicação

Com os serviços iniciados conforme o [README](../README.md), abrir `http://localhost:3000`. O cliente, o vendedor e o administrador utilizam este mesmo endereço. A API em `http://127.0.0.1:8000/docs` apresenta documentação técnica.

Para aceder por outro endereço da rede, seguir a configuração de origens no README. Login e registo requerem JavaScript; os campos ficam disponíveis quando a página termina de iniciar.

## Cliente

1. Pesquisar no catálogo e filtrar por categoria, loja, localização ou preço. Abrir o anúncio para consultar a descrição, o vendedor e a disponibilidade.
2. Criar conta ou iniciar sessão. A palavra-passe de registo deve ter entre 12 e 128 caracteres. Gerir perfil e moradas em `/conta`.
3. Adicionar produtos ou serviços com preço definido ao carrinho. Ajustar quantidades e rever o total calculado pela API.
4. Seleccionar levantamento ou entrega combinada. Entrega exige morada e tarifa definida por cada loja; uma tarifa ausente não significa entrega gratuita.
5. Confirmar a encomenda. Compras a várias lojas geram uma encomenda principal e uma parcela por vendedor.
6. No detalhe da encomenda, conferir o número, nome do titular e valor por loja. Transferir na carteira M-Pesa/e-Mola e informar a referência na Deloya. Aguardar a conferência do vendedor; informar uma referência não confirma pagamento.
7. Consultar o histórico para acompanhar os estados. O PDF individual fica disponível apenas ao titular e conserva nomes e preços da compra.
8. Para um serviço «sob consulta», enviar uma solicitação ao vendedor. A data pretendida depende de confirmação; não representa reserva automática de agenda.

Compras a várias lojas exigem transferências separadas. Encomendas elegíveis podem ser canceladas antes de existir referência pendente ou recebimento confirmado. Para esclarecer um problema, abrir uma reclamação associada à própria encomenda; pode anexar imagens/PDF privados até 3 MiB, quando o armazenamento estiver configurado.

## Vendedor

1. Iniciar sessão e apresentar a candidatura da loja com os contactos e dados comerciais. Para receber por M-Pesa, indicar número Vodacom e nome do titular; para e-Mola, número Movitel e nome do titular. Usar o nome exacto apresentado pela carteira. Estes campos também podem ser alterados na edição da loja.
2. Aguardar a aprovação do administrador. Uma candidatura pendente não publica anúncios.
3. Aceder a `/vendedor/dashboard` para consultar os indicadores da própria loja.
4. Criar produtos com preço, SKU e stock; criar serviços com preço definido ou sob consulta. Submeter anúncios à moderação antes da publicação.
5. Actualizar stock e condições da loja. Se outra operação alterar o anúncio durante uma edição, actualizar a página e rever os dados antes de tentar novamente.
6. Nas encomendas, conferir cada referência na própria carteira. Confirmar apenas depois de verificar valor e recebimento; rejeitar com motivo se não encontrar a transferência. Depois processar a parcela paga e as solicitações de serviço, seguindo as transições disponíveis.

O carregamento de imagens exige armazenamento configurado. Sem essa configuração, a aplicação apresenta a indisponibilidade. Cada vendedor gere apenas as suas imagens, anúncios e encomendas.

## Administrador

Iniciar sessão com uma conta administrativa e abrir `/admin/dashboard`. A área permite aprovar ou suspender lojas, moderar anúncios, gerir categorias, acompanhar encomendas e pagamentos, tratar reclamações e consultar auditoria.

Em `/admin/categorias`, seleccionar **Nova categoria** e indicar o nome. O identificador no endereço é opcional e pode ser gerado automaticamente; quando preenchido, espaços e acentos são convertidos para um formato válido. Deixar **Sem categoria principal** para criar uma categoria principal, inclusive a primeira. Seleccionar uma categoria existente apenas para criar uma subcategoria. Erros aparecem no próprio formulário e os valores são preservados para correcção.

Os relatórios CSV/PDF aceitam filtros de período, loja, categoria e estado conforme a permissão. Datas são interpretadas no fuso Africa/Maputo. Usar filtros para respeitar o limite de 5000 parcelas por exportação.

Para criar a primeira conta administrativa, seguir o procedimento privado em [SECURITY.md](SECURITY.md). As contas opcionais do seed destinam-se a testes.

## Pagamentos e dados de teste

O modo habitual é transferência directa para o vendedor, com confirmação manual. Não é necessário integrar as APIs M-Pesa/e-Mola. Nunca fornecer PIN. Verificar sempre o nome apresentado na carteira antes de transferir.

**PAGAMENTO DE TESTE — SEM MOVIMENTAÇÃO DE DINHEIRO.** Não transferir dinheiro para lojas ou encomendas marcadas como teste. O simulador legado admite sucesso, falha e expiração apenas em dados de teste elegíveis. Um estado «pago» nesse contexto confirma o cenário de teste, sem cobrança ou transferência.

O PDF e os relatórios identificam os registos de teste e não constituem prova de dinheiro recebido. Não fornecer PIN ou dados bancários. Consultar [PAYMENTS.md](PAYMENTS.md) para o estado das integrações.

## Resolver problemas de acesso

Se a página abre mas o catálogo ou o login falha, verificar `/health` na API e `/api/v1/products?page_size=1` no endereço do frontend. Confirmar `BACKEND_URL`, os dois processos activos e a autorização explícita do endereço usado no browser. O [README](../README.md) apresenta os comandos e o exemplo para acesso pela rede.

Se a API estiver indisponível, a interface apresenta um erro e permite tentar novamente. Não repetir uma compra sem consultar primeiro o histórico. Segredos, cookies e dados pessoais devem ficar fora de capturas e pedidos de suporte.

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
6. Consultar o histórico e o detalhe da encomenda para acompanhar os estados. O PDF individual fica disponível apenas ao titular e conserva nomes e preços da compra.
7. Para um serviço «sob consulta», enviar uma solicitação ao vendedor. A data pretendida depende de confirmação; não representa reserva automática de agenda.

Encomendas ainda por pagar podem ser canceladas conforme o estado permitido. Para esclarecer um problema, abrir uma reclamação associada à própria encomenda.

## Vendedor

1. Iniciar sessão e apresentar a candidatura da loja com os contactos e dados comerciais solicitados.
2. Aguardar a aprovação do administrador. Uma candidatura pendente não publica anúncios.
3. Aceder a `/vendedor/dashboard` para consultar os indicadores da própria loja.
4. Criar produtos com preço, SKU e stock; criar serviços com preço definido ou sob consulta. Submeter anúncios à moderação antes da publicação.
5. Actualizar stock e condições da loja. Se outra operação alterar o anúncio durante uma edição, actualizar a página e rever os dados antes de tentar novamente.
6. Processar as parcelas de encomendas e as solicitações de serviço da própria loja, seguindo as transições disponíveis.

O carregamento de imagens exige armazenamento configurado. Sem essa configuração, a aplicação apresenta a indisponibilidade. Cada vendedor gere apenas as suas imagens, anúncios e encomendas.

## Administrador

Iniciar sessão com uma conta administrativa e abrir `/admin/dashboard`. A área permite aprovar ou suspender lojas, moderar anúncios, gerir categorias, acompanhar encomendas e pagamentos, tratar reclamações e consultar auditoria.

Os relatórios CSV/PDF aceitam filtros de período, loja, categoria e estado conforme a permissão. Datas são interpretadas no fuso Africa/Maputo. Usar filtros para respeitar o limite de 5000 parcelas por exportação.

Para criar a primeira conta administrativa, seguir o procedimento privado em [SECURITY.md](SECURITY.md). As contas opcionais do seed destinam-se a testes.

## Pagamentos de teste

**PAGAMENTO DE TESTE — SEM MOVIMENTAÇÃO DE DINHEIRO.** M-Pesa e e-Mola reais estão desactivados. O simulador admite sucesso, falha e expiração apenas em encomendas de teste elegíveis. Um estado «pago» nesse contexto confirma o cenário de teste, sem cobrança ou transferência.

O PDF e os relatórios identificam os registos de teste e não constituem prova de dinheiro recebido. Não fornecer PIN ou dados bancários. Consultar [PAYMENTS.md](PAYMENTS.md) para o estado das integrações.

## Resolver problemas de acesso

Se a página abre mas o catálogo ou o login falha, verificar `/health` na API e `/api/v1/products?page_size=1` no endereço do frontend. Confirmar `BACKEND_URL`, os dois processos activos e a autorização explícita do endereço usado no browser. O [README](../README.md) apresenta os comandos e o exemplo para acesso pela rede.

Se a API estiver indisponível, a interface apresenta um erro e permite tentar novamente. Não repetir uma compra sem consultar primeiro o histórico. Segredos, cookies e dados pessoais devem ficar fora de capturas e pedidos de suporte.

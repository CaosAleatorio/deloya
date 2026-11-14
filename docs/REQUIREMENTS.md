# Requisitos, âmbito e fluxos

## Contexto

Marketplace multivendedor de produtos e serviços para Deloya Serviços e Comércios, Nampula, Moçambique. Projecto de Adelino Fonseca João, 2026. O sistema reúne clientes, vendedores e administração numa aplicação com dados persistentes e acesso por papel e titularidade.

## Actores

| Actor | Permissões principais | Restrição |
| --- | --- | --- |
| Visitante | Catálogo, pesquisa, categorias, lojas e detalhes publicados | Sem acesso a encomendas privadas |
| Cliente | Perfil, moradas, carrinho, encomendas e pagamentos de teste elegíveis | Apenas recursos próprios |
| Vendedor | Candidatura, loja aprovada, anúncios e subencomendas próprios | Sem editar dados de outra loja |
| Administrador | Aprovação, moderação, categorias, encomendas, reclamações e relatórios | Acções críticas auditadas |

## Requisitos principais

1. API e PostgreSQL como fonte dos dados operacionais; nenhuma lista fixa do frontend substitui uma API indisponível.
2. Registo/login e autorização aplicada no backend, inclusive para UUIDs manipulados.
3. Loja pendente até aprovação; anúncios visíveis apenas quando elegíveis.
4. Produtos com stock e serviços sem stock físico; preço em meticais, calculado no servidor.
5. Carrinho persistente com várias lojas; encomenda principal e subencomendas separadas.
6. Reserva transaccional de stock, snapshots e tratamento consistente de cancelamento/falha.
7. Pagamentos de teste explícitos, idempotentes e restritos a dados de teste.
8. Métricas da base de dados e separação entre dados de teste e dados de operação.
9. Documentação, testes essenciais, migrações e arranque reprodutível.

## Fluxos essenciais

**Descoberta:** visitante pesquisa → filtra → abre anúncio → consulta loja e disponibilidade → inicia sessão para adicionar ao carrinho. Uma ausência de dados apresenta estado vazio; indisponibilidade técnica apresenta erro recuperável.

**Candidatura:** cliente submete dados da loja → estado pendente → administrador aprova ou suspende → titular passa a gerir catálogo próprio. Alterar o URL da interface não concede permissões.

**Compra:** cliente autentica → adiciona itens → escolhe logística e verifica condições → backend bloqueia os recursos necessários, revalida stock e preços, cria encomenda e subencomendas → carrinho é actualizado na mesma operação. Subtotal não é aceite do browser como verdade.

**Serviço:** cliente consulta preço base ou «sob consulta» → pede confirmação ao vendedor e, quando aplicável, indica data pretendida. Não existe promessa de agenda sincronizada em tempo real. Um serviço sob consulta requer acordo de preço antes de entrar num fluxo de pagamento.

**Pagamento de teste:** encomenda de teste elegível → tentativa com chave de idempotência → cenário de sucesso/falha/expiração → estado persistido no servidor. Repetições não geram novo débito de stock. O aviso de ausência de movimentação de dinheiro acompanha o fluxo e os documentos. Provedores reais permanecem bloqueados.

**Processamento:** vendedor consulta apenas a sua subencomenda → avança conforme transições autorizadas → cliente acompanha estado agregado. Não se simula GPS ou transportadora.

**Reclamação e auditoria:** cliente regista problema associado aos seus recursos → administrador autorizado consulta e trata → alterações críticas ficam identificáveis em auditoria.

## Critérios transversais

Interface pt-MZ, valores MZN/MT, datas dd/mm/aaaa em Africa/Maputo e armazenamento UTC. Formulários com rótulos, erros compreensíveis, foco visível e navegação por teclado. Listagens paginadas. Segredos fora do Git e de variáveis públicas do Next.js. A publicação requer configuração de alojamento, revisão dos textos de operação e verificação das integrações utilizadas.

## Integrações e extensões

Desembolsos automáticos, divisão real de fundos, transportadoras e cálculo automático de tarifas não estão implementados. A aplicação não recolhe PIN de carteira móvel. Capacidades dependentes de serviços externos são descritas em [LIMITATIONS.md](LIMITATIONS.md).

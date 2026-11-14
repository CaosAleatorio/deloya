# Requisitos, âmbito e fluxos

## Contexto

Protótipo académico multivendedor para Deloya Serviços e Comércios, Nampula. A marca é provisória. O objectivo é desenvolver e permitir avaliar o sistema durante 2027; não se afirma impacto comprovado nas vendas.

## Actores

| Actor | Permissões principais | Restrição |
| --- | --- | --- |
| Visitante | Catálogo, pesquisa, categorias, lojas e detalhes publicados | Sem acesso a encomendas privadas |
| Cliente | Perfil, moradas, carrinho, encomendas e pagamentos de demonstração elegíveis | Apenas recursos próprios |
| Vendedor | Candidatura, loja aprovada, anúncios e subencomendas próprios | Sem editar dados de outra loja |
| Administrador | Aprovação, moderação, categorias, encomendas, reclamações e relatórios | Acções críticas auditadas |

## Prioridades do MVP

1. API e PostgreSQL como fonte dos dados operacionais; nenhuma lista fixa do frontend substitui uma API indisponível.
2. Registo/login e autorização aplicada no backend, inclusive para UUIDs manipulados.
3. Loja pendente até aprovação; anúncios visíveis apenas quando elegíveis.
4. Produtos com stock e serviços sem stock físico; preço em meticais, calculado no servidor.
5. Carrinho persistente com várias lojas; encomenda principal e subencomendas separadas.
6. Reserva transaccional de stock, snapshots e tratamento consistente de cancelamento/falha.
7. Pagamentos de demonstração explícitos, idempotentes e restritos a dados demonstrativos.
8. Métricas da base de dados e separação entre demonstração e operação real.
9. Documentação, testes essenciais, migrações e arranque reprodutível.

## Fluxos essenciais

**Descoberta:** visitante pesquisa → filtra → abre anúncio → consulta loja e disponibilidade → inicia sessão para adicionar ao carrinho. Uma ausência de dados apresenta estado vazio; indisponibilidade técnica apresenta erro recuperável.

**Candidatura:** cliente submete dados da loja → estado pendente → administrador aprova ou suspende → titular passa a gerir catálogo próprio. Alterar o URL da interface não concede permissões.

**Compra:** cliente autentica → adiciona itens → escolhe logística e verifica condições → backend bloqueia os recursos necessários, revalida stock e preços, cria encomenda e subencomendas → carrinho é actualizado na mesma operação. Subtotal não é aceite do browser como verdade.

**Serviço:** cliente consulta preço base ou «sob consulta» → pede confirmação ao vendedor e, quando aplicável, indica data pretendida. Não existe promessa de agenda sincronizada em tempo real. Um serviço sob consulta requer acordo de preço antes de entrar num fluxo de pagamento.

**Pagamento:** encomenda demonstrativa elegível → tentativa com chave de idempotência → simulação de sucesso/falha/expiração → estado persistido no servidor. Repetições não geram novo débito de stock. Provedores reais permanecem bloqueados.

**Processamento:** vendedor consulta apenas a sua subencomenda → avança conforme transições autorizadas → cliente acompanha estado agregado. Não se simula GPS ou transportadora.

**Reclamação e auditoria:** cliente regista problema associado aos seus recursos → administrador autorizado consulta e trata → alterações críticas ficam identificáveis em auditoria.

## Critérios transversais

Interface pt-MZ, valores MZN/MT, datas dd/mm/aaaa em Africa/Maputo e armazenamento UTC. Formulários com rótulos, erros compreensíveis, foco visível e navegação por teclado. Listagens paginadas. Segredos fora do Git e de variáveis públicas do Next.js. Deploy comercial, credenciais financeiras, política de armazenamento, tarifas e branding dependem de validação institucional.

## Fora do âmbito autorizado

Não se implementam desembolsos automáticos, divisão real de fundos, recolha de PIN, resultados de investigação fabricados, transportadoras fictícias ou taxas de entrega inventadas. Credenciais de serviços pagos não são criadas. Capacidades dependentes de serviços externos são descritas em [LIMITATIONS.md](LIMITATIONS.md).

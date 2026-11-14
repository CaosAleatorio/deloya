# Limitações e condições de utilização

Este protótipo académico não é apresentado como sistema financeiro autorizado para produção. As limitações abaixo descrevem o âmbito e dependências externas efectivamente identificados; resultados de execução ficam em [VALIDATION.md](VALIDATION.md).

| Área | Estado e consequência |
| --- | --- |
| M-Pesa/e-Mola | Adaptadores reais desactivados. Não há credenciais/contratos autorizados nem chamadas de cobrança reais. Sandbox oficial não está ligado. |
| Simulação | Sucesso/falha/expiração são cenários explícitos, restritos a encomendas demonstrativas. Não comprovam recebimento de dinheiro. |
| Liquidação | Não há transferência automática a vendedores, split settlement ou reembolso financeiro real. Valores por loja permitem futura conciliação manual autorizada. |
| Email | Sem provedor real de email; recuperação de palavra-passe e confirmação por email não estão disponíveis. Não existe uma recuperação fictícia que afirme envio. |
| Imagens | Upload público de catálogo depende de Vercel Blob configurado. Sem token/origem autorizados devolve indisponibilidade. A execução local sem credenciais não valida upload remoto. |
| Anexos privados | Não há módulo de upload de documentos sensíveis de utilizadores. A futura persistência requer armazenamento privado e rota de acesso autenticada. Relatórios e documentos individuais de encomenda PDF são respostas autenticadas em memória, sem persistência de ficheiros. |
| Serviços | Solicitação e confirmação pelo vendedor; sem agenda em tempo real. Serviço sob consulta não entra no checkout com um preço inventado. |
| Logística | Levantamento e entrega combinada com tarifa explícita definida pela loja; sem GPS, transportadoras ou tarifas automáticas inventadas. |
| Avaliações | Não há reputação pública, classificações de estrelas ou testemunhos fictícios. Avaliação de compra verificada pode ser extensão futura. |
| Investigação | Cerca de 15 questionários e cinco testes são plano para 2027, não participantes/resultados recolhidos. Não existe recolha digital automática de investigação. |
| Branding/documentos | Marca/logótipo provisórios e termos/privacidade demonstrativos, sujeitos à revisão institucional antes de uso comercial. |
| Deploy | Preparação Vercel/Neon/Blob não significa publicação ou recursos criados. Só comunicar URLs depois de verificação real. |

## Limites operacionais do MVP

Stock é reservado quando a encomenda é criada e libertado por cancelamento ou resultado explícito de falha/expiração. Não existe um worker permanente que expire encomendas por relógio. Uma encomenda abandonada pode manter reserva até ser cancelada; antes de operação comercial, definir prazo e reconciliação por chamadas HTTP idempotentes autorizadas.

As exportações limitam o resultado a 5000 subencomendas para evitar relatórios sem limite. Filtrar por categoria usa a categoria actual do anúncio; snapshots de compra preservam nome/preço, não uma taxonomia histórica completa.

A documentação de segurança e a existência de testes não substituem auditoria externa, validação comercial, autorização dos operadores de pagamento ou ensaios com utilizadores. Não somar dados demonstrativos a receitas reais e não utilizar o seed para preencher lacunas de investigação.

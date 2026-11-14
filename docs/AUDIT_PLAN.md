# Plano de manutenção e verificação

Deloya Marketplace — Adelino Fonseca João, 2026. Este plano organiza a revisão técnica e a entrega de versões do sistema.

## Componentes

| Componente | Pontos de revisão |
| --- | --- |
| Frontend Next.js | Navegação, formulários, acessibilidade, proxy da API e build |
| API FastAPI | Validação, sessão, autorização por titular e contratos HTTP |
| PostgreSQL | Constraints, migrações, consistência de stock e recuperação |
| Marketplace | Catálogo, candidaturas, moderação, carrinho e parcelas por loja |
| Pagamentos | Idempotência, aviso de teste e bloqueio dos provedores reais |
| Administração | Indicadores, reclamações, auditoria e relatórios privados |
| Integrações | Configuração de armazenamento e verificação dos serviços utilizados |

## Processo de alteração

1. Identificar o requisito, o comportamento esperado e os componentes afectados em [REQUIREMENTS_TRACEABILITY.md](REQUIREMENTS_TRACEABILITY.md).
2. Rever compatibilidade dos contratos HTTP e das migrações. Preservar os dados existentes e o isolamento entre lojas e clientes.
3. Implementar a alteração e executar os testes adequados numa base isolada, conforme [TESTING.md](TESTING.md).
4. Registar resultados, falhas e limites em [VALIDATION.md](VALIDATION.md), com ambiente e revisão identificados.
5. Antes de publicar uma versão, verificar configuração, backup, migração e fluxos essenciais conforme [DEPLOYMENT.md](DEPLOYMENT.md).

## Dependências operacionais

A configuração local usa PostgreSQL e processos separados para a API e o frontend. Os dados de teste são opcionais e carregados por comando explícito. A publicação requer alojamento configurado; pagamentos reais, email e armazenamento remoto dependem das integrações descritas em [LIMITATIONS.md](LIMITATIONS.md).

O código é mantido em [CaosAleatorio/deloya](https://github.com/CaosAleatorio/deloya). Um envio para GitHub identifica uma revisão; a disponibilidade da aplicação deve ser verificada no ambiente onde for instalada.

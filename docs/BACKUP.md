# Backup e recuperação

## Política proposta

Definir responsável, frequência, retenção e objectivos de recuperação para a instalação. O agendamento de backups remotos e a recuperação automática dependem da infraestrutura utilizada. A retenção de contactos, moradas e encomendas deve seguir a política de privacidade.

Guardar dumps cifrados fora do repositório, com acesso restrito. Incluir revisão Alembic, versão PostgreSQL e SHA da aplicação num registo sem segredos. Não copiar `.env` ou passwords para a pasta pública de artefactos.

## Backup PostgreSQL local

Com o serviço `db` activo, pode criar um dump dentro do contentor e copiá-lo para uma pasta local privada. Os comandos partem da raiz; adaptar nome da base/utilizador se `.env` os alterar.

```powershell
New-Item -ItemType Directory -Force .local-backups
docker compose exec db pg_dump -U deloya -d deloya -Fc -f /tmp/deloya-backup.dump
$databaseContainer = docker compose ps -q db
docker cp "${databaseContainer}:/tmp/deloya-backup.dump" .local-backups/deloya-backup.dump
```

Não usar redireccionamento de saída binária do `pg_dump` em versões antigas de PowerShell. Fazer uma nova cópia com nome e data próprios para não substituir a única cópia disponível. A pasta `.local-backups` deve continuar ignorada pelo Git.

Para Neon, usar uma ligação **directa**, não pooled, com `pg_dump` compatível. Carregar a credencial por mecanismo privado do ambiente ou ficheiro de password com permissões adequadas; não a colocar no histórico de comandos. Consultar [pooling e ferramentas administrativas Neon](https://neon.com/docs/connect/connection-pooling).

## Ensaiar recuperação sem sobrescrever a base activa

Criar uma base vazia e isolada; nunca executar `--clean` na base que contém dados a preservar. Exemplo local:

```powershell
docker compose exec db createdb -U deloya deloya_restore_check
$databaseContainer = docker compose ps -q db
docker cp .local-backups/deloya-backup.dump "${databaseContainer}:/tmp/deloya-backup.dump"
docker compose exec db pg_restore -U deloya -d deloya_restore_check --no-owner /tmp/deloya-backup.dump
docker compose exec db psql -U deloya -d deloya_restore_check -c "SELECT version_num FROM alembic_version;"
```

Comparar contagens e relações essenciais sem imprimir dados pessoais. Apontar uma instância de verificação da API para a base restaurada e testar leitura/autorização. Um dump criado com sucesso não confirma que a recuperação funciona; registar separadamente o resultado do ensaio.

## Ficheiros e incidentes

Se Blob vier a ser activado, inventariar referências e política de recuperação do armazenamento; o dump PostgreSQL não contém os bytes das imagens/anexos. Confirmar a possibilidade de restaurar ficheiros privados sem os tornar públicos.

Em incidente: limitar novas escritas, preservar evidência com acesso restrito, identificar último backup verificado, restaurar para ambiente separado, validar integridade e autorizações, e só então efectuar a mudança de serviço autorizada. Documentar perda efectiva de dados e não ocultar lacunas com seed.

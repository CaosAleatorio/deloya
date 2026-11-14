$ErrorActionPreference = 'Stop'
$workspacePath = Split-Path -Parent $PSScriptRoot
Push-Location (Join-Path $workspacePath 'frontend')
try {
    npm.cmd run lint
    if ($LASTEXITCODE -ne 0) { throw 'Frontend: lint falhou.' }
    npx.cmd tsc --noEmit
    if ($LASTEXITCODE -ne 0) { throw 'Frontend: TypeScript falhou.' }
    npm.cmd test
    if ($LASTEXITCODE -ne 0) { throw 'Frontend: testes falharam.' }
    npm.cmd run build
    if ($LASTEXITCODE -ne 0) { throw 'Frontend: build falhou.' }
} finally { Pop-Location }
Push-Location (Join-Path $workspacePath 'backend')
try {
    & (Join-Path $workspacePath '.venv/Scripts/python.exe') (Join-Path $workspacePath 'scripts/test-backend.py') -q
    if ($LASTEXITCODE -ne 0) { throw 'Backend: testes falharam.' }
} finally { Pop-Location }

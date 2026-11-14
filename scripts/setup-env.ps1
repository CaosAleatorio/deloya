param([switch]$Force)
$ErrorActionPreference = 'Stop'
$workspacePath = Split-Path -Parent $PSScriptRoot
$envPath = Join-Path $workspacePath '.env'
if ((Test-Path -LiteralPath $envPath) -and -not $Force) {
    Write-Host '.env já existe. Nenhuma configuração foi alterada.'
    exit 0
}
if ((Test-Path -LiteralPath $envPath) -and $Force) {
    throw 'Preserve o .env existente; renomeie-o explicitamente antes de gerar outro.'
}
function New-LocalSecret {
    $secretBytes = New-Object byte[] 32
    $generator = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try { $generator.GetBytes($secretBytes) } finally { $generator.Dispose() }
    return ([BitConverter]::ToString($secretBytes)).Replace('-', '').ToLowerInvariant()
}
$databaseSecret = New-LocalSecret
$jwtSecret = New-LocalSecret
$demoSecret = New-LocalSecret
$templatePath = Join-Path $workspacePath '.env.example'
$content = [IO.File]::ReadAllText($templatePath)
$content = $content.Replace('POSTGRES_PASSWORD=', 'POSTGRES_PASSWORD=' + $databaseSecret)
$content = $content.Replace('deloya:ALTERAR@', 'deloya:' + $databaseSecret + '@')
$content = $content.Replace('JWT_SECRET=', 'JWT_SECRET=' + $jwtSecret)
$content = $content.Replace('DEMO_PASSWORD=', 'DEMO_PASSWORD=' + $demoSecret)
[IO.File]::WriteAllText($envPath, $content, (New-Object System.Text.UTF8Encoding($false)))
Write-Host '.env criado com segredos aleatórios. Consulte-o localmente; nunca o envie para Git.'

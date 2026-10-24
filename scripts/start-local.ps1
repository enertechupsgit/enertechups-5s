param([switch]$UseExistingData)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$runtimeRoot = Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies'
$pythonPath = Join-Path $runtimeRoot 'python/python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) {
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if (-not $pythonCommand) { throw 'Python 3.12 is required. Install Python and backend/requirements.txt.' }
    $pythonPath = $pythonCommand.Source
}
$nodeCommand = Get-Command node -ErrorAction SilentlyContinue
if (-not $nodeCommand) { throw 'Node.js is required.' }
$logDirectory = Join-Path $projectRoot 'artifacts'
New-Item -ItemType Directory -Path $logDirectory -Force | Out-Null
if (-not (Test-Path (Join-Path $projectRoot 'apps/web/node_modules/vite/bin/vite.js'))) { throw 'Install web dependencies with pnpm install in apps/web first.' }
foreach ($port in @(8000,5173)) {
    $probe = [System.Net.Sockets.TcpClient]::new()
    $occupied = $false
    try { $probe.Connect('127.0.0.1', $port); $occupied = $true } catch { $occupied = $false } finally { $probe.Dispose() }
    if ($occupied) { throw "Port $port is already in use. Existing services were left running." }
}
$previousPythonPath = $env:PYTHONPATH
$previousDatabase = $env:DATABASE_URL
$previousDemo = $env:LOCAL_DEMO
try {
    $localPackages = Join-Path $projectRoot 'backend/.venv/Lib/site-packages'
    if (Test-Path $localPackages) { $env:PYTHONPATH = $localPackages }
    $databaseName = if ($UseExistingData) { 'digi5s.db' } else { 'local-preview.db' }
    $databasePath = (Join-Path $projectRoot "backend/$databaseName").Replace('\','/')
    $env:DATABASE_URL = "sqlite+aiosqlite:///$databasePath"
    $env:LOCAL_DEMO = if ($UseExistingData) { '0' } else { '1' }
    $api = Start-Process -FilePath $pythonPath -ArgumentList '-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8000' -WorkingDirectory (Join-Path $projectRoot 'backend') -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logDirectory 'api.log') -RedirectStandardError (Join-Path $logDirectory 'api-error.log') -PassThru
    $web = Start-Process -FilePath $nodeCommand.Source -ArgumentList 'node_modules/vite/bin/vite.js','--host','127.0.0.1','--port','5173','--strictPort' -WorkingDirectory (Join-Path $projectRoot 'apps/web') -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logDirectory 'web.log') -RedirectStandardError (Join-Path $logDirectory 'web-error.log') -PassThru
    @{ api = $api.Id; web = $web.Id } | ConvertTo-Json | Set-Content (Join-Path $logDirectory 'local-processes.json')
    Write-Output 'Enertech web: http://127.0.0.1:5173'
    Write-Output 'API docs: http://127.0.0.1:8000/docs'
    Write-Output "Database: $databasePath"
    Write-Output "Process IDs: API $($api.Id), web $($web.Id). Logs: $logDirectory"
} finally {
    $env:PYTHONPATH = $previousPythonPath
    $env:DATABASE_URL = $previousDatabase
    $env:LOCAL_DEMO = $previousDemo
}

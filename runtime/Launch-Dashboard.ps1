$ErrorActionPreference = 'Stop'
$projectDir = Split-Path -Parent $PSScriptRoot
$runtimeDir = Join-Path $PSScriptRoot 'LibreOffice'
$archivePath = Join-Path $PSScriptRoot 'LibreOffice.zip'
$pythonPath = Join-Path $runtimeDir 'program\python.exe'
$readyPath = Join-Path $runtimeDir '.dashboard-ready'
try {
    if (!(Test-Path -LiteralPath $readyPath) -or !(Test-Path -LiteralPath $pythonPath)) {
        if (!(Test-Path -LiteralPath $archivePath)) { throw 'The bundled LibreOffice archive is missing.' }
        $stream = [IO.File]::OpenRead($archivePath)
        try { $first = $stream.ReadByte(); $second = $stream.ReadByte() } finally { $stream.Dispose() }
        if ($first -ne 80 -or $second -ne 75) {
            throw 'LibreOffice.zip is a Git LFS pointer, not the runtime. Download the full project bundle or run git lfs pull in this repository.'
        }
        Write-Host 'Preparing LibreOffice for first use. This can take a few minutes...'
        Expand-Archive -LiteralPath $archivePath -DestinationPath $runtimeDir -Force
        & $pythonPath -c 'import uno; import sys; print("Bundled Python:", sys.version)'
        if ($LASTEXITCODE -ne 0) { throw 'Bundled Python or UNO failed to start.' }
        Set-Content -LiteralPath $readyPath -Value 'Runtime extracted and UNO import verified.'
    }
    Push-Location $projectDir
    try {
        & $pythonPath (Join-Path $projectDir 'Map_webui\start_all.py')
        exit $LASTEXITCODE
    } finally { Pop-Location }
} catch {
    Write-Host "Dashboard could not start: $_" -ForegroundColor Red
    exit 1
}

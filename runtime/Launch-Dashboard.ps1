$ErrorActionPreference = 'Stop'
$projectDir = Split-Path -Parent $PSScriptRoot
$runtimeDir = Join-Path $PSScriptRoot 'LibreOffice'
$archivePath = Join-Path $PSScriptRoot 'LibreOffice.zip'
$pythonPath = Join-Path $runtimeDir 'program\python.exe'
$readyPath = Join-Path $runtimeDir '.dashboard-ready'
$extractedPath = Join-Path $runtimeDir '.dashboard-extracted'
try {
    # Release ZIPs already contain the expanded runtime and this extraction marker.
    if (!(Test-Path -LiteralPath $extractedPath) -and !(Test-Path -LiteralPath $readyPath)) {
        if (!(Test-Path -LiteralPath $archivePath)) { throw 'The bundled LibreOffice archive is missing. Extract the complete portable project ZIP.' }
        Add-Type -AssemblyName System.IO.Compression.FileSystem
        Write-Host 'Preparing LibreOffice (completed files will be reused)...'
        $zip = $null
        try {
            $zip = [IO.Compression.ZipFile]::OpenRead($archivePath)
            $rootPath = [IO.Path]::GetFullPath($runtimeDir) + [IO.Path]::DirectorySeparatorChar
            $index = 0
            foreach ($entry in $zip.Entries) {
                $destination = [IO.Path]::GetFullPath((Join-Path $runtimeDir $entry.FullName))
                if (!$destination.StartsWith($rootPath, [StringComparison]::OrdinalIgnoreCase)) { throw 'Invalid archive entry.' }
                if (!$entry.Name) { [IO.Directory]::CreateDirectory($destination) | Out-Null; continue }
                [IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($destination)) | Out-Null
                if (!(Test-Path -LiteralPath $destination) -or (Get-Item -LiteralPath $destination).Length -ne $entry.Length) {
                    [IO.Compression.ZipFileExtensions]::ExtractToFile($entry, $destination, $true)
                }
                $index++
                if ($index % 100 -eq 0) { Write-Progress -Activity 'Preparing LibreOffice' -Status $entry.Name -PercentComplete (100 * $index / $zip.Entries.Count) }
            }
            Set-Content -LiteralPath $extractedPath -Value 'Extraction complete.'
        } catch {
            throw "Runtime extraction failed: $_. If this is a GitHub source ZIP, ensure Git LFS objects are included, or use the complete portable release ZIP."
        } finally {
            if ($zip) { $zip.Dispose() }
            Write-Progress -Activity 'Preparing LibreOffice' -Completed
        }
    }
    # The installed distribution keeps VC++ DLLs in System64 for its installer.
    # A portable launch needs them beside the x64 executables instead.
    $programDir = Join-Path $runtimeDir 'program'
    $systemDllDir = Join-Path $runtimeDir 'System64'
    if (!(Test-Path -LiteralPath $systemDllDir)) { throw 'Bundled System64 runtime files are missing. Re-extract the complete download.' }
    Get-ChildItem -LiteralPath $systemDllDir -Filter '*.dll' -File | ForEach-Object {
        $target = Join-Path $programDir $_.Name
        if (!(Test-Path -LiteralPath $target)) { Copy-Item -LiteralPath $_.FullName -Destination $target }
    }
    Write-Host 'Checking bundled Python and UNO...' 
    $diagnostic = & $pythonPath (Join-Path $PSScriptRoot 'check_runtime.py') 2>&1
    $checkExit = $LASTEXITCODE
    $diagnostic | ForEach-Object { Write-Host $_ }
    if ($checkExit -ne 0) { throw "Runtime check exited with code $checkExit. $($diagnostic -join ' ')" }
    Set-Content -LiteralPath $readyPath -Value 'Runtime verified.'
    Push-Location $projectDir
    try {
        & $pythonPath (Join-Path $projectDir 'Map_webui\start_all.py')
        exit $LASTEXITCODE
    } finally { Pop-Location }
} catch {
    Write-Host "Dashboard could not start: $_" -ForegroundColor Red
    exit 1
}

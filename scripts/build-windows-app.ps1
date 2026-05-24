$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$DesktopDir = Join-Path $ProjectRoot "ui\desktop"
$BackendBuildScript = Join-Path $ProjectRoot "scripts\build-backend.ps1"

Write-Host "== IA Local Agent Windows build =="

Write-Host "1/3 Empaquetando backend Python..."
& $BackendBuildScript
if ($LASTEXITCODE -ne 0) {
    throw "Fallo el build del backend."
}

Write-Host "2/3 Preparando frontend..."
Push-Location $DesktopDir
try {
    if (-not (Test-Path (Join-Path $DesktopDir "node_modules"))) {
        npm install
        if ($LASTEXITCODE -ne 0) {
            throw "npm install fallo."
        }
    }

    Write-Host "3/3 Ejecutando Tauri build..."
    npm run tauri:build
    if ($LASTEXITCODE -ne 0) {
        throw "tauri build fallo."
    }
}
finally {
    Pop-Location
}

$BundleRoot = Join-Path $DesktopDir "src-tauri\target\release\bundle"
$Installers = @()
if (Test-Path $BundleRoot) {
    $Installers = Get-ChildItem -Path $BundleRoot -Recurse -Include "*.exe", "*.msi" | Where-Object {
        $_.FullName -match "\\(nsis|msi)\\"
    }
}

if ($Installers.Count -eq 0) {
    Write-Host "Build completado, pero no se encontro instalador en $BundleRoot"
    exit 0
}

Write-Host "Instalador generado:"
$Installers | Sort-Object LastWriteTime -Descending | ForEach-Object {
    Write-Host "  $($_.FullName)"
}

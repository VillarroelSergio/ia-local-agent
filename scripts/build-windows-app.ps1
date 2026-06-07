param(
    [ValidateSet("major", "minor", "patch")]
    [string]$VersionPart = "patch",
    [switch]$NoVersionBump
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$DesktopDir = Join-Path $ProjectRoot "ui\desktop"
$BackendBuildScript = Join-Path $ProjectRoot "scripts\build-backend.ps1"
$VersionScript = Join-Path $ProjectRoot "scripts\bump-version.ps1"

Write-Host "== IA Local Agent Windows build =="

if (-not $NoVersionBump) {
    Write-Host "1/4 Incrementando version ($VersionPart)..."
    & $VersionScript -Part $VersionPart
    if ($LASTEXITCODE -ne 0) {
        throw "Fallo el incremento de version."
    }
}
else {
    Write-Host "1/4 Version sin cambios (-NoVersionBump)."
}

Write-Host "2/4 Empaquetando backend Python..."
& $BackendBuildScript
if ($LASTEXITCODE -ne 0) {
    throw "Fallo el build del backend."
}

Write-Host "3/4 Preparando frontend..."
Push-Location $DesktopDir
try {
    if (-not (Test-Path (Join-Path $DesktopDir "node_modules"))) {
        npm install
        if ($LASTEXITCODE -ne 0) {
            throw "npm install fallo."
        }
    }

    Write-Host "4/4 Ejecutando Tauri build..."
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

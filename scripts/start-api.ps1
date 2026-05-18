param(
    [string]$HostName = "127.0.0.1",
    [int]$Port = 8765
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $ProjectRoot "venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    throw "No se encontro el venv en $Python"
}

Set-Location $ProjectRoot
$env:API_HOST = $HostName
$env:API_PORT = [string]$Port

Write-Host "IA Local Agent API escuchando en http://$HostName`:$Port"
Write-Host "Deja esta ventana abierta mientras uses la API."
& $Python -m src.api.main

param(
    [switch]$CleanOnly
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$SpecPath = Join-Path $ProjectRoot "build\ia-local-agent-api.spec"
$DistDir = Join-Path $ProjectRoot "dist"
$BuildWorkDir = Join-Path $ProjectRoot "build\pyinstaller"
$BinaryDir = Join-Path $ProjectRoot "ui\desktop\src-tauri\binaries"
$VersionPath = Join-Path $ProjectRoot "VERSION"
$ExeName = "ia-local-agent-api.exe"
$PlainSidecarPath = Join-Path $BinaryDir $ExeName

function Resolve-Python {
    $VenvPython = Join-Path $ProjectRoot "venv\Scripts\python.exe"
    if (Test-Path $VenvPython) {
        return $VenvPython
    }

    $PythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($PythonCommand) {
        return $PythonCommand.Source
    }

    throw "No se encontro Python. Crea venv o instala Python y vuelve a ejecutar el script."
}

function Resolve-TargetTriple {
    $Rustc = Get-Command rustc -ErrorAction SilentlyContinue
    if (-not $Rustc) {
        return "x86_64-pc-windows-msvc"
    }

    $HostLine = (& $Rustc.Source -Vv | Select-String "host:" | Select-Object -First 1).Line
    if (-not $HostLine) {
        return "x86_64-pc-windows-msvc"
    }

    return $HostLine.Split(" ", [System.StringSplitOptions]::RemoveEmptyEntries)[1]
}

function Assert-UnderProject {
    param([string]$PathToCheck)

    $ResolvedProject = [System.IO.Path]::GetFullPath($ProjectRoot)
    $ResolvedTarget = [System.IO.Path]::GetFullPath($PathToCheck)
    if (-not $ResolvedTarget.StartsWith($ResolvedProject, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Ruta fuera del proyecto, no se limpiara: $ResolvedTarget"
    }
}

function Remove-PathWithRetry {
    param(
        [string]$PathToRemove,
        [switch]$Recurse
    )

    for ($Attempt = 1; $Attempt -le 5; $Attempt++) {
        try {
            if ($Recurse) {
                Remove-Item -Recurse -Force -LiteralPath $PathToRemove
            }
            else {
                Remove-Item -Force -LiteralPath $PathToRemove
            }
            return
        }
        catch {
            if ($Attempt -eq 5) {
                throw
            }
            Start-Sleep -Milliseconds (300 * $Attempt)
        }
    }
}

New-Item -ItemType Directory -Force -Path $BinaryDir | Out-Null

Write-Host "Limpiando builds anteriores del backend..."
if (Test-Path $BuildWorkDir) {
    Assert-UnderProject $BuildWorkDir
    Remove-PathWithRetry $BuildWorkDir -Recurse
}
if (Test-Path (Join-Path $DistDir $ExeName)) {
    Remove-PathWithRetry (Join-Path $DistDir $ExeName)
}
Get-ChildItem -Path $BinaryDir -Filter "ia-local-agent-api*.exe" -ErrorAction SilentlyContinue | Remove-Item -Force

if ($CleanOnly) {
    Write-Host "Limpieza completada."
    exit 0
}

$Python = Resolve-Python
Write-Host "Usando Python: $Python"

& $Python -c "import PyInstaller" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "PyInstaller no esta instalado. Instalando en el entorno detectado..."
    & $Python -m pip install pyinstaller
    if ($LASTEXITCODE -ne 0) {
        throw "No se pudo instalar PyInstaller."
    }
}

if (-not (Test-Path $SpecPath)) {
    throw "No se encontro el spec de PyInstaller en $SpecPath"
}

Push-Location $ProjectRoot
try {
    & $Python -m PyInstaller --clean --noconfirm --distpath $DistDir --workpath $BuildWorkDir $SpecPath
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller fallo con codigo $LASTEXITCODE"
    }
}
finally {
    Pop-Location
}

$BuiltExe = Join-Path $DistDir $ExeName
if (-not (Test-Path $BuiltExe)) {
    throw "No se genero $BuiltExe"
}

$TargetTriple = Resolve-TargetTriple
$TripledSidecarPath = Join-Path $BinaryDir "ia-local-agent-api-$TargetTriple.exe"
$ReleaseVersion = if (Test-Path $VersionPath) { (Get-Content -LiteralPath $VersionPath -Raw).Trim() } else { "unversioned" }
$VersionedExePath = Join-Path $BinaryDir "ia-local-agent-api-$ReleaseVersion.exe"

Copy-Item -Force -LiteralPath $BuiltExe -Destination $PlainSidecarPath
Copy-Item -Force -LiteralPath $BuiltExe -Destination $TripledSidecarPath
Copy-Item -Force -LiteralPath $BuiltExe -Destination $VersionedExePath

Write-Host "Backend empaquetado:"
Write-Host "  $BuiltExe"
Write-Host "Sidecar Tauri:"
Write-Host "  $TripledSidecarPath"
Write-Host "Copia versionada:"
Write-Host "  $VersionedExePath"
exit 0

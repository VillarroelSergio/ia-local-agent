param(
    [ValidateSet("major", "minor", "patch")]
    [string]$Part = "patch",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$VersionPath = Join-Path $ProjectRoot "VERSION"
$PackageJsonPath = Join-Path $ProjectRoot "ui\desktop\package.json"
$PackageLockPath = Join-Path $ProjectRoot "ui\desktop\package-lock.json"
$TauriConfigPath = Join-Path $ProjectRoot "ui\desktop\src-tauri\tauri.conf.json"
$CargoTomlPath = Join-Path $ProjectRoot "ui\desktop\src-tauri\Cargo.toml"

function Get-CurrentVersion {
    if (Test-Path $VersionPath) {
        return (Get-Content -LiteralPath $VersionPath -Raw).Trim()
    }

    if (Test-Path $TauriConfigPath) {
        $Config = Get-Content -LiteralPath $TauriConfigPath -Raw | ConvertFrom-Json
        if ($Config.version) {
            return [string]$Config.version
        }
    }

    throw "No se encontro version actual. Crea VERSION o configura version en tauri.conf.json."
}

function Get-NextVersion {
    param(
        [string]$Version,
        [string]$VersionPart
    )

    if ($Version -notmatch '^(\d+)\.(\d+)\.(\d+)$') {
        throw "Version no soportada: $Version. Usa formato semver simple: MAJOR.MINOR.PATCH."
    }

    $Major = [int]$Matches[1]
    $Minor = [int]$Matches[2]
    $Patch = [int]$Matches[3]

    switch ($VersionPart) {
        "major" {
            $Major += 1
            $Minor = 0
            $Patch = 0
        }
        "minor" {
            $Minor += 1
            $Patch = 0
        }
        "patch" {
            $Patch += 1
        }
    }

    return "$Major.$Minor.$Patch"
}

function Update-JsonRootVersion {
    param(
        [string]$Path,
        [string]$Version
    )

    if (-not (Test-Path $Path)) {
        return
    }

    $Content = Get-Content -LiteralPath $Path -Raw
    $Updated = [regex]::Replace(
        $Content,
        '(?m)^  "version": "[^"]+"',
        "  `"version`": `"$Version`"",
        1
    )

    if ($Updated -eq $Content) {
        throw "No se encontro version raiz en $Path"
    }

    Set-Content -LiteralPath $Path -Value $Updated -Encoding UTF8
}

function Update-PackageLockVersion {
    param(
        [string]$Path,
        [string]$Version
    )

    if (-not (Test-Path $Path)) {
        return
    }

    $Content = Get-Content -LiteralPath $Path -Raw
    $Updated = [regex]::Replace(
        $Content,
        '(?m)^  "version": "[^"]+"',
        "  `"version`": `"$Version`"",
        1
    )
    $Updated = [regex]::Replace(
        $Updated,
        '(?m)^      "version": "[^"]+"',
        "      `"version`": `"$Version`"",
        1
    )

    if ($Updated -eq $Content) {
        throw "No se actualizo version en $Path"
    }

    Set-Content -LiteralPath $Path -Value $Updated -Encoding UTF8
}

function Update-CargoPackageVersion {
    param(
        [string]$Path,
        [string]$Version
    )

    if (-not (Test-Path $Path)) {
        return
    }

    $Lines = Get-Content -LiteralPath $Path
    $InPackage = $false
    $Updated = $false

    for ($Index = 0; $Index -lt $Lines.Count; $Index++) {
        $Line = $Lines[$Index]

        if ($Line -match '^\s*\[package\]\s*$') {
            $InPackage = $true
            continue
        }

        if ($InPackage -and $Line -match '^\s*\[') {
            break
        }

        if ($InPackage -and $Line -match '^\s*version\s*=') {
            $Lines[$Index] = "version = `"$Version`""
            $Updated = $true
            break
        }
    }

    if ($Updated) {
        Set-Content -LiteralPath $Path -Value $Lines -Encoding UTF8
    }
}

$CurrentVersion = Get-CurrentVersion
$NextVersion = Get-NextVersion -Version $CurrentVersion -VersionPart $Part

if ($DryRun) {
    Write-Host "Version actual: $CurrentVersion"
    Write-Host "Siguiente version ($Part): $NextVersion"
    exit 0
}

Set-Content -LiteralPath $VersionPath -Value ($NextVersion + [Environment]::NewLine) -Encoding UTF8
Update-JsonRootVersion -Path $PackageJsonPath -Version $NextVersion
Update-PackageLockVersion -Path $PackageLockPath -Version $NextVersion
Update-JsonRootVersion -Path $TauriConfigPath -Version $NextVersion
Update-CargoPackageVersion -Path $CargoTomlPath -Version $NextVersion

Write-Host "Version actualizada: $CurrentVersion -> $NextVersion"

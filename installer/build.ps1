# Build de OpenBotV Studio: PyInstaller + portable (zip) + instalador (Inno Setup).
#
# Uso:
#   .\installer\build.ps1                 -> menú interactivo
#   .\installer\build.ps1 -Task Exe       -> solo PyInstaller
#   .\installer\build.ps1 -Task Portable  -> solo zip portable (requiere dist\)
#   .\installer\build.ps1 -Task Installer -> solo instalador (requiere dist\)
#   .\installer\build.ps1 -Task All       -> los tres pasos en orden
#   .\installer\build.ps1 -Task All -NoPause  -> sin pausa final (automatización)
#
# Requiere: entorno .venv de conda e Inno Setup (rutas ajustables abajo).

param(
    [ValidateSet('Exe', 'Portable', 'Installer', 'All')]
    [string]$Task,
    [switch]$NoPause
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$Python = "C:\Users\jvele\miniconda3\envs\.venv\python.exe"
$IsccCandidates = @(
    "C:\Users\jvele\AppData\Local\Programs\Inno Setup 7\ISCC.exe",
    "C:\Program Files (x86)\Inno Setup 7\ISCC.exe",
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
)
$ExeDir = "dist\OpenBotV-Studio"
$ExePath = Join-Path $ExeDir "OpenBotV-Studio.exe"

# ---------- Utilidades ----------

function Test-DistReady {
    return (Test-Path $ExePath)
}

function Warn-DistStale {
    # Avisa si el exe de dist es más antiguo que el código fuente.
    if (-not (Test-DistReady)) { return }
    $exeTime = (Get-Item $ExePath).LastWriteTime
    $newestSource = Get-ChildItem src -Recurse -File |
        Where-Object { $_.FullName -notmatch '__pycache__' } |
        Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($newestSource -and $newestSource.LastWriteTime -gt $exeTime) {
        Write-Warning ("El exe de dist es más antiguo que '{0}'. " +
            "Considera recompilar (opción Exe) antes de empaquetar." -f $newestSource.Name)
    }
}

function Invoke-PyInstaller {
    Write-Host "==> PyInstaller (onedir)" -ForegroundColor Cyan
    & $Python -m PyInstaller installer\main.spec --noconfirm
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller falló" }
    Write-Host "OK: $ExeDir" -ForegroundColor Green
}

function Invoke-Portable {
    if (-not (Test-DistReady)) {
        throw "No existe $ExePath. Ejecuta primero el paso Exe."
    }
    Warn-DistStale
    Write-Host "==> Portable (zip)" -ForegroundColor Cyan
    Compress-Archive -Path $ExeDir `
        -DestinationPath dist\OpenBotV-Studio-portable.zip -Force
    Write-Host "OK: dist\OpenBotV-Studio-portable.zip" -ForegroundColor Green
}

function Invoke-Installer {
    if (-not (Test-DistReady)) {
        throw "No existe $ExePath. Ejecuta primero el paso Exe."
    }
    Warn-DistStale
    $Iscc = $IsccCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
    if (-not $Iscc) {
        throw "No se encontró ISCC.exe. Instala Inno Setup o ajusta `$IsccCandidates."
    }
    Write-Host "==> Instalador (Inno Setup: $Iscc)" -ForegroundColor Cyan
    & $Iscc installer\OpenBotV-Studio.iss
    if ($LASTEXITCODE -ne 0) { throw "Inno Setup falló" }
    Write-Host "OK: dist\installer\OpenBotV-Studio-Setup.exe" -ForegroundColor Green
}

function Show-Report {
    Write-Host ""
    Write-Host "Artefactos en dist\:" -ForegroundColor Green
    Get-ChildItem dist | Select-Object Name, @{n='SizeMB'; e={
        if ($_.PSIsContainer) {
            [math]::Round((Get-ChildItem $_.FullName -Recurse -File |
                Measure-Object Length -Sum).Sum / 1MB, 1)
        } else { [math]::Round($_.Length / 1MB, 1) } }} |
        Format-Table -AutoSize | Out-Host
}

# ---------- Selección de tareas ----------

$tasks = @()

if ($Task) {
    $tasks = switch ($Task) {
        'Exe'       { @('exe') }
        'Portable'  { @('portable') }
        'Installer' { @('installer') }
        'All'       { @('exe', 'portable', 'installer') }
    }
} else {
    while (-not $tasks) {
        Write-Host ""
        Write-Host "OpenBotV Studio - Build" -ForegroundColor White
        Write-Host "  [1] Solo PyInstaller       (regenera dist\OpenBotV-Studio)"
        Write-Host "  [2] Solo Portable          (zip de dist\OpenBotV-Studio)"
        Write-Host "  [3] Solo Instalador        (Inno Setup)"
        Write-Host "  [4] Portable + Instalador  (sin recompilar el exe)"
        Write-Host "  [5] Todo                   (1 + 2 + 3)"
        Write-Host "  [0] Salir"
        $choice = Read-Host "Elige una opción"
        $tasks = switch ($choice) {
            '1' { @('exe') }
            '2' { @('portable') }
            '3' { @('installer') }
            '4' { @('portable', 'installer') }
            '5' { @('exe', 'portable', 'installer') }
            '0' { Write-Host "Cancelado."; exit 0 }
            default { Write-Host "Opción no válida." -ForegroundColor Yellow; @() }
        }
    }
}

# ---------- Ejecución ----------

try {
    foreach ($t in $tasks) {
        switch ($t) {
            'exe'       { Invoke-PyInstaller }
            'portable'  { Invoke-Portable }
            'installer' { Invoke-Installer }
        }
    }
    Show-Report
} catch {
    Write-Host ""
    Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
} finally {
    if (-not $NoPause) {
        Write-Host ""
        Write-Host "Presione cualquier tecla para salir..." -NoNewline
        try {
            $null = $Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown')
        } catch {
            Read-Host "Enter para salir" | Out-Null
        }
    }
}

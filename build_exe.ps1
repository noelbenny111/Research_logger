# ============================================================
#  Research Logger - EXE Builder (PowerShell version)
#  Supports both pip and uv.
#  Run from inside the research_logger folder:
#    .\build_exe.ps1
# ============================================================

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  Research Logger - EXE Builder" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Prefer the project venv so the build uses the same packages as the app.
$projectPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
$useProjectPython = Test-Path $projectPython
$use_uv = $false

if ($useProjectPython) {
    Write-Host "[INFO] Using project venv at .venv" -ForegroundColor Green
} elseif (Get-Command uv -ErrorAction SilentlyContinue) {
    Write-Host "[INFO] Found 'uv' - using uv pip" -ForegroundColor Green
    $use_uv = $true
} else {
    Write-Host "[INFO] Using pip" -ForegroundColor Yellow
}

# 1. Install dependencies
Write-Host ""
Write-Host "[1/4] Installing dependencies..." -ForegroundColor White
if ($useProjectPython) {
    & $projectPython -m ensurepip --upgrade | Out-Null
    & $projectPython -m pip install --upgrade -r (Join-Path $PSScriptRoot "requirements.txt") pyinstaller
} elseif ($use_uv) {
    uv pip install PySide6 reportlab markdown2 pyinstaller
} else {
    pip install --upgrade PySide6 reportlab markdown2 pyinstaller
}
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Dependency install failed." -ForegroundColor Red
    exit 1
}

# 2. Clean
Write-Host ""
Write-Host "[2/4] Cleaning previous build..." -ForegroundColor White
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
if (Test-Path "dist")  { Remove-Item -Recurse -Force "dist" }

# 3. Build
Write-Host ""
Write-Host "[3/4] Running PyInstaller..." -ForegroundColor White
if ($useProjectPython) {
    & $projectPython -m PyInstaller (Join-Path $PSScriptRoot "research_logger.spec") --noconfirm
} elseif ($use_uv) {
    uv run pyinstaller research_logger.spec --noconfirm
} else {
    python -m PyInstaller research_logger.spec --noconfirm
}
if ((-not $?) -or ($LASTEXITCODE -ne 0)) {
    Write-Host "ERROR: PyInstaller build failed." -ForegroundColor Red
    exit 1
}

# 4. Done
Write-Host ""
Write-Host "[4/4] Build complete!" -ForegroundColor Green
Write-Host ""
Write-Host "EXE location:" -ForegroundColor Cyan
Write-Host "  dist\ResearchLogger\ResearchLogger.exe" -ForegroundColor White
Write-Host ""
Write-Host "To distribute: zip the entire 'dist\ResearchLogger\' folder." -ForegroundColor Yellow
Write-Host "No Python needed on the target machine." -ForegroundColor Yellow
Write-Host ""

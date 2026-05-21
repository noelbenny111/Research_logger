@echo off
REM ============================================================
REM  Research Logger — Windows EXE Builder
REM  Run this script from inside the research_logger folder.
REM  Requirements: Python 3.10+, pip
REM ============================================================

echo.
echo ==========================================
echo   Research Logger — EXE Builder
echo ==========================================
echo.

REM 1. Install / upgrade dependencies
echo [1/4] Installing dependencies...
if exist .venv\Scripts\python.exe (
    .venv\Scripts\python.exe -m ensurepip --upgrade >nul
    .venv\Scripts\python.exe -m pip install --upgrade -r requirements.txt pyinstaller
    if %errorlevel% neq 0 (
        echo ERROR: venv pip install failed.
        pause
        exit /b 1
    )
) else (
    pip install --upgrade PySide6 reportlab markdown2 pyinstaller
    if %errorlevel% neq 0 (
        echo ERROR: pip install failed. Make sure Python is on your PATH.
        pause
        exit /b 1
    )
)

echo.
echo [2/4] Cleaning previous build...
if exist build   rmdir /s /q build
if exist dist    rmdir /s /q dist

echo.
echo [3/4] Building EXE with PyInstaller...
if exist .venv\Scripts\python.exe (
    .venv\Scripts\python.exe -m PyInstaller research_logger.spec --noconfirm
    if %errorlevel% neq 0 (
        echo.
        echo ERROR: PyInstaller build failed. See output above.
        pause
        exit /b 1
    )
) else (
    pyinstaller research_logger.spec --noconfirm
    if %errorlevel% neq 0 (
        echo.
        echo ERROR: PyInstaller build failed. See output above.
        pause
        exit /b 1
    )
)

echo.
echo [4/4] Done!
echo.
echo Your application is in:
echo   dist\ResearchLogger\ResearchLogger.exe
echo.
echo You can zip the entire dist\ResearchLogger\ folder and
echo share it — no Python installation needed on the target PC.
echo.
pause

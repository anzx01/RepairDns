@echo off
set PYTHON=C:\Python314\python.exe

if not exist "%PYTHON%" (
    echo [ERROR] Python not found: %PYTHON%
    pause
    exit /b 1
)

echo [1/3] Installing PyInstaller...
"%PYTHON%" -m pip install pyinstaller --quiet --upgrade
if errorlevel 1 (
    echo [ERROR] pip install failed
    pause
    exit /b 1
)

echo [2/3] Cleaning old build...
if exist build  rmdir /s /q build
if exist dist   rmdir /s /q dist
if exist "DNS-RepairTool.spec" del /q "DNS-RepairTool.spec"

echo [3/3] Building...
"%PYTHON%" -m PyInstaller ^
    --onefile ^
    --windowed ^
    --name "DNS-RepairTool" ^
    main.py

if errorlevel 1 (
    echo [ERROR] Build failed
    pause
    exit /b 1
)

echo.
echo [OK] Done! Output: dist\DNS-RepairTool.exe
echo.
pause

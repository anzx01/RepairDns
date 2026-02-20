@echo off
chcp 65001 >nul
echo ============================================
echo  DNS 一键修复助手 — PyInstaller 打包脚本
echo ============================================

set PYTHON=C:\Python314\python.exe

:: 检查 Python
if not exist "%PYTHON%" (
    echo [ERROR] 未找到 Python: %PYTHON%
    pause
    exit /b 1
)

:: 安装 / 升级 PyInstaller
echo [1/3] 安装 PyInstaller...
"%PYTHON%" -m pip install pyinstaller --quiet --upgrade
if errorlevel 1 (
    echo [ERROR] PyInstaller 安装失败
    pause
    exit /b 1
)

:: 清理旧产物
echo [2/3] 清理旧构建...
if exist build  rmdir /s /q build
if exist dist   rmdir /s /q dist
if exist "DNS一键修复助手.spec" del /q "DNS一键修复助手.spec"

:: 打包
echo [3/3] 打包中，请稍候...
"%PYTHON%" -m PyInstaller ^
    --onefile ^
    --windowed ^
    --name "DNS一键修复助手" ^
    main.py

if errorlevel 1 (
    echo [ERROR] 打包失败，请查看上方错误信息
    pause
    exit /b 1
)

echo.
echo [OK] 打包完成！
echo 输出文件: dist\DNS一键修复助手.exe
echo.
pause

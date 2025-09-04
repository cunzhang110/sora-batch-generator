@echo off
chcp 65001 > nul
title Sora 4.0 - Python环境诊断

echo ========================================
echo       Sora 4.0 - Python环境诊断
echo ========================================
echo.

echo 正在检查Python环境...
echo.

:: 检查Python版本
echo [1] 检查Python版本:
python --version 2>nul
if errorlevel 1 (
    echo   ❌ Python未安装或无法访问
    goto :install_guide
) else (
    echo   ✅ Python已安装
)
echo.

:: 检查pip
echo [2] 检查pip:
python -m pip --version 2>nul
if errorlevel 1 (
    echo   ❌ pip无法使用
) else (
    echo   ✅ pip正常
)
echo.

:: 检查关键依赖
echo [3] 检查依赖包:
python -c "import PyQt6; print('  ✅ PyQt6 已安装')" 2>nul || echo   ❌ PyQt6 未安装
python -c "import requests; print('  ✅ requests 已安装')" 2>nul || echo   ❌ requests 未安装  
python -c "import pandas; print('  ✅ pandas 已安装')" 2>nul || echo   ❌ pandas 未安装
echo.

:: 如果基本检查都通过，说明问题可能在特定环境
python -c "print('Python基本功能测试通过')" 2>nul
if errorlevel 1 (
    echo [4] ❌ Python存在严重问题，建议重新安装
    goto :install_guide
) else (
    echo [4] ✅ Python基本功能正常
    goto :install_deps
)

:install_deps
echo.
echo ========================================
echo 是否要安装/更新依赖包？(y/n)
set /p choice=请选择: 
if /i "%choice%"=="y" (
    echo.
    echo 正在安装依赖包...
    python -m pip install --upgrade pip
    python -m pip install PyQt6 requests pandas
    echo.
    echo 依赖安装完成！
    goto :test_run
)
goto :test_run

:install_guide
echo.
echo ========================================
echo          Python重新安装指南
echo ========================================
echo.
echo 1. 卸载当前Python：
echo    - 打开"设置" → "应用" → 搜索"Python"
echo    - 卸载所有Python相关程序
echo.
echo 2. 下载最新Python：
echo    - 访问: https://www.python.org/downloads/
echo    - 下载Python 3.10或3.11版本
echo.
echo 3. 安装时注意：
echo    - ✅ 勾选"Add Python to PATH"
echo    - ✅ 选择"Install for all users"
echo    - ✅ 以管理员身份安装
echo.
echo 4. 安装完成后重启电脑
echo.
echo 按任意键打开Python下载页面...
pause > nul
start https://www.python.org/downloads/
goto :end

:test_run
echo.
echo ========================================
echo 是否要测试运行Sora工具？(y/n)
set /p choice=请选择: 
if /i "%choice%"=="y" (
    echo.
    echo 正在启动Sora工具...
    python main.py
)

:end
echo.
echo 诊断完成！
pause
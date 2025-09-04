@echo off
chcp 65001 > nul
title Sora 4.0 - 简单启动

echo ====================================
echo           Sora 4.0 启动器
echo ====================================
echo.

cd /d "%~dp0"

echo 提示：如果出现Python环境错误，请：
echo 1. 重新安装Python 3.10或3.11
echo 2. 安装时勾选"Add Python to PATH"
echo 3. 手动安装依赖：python -m pip install PyQt6 requests pandas
echo.

echo 正在启动...
python main.py

echo.
echo 程序已退出
pause
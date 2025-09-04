@echo off
chcp 65001
cd /d "%~dp0"

echo.
echo ==========================================
echo        GitHub 远程备份设置
echo ==========================================
echo.
echo 请先在 GitHub.com 创建一个私有仓库
echo.
set /p repo_url=请输入GitHub仓库地址(如: https://github.com/用户名/仓库名.git): 

echo.
echo 正在设置远程仓库...
git remote add origin %repo_url%

echo.
echo 正在推送到GitHub...
git branch -M main
git push -u origin main

if %errorlevel% equ 0 (
    echo.
    echo ✅ GitHub备份设置成功！
    echo 📁 仓库地址: %repo_url%
    echo.
    echo 后续操作:
    echo - 创建备份: git add . ^&^& git commit -m "描述" ^&^& git push
    echo - 或运行: GitHub备份.bat
) else (
    echo.
    echo ❌ 设置失败！请检查:
    echo 1. GitHub仓库地址是否正确
    echo 2. 是否已登录Git账户
    echo 3. 网络连接是否正常
)

echo.
pause
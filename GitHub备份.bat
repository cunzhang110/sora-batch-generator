@echo off
chcp 65001
cd /d "%~dp0"

echo.
echo ==========================================
echo        GitHub 云端备份
echo ==========================================
echo.

:: 检查是否有未提交的更改
git status --porcelain > temp_status.txt
set /p has_changes=<temp_status.txt
del temp_status.txt

if "%has_changes%"=="" (
    echo ℹ️  没有新的更改需要备份
    echo.
    echo 最近的提交记录:
    git log --oneline -3
    echo.
    pause
    exit /b
)

echo 📋 待备份的更改:
git status --short
echo.

set /p description=💬 请输入本次更新描述: 

echo.
echo 🔄 正在创建本地备份...
git add .
git commit -m "%description%

🤖 Generated with Claude Code

Co-Authored-By: Claude <noreply@anthropic.com>"

if %errorlevel% neq 0 (
    echo ❌ 本地备份失败！
    pause
    exit /b
)

echo ✅ 本地备份完成
echo.
echo 📤 正在推送到GitHub...
git push

if %errorlevel% equ 0 (
    echo.
    echo ✅ 成功备份到GitHub！
    echo 🌐 可在线查看: git remote get-url origin
    git remote get-url origin
) else (
    echo.
    echo ❌ GitHub推送失败！
    echo 💡 可能原因:
    echo   - 网络连接问题
    echo   - 需要重新登录GitHub
    echo   - 本地版本落后于远程版本
    echo.
    echo 🔧 解决方案:
    echo   1. 检查网络连接
    echo   2. 运行: git pull origin main
    echo   3. 重新执行此脚本
)

echo.
pause
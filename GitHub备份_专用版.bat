@echo off
chcp 65001
cd /d "%~dp0"

:: 设置你的Git路径
set GIT_PATH="D:\claudecode\git\Git\bin\git.exe"

echo.
echo ==========================================
echo        GitHub 云端备份（专用版）
echo ==========================================
echo.

:: 检查Git是否可用
echo 🔍 检测Git环境...
%GIT_PATH% --version
if %errorlevel% neq 0 (
    echo ❌ Git路径不正确，请检查: %GIT_PATH%
    pause
    exit /b
)
echo ✅ Git环境正常
echo.

:: 检查是否有未提交的更改
echo 📋 检查待备份的更改...
%GIT_PATH% status --porcelain > temp_status.txt
set /p has_changes=<temp_status.txt
del temp_status.txt

if "%has_changes%"=="" (
    echo ℹ️  没有新的更改需要备份
    echo.
    echo 最近的提交记录:
    %GIT_PATH% log --oneline -3
    echo.
    pause
    exit /b
)

echo 📋 待备份的更改:
%GIT_PATH% status --short
echo.

set /p description=💬 请输入本次更新描述: 

echo.
echo 🔄 正在创建本地备份...
%GIT_PATH% add .
%GIT_PATH% commit -m "%description%

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"

if %errorlevel% neq 0 (
    echo ❌ 本地备份失败！
    pause
    exit /b
)

echo ✅ 本地备份完成
echo.
echo 📤 正在推送到GitHub...
%GIT_PATH% push

if %errorlevel% equ 0 (
    echo.
    echo ✅ 成功备份到GitHub！
    echo 🌐 仓库地址: 
    %GIT_PATH% remote get-url origin
) else (
    echo.
    echo ❌ GitHub推送失败！
    echo 💡 可能原因:
    echo   - 网络连接问题  
    echo   - 需要先设置远程仓库
    echo   - 需要Git登录认证
    echo.
    echo 🔧 请先运行: GitHub备份设置_专用版.bat
)

echo.
pause
@echo off
chcp 65001
cd /d "%~dp0"

echo.
echo ==========================================
echo        从GitHub恢复版本
echo ==========================================
echo.
echo ⚠️  警告: 此操作将覆盖本地所有更改！
echo.

set /p confirm=确认要从GitHub恢复最新版本吗? (Y/N): 
if /i not "%confirm%"=="Y" (
    echo 操作已取消
    pause
    exit /b
)

echo.
echo 📥 正在从GitHub拉取最新版本...
git fetch origin main

echo.
echo 🔄 正在恢复到最新版本...
git reset --hard origin/main

if %errorlevel% equ 0 (
    echo.
    echo ✅ 成功从GitHub恢复最新版本！
    echo.
    echo 📋 当前版本信息:
    git log --oneline -1
) else (
    echo.
    echo ❌ 恢复失败！
    echo 💡 可能需要先运行: GitHub备份设置.bat
)

echo.
pause
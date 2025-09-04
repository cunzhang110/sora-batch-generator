@echo off
chcp 65001
cd /d "%~dp0"

echo.
echo ==========================================
echo           深海圈生图 - 版本管理
echo ==========================================
echo.
echo 1. 创建新版本备份
echo 2. 查看版本历史  
echo 3. 回退到指定版本
echo 4. 查看当前状态
echo 5. 退出
echo.
set /p choice=请选择操作(1-5): 

if "%choice%"=="1" goto backup
if "%choice%"=="2" goto history
if "%choice%"=="3" goto rollback
if "%choice%"=="4" goto status
if "%choice%"=="5" goto exit

:backup
echo.
set /p message=请输入版本描述: 
git add .
git commit -m "%message%"
if %errorlevel% equ 0 (
    echo ✅ 备份创建成功！
) else (
    echo ❌ 备份创建失败！
)
pause
goto start

:history
echo.
echo 版本历史:
git log --oneline -10
echo.
pause
goto start

:rollback
echo.
echo 最近的版本:
git log --oneline -5
echo.
set /p commit=请输入要回退的版本号(前7位): 
git reset --hard %commit%
if %errorlevel% equ 0 (
    echo ✅ 成功回退到版本 %commit%
) else (
    echo ❌ 回退失败！
)
pause
goto start

:status
echo.
echo 当前状态:
git status
echo.
pause
goto start

:start
cls
goto start

:exit
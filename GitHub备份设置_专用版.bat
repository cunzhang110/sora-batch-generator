@echo off
chcp 65001
cd /d "%~dp0"

:: 设置你的Git路径
set GIT_PATH="D:\claudecode\git\Git\bin\git.exe"

echo.
echo ==========================================
echo        GitHub 远程备份设置（专用版）
echo ==========================================
echo.

:: 检查Git环境
echo 🔍 检测Git环境...
%GIT_PATH% --version
if %errorlevel% neq 0 (
    echo ❌ Git路径错误: %GIT_PATH%
    echo 💡 请确认Git安装在 D:\claudecode\git\Git\ 目录
    pause
    exit /b
)
echo ✅ Git环境正常
echo.

:: 检查当前仓库状态
echo 📋 检查本地仓库状态...
%GIT_PATH% status
echo.

echo 📝 请按以下步骤操作：
echo.
echo 1️⃣  在浏览器中访问: https://github.com
echo 2️⃣  登录你的GitHub账户
echo 3️⃣  点击右上角 "+" -> "New repository"
echo 4️⃣  仓库名称输入: sora-batch-generator
echo 5️⃣  ⚠️  重要：设置为 Private（私有仓库）
echo 6️⃣  不要勾选 "Add README file"
echo 7️⃣  点击 "Create repository"
echo.

set /p ready=已创建GitHub仓库？请输入 Y 继续: 
if /i not "%ready%"=="Y" (
    echo 操作取消
    pause
    exit /b
)

echo.
set /p repo_url=请输入GitHub仓库地址（复制完整URL）: 

:: 验证URL格式
echo %repo_url% | findstr /i "github.com" >nul
if %errorlevel% neq 0 (
    echo ❌ 仓库地址格式不正确
    echo 💡 应该类似: https://github.com/用户名/sora-batch-generator.git
    pause
    exit /b
)

echo.
echo 🔗 正在连接远程仓库...
%GIT_PATH% remote remove origin 2>nul
%GIT_PATH% remote add origin %repo_url%

if %errorlevel% neq 0 (
    echo ❌ 远程仓库设置失败
    pause
    exit /b
)

echo.
echo 📤 正在首次推送到GitHub...
%GIT_PATH% branch -M main
%GIT_PATH% push -u origin main

if %errorlevel% equ 0 (
    echo.
    echo 🎉 GitHub备份设置成功！
    echo.
    echo 📁 仓库地址: %repo_url%
    echo 💾 所有文件已上传到GitHub
    echo.
    echo 🔄 后续使用方法:
    echo   - 运行 "GitHub备份_专用版.bat" 进行备份
    echo   - 运行 "GitHub恢复_专用版.bat" 恢复版本
    echo.
    
    :: 创建恢复脚本
    echo 📝 正在创建恢复脚本...
    echo @echo off > GitHub恢复_专用版.bat
    echo chcp 65001 >> GitHub恢复_专用版.bat
    echo cd /d "%%~dp0" >> GitHub恢复_专用版.bat
    echo set GIT_PATH="D:\claudecode\git\Git\bin\git.exe" >> GitHub恢复_专用版.bat
    echo echo 从GitHub恢复最新版本... >> GitHub恢复_专用版.bat
    echo %%GIT_PATH%% fetch origin main >> GitHub恢复_专用版.bat
    echo %%GIT_PATH%% reset --hard origin/main >> GitHub恢复_专用版.bat
    echo echo 恢复完成！ >> GitHub恢复_专用版.bat
    echo pause >> GitHub恢复_专用版.bat
    
    echo ✅ 已创建 GitHub恢复_专用版.bat
    
) else (
    echo.
    echo ❌ GitHub推送失败！
    echo.
    echo 💡 可能的解决方案:
    echo 1. 检查网络连接
    echo 2. 确认GitHub账户权限
    echo 3. 可能需要配置Git认证信息:
    echo    "%GIT_PATH%" config --global user.name "你的用户名"
    echo    "%GIT_PATH%" config --global user.email "你的邮箱"
    echo.
    
    set /p setup_auth=需要配置Git认证信息吗？(Y/N): 
    if /i "%setup_auth%"=="Y" (
        set /p git_name=请输入你的GitHub用户名: 
        set /p git_email=请输入你的邮箱: 
        
        "%GIT_PATH%" config --global user.name "!git_name!"
        "%GIT_PATH%" config --global user.email "!git_email!"
        
        echo ✅ Git认证信息已配置
        echo 🔄 请重新运行此脚本完成设置
    )
)

echo.
pause
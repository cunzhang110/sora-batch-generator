@echo off
chcp 65001
cd /d "%~dp0"

:: 创建备份文件夹
set backup_dir=备份版本
if not exist "%backup_dir%" mkdir "%backup_dir%"

:: 生成时间戳
for /f "tokens=2 delims==" %%i in ('wmic OS Get localdatetime /value') do call :SetDate %%i
goto :BackupStart

:SetDate
set datetime=%1
set year=%datetime:~0,4%
set month=%datetime:~4,2%
set day=%datetime:~6,2%
set hour=%datetime:~8,2%
set minute=%datetime:~10,2%
set timestamp=%year%-%month%-%day%_%hour%-%minute%
goto :eof

:BackupStart
set /p description=请输入备份描述: 
set backup_name=%timestamp%_%description%

echo.
echo 正在创建备份: %backup_name%

:: 创建备份文件夹
mkdir "%backup_dir%\%backup_name%"

:: 复制重要文件
copy "main.py" "%backup_dir%\%backup_name%\"
copy "config.json" "%backup_dir%\%backup_name%\"
copy "requirements.txt" "%backup_dir%\%backup_name%\"
if exist "README.md" copy "README.md" "%backup_dir%\%backup_name%\"

:: 复制images文件夹
if exist "images" xcopy "images" "%backup_dir%\%backup_name%\images" /E /I /Q

echo.
echo ✅ 备份创建完成: %backup_dir%\%backup_name%
echo.

:: 显示现有备份
echo 现有备份版本:
dir "%backup_dir%" /AD /B

echo.
pause
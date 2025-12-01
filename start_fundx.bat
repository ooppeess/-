@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

:: ============================================================
:: FundX 资金分析平台 - 增强版启动脚本
:: 功能: 环境检查 -> 依赖安装 -> 数据库初始化 -> 启动服务
:: ============================================================

:: --- 1. 配置区域 ---
set "APP_HOST=0.0.0.0"
set "APP_PORT=8000"
set "PROJECT_DIR=%~dp0"
set "REQUIREMENTS=%PROJECT_DIR%requirements.txt"
set "MAIN_SCRIPT=%PROJECT_DIR%main.py"
set "DB_SCRIPT=%PROJECT_DIR%database.py"

:: 设置颜色
set "GREEN=[92m"
set "RED=[91m"
set "YELLOW=[93m"
set "CYAN=[96m"
set "RESET=[0m"

cls
echo.
echo  %CYAN%================================================%RESET%
echo  %CYAN%       FundX 资金分析平台 - 智能启动助手       %RESET%
echo  %CYAN%================================================%RESET%
echo.

:: --- 2. 检查 Python 环境 ---
echo [%YELLOW%*%RESET%] 正在检查 Python 环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo %RED%[X] 未检测到 Python，请先安装 Python 3.10+ 并添加到环境变量！%RESET%
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('python --version') do set PY_VER=%%i
echo %GREEN%[V] 检测到 %PY_VER%%RESET%

:: --- 3. 检查核心文件 ---
echo.
echo [%YELLOW%*%RESET%] 正在检查项目文件...
if not exist "%MAIN_SCRIPT%" (
    echo %RED%[X] 错误：找不到入口文件 main.py%RESET%
    pause
    exit /b 1
)
if not exist "%REQUIREMENTS%" (
    echo %RED%[X] 错误：找不到依赖文件 requirements.txt%RESET%
    pause
    exit /b 1
)
echo %GREEN%[V] 项目文件完整%RESET%

:: --- 4. 检查并安装依赖 ---
echo.
echo [%YELLOW%*%RESET%] 正在检查依赖库...
:: 简单检查一个核心库是否存在，不存在则安装所有
python -c "import fastapi" >nul 2>&1
if errorlevel 1 (
    echo %YELLOW%[!] 发现依赖缺失，正在自动安装...%RESET%
    pip install -r "%REQUIREMENTS%" -i https://pypi.tuna.tsinghua.edu.cn/simple
    if errorlevel 1 (
        echo %RED%[X] 依赖安装失败，请检查网络或手动执行 pip install%RESET%
        pause
        exit /b 1
    )
    echo %GREEN%[V] 依赖安装完成%RESET%
) else (
    echo %GREEN%[V] 依赖库已就绪%RESET%
)

:: --- 5. 初始化数据库 ---
echo.
echo [%YELLOW%*%RESET%] 正在初始化数据库结构...
python "%DB_SCRIPT%"
if errorlevel 1 (
    echo %RED%[X] 数据库初始化失败！%RESET%
    pause
    exit /b 1
)
echo %GREEN%[V] 数据库就绪 (DuckDB)%RESET%

:: --- 6. 端口占用检查 ---
echo.
echo [%YELLOW%*%RESET%] 正在检查端口 %APP_PORT%...
netstat -ano | findstr ":%APP_PORT% " | findstr "LISTENING" >nul 2>&1
if not errorlevel 1 (
    echo %RED%[!] 端口 %APP_PORT% 被占用！%RESET%
    set /p KILL_CHOICE="是否尝试结束占用进程？(Y/N): "
    if /i "!KILL_CHOICE!"=="Y" (
        for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%APP_PORT% " ^| findstr "LISTENING"') do (
            taskkill /F /PID %%a >nul 2>&1
            echo %GREEN%[V] 已释放端口 %APP_PORT% (PID: %%a)%RESET%
        )
    ) else (
        echo %RED%[X] 无法启动，端口被占用%RESET%
        pause
        exit /b 1
    )
) else (
    echo %GREEN%[V] 端口空闲%RESET%
)

:: --- 7. 启动服务 ---
echo.
echo %CYAN%================================================%RESET%
echo %GREEN% 正在启动 FundX 服务...%RESET%
echo %GREEN% 访问地址: http://localhost:%APP_PORT% %RESET%
echo %CYAN%================================================%RESET%
echo.

:: 启动 main.py (main.py 内部已经包含了 uvicorn.run 和 webbrowser.open)
python main.py

if errorlevel 1 (
    echo.
    echo %RED%[X] 服务异常退出%RESET%
    pause
)
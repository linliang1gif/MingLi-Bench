@echo off
setlocal
REM ====================================================================
REM 明理 MingLi Bench - 后端启动脚本
REM 1) 激活项目根 .venv（如果存在）
REM 2) 安装/校验 backend/requirements.txt（幂等）
REM 3) 启动 uvicorn backend.main:app
REM ====================================================================

set "ROOT=%~dp0.."
cd /d "%ROOT%"

if exist ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
) else (
    echo [warn] .venv not found. Falling back to system Python.
)

echo [step] ensure backend deps...
python -m pip install -r backend\requirements.txt
if errorlevel 1 (
    echo [error] failed to install backend deps.
    exit /b 1
)

echo [step] start uvicorn at http://127.0.0.1:8000
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000

endlocal

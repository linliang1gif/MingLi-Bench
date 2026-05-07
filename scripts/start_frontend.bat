@echo off
setlocal
REM ====================================================================
REM 明理 MingLi Bench - 前端启动脚本
REM 进入 frontend，启动 Vite 开发服务器（默认 http://localhost:5173）
REM ====================================================================

set "ROOT=%~dp0.."
cd /d "%ROOT%\frontend"

if not exist "node_modules" (
    echo [step] installing npm deps...
    call npm install
    if errorlevel 1 (
        echo [error] npm install failed.
        exit /b 1
    )
)

echo [step] start vite dev server at http://localhost:5173
call npm run dev

endlocal

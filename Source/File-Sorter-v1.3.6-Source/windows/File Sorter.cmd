@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    py -3 "%~dp0src\file_sorter_app.py" %*
) else (
    where python >nul 2>nul
    if %ERRORLEVEL% EQU 0 (
        python "%~dp0src\file_sorter_app.py" %*
    ) else (
        echo Python 3 is required. Install it from https://www.python.org/downloads/windows/
        pause
        exit /b 1
    )
)
if %ERRORLEVEL% NEQ 0 pause

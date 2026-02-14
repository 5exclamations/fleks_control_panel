@echo off
setlocal

REM Simple one-click launcher for the Django app
set BASE=%~dp0

REM Prefer project virtualenv if present
if exist "%BASE%.venv\\Scripts\\python.exe" (
    set PYTHON="%BASE%.venv\\Scripts\\python.exe"
) else if exist "%BASE%.venv312\\Scripts\\python.exe" (
    set PYTHON="%BASE%.venv312\\Scripts\\python.exe"
) else (
    set PYTHON=python
)

set PORT=8000
echo Starting server on http://127.0.0.1:%PORT%
cd /d "%BASE%"
%PYTHON% manage.py runserver 0.0.0.0:%PORT%

endlocal

@echo off
cd /d "%~dp0"
where python >nul 2>nul && (set PY=python) || (set PY=py)
if not exist my-config.json copy sample-config.json my-config.json >nul
%PY% simulate.py my-config.json --output my-output
if errorlevel 1 (echo. & echo Something went wrong. Read the message above. & pause & exit /b 1)
start "" "my-output\report.html"
echo.
echo Done. Report opened in your browser.
pause

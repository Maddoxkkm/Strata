@echo off
REM Stop the Strata server started by run-iq2_xs.bat, plus the engine it spawned.
REM Usage: double-click, or:  stop-server.bat
setlocal
set PORT=8080

echo Stopping anything listening on port %PORT% ...
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":%PORT%" ^| findstr "LISTENING"') do (
    echo   killing listener PID %%p
    taskkill /F /PID %%p >nul 2>&1
)

echo Stopping the engine processes ...
REM Any *current* engine name, not a fixed list: newer A/B binaries (strata-141-*.exe, strata-142-*.exe, ...)
REM were leaking and holding several GiB each, which quietly crushed the next measurement's RAM budget.
for /f "tokens=1,2" %%a in ('tasklist /NH /FI "IMAGENAME eq strata*.exe" ^| findstr /I "strata"') do (
    echo   killing engine %%a (PID %%b)
    taskkill /F /PID %%b >nul 2>&1
)
for /f "tokens=1,2" %%a in ('tasklist /NH /FI "IMAGENAME eq tune_decode*" ^| findstr /I "tune_decode"') do (
    echo   killing tuner %%a (PID %%b)
    taskkill /F /PID %%b >nul 2>&1
)

"%SystemRoot%\System32\timeout.exe" /t 2 /nobreak >nul 2>&1
netstat -ano | findstr ":%PORT%" | findstr "LISTENING" >nul
if errorlevel 1 (echo   port %PORT% is free - stopped) else (echo   WARNING: something still holds port %PORT%)
echo.
echo You can close the server's console window now.
pause

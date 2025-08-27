::::::::::::::::::::::::::::::::::
::                              ::
::    GUI Menu Version 1.0.0    ::
::                              ::
::::::::::::::::::::::::::::::::::

@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
set APP=%CD%
set STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
set LNK=%STARTUP%\HawkEyeGuard.lnk

:menu
cls
echo ===============================
echo HawkEyeGuard
echo ===============================
echo [1] Add to Startup
echo [2] Remove from Startup
echo [3] Force Update (fetch only)
echo [4] Start Now
echo [5] Exit
echo.
set /p choice=Select: 

if "%choice%"=="1" goto add
if "%choice%"=="2" goto rem
if "%choice%"=="3" goto upd
if "%choice%"=="4" goto run
if "%choice%"=="5" goto end
goto menu

:add
powershell -NoProfile -Command ^
 $WScriptShell=New-Object -ComObject WScript.Shell; ^
 $Shortcut=$WScriptShell.CreateShortcut('%LNK%'); ^
 $Shortcut.TargetPath='py'; ^
 $Shortcut.Arguments='-3 "%APP%\main.py"'; ^
 $Shortcut.WorkingDirectory='%APP%'; ^
 $Shortcut.WindowStyle=7; ^
 $Shortcut.IconLocation='%APP%\python.ico,0'; ^
 $Shortcut.Save() | Out-Null
if exist "%LNK%" (echo [OK] Startup shortcut created) else (echo [FAIL] Cannot create shortcut)
pause
goto menu

:rem
if exist "%LNK%" (del /f /q "%LNK%" && echo [OK] Startup shortcut removed) else (echo [FAIL] Shortcut not found)
pause
goto menu

:upd
py -3 "%APP%\main.py" --no-run
pause
goto menu

:run
start "" py -3 "%APP%\main.py"
echo [OK] Launched
pause
goto menu

:end
endlocal
exit /b 0

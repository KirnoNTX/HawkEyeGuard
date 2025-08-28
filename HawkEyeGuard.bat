::::::::::::::::::::::::::::::::::
::                              ::
::    GUI Menu Version 1.0.0    ::
::                              ::
::::::::::::::::::::::::::::::::::

@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
set APP=%CD%\src
set TASK=HawkEyeGuard
set TASKBAT=%APP%\HawkEyeGuardTask.bat
set STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
set LNK=%STARTUP%\HawkEyeGuard.lnk

:menu
cls
echo ===============================
echo HawkEyeGuard
echo ===============================
echo [1] Installer demarrage auto (une seule UAC)
echo [2] Desinstaller demarrage auto
echo [3] Forcer Update (fetch only)
echo [4] Demarrer maintenant
echo [5] Tester la tache planifiee
echo [6] Raccourci Startup (legacy)
echo [7] Supprimer raccourci Startup (legacy)
echo [8] Quitter
echo.
set /p choice=Select: 

if "%choice%"=="1" goto install
if "%choice%"=="2" goto uninstall
if "%choice%"=="3" goto upd
if "%choice%"=="4" goto run
if "%choice%"=="5" goto run_task
if "%choice%"=="6" goto add_lnk
if "%choice%"=="7" goto rem_lnk
if "%choice%"=="8" goto end
goto menu

:install
if not exist "%TASKBAT%" (
  echo [FAIL] Missing: "%TASKBAT%"
  pause
  goto menu
)
powershell -NoProfile -Command "Start-Process 'schtasks' -ArgumentList '/Create','/F','/TN','%TASK%','/SC','ONSTART','/RL','HIGHEST','/RU','SYSTEM','/TR','\"\"%TASKBAT%\"\"' -Verb RunAs"
schtasks /Query /TN "%TASK%" >nul 2>&1 && echo [OK] Installed as SYSTEM && pause && goto menu
echo [FAIL] Install failed
pause
goto menu

:uninstall
schtasks /Delete /TN "%TASK%" /F >nul 2>&1 && echo [OK] Uninstalled || echo [FAIL] Not found
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

:run_task
schtasks /Run /TN "%TASK%" >nul 2>&1 && echo [OK] Task started || echo [FAIL] Cannot start task
pause
goto menu

:add_lnk
powershell -NoProfile -Command ^
 $WScriptShell=New-Object -ComObject WScript.Shell; ^
 $Shortcut=$WScriptShell.CreateShortcut('%LNK%'); ^
 $Shortcut.TargetPath='py'; ^
 $Shortcut.Arguments='-3 \"%APP%\main.py\"'; ^
 $Shortcut.WorkingDirectory='%APP%'; ^
 $Shortcut.WindowStyle=7; ^
 $Shortcut.IconLocation='%APP%\python.ico,0'; ^
 $Shortcut.Save() | Out-Null
if exist "%LNK%" (echo [OK] Startup shortcut created) else (echo [FAIL] Cannot create shortcut)
pause
goto menu

:rem_lnk
if exist "%LNK%" (del /f /q "%LNK%" && echo [OK] Startup shortcut removed) else (echo [FAIL] Shortcut not found)
pause
goto menu

:end
endlocal
exit /b 0

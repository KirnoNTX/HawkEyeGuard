::::::::::::::::::::::::::::::::::
::                              ::
::      Task Version 1.0.1      ::
::                              ::
::::::::::::::::::::::::::::::::::

@echo off
setlocal
cd /d "%~dp0"
set PYCMD=C:\Windows\py.exe
if not exist "%PYCMD%" set PYCMD=py
if not exist "%SystemRoot%\System32\where.exe" goto run
where /q "%PYCMD%" || set PYCMD=python
:run
"%PYCMD%" -3 "%CD%\main.py"
endlocal
exit /b 0

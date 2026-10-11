@echo off
setlocal

where py >nul 2>nul
if errorlevel 1 goto use_python
py -3 "%~dp0start.py" %*
exit /b %errorlevel%

:use_python
where python >nul 2>nul
if errorlevel 1 goto missing_python
python "%~dp0start.py" %*
exit /b %errorlevel%

:missing_python
echo Error: Python 3.10 or newer was not found. Install Python and try again.
exit /b 1

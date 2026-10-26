@echo off
setlocal
set "PYTHONPATH=%~dp0;%PYTHONPATH%"
python -m src.cli.main %*
exit /b %ERRORLEVEL%

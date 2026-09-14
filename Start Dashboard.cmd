@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0runtime\Launch-Dashboard.ps1"
if errorlevel 1 pause
endlocal

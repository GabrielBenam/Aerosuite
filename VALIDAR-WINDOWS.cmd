@echo off
rem AeroSuite - validacion en Windows. Doble clic para ejecutar.
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\validate-windows.ps1"
echo.
echo Terminado. Puedes cerrar esta ventana.
pause

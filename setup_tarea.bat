@echo off
echo Actualizando tarea programada WurthDashboard...

:: Elimina la tarea vieja y la recrea apuntando al .bat
schtasks /Delete /TN "WurthDashboard" /F

schtasks /Create /TN "WurthDashboard" ^
  /TR "C:\taginfo\iniciar_dashboard.bat" ^
  /SC ONLOGON ^
  /RU "%USERNAME%" ^
  /RL HIGHEST ^
  /F

echo.
echo Listo. La tarea WurthDashboard ahora arranca automaticamente al iniciar sesion.
echo Podes verificarla con: schtasks /Query /TN "WurthDashboard" /FO LIST /V
pause

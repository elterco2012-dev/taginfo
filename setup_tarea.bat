@echo off
echo Actualizando tarea programada WurthDashboard...
echo.

:: Elimina la tarea vieja
schtasks /Delete /TN "WurthDashboard" /F 2>nul

:: Pide la contrasena del usuario de Windows (necesaria para correr
:: la tarea aunque la sesion no este iniciada, tras un reinicio)
echo La tarea va a correr aunque nadie inicie sesion (sobrevive reinicios).
echo Para eso Windows necesita la contrasena de tu usuario: %USERNAME%
echo.
set /p WINPASS=Contrasena de Windows para %USERNAME%:

:: ONSTART = arranca al encender la maquina, sin esperar login
:: /RU + /RP = corre con tu usuario aunque la sesion este cerrada
:: /RL HIGHEST = privilegios elevados
schtasks /Create /TN "WurthDashboard" ^
  /TR "C:\taginfo\iniciar_dashboard.bat" ^
  /SC ONSTART ^
  /RU "%USERNAME%" ^
  /RP "%WINPASS%" ^
  /RL HIGHEST ^
  /DELAY 0001:00 ^
  /F

echo.
if %ERRORLEVEL%==0 (
  echo Listo. WurthDashboard ahora arranca al encender el servidor,
  echo aunque nadie inicie sesion. Espera ~1 min tras el arranque.
) else (
  echo ERROR al crear la tarea. Revisa la contrasena e intenta de nuevo.
)
echo.
echo Verificala con: schtasks /Query /TN "WurthDashboard" /FO LIST /V
echo Para arrancarla ahora mismo:  schtasks /Run /TN "WurthDashboard"
pause

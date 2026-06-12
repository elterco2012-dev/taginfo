@echo off
echo ====================================================================
echo  Configuracion de tareas programadas del Wurth Dashboard
echo ====================================================================
echo.
echo  Se crean DOS tareas que arrancan al encender el servidor,
echo  aunque nadie inicie sesion (sobreviven reinicios):
echo.
echo    1) WurthDashboard         - corre el dashboard con auto-restart
echo    2) WurthDashboardWatchdog - reinicia el dashboard si se cuelga
echo.
echo  Las tareas corren con la cuenta SYSTEM: no piden contrasena y
echo  NUNCA se rompen porque venza o cambie la clave de un usuario.
echo.

:: ── Borra tareas viejas ─────────────────────────────────────────────────────
schtasks /Delete /TN "WurthDashboard" /F 2>nul
schtasks /Delete /TN "WurthDashboardWatchdog" /F 2>nul

:: ── 1) Dashboard principal — ONSTART, arranca al minuto del boot ────────────
::    /RU SYSTEM = sin contrasena, no expira nunca
schtasks /Create /TN "WurthDashboard" ^
  /TR "C:\taginfo\iniciar_dashboard.bat" ^
  /SC ONSTART ^
  /RU "SYSTEM" ^
  /RL HIGHEST ^
  /DELAY 0001:00 ^
  /F
set ERR1=%ERRORLEVEL%

:: ── 2) Watchdog — ONSTART, arranca 2 min despues (deja levantar el dashboard)
schtasks /Create /TN "WurthDashboardWatchdog" ^
  /TR "C:\taginfo\watchdog_dashboard.bat" ^
  /SC ONSTART ^
  /RU "SYSTEM" ^
  /RL HIGHEST ^
  /DELAY 0002:00 ^
  /F
set ERR2=%ERRORLEVEL%

echo.
if %ERR1%==0 if %ERR2%==0 (
  echo  LISTO. Ambas tareas creadas correctamente.
  echo.
  echo  El dashboard ahora:
  echo   - Arranca solo al encender el servidor ^(sin necesidad de login^)
  echo   - Se reinicia solo si el proceso se cae
  echo   - Se reinicia solo si queda colgado ^(watchdog cada 60s^)
  echo   - Libera el puerto 8765 antes de arrancar ^(evita TIME_WAIT^)
  echo   - Guarda logs en C:\taginfo\logs\
) else (
  echo  ERROR al crear alguna tarea. Revisa la contrasena e intenta de nuevo.
)
echo.
echo  Comandos utiles:
echo    Arrancar ahora:   schtasks /Run /TN "WurthDashboard"
echo    Ver estado:       schtasks /Query /TN "WurthDashboard" /FO LIST /V
echo    Ver logs:         type C:\taginfo\logs\dashboard.log
echo.
pause

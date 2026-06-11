@echo off
title Würth Dashboard - Watchdog
setlocal

:: ── Watchdog: verifica que el dashboard RESPONDA por HTTP cada 60s ──────────
:: Si el proceso esta vivo pero colgado (no responde), lo mata. El loop de
:: iniciar_dashboard.bat lo vuelve a levantar automaticamente.

set PORT=8765
set URL=http://localhost:%PORT%/
if not exist "C:\taginfo\logs" mkdir "C:\taginfo\logs"
set LOGFILE=C:\taginfo\logs\watchdog.log

:loop
timeout /t 60 /nobreak >nul

:: PowerShell hace un GET con timeout de 15s. Si falla, devuelve codigo != 0
powershell -NoProfile -Command ^
  "try { $r = Invoke-WebRequest -Uri '%URL%' -TimeoutSec 15 -UseBasicParsing; if ($r.StatusCode -eq 200) { exit 0 } else { exit 1 } } catch { exit 1 }"

if %ERRORLEVEL%==0 (
    :: Responde OK — no hacer nada
    goto loop
)

:: No respondio — el proceso esta colgado. Matarlo para que se reinicie.
echo [%date% %time%] Dashboard NO responde. Matando python para forzar reinicio. >> "%LOGFILE%"
taskkill /F /IM python.exe >nul 2>&1
goto loop

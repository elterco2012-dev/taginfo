@echo off
title Würth Dashboard
setlocal enabledelayedexpansion

:: ── Configuración FTP (valores por defecto, NO secretos) ────────────────────
set FTP_ENABLED=1
set FTP_HOST=www.wurth.com.ar
set FTP_USER=wurth_demotel
set FTP_PATH=/download/w20260609a01
set FTP_INTERVAL=60
set PORT=8765

:: ── Contraseña FTP — se lee de un archivo LOCAL que git NO pisa ──────────────
if exist "%~dp0ftp_credenciales.bat" (
    call "%~dp0ftp_credenciales.bat"
) else (
    echo.
    echo  ====================================================================
    echo   FALTA EL ARCHIVO ftp_credenciales.bat con la contrasena FTP.
    echo   Crealo en C:\taginfo con este contenido ^(una sola linea^):
    echo.
    echo       set FTP_PASS=TU_CONTRASENA_FTP
    echo.
    echo   Guardalo y volve a ejecutar este .bat.
    echo  ====================================================================
    echo.
    pause
    exit /b
)

:: ── Ruta de Python ─────────────────────────────────────────────────────────
set PYTHON="C:\Users\Dashboard-Daniel\AppData\Local\Programs\Python\Python312-32\python.exe"

:: ── Forzar UTF-8 para que el redirect a log no crashee por acentos/ü ────────
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

:: ── Directorio del proyecto ────────────────────────────────────────────────
cd /d C:\taginfo

:: ── Archivo de log con fecha ───────────────────────────────────────────────
if not exist "C:\taginfo\logs" mkdir "C:\taginfo\logs"
set LOGFILE=C:\taginfo\logs\dashboard.log

:loop
:: ── 0) Rotar el log si supera 5 MB (evita que crezca sin limite) ────────────
for %%F in ("%LOGFILE%") do if %%~zF GTR 5242880 (
    move /Y "%LOGFILE%" "%LOGFILE%.old" >nul 2>&1
)

:: ── 1) Limpiar cualquier proceso pegado en el puerto (evita TIME_WAIT) ──────
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :%PORT% ^| findstr LISTENING') do (
    echo [%date% %time%] Liberando puerto %PORT% ^(PID %%a^)... >> "%LOGFILE%"
    taskkill /PID %%a /F >nul 2>&1
)

echo.
echo [%date% %time%] Iniciando Wurth Dashboard...
echo [%date% %time%] Iniciando Wurth Dashboard... >> "%LOGFILE%"

:: ── 2) Lanzar el dashboard — salida en PANTALLA y al LOG a la vez (tee) ──────
::    -u  = Python sin buffer, asi se ve en vivo
%PYTHON% -u dashboard.py 2>&1 | powershell -NoProfile -Command "$input | Tee-Object -FilePath '%LOGFILE%' -Append"

:: ── 3) Si llega aca es porque el proceso termino/crasheo ────────────────────
echo.
echo [%date% %time%] El dashboard se detuvo. Reiniciando en 5 segundos...
echo [%date% %time%] El dashboard se detuvo (exit). Reiniciando... >> "%LOGFILE%"
echo Presiona Ctrl+C para cancelar el reinicio.
timeout /t 5 /nobreak >nul
goto loop

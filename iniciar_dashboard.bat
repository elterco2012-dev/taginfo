@echo off
title Würth Dashboard

:: ── Configuración FTP (valores por defecto, NO secretos) ────────────────────
set FTP_ENABLED=1
set FTP_HOST=www.wurth.com.ar
set FTP_USER=wurth_demotel
set FTP_PATH=/download/w20260609a01
set FTP_INTERVAL=60

:: ── Contraseña FTP — se lee de un archivo LOCAL que git NO pisa ──────────────
:: La primera vez, crea el archivo ftp_credenciales.bat (ver instrucciones abajo).
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

:: ── Directorio del proyecto ────────────────────────────────────────────────
cd /d C:\taginfo

:loop
echo.
echo [%time%] Iniciando Wurth Dashboard...
%PYTHON% dashboard.py
echo.
echo [%time%] El dashboard se detuvo. Reiniciando en 5 segundos...
echo Presiona Ctrl+C para cancelar el reinicio.
timeout /t 5 /nobreak
goto loop

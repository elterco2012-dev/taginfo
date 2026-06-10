@echo off
title Würth Dashboard

:: ── Configuración FTP ──────────────────────────────────────────────────────
:: Cambiá solo la contraseña (FTP_PASS) — el resto ya está configurado
set FTP_ENABLED=1
set FTP_HOST=www.wurth.com.ar
set FTP_USER=wurth_demotel
set FTP_PASS=CAMBIAR_ESTA_CONTRASEÑA
set FTP_PATH=/download/w20260609a01
set FTP_INTERVAL=60

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

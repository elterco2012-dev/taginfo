#!/usr/bin/env python3
"""Verifica que dashboard.py tenga todos los features criticos.
Ejecutar antes de cada git push para evitar perder cambios."""

REQUIRED = [
    # FTP
    ("start_snapshot_job",         "FTP: start_snapshot_job no esta en main()"),
    # Kiosk / Wallboard (tablero fijo 1920x1080 en /kiosk)
    ("KIOSK_PAGE",                 "Kiosk: pagina wallboard KIOSK_PAGE falta"),
    ('"/kiosk"',                   "Kiosk: ruta /kiosk falta en do_GET"),
    ("toggleKiosk",                "Kiosk: boton toggleKiosk falta"),
    ("function mapData",           "Kiosk: mapData (datos reales) falta"),
    ("fitStage",                   "Kiosk: escalado fitStage falta"),
    # Dias habiles restantes
    ("rest-chip",                  "Plan: chip dias habiles restantes falta"),
    ("restDias",                   "Plan: calculo restDias falta"),
    # Trend fix
    ("wd_log if d <= target_str",   "Chart: trend query debe filtrar por wd_log hasta target_str"),
    # Ranking oculto
    ('display:none">',             "Ranking: debe estar oculto con display:none"),
]

with open("dashboard.py") as f:
    src = f.read()

ok = True
for pattern, msg in REQUIRED:
    if pattern not in src:
        print(f"FALTA: {msg}")
        ok = False

if ok:
    print("OK - todos los features presentes")
else:
    print("\nAVISO: corregir antes de hacer push")
    exit(1)

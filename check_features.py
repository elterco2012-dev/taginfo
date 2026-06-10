#!/usr/bin/env python3
"""Verifica que dashboard.py tenga todos los features criticos.
Ejecutar antes de cada git push para evitar perder cambios."""

REQUIRED = [
    # FTP
    ("start_snapshot_job",         "FTP: start_snapshot_job no esta en main()"),
    # Kiosk CSS
    ("body.kiosk .main",           "Kiosk: CSS body.kiosk falta"),
    ("kiosk-bar",                  "Kiosk: kiosk-bar falta"),
    # Kiosk HTML
    ('id="kiosk-p2"',              "Kiosk: ancla kiosk-p2 falta en HTML"),
    ("toggleKiosk",                "Kiosk: boton toggleKiosk falta"),
    # Kiosk JS
    ("kioskStart",                 "Kiosk: funcion kioskStart falta"),
    ("KIOSK_INTERVAL",             "Kiosk: KIOSK_INTERVAL falta"),
    # Dias habiles restantes
    ("rest-chip",                  "Plan: chip dias habiles restantes falta"),
    ("restDias",                   "Plan: calculo restDias falta"),
    # Trend fix
    ("target_str, target_str",     "Chart: trend query debe usar target_str (no CURDATE)"),
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

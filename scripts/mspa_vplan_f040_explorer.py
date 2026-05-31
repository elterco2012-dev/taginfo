"""
Explora vplan (plan de ventas) y f040 (nombres vendedores) en MSPA Informix.
SOLO LECTURA.
"""
import pyodbc
from datetime import date

DSN   = "MSPA"
FIRMA = 1

conn = pyodbc.connect(f"DSN={DSN};", autocommit=True)
cur  = conn.cursor()

def run(label, sql):
    print(f"\n--- {label} ---")
    try:
        cur.execute(sql)
        rows = cur.fetchall()
        for r in rows: print(f"  {r}")
        return rows
    except Exception as e:
        print(f"  SQL ERROR: {e}")
        return []

def cols(label, tbl):
    print(f"\n--- COLUMNAS de {tbl} ---")
    try:
        cur.execute(f"SELECT * FROM {tbl} WHERE 1=0")
        for d in cur.description: print(f"  {d[0]}")
    except Exception as e:
        print(f"  SQL ERROR: {e}")

# ── f040 (nombres vendedores) ────────────────────────────────────────────────
cols("columnas", "f040")

run("f040 muestra (5 rows)",
    f"SELECT FIRST 5 * FROM f040 WHERE firma={FIRMA}")

# Buscar campo que linkea con vertr1 de sbas
run("f040 — campos vertr/vtrt/kdnr (distintos)",
    f"SELECT FIRST 10 * FROM f040 WHERE firma={FIRMA} ORDER BY 1")

# ── vplan (plan de ventas) ───────────────────────────────────────────────────
cols("columnas", "vplan")

run("vplan muestra (5 rows)",
    f"SELECT FIRST 5 * FROM vplan WHERE firma={FIRMA}")

# Ver estructura temporal: ¿tiene año/mes o fecha?
run("vplan — meses disponibles (últimos)",
    f"SELECT DISTINCT jahr, monat FROM vplan WHERE firma={FIRMA} ORDER BY jahr DESC, monat DESC")

# Totales por mes del año actual
run("vplan — total plan por mes año actual",
    f"SELECT monat, SUM(plnwrt) plan FROM vplan "
    f"WHERE firma={FIRMA} AND jahr=YEAR(TODAY) "
    f"GROUP BY monat ORDER BY monat")

# ¿Tiene campo vendedor?
run("vplan — GROUP BY vendedor (mes actual)",
    f"SELECT vertr, monat, SUM(plnwrt) plan FROM vplan "
    f"WHERE firma={FIRMA} AND jahr=YEAR(TODAY) AND monat=MONTH(TODAY) "
    f"GROUP BY vertr, monat ORDER BY plan DESC")

# Cruzar f040 con vplan para ver nombres
run("JOIN vplan + f040 mes actual",
    f"SELECT v.vertr, f.knam, SUM(v.plnwrt) plan "
    f"FROM vplan v, f040 f "
    f"WHERE v.firma={FIRMA} AND f.firma=v.firma AND f.vertr=v.vertr "
    f"AND v.jahr=YEAR(TODAY) AND v.monat=MONTH(TODAY) "
    f"GROUP BY v.vertr, f.knam ORDER BY plan DESC")

# Cruzar sbas (facturacion hoy) con f040 (nombres) via vertr1
run("sbas vertr1 → f040 nombre (hoy)",
    f"SELECT s.vertr1, f.knam, COUNT(DISTINCT s.auftrag) ped, SUM(s.netwert) fact "
    f"FROM sbas s, f040 f "
    f"WHERE s.firma={FIRMA} AND f.firma=s.firma AND f.vertr=s.vertr1 "
    f"AND s.redat=TODAY "
    f"GROUP BY s.vertr1, f.knam ORDER BY fact DESC")

# Plan total del mes (todos los vendedores) vs facturado en el mes
run("Plan total mes actual vs facturado acumulado",
    f"SELECT SUM(v.plnwrt) plan_mes "
    f"FROM vplan v WHERE v.firma={FIRMA} AND v.jahr=YEAR(TODAY) AND v.monat=MONTH(TODAY)")

run("Facturado acumulado mes actual (sbas)",
    f"SELECT SUM(netwert) fact_acum "
    f"FROM sbas WHERE firma={FIRMA} AND bujahr=YEAR(TODAY) AND bumonat=MONTH(TODAY)")

conn.close()
print("\nFin.")

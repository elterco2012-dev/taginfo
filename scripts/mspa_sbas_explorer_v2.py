"""
MSPA sbas explorer v2 — confirma vertr1/vertr2 y busca tabla de nombres de vendedores.
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
        for r in rows:
            print(f"  {r}")
        return rows
    except Exception as e:
        print(f"  SQL ERROR: {e}")
        return []

# 1. Ranking por vertr1 hoy
run("TOP 10 vendedores por vertr1 (facturado hoy)",
    f"SELECT vertr1, COUNT(DISTINCT auftrag) ped, COUNT(*) pos, SUM(netwert) venta "
    f"FROM sbas WHERE firma={FIRMA} AND redat=TODAY "
    f"GROUP BY vertr1 ORDER BY venta DESC")

# 2. Ranking por vertr2 hoy
run("TOP 10 por vertr2",
    f"SELECT vertr2, COUNT(DISTINCT auftrag) ped, SUM(netwert) venta "
    f"FROM sbas WHERE firma={FIRMA} AND redat=TODAY "
    f"GROUP BY vertr2 ORDER BY venta DESC")

# 3. Valores distintos de vertr1 (todos los tiempos, para ver formato)
run("Valores distintos de vertr1 (sample)",
    f"SELECT DISTINCT vertr1 FROM sbas WHERE firma={FIRMA} AND vertr1 IS NOT NULL")

# 4. Buscar tabla de nombres de vertreter — probar varias opciones
for tbl in ["vertr", "vtrnam", "vtr_name", "vendedores", "representantes",
            "personal", "empleados", "usuarios", "agentes"]:
    run(f"Estructura de {tbl}",
        f"SELECT * FROM {tbl} WHERE 1=0")

# 5. Si f090 tiene vertr1, unir para ver si coincide
run("f090 tiene vertr1?",
    "SELECT * FROM f090 WHERE 1=0")
try:
    cur.execute("SELECT * FROM f090 WHERE 1=0")
    cols = [d[0].lower() for d in cur.description]
    print(f"  Columnas f090: {cols}")
    if 'vertr1' in cols or 'vertr' in cols:
        print("  >>> f090 tiene campo vertr1/vertr!")
except Exception as e:
    print(f"  ERROR: {e}")

# 6. Join sbas -> f090 para cruzar vendedor con order_placed si existe kdnr
run("sbas JOIN f090 por auftrag (muestra vertr)",
    f"SELECT FIRST 5 s.vertr1, s.auftrag, s.netwert "
    f"FROM sbas s, f090 o "
    f"WHERE s.firma={FIRMA} AND o.firma=s.firma AND s.auftrag=o.auftrag "
    f"AND s.redat=TODAY")

# 7. ¿Hay tabla kund con nombre del vendedor asignado?
run("kund tiene campo vertr/vendedor?",
    "SELECT * FROM kund WHERE 1=0")
try:
    cur.execute("SELECT * FROM kund WHERE 1=0")
    cols = [d[0].lower() for d in cur.description]
    print(f"  Columnas kund: {cols}")
    for c in cols:
        if 'vert' in c or 'vend' in c or 'agent' in c or 'repr' in c:
            print(f"  >>> Posible campo vendedor en kund: {c}")
except Exception as e:
    print(f"  ERROR: {e}")

conn.close()
print("\nFin.")

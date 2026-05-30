"""
Explora la tabla sbas de MSPA para encontrar el campo vendedor.
SOLO LECTURA.
"""
import pyodbc
from datetime import date

DSN = "MSPA"
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

# 1. Estructura completa de sbas
run("DESCRIBE sbas (todos los campos)", "SELECT * FROM sbas WHERE 1=0")
try:
    cur.execute("SELECT * FROM sbas WHERE 1=0")
    cols = [d[0] for d in cur.description]
    print("\nCOLUMNAS de sbas:")
    for c in cols:
        print(f"  {c}")
except Exception as e:
    print(f"  ERROR: {e}")

# 2. Muestra de hoy
run("Muestra sbas hoy (3 rows)", f"SELECT FIRST 3 * FROM sbas WHERE firma={FIRMA} AND redat=TODAY")

# 3. Intentar posibles campos vendedor
for field in ["vtrtg", "vkbur", "kdver", "verkbur", "vertreter", "vtr", "seller",
              "vendedor", "agente", "verid", "vkorg", "vtrst", "bzirk"]:
    rows = run(f"sbas GROUP BY {field} hoy",
        f"SELECT {field}, COUNT(DISTINCT auftrag) ped, SUM(netwert) val FROM sbas WHERE firma={FIRMA} AND redat=TODAY GROUP BY {field} ORDER BY val DESC")
    if rows:
        print(f"  >>> CAMPO ENCONTRADO: {field}")

# 4. Tablas relacionadas con vendedores
for tbl in ["vtr", "verkbur", "vkbur", "vertreter", "seller", "vendedor", "agente"]:
    run(f"FIRST 3 de tabla {tbl}", f"SELECT FIRST 3 * FROM {tbl}")

conn.close()
print("\nFin.")

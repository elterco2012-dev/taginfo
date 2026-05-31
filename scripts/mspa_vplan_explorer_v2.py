"""
Explorer vplan v2 — detecta columnas reales de la tabla.
SOLO LECTURA.
"""
import pyodbc

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

# 1. Columnas reales de vplan
print("\n--- COLUMNAS de vplan ---")
try:
    cur.execute("SELECT * FROM vplan WHERE 1=0")
    for d in cur.description:
        print(f"  {d[0]}")
except Exception as e:
    print(f"  ERROR: {e}")

# 2. Muestra sin FIRST (usar WHERE rownum o subquery)
run("vplan muestra sin FIRST",
    f"SELECT * FROM vplan WHERE firma={FIRMA}")

# 3. Confirmar join sbas -> f040 con name1
run("sbas vertr1 → f040.name1 (hoy)",
    f"SELECT s.vertr1, f.name1, COUNT(DISTINCT s.auftrag) ped, SUM(s.netwert) fact "
    f"FROM sbas s, f040 f "
    f"WHERE s.firma={FIRMA} AND f.firma=s.firma AND f.vertr=s.vertr1 "
    f"AND s.redat=TODAY "
    f"GROUP BY s.vertr1, f.name1 ORDER BY fact DESC")

conn.close()
print("\nFin.")

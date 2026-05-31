"""
Obtiene nombres de columnas de vplan desde el catálogo Informix + confirma joins.
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

# Nombres de columnas desde catálogo Informix
run("COLUMNAS vplan (syscolumns)",
    "SELECT c.colno, c.colname, c.coltype "
    "FROM systables t, syscolumns c "
    "WHERE t.tabname='vplan' AND c.tabid=t.tabid "
    "ORDER BY c.colno")

# Columnas f040
run("COLUMNAS f040 (syscolumns)",
    "SELECT c.colno, c.colname "
    "FROM systables t, syscolumns c "
    "WHERE t.tabname='f040' AND c.tabid=t.tabid "
    "ORDER BY c.colno")

# sbas -> f040 por mes (no solo hoy, sino el mes acumulado)
run("sbas vertr1 → f040.name1 (mes actual acumulado)",
    f"SELECT s.vertr1, f.name1, COUNT(DISTINCT s.auftrag) ped, SUM(s.netwert) fact "
    f"FROM sbas s, f040 f "
    f"WHERE s.firma={FIRMA} AND f.firma=s.firma AND f.vertr=s.vertr1 "
    f"AND s.bujahr=YEAR(TODAY) AND s.bumonat=MONTH(TODAY) "
    f"GROUP BY s.vertr1, f.name1 ORDER BY fact DESC")

conn.close()
print("\nFin.")

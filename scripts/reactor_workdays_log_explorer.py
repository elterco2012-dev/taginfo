"""
Explora work_days_log para entender estructura y uso.
SOLO LECTURA.
"""
import pyodbc
conn = pyodbc.connect("DSN=Wurth Reactor Produccion;", autocommit=True)
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

# 1. Columnas
print("\n--- COLUMNAS work_days_log ---")
cur.execute("SELECT * FROM work_days_log LIMIT 0")
cols = [d[0] for d in cur.description]
print(f"  {cols}")

# 2. Muestra de 15 filas
run("Muestra 15 filas", "SELECT * FROM work_days_log LIMIT 15")

# 3. Filas de mayo 2026
run("Mayo 2026", "SELECT * FROM work_days_log WHERE YEAR(date) = 2026 AND MONTH(date) = 5 ORDER BY date")

# 4. Rango de fechas disponibles
run("Rango fechas", "SELECT MIN(date), MAX(date), COUNT(*) FROM work_days_log")

conn.close()
print("\nFin.")

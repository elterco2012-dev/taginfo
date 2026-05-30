"""
Reactor Explorer v3 - work_days table structure
SOLO LECTURA.
"""
import pyodbc
from datetime import date, datetime

DSN = "Wurth Reactor Produccion"

def run(cur, label, sql, params=None):
    print(f"  {label}...")
    try:
        cur.execute(sql, params) if params else cur.execute(sql)
        return cur.fetchall()
    except Exception as e:
        print(f"    SQL ERROR: {e}")
        return []

conn = pyodbc.connect(f"DSN={DSN};", autocommit=True)
cur = conn.cursor()

print("=== DESCRIBE work_days ===")
for r in run(cur, "describe", "DESCRIBE work_days"):
    print(f"  {r[0]:30s} {r[1]}")

print("\n=== MUESTRA work_days (10 rows) ===")
for r in run(cur, "sample", "SELECT * FROM work_days ORDER BY id DESC LIMIT 10"):
    print(f"  {r}")

print("\n=== COUNT work_days por mes 2025-2026 ===")
for field in ["date", "fecha", "day", "work_date", "fecha_habil", "fecha_dia"]:
    rows = run(cur, f"field {field}", f"""
        SELECT DATE_FORMAT({field}, '%Y-%m') mes, COUNT(*) dias
        FROM work_days
        WHERE {field} >= '2025-01-01'
        GROUP BY DATE_FORMAT({field}, '%Y-%m')
        ORDER BY mes DESC LIMIT 15
    """)
    if rows:
        print(f"\n  Campo fecha: {field}")
        for r in rows: print(f"    {r[0]}  dias_habiles={r[1]}")
        break

conn.close()

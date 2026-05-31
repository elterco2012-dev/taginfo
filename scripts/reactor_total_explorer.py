"""
Investiga qué representa order_placed.total y busca campo de precio neto.
SOLO LECTURA.
"""
import pyodbc

DSN = "Wurth Reactor Produccion"
conn = pyodbc.connect(f"DSN={DSN};", autocommit=True)
cur  = conn.cursor()

def run(label, sql, params=None):
    print(f"\n--- {label} ---")
    try:
        cur.execute(sql, params) if params else cur.execute(sql)
        rows = cur.fetchall()
        for r in rows: print(f"  {r}")
        return rows
    except Exception as e:
        print(f"  SQL ERROR: {e}")
        return []

# 1. Columnas de order_placed
print("\n--- COLUMNAS order_placed ---")
cur.execute("SELECT * FROM order_placed LIMIT 0")
cols = [d[0] for d in cur.description]
print(f"  {cols}")

# 2. Columnas de order_detail
print("\n--- COLUMNAS order_detail ---")
cur.execute("SELECT * FROM order_detail LIMIT 0")
cols_det = [d[0] for d in cur.description]
print(f"  {cols_det}")

# 3. Muestra de 3 pedidos del 29/05/2026 con sus totales
run("Muestra 3 pedidos 29/05/2026",
    "SELECT id, id_user, id_order_status, total FROM order_placed WHERE DATE(order_date)='2026-05-29' LIMIT 3")

# 4. Suma de total vs cuenta de pedidos
run("SUM(total) vs COUNT pedidos 29/05",
    "SELECT COUNT(DISTINCT id) pedidos, SUM(total) total_sum, AVG(total) total_avg FROM order_placed WHERE DATE(order_date)='2026-05-29'")

# 5. Precio desde order_detail para esos pedidos (unit_price * quantity)
run("SUM de lineas (price * qty) 29/05",
    """SELECT COUNT(DISTINCT op.id) pedidos,
              SUM(od.unit_price * od.quantity) total_det,
              SUM(op.total) total_op
       FROM order_placed op
       JOIN order_detail od ON od.id_order_placed = op.id
       WHERE DATE(op.order_date) = '2026-05-29'""")

# 6. Rangos de total para detectar si está en centavos o incluye IVA
run("Rangos de total 29/05",
    """SELECT MIN(total) min_t, MAX(total) max_t, AVG(total) avg_t,
              SUM(CASE WHEN total > 10000000 THEN 1 ELSE 0 END) pedidos_millonarios
       FROM order_placed WHERE DATE(order_date)='2026-05-29'""")

# 7. Buscar campos alternativos de precio neto en order_placed
price_like = [c for c in cols if any(k in c.lower() for k in ['net','neto','price','precio','amount','monto','subtotal'])]
print(f"\n--- Campos de precio en order_placed: {price_like} ---")
if price_like:
    sums = ', '.join(f'SUM({c}) AS {c}' for c in price_like)
    run("Sumas de campos de precio alternativos",
        f"SELECT {sums} FROM order_placed WHERE DATE(order_date)='2026-05-29'")

conn.close()
print("\nFin.")

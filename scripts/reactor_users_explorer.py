"""
Explora tabla users de Reactor (MySQL) para encontrar nombres de vendedores y supervisores.
SOLO LECTURA.
"""
import pyodbc

DSN = "Wurth Reactor Produccion"
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

# 1. Columnas de la tabla users
print("\n--- COLUMNAS de users ---")
try:
    cur.execute("SELECT * FROM users LIMIT 0")
    for d in cur.description: print(f"  {d[0]}")
except Exception as e:
    print(f"  ERROR: {e}")

# 2. Muestra de 5 filas
run("users muestra (5 rows)", "SELECT * FROM users LIMIT 5")

# 3. Vendedores que aparecen en order_placed hoy
run("Vendedores activos hoy (id_user)",
    "SELECT DISTINCT id_user FROM order_placed WHERE DATE(order_date) = DATE(NOW()) ORDER BY id_user LIMIT 20")

# 4. JOIN order_placed con users para ver cuáles matchean
run("order_placed JOIN users (muestra de hoy)",
    """SELECT op.id_user, u.*
       FROM order_placed op
       JOIN users u ON u.id = op.id_user
       WHERE DATE(op.order_date) = DATE(NOW())
       LIMIT 3""")

# 5. Tablas relacionadas a jerarquía / supervisores
for tbl in ["user_roles", "roles", "employees", "sellers", "teams", "supervisors",
            "user_supervisor", "user_manager", "hierarchies"]:
    run(f"Columnas de {tbl}",
        f"SELECT * FROM {tbl} LIMIT 0")

# 6. ¿users tiene campo supervisor/manager/parent?
print("\n--- Campos posibles de supervisor en users ---")
try:
    cur.execute("SELECT * FROM users LIMIT 0")
    cols = [d[0].lower() for d in cur.description]
    for c in cols:
        if any(k in c for k in ['sup','manager','jefe','boss','parent','lead','chief','report']):
            print(f"  >>> {c}")
    print(f"  Todas las columnas: {cols}")
except Exception as e:
    print(f"  ERROR: {e}")

conn.close()
print("\nFin.")

"""
Reactor Explorer v1 - Explorar tablas order_place, order_detail, order_status
MySQL DSN: "Wurth Reactor Produccion"
SOLO LECTURA.
"""

import pyodbc
from datetime import date, datetime

DSN_REACTOR = "Wurth Reactor Produccion"
OUTPUT_FILE = "reactor_explorer_v1.txt"


def get_conn():
    return pyodbc.connect(f"DSN={DSN_REACTOR};", autocommit=True)


def run(cursor, label, sql):
    print(f"  {label}...")
    try:
        cursor.execute(sql)
        return cursor.fetchall()
    except Exception as e:
        print(f"    SQL ERROR [{label}]: {e}")
        return []


def main():
    lines = []
    log = lines.append
    today = date.today()

    log(f"Reactor Explorer v1 - {datetime.now()}")
    log(f"DSN: {DSN_REACTOR}  |  Fecha: {today}  |  SOLO LECTURA")
    log("=" * 70)

    conn = get_conn()
    cur = conn.cursor()
    log("Conexion OK\n")

    # ============================================================
    # 1. LISTAR TODAS LAS TABLAS de la BD
    # ============================================================
    log("=== TABLAS EN LA BD ===")
    for r in run(cur, "show tables", "SHOW TABLES"):
        log(f"  {r[0]}")

    # ============================================================
    # 2. ESTRUCTURA de order_place
    # ============================================================
    log("\n=== ESTRUCTURA order_place ===")
    for r in run(cur, "describe order_place", "DESCRIBE order_place"):
        log(f"  {r[0]:30s} {r[1]:25s} null={r[2]} key={r[3]} default={r[4]}")

    # ============================================================
    # 3. ESTRUCTURA de order_detail
    # ============================================================
    log("\n=== ESTRUCTURA order_detail ===")
    for r in run(cur, "describe order_detail", "DESCRIBE order_detail"):
        log(f"  {r[0]:30s} {r[1]:25s} null={r[2]} key={r[3]} default={r[4]}")

    # ============================================================
    # 4. ESTRUCTURA de order_status
    # ============================================================
    log("\n=== ESTRUCTURA order_status ===")
    for r in run(cur, "describe order_status", "DESCRIBE order_status"):
        log(f"  {r[0]:30s} {r[1]:25s} null={r[2]} key={r[3]} default={r[4]}")

    # ============================================================
    # 5. MUESTRA DE order_place (ultimos 5 registros)
    # ============================================================
    log("\n=== MUESTRA order_place (LIMIT 5 recientes) ===")
    rows = run(cur, "sample order_place", """
        SELECT * FROM order_place ORDER BY id DESC LIMIT 5
    """)
    if rows:
        for r in rows:
            log(f"  {r}")

    # ============================================================
    # 6. MUESTRA DE order_status (valores distintos de status)
    # ============================================================
    log("\n=== DIST order_status.status ===")
    for r in run(cur, "dist status", """
        SELECT status, COUNT(*) cnt FROM order_status GROUP BY status ORDER BY status
    """):
        log(f"  status={r[0]}  cnt={r[1]}")

    # ============================================================
    # 7. COUNT por fecha reciente en order_place
    # ============================================================
    log("\n=== order_place COUNT por fecha (ultimos 10 dias) ===")
    # Intentar detectar campo de fecha
    date_fields = ["created_at", "fecha", "date", "order_date", "informed_at",
                   "created", "dt", "datetime", "fechahora", "timestamp"]
    for field in date_fields:
        rows = run(cur, f"date field {field}", f"""
            SELECT DATE({field}), COUNT(*) FROM order_place
            WHERE DATE({field}) >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
            GROUP BY DATE({field}) ORDER BY DATE({field}) DESC LIMIT 10
        """)
        if rows:
            log(f"\n  Campo de fecha encontrado: {field}")
            for r in rows:
                log(f"    {r[0]}  cnt={r[1]}")
            break

    # ============================================================
    # 8. MUESTRA DE order_status (5 registros)
    # ============================================================
    log("\n=== MUESTRA order_status (LIMIT 5) ===")
    rows = run(cur, "sample order_status", """
        SELECT * FROM order_status ORDER BY id DESC LIMIT 5
    """)
    if rows:
        for r in rows:
            log(f"  {r}")

    # ============================================================
    # 9. JOIN order_place + order_status HOY
    # ============================================================
    log("\n=== Intentar JOIN order_place + order_status HOY ===")
    # Try common join patterns
    join_tries = [
        ("op.id = os.order_id", """
            SELECT os.status, COUNT(DISTINCT op.id) ords
            FROM order_place op, order_status os
            WHERE op.id = os.order_id
              AND DATE(op.created_at) = CURDATE()
            GROUP BY os.status ORDER BY os.status
        """),
        ("op.id = os.order_place_id", """
            SELECT os.status, COUNT(DISTINCT op.id) ords
            FROM order_place op, order_status os
            WHERE op.id = os.order_place_id
              AND DATE(op.created_at) = CURDATE()
            GROUP BY os.status ORDER BY os.status
        """),
        ("op.order_id = os.order_id", """
            SELECT os.status, COUNT(DISTINCT op.id) ords
            FROM order_place op, order_status os
            WHERE op.order_id = os.order_id
              AND DATE(op.created_at) = CURDATE()
            GROUP BY os.status ORDER BY os.status
        """),
    ]
    for label, sql in join_tries:
        rows = run(cur, f"join {label}", sql)
        if rows:
            log(f"\n  JOIN via {label} FUNCIONA:")
            for r in rows:
                log(f"    status={r[0]}  ords={r[1]}")
            break

    # ============================================================
    # 10. ESTADISTICAS HISTORICAS - pedidos por mes
    # ============================================================
    log("\n=== HISTORICO mensual order_place ===")
    for r in run(cur, "mensual historico", """
        SELECT DATE_FORMAT(created_at, '%Y-%m') mes,
               COUNT(DISTINCT id) pedidos,
               COUNT(DISTINCT seller_id) vendedores
        FROM order_place
        WHERE created_at >= DATE_SUB(CURDATE(), INTERVAL 12 MONTH)
        GROUP BY DATE_FORMAT(created_at, '%Y-%m')
        ORDER BY mes DESC
        LIMIT 13
    """):
        log(f"  mes={r[0]}  pedidos={r[1]}  vendedores={r[2]}")

    # ============================================================
    # 11. VENDEDORES - campo seller
    # ============================================================
    log("\n=== CAMPOS VENDEDOR en order_place ===")
    seller_fields = ["seller_id", "seller", "vendedor", "user_id", "salesman_id",
                     "agent_id", "employee_id", "representative_id"]
    for field in seller_fields:
        rows = run(cur, f"seller field {field}", f"""
            SELECT COUNT(DISTINCT {field}) FROM order_place
            WHERE DATE(created_at) = CURDATE()
        """)
        if rows:
            log(f"  OK: {field} — vendedores hoy={rows[0][0]}")

    # ============================================================
    # 12. order_detail - muestra y conteo
    # ============================================================
    log("\n=== order_detail COUNT y muestra ===")
    for r in run(cur, "order_detail count", "SELECT COUNT(*) FROM order_detail"):
        log(f"  total order_detail: {r[0]}")

    rows = run(cur, "order_detail sample", "SELECT * FROM order_detail LIMIT 3")
    if rows:
        for r in rows:
            log(f"  {r}")

    conn.close()

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\nListo -> {OUTPUT_FILE}")


if __name__ == "__main__":
    main()

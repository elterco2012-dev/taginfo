"""
Reactor Explorer v2 - Foco en order_placed + order_status_history + kpi_sales
SOLO LECTURA.
"""

import pyodbc
from datetime import date, datetime

DSN_REACTOR = "Wurth Reactor Produccion"
OUTPUT_FILE = "reactor_explorer_v2.txt"


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

    log(f"Reactor Explorer v2 - {datetime.now()}")
    log(f"DSN: {DSN_REACTOR}  |  Fecha: {today}  |  SOLO LECTURA")
    log("=" * 70)

    conn = get_conn()
    cur = conn.cursor()
    log("Conexion OK\n")

    # ============================================================
    # 1. order_placed - estructura completa
    # ============================================================
    log("=== ESTRUCTURA order_placed ===")
    for r in run(cur, "describe order_placed", "DESCRIBE order_placed"):
        log(f"  {r[0]:35s} {r[1]:25s} null={r[2]} key={r[3]}")

    # ============================================================
    # 2. order_placed - muestra reciente
    # ============================================================
    log("\n=== MUESTRA order_placed (5 recientes) ===")
    for r in run(cur, "sample order_placed", "SELECT * FROM order_placed ORDER BY id DESC LIMIT 5"):
        log(f"  {r}")

    # ============================================================
    # 3. order_status_history - estructura
    # ============================================================
    log("\n=== ESTRUCTURA order_status_history ===")
    for r in run(cur, "describe order_status_history", "DESCRIBE order_status_history"):
        log(f"  {r[0]:35s} {r[1]:25s} null={r[2]} key={r[3]}")

    # ============================================================
    # 4. order_status_history - muestra reciente
    # ============================================================
    log("\n=== MUESTRA order_status_history (5 recientes) ===")
    for r in run(cur, "sample order_status_history", "SELECT * FROM order_status_history ORDER BY id DESC LIMIT 5"):
        log(f"  {r}")

    # ============================================================
    # 5. order_status completo (todos los status IDs y nombres)
    # ============================================================
    log("\n=== order_status COMPLETO ===")
    for r in run(cur, "all statuses", "SELECT id, name, description FROM order_status ORDER BY id"):
        log(f"  id={r[0]:3d}  name={r[1]:40s}  desc={r[2]}")

    # ============================================================
    # 6. Pedidos por fecha usando order_placed
    # ============================================================
    log("\n=== order_placed COUNT por fecha (ultimos 30 dias) ===")
    date_fields = ["created_at", "fecha", "date", "order_date", "informed_at",
                   "created", "dt", "timestamp", "fechahora", "placed_at", "updated_at"]
    found_date = None
    for field in date_fields:
        rows = run(cur, f"date field {field}", f"""
            SELECT DATE({field}), COUNT(*) cnt
            FROM order_placed
            WHERE DATE({field}) >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
            GROUP BY DATE({field}) ORDER BY DATE({field}) DESC LIMIT 10
        """)
        if rows:
            found_date = field
            log(f"\n  Campo fecha: {field}")
            for r in rows:
                log(f"    {r[0]}  cnt={r[1]}")
            break

    # ============================================================
    # 7. STATS HOY: pedidos, lineas, vendedores, promedio
    # ============================================================
    if found_date:
        log(f"\n=== STATS HOY ({today}) ===")
        for r in run(cur, "stats hoy total", f"""
            SELECT COUNT(DISTINCT op.id) pedidos,
                   COUNT(od.id) lineas,
                   ROUND(COUNT(od.id)/COUNT(DISTINCT op.id),1) avg_lineas
            FROM order_placed op
            LEFT JOIN order_detail od ON od.id_order_placed = op.id
            WHERE DATE(op.{found_date}) = CURDATE()
        """):
            log(f"  pedidos={r[0]}  lineas={r[1]}  avg_lineas={r[2]}")

        # Vendedor fields
        seller_candidates = ["seller_id", "user_id", "employee_id", "seller_user_id",
                             "salesman_id", "agent_id", "id_seller", "id_user"]
        for field in seller_candidates:
            rows = run(cur, f"seller {field}", f"""
                SELECT COUNT(DISTINCT {field}) vendedores
                FROM order_placed
                WHERE DATE({found_date}) = CURDATE()
            """)
            if rows:
                log(f"  vendedores via {field}: {rows[0][0]}")
                break

        # ── Pedidos por status HOY ──
        log(f"\n=== PEDIDOS POR STATUS HOY ===")
        # Try join order_placed -> order_status_history -> order_status
        status_joins = [
            ("osh.id_order_placed", f"""
                SELECT os.name, COUNT(DISTINCT op.id) cnt
                FROM order_placed op
                JOIN order_status_history osh ON osh.id_order_placed = op.id
                JOIN order_status os ON os.id = osh.id_order_status
                WHERE DATE(op.{found_date}) = CURDATE()
                GROUP BY os.id, os.name ORDER BY os.id
            """),
            ("osh.order_placed_id", f"""
                SELECT os.name, COUNT(DISTINCT op.id) cnt
                FROM order_placed op
                JOIN order_status_history osh ON osh.order_placed_id = op.id
                JOIN order_status os ON os.id = osh.order_status_id
                WHERE DATE(op.{found_date}) = CURDATE()
                GROUP BY os.id, os.name ORDER BY os.id
            """),
            ("direct status in order_placed", f"""
                SELECT id_order_status, COUNT(*) cnt
                FROM order_placed
                WHERE DATE({found_date}) = CURDATE()
                GROUP BY id_order_status ORDER BY id_order_status
            """),
            ("direct status2 in order_placed", f"""
                SELECT order_status_id, COUNT(*) cnt
                FROM order_placed
                WHERE DATE({found_date}) = CURDATE()
                GROUP BY order_status_id ORDER BY order_status_id
            """),
        ]
        for label, sql in status_joins:
            rows = run(cur, f"status join {label}", sql)
            if rows:
                log(f"\n  JOIN via [{label}] FUNCIONA:")
                for r in rows:
                    log(f"    {r}")
                break

    # ============================================================
    # 8. kpi_sales - estructura y muestra
    # ============================================================
    log("\n=== ESTRUCTURA kpi_sales ===")
    for r in run(cur, "describe kpi_sales", "DESCRIBE kpi_sales"):
        log(f"  {r[0]:35s} {r[1]:25s} null={r[2]} key={r[3]}")

    log("\n=== MUESTRA kpi_sales (5 recientes) ===")
    for r in run(cur, "sample kpi_sales", "SELECT * FROM kpi_sales ORDER BY id DESC LIMIT 5"):
        log(f"  {r}")

    # ============================================================
    # 9. sales_ifx - estructura (puede tener historico ventas)
    # ============================================================
    log("\n=== ESTRUCTURA sales_ifx ===")
    for r in run(cur, "describe sales_ifx", "DESCRIBE sales_ifx"):
        log(f"  {r[0]:35s} {r[1]:25s} null={r[2]} key={r[3]}")

    log("\n=== sales_ifx COUNT por mes (12 meses) ===")
    # Try date fields
    for field in ["date", "fecha", "created_at", "sale_date", "redat"]:
        rows = run(cur, f"sales_ifx por mes {field}", f"""
            SELECT DATE_FORMAT({field}, '%Y-%m') mes, COUNT(*) cnt, SUM(net_value) val
            FROM sales_ifx
            WHERE {field} >= DATE_SUB(CURDATE(), INTERVAL 12 MONTH)
            GROUP BY DATE_FORMAT({field}, '%Y-%m')
            ORDER BY mes DESC LIMIT 13
        """)
        if rows:
            log(f"  Campo fecha en sales_ifx: {field}")
            for r in rows:
                log(f"    {r}")
            break

    # ============================================================
    # 10. HISTORICO MENSUAL order_placed (12 meses)
    # ============================================================
    if found_date:
        log(f"\n=== HISTORICO MENSUAL order_placed (12 meses via {found_date}) ===")
        for r in run(cur, "historico mensual order_placed", f"""
            SELECT DATE_FORMAT(op.{found_date}, '%Y-%m') mes,
                   COUNT(DISTINCT op.id) pedidos,
                   COUNT(od.id) lineas,
                   ROUND(COUNT(od.id)/NULLIF(COUNT(DISTINCT op.id),0),1) avg_lineas
            FROM order_placed op
            LEFT JOIN order_detail od ON od.id_order_placed = op.id
            WHERE op.{found_date} >= DATE_SUB(CURDATE(), INTERVAL 12 MONTH)
            GROUP BY DATE_FORMAT(op.{found_date}, '%Y-%m')
            ORDER BY mes DESC LIMIT 13
        """):
            log(f"  mes={r[0]}  pedidos={r[1]}  lineas={r[2]}  avg={r[3]}")

    conn.close()

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\nListo -> {OUTPUT_FILE}")


if __name__ == "__main__":
    main()

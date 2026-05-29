"""
TagInfo v19 — backorders sin termin, bloqueados total all-aufkstat, sb104 remitos.
SOLO LECTURA.
"""

import pyodbc
from datetime import date, datetime

DSN = "MSPA"
OUTPUT_FILE = "taginfo_v19.txt"
FIRMA = 1


def get_conn():
    return pyodbc.connect(f"DSN={DSN};", autocommit=True)


def run(cursor, label, sql):
    print(f"  {label}...")
    try:
        cursor.execute(sql)
        return cursor.fetchall()
    except Exception as e:
        print(f"    SQL ERROR: {e}")
        return []


def main():
    lines = []
    log = lines.append
    today = date.today()

    log(f"TagInfo v19 — {datetime.now()}")
    log(f"DSN: {DSN}  |  Fecha: {today}  |  SOLO LECTURA")
    log("=" * 70)

    conn = get_conn()
    cur = conn.cursor()
    log("Conexión OK\n")

    # ============================================================
    # 1. BLOQUEADOS — total_open de TODAS las ordenes del cliente
    #    (no solo aufkstat=0, sino todos los estados)
    # ============================================================
    log("=== BLOQUEADOS v2 — total_open ALL aufkstat ===")

    totals_all = run(cur, "kdnr open totals ALL aufkstat", f"""
        SELECT h.kdnr, SUM(p.poswert) total_open
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND p.kzerl = '0'
        GROUP BY h.kdnr
    """)
    log(f"  Step1 all-aufkstat: {len(totals_all)} customers")

    # kredlim per customer
    kredlim_rows = run(cur, "kredlim per kdnr", f"""
        SELECT kdnr, kredlim FROM kund
        WHERE firma = {FIRMA} AND kredlim > 0
    """)
    kredlim_map = {r[0]: r[1] for r in kredlim_rows}

    over_all = [r[0] for r in totals_all
                if kredlim_map.get(r[0], 0) > 0 and r[1] is not None and r[1] > kredlim_map.get(r[0], 0)]
    under_all = [r[0] for r in totals_all
                 if kredlim_map.get(r[0], 0) == 0 or r[1] is None or r[1] <= kredlim_map.get(r[0], 0)]

    log(f"  over_limit_ALL={len(over_all)}  under_limit_ALL={len(under_all)}")

    if over_all:
        in_list = ','.join(str(k) for k in over_all)
        for r in run(cur, "bloq ALL-aufkstat IN", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p
            WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
              AND h.auftrag = p.auftrag
              AND h.aufkstat = 0 AND p.posstat = 0 AND p.kzerl = '0'
              AND h.kdnr IN ({in_list})
        """):
            log(f"  BLOQUEADOS (all-aufkstat total): ords={r[0]}  pos={r[1]}  val={r[2]}")

    # Also try: bloqueados only using aufkstat=0 open orders as the sum
    # but WITHOUT posstat=0 filter (include all positions)
    log("\n--- Bloqueados SIN posstat filter ---")
    totals_no_posstat = run(cur, "kdnr open totals no posstat", f"""
        SELECT h.kdnr, SUM(p.poswert) total_open
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND h.aufkstat = 0 AND p.kzerl = '0'
        GROUP BY h.kdnr
    """)

    over_np = [r[0] for r in totals_no_posstat
               if kredlim_map.get(r[0], 0) > 0 and r[1] is not None and r[1] > kredlim_map.get(r[0], 0)]

    log(f"  over_limit (no posstat filter): {len(over_np)} customers")

    if over_np:
        in_list_np = ','.join(str(k) for k in over_np)
        for r in run(cur, "bloq no-posstat IN", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p
            WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
              AND h.auftrag = p.auftrag
              AND h.aufkstat = 0 AND p.posstat = 0 AND p.kzerl = '0'
              AND h.kdnr IN ({in_list_np})
        """):
            log(f"  BLOQUEADOS (no posstat sum): ords={r[0]}  pos={r[1]}  val={r[2]}")

    # ============================================================
    # 2. BACKORDERS — todos los aufkstat=0 que NO son bloqueados
    #    (sin filtro de termin)
    # ============================================================
    log("\n=== BACKORDERS v2 — aufkstat=0 NOT bloqueados ===")

    # Using the original over_limit (aufkstat=0, posstat=0 sum)
    totals_orig = run(cur, "kdnr open totals orig", f"""
        SELECT h.kdnr, SUM(p.poswert) total_open
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND h.aufkstat = 0 AND p.posstat = 0 AND p.kzerl = '0'
        GROUP BY h.kdnr
    """)

    over_orig = [r[0] for r in totals_orig
                 if kredlim_map.get(r[0], 0) > 0 and r[1] is not None and r[1] > kredlim_map.get(r[0], 0)]
    under_orig = [r[0] for r in totals_orig
                  if not (kredlim_map.get(r[0], 0) > 0 and r[1] is not None and r[1] > kredlim_map.get(r[0], 0))]

    log(f"  over_orig={len(over_orig)}  under_orig={len(under_orig)}")

    if over_orig:
        in_over = ','.join(str(k) for k in over_orig)
        for r in run(cur, "BLOQUEADOS orig", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p
            WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
              AND h.auftrag = p.auftrag
              AND h.aufkstat = 0 AND p.posstat = 0 AND p.kzerl = '0'
              AND h.kdnr IN ({in_over})
        """):
            log(f"  BLOQUEADOS: ords={r[0]}  pos={r[1]}  val={r[2]}")

    if under_orig:
        in_under = ','.join(str(k) for k in under_orig)
        # Without termin filter — ALL under-limit orders
        for r in run(cur, "BACKORDERS all termin", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p
            WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
              AND h.auftrag = p.auftrag
              AND h.aufkstat = 0 AND p.posstat = 0 AND p.kzerl = '0'
              AND h.kdnr IN ({in_under})
        """):
            log(f"  BACKORDERS (no termin filter): ords={r[0]}  pos={r[1]}  val={r[2]}")

    # Total aufkstat=0 posstat=0 without any kdnr filter
    for r in run(cur, "aufkstat0 posstat0 total", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND h.aufkstat = 0 AND p.posstat = 0 AND p.kzerl = '0'
    """):
        log(f"  aufkstat=0 posstat=0 total: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # ============================================================
    # 3. sb104 — estructura y datos para remitos
    # ============================================================
    log("\n=== sb104 — COLUMNAS ===")
    for r in run(cur, "sb104 cols", """
        SELECT c.colno, c.colname, c.coltype
        FROM syscolumns c, systables t
        WHERE c.tabid = t.tabid AND t.tabname = 'sb104'
        ORDER BY c.colno
    """):
        log(f"  [{r[0]}] {r[1]}  type={r[2]}")

    log("\n=== sb104 — TOTALES ===")
    for r in run(cur, "sb104 count", f"SELECT COUNT(*) FROM sb104 WHERE firma = {FIRMA}"):
        log(f"  sb104 total rows: {r[0]}")

    # Distribution of key flag columns in sb104
    for col in ['kzfakt', 'kzerl', 'posstat', 'status']:
        for r in run(cur, f"sb104 {col} dist", f"""
            SELECT {col}, COUNT(*) cnt
            FROM sb104 WHERE firma = {FIRMA}
            GROUP BY {col} ORDER BY {col}
        """):
            log(f"  sb104.{col}={r[0]}  cnt={r[1]}")

    # Remitos open in sb104 — kzfakt='0' (not yet invoiced)
    for r in run(cur, "sb104 kzfakt='0'", f"""
        SELECT COUNT(DISTINCT lsnr) docs, COUNT(*) pos, SUM(liefwert) val
        FROM sb104 WHERE firma = {FIRMA} AND kzfakt = '0'
    """):
        log(f"  sb104 kzfakt='0': docs={r[0]}  pos={r[1]}  val={r[2]}")

    # sb104 with kzerl='0'
    for r in run(cur, "sb104 kzerl='0'", f"""
        SELECT COUNT(DISTINCT lsnr) docs, COUNT(*) pos, SUM(liefwert) val
        FROM sb104 WHERE firma = {FIRMA} AND kzerl = '0'
    """):
        log(f"  sb104 kzerl='0': docs={r[0]}  pos={r[1]}  val={r[2]}")

    # ============================================================
    # 4. SNAPSHOT COMPLETO
    # ============================================================
    log("\n=== SNAPSHOT COMPLETO ===")
    ts = datetime.now()

    for r in run(cur, "snap produccion", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND h.aufkstat = 2 AND p.posstat = 2 AND p.kzerl = '0'
    """):
        log(f"  [PRODUCCION] ords={r[0]}  pos={r[1]}  val={r[2]}")

    # Recompute bloqueados/backorders fresh at snapshot time
    totals_snap = run(cur, "snap kdnr totals", f"""
        SELECT h.kdnr, SUM(p.poswert) total_open
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND h.aufkstat = 0 AND p.posstat = 0 AND p.kzerl = '0'
        GROUP BY h.kdnr
    """)
    over_snap = [r[0] for r in totals_snap
                 if kredlim_map.get(r[0], 0) > 0 and r[1] is not None and r[1] > kredlim_map.get(r[0], 0)]
    under_snap = [r[0] for r in totals_snap
                  if not (kredlim_map.get(r[0], 0) > 0 and r[1] is not None and r[1] > kredlim_map.get(r[0], 0))]

    if over_snap:
        in_o = ','.join(str(k) for k in over_snap)
        for r in run(cur, "snap bloqueados", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p
            WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
              AND h.auftrag = p.auftrag
              AND h.aufkstat = 0 AND p.posstat = 0 AND p.kzerl = '0'
              AND h.kdnr IN ({in_o})
        """):
            log(f"  [BLOQUEADOS] ords={r[0]}  pos={r[1]}  val={r[2]}")

    if under_snap:
        in_u = ','.join(str(k) for k in under_snap)
        for r in run(cur, "snap backorders", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p
            WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
              AND h.auftrag = p.auftrag
              AND h.aufkstat = 0 AND p.posstat = 0 AND p.kzerl = '0'
              AND h.kdnr IN ({in_u})
        """):
            log(f"  [BACKORDERS] ords={r[0]}  pos={r[1]}  val={r[2]}")

    for r in run(cur, "snap venta", f"""
        SELECT COUNT(DISTINCT renr) docs, COUNT(*) pos, SUM(netwert) val
        FROM sbas WHERE firma = {FIRMA} AND redat = TODAY AND belegart IN (8, 11)
    """):
        log(f"  [VENTA bel8+11] docs={r[0]}  pos={r[1]}  val={r[2]}")

    for r in run(cur, "snap status<-1", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag AND h.aufkstat < -1 AND p.kzerl = '0'
    """):
        log(f"  [STATUS<-1] ords={r[0]}  pos={r[1]}  val={r[2]}")

    log(f"  Timestamp: {ts}")

    conn.close()

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\nListo → {OUTPUT_FILE}")


if __name__ == "__main__":
    main()

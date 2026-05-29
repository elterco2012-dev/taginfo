"""
TagInfo v20 — backorders/bloqueados con kzlsdru=0, sb105 remitos.
SOLO LECTURA.
"""

import pyodbc
from datetime import date, datetime

DSN = "MSPA"
OUTPUT_FILE = "taginfo_v20.txt"
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

    log(f"TagInfo v20 — {datetime.now()}")
    log(f"DSN: {DSN}  |  Fecha: {today}  |  SOLO LECTURA")
    log("=" * 70)

    conn = get_conn()
    cur = conn.cursor()
    log("Conexión OK\n")

    # ============================================================
    # 1. kzlsdru distribution for aufkstat=0 posstat=0
    # ============================================================
    log("=== kzlsdru dist para aufkstat=0 posstat=0 ===")
    for r in run(cur, "kzlsdru dist aufkstat0", f"""
        SELECT p.kzlsdru, COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND h.aufkstat = 0 AND p.posstat = 0 AND p.kzerl = '0'
        GROUP BY p.kzlsdru
        ORDER BY p.kzlsdru
    """):
        log(f"  kzlsdru={r[0]}  ords={r[1]}  pos={r[2]}  val={r[3]}")

    # ============================================================
    # 2. BLOQUEADOS + BACKORDERS — excluyendo kzlsdru=2
    #    (ordenes con remito ya impreso van a "Remitos" row)
    # ============================================================
    log("\n=== BLOQUEADOS/BACKORDERS sin kzlsdru=2 ===")

    kredlim_rows = run(cur, "kredlim per kdnr", f"""
        SELECT kdnr, kredlim FROM kund WHERE firma = {FIRMA} AND kredlim > 0
    """)
    kredlim_map = {r[0]: r[1] for r in kredlim_rows}

    # Total open per customer — solo ordenes sin remito impreso (kzlsdru <> 2)
    totals_no_ls = run(cur, "kdnr totals kzlsdru<>2", f"""
        SELECT h.kdnr, SUM(p.poswert) total_open
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND h.aufkstat = 0 AND p.posstat = 0 AND p.kzerl = '0'
          AND p.kzlsdru <> 2
        GROUP BY h.kdnr
    """)
    log(f"  Customers aufkstat=0 kzlsdru<>2: {len(totals_no_ls)}")

    over_ls = [r[0] for r in totals_no_ls
               if kredlim_map.get(r[0], 0) > 0 and r[1] is not None and r[1] > kredlim_map.get(r[0], 0)]
    under_ls = [r[0] for r in totals_no_ls
                if not (kredlim_map.get(r[0], 0) > 0 and r[1] is not None and r[1] > kredlim_map.get(r[0], 0))]
    log(f"  over_limit={len(over_ls)}  under_limit={len(under_ls)}")

    if over_ls:
        in_o = ','.join(str(k) for k in over_ls)
        for r in run(cur, "BLOQUEADOS kzlsdru<>2", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p
            WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
              AND h.auftrag = p.auftrag
              AND h.aufkstat = 0 AND p.posstat = 0 AND p.kzerl = '0'
              AND p.kzlsdru <> 2
              AND h.kdnr IN ({in_o})
        """):
            log(f"  BLOQUEADOS: ords={r[0]}  pos={r[1]}  val={r[2]}")

    if under_ls:
        in_u = ','.join(str(k) for k in under_ls)
        for r in run(cur, "BACKORDERS kzlsdru<>2", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p
            WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
              AND h.auftrag = p.auftrag
              AND h.aufkstat = 0 AND p.posstat = 0 AND p.kzerl = '0'
              AND p.kzlsdru <> 2
              AND h.kdnr IN ({in_u})
        """):
            log(f"  BACKORDERS: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # REMITOS = aufkstat=0 con kzlsdru=2
    for r in run(cur, "REMITOS kzlsdru=2 aufkstat0", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND h.aufkstat = 0 AND p.posstat = 0 AND p.kzerl = '0'
          AND p.kzlsdru = 2
    """):
        log(f"  REMITOS (aufkstat=0 kzlsdru=2): ords={r[0]}  pos={r[1]}  val={r[2]}")

    # ============================================================
    # 3. sb105 — estructura y remitos abiertos
    # ============================================================
    log("\n=== sb105 — COLUMNAS ===")
    for r in run(cur, "sb105 cols", """
        SELECT c.colno, c.colname, c.coltype
        FROM syscolumns c, systables t
        WHERE c.tabid = t.tabid AND t.tabname = 'sb105'
        ORDER BY c.colno
    """):
        log(f"  [{r[0]}] {r[1]}  type={r[2]}")

    log("\n=== sb105 — TOTALES ===")
    for r in run(cur, "sb105 count", f"SELECT COUNT(*) FROM sb105 WHERE firma = {FIRMA}"):
        log(f"  sb105 total rows: {r[0]}")

    # sb104 liefstat distribution
    log("\n=== sb104 liefstat dist ===")
    for r in run(cur, "sb104 liefstat dist", f"""
        SELECT liefstat, COUNT(*) cnt
        FROM sb104 WHERE firma = {FIRMA}
        GROUP BY liefstat ORDER BY liefstat
    """):
        log(f"  liefstat={r[0]}  cnt={r[1]}")

    # sb104 open lieferscheine (liefstat=0 or small value = not fully processed)
    for r in run(cur, "sb104 liefstat=0", f"""
        SELECT COUNT(*) docs, SUM(liefwe) val
        FROM sb104 WHERE firma = {FIRMA} AND liefstat = 0
    """):
        log(f"  sb104 liefstat=0: docs={r[0]}  val={r[1]}")

    for r in run(cur, "sb104 liefstat=1", f"""
        SELECT COUNT(*) docs, SUM(liefwe) val
        FROM sb104 WHERE firma = {FIRMA} AND liefstat = 1
    """):
        log(f"  sb104 liefstat=1: docs={r[0]}  val={r[1]}")

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

    # Recompute fresh at snapshot time
    totals_snap = run(cur, "snap kdnr totals kzlsdru<>2", f"""
        SELECT h.kdnr, SUM(p.poswert) total_open
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND h.aufkstat = 0 AND p.posstat = 0 AND p.kzerl = '0'
          AND p.kzlsdru <> 2
        GROUP BY h.kdnr
    """)
    over_snap = [r[0] for r in totals_snap
                 if kredlim_map.get(r[0], 0) > 0 and r[1] is not None and r[1] > kredlim_map.get(r[0], 0)]
    under_snap = [r[0] for r in totals_snap
                  if not (kredlim_map.get(r[0], 0) > 0 and r[1] is not None and r[1] > kredlim_map.get(r[0], 0))]

    if over_snap:
        in_o2 = ','.join(str(k) for k in over_snap)
        for r in run(cur, "snap bloqueados", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p
            WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
              AND h.auftrag = p.auftrag
              AND h.aufkstat = 0 AND p.posstat = 0 AND p.kzerl = '0'
              AND p.kzlsdru <> 2
              AND h.kdnr IN ({in_o2})
        """):
            log(f"  [BLOQUEADOS] ords={r[0]}  pos={r[1]}  val={r[2]}")

    if under_snap:
        in_u2 = ','.join(str(k) for k in under_snap)
        for r in run(cur, "snap backorders", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p
            WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
              AND h.auftrag = p.auftrag
              AND h.aufkstat = 0 AND p.posstat = 0 AND p.kzerl = '0'
              AND p.kzlsdru <> 2
              AND h.kdnr IN ({in_u2})
        """):
            log(f"  [BACKORDERS] ords={r[0]}  pos={r[1]}  val={r[2]}")

    for r in run(cur, "snap remitos", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND h.aufkstat = 0 AND p.posstat = 0 AND p.kzerl = '0'
          AND p.kzlsdru = 2
    """):
        log(f"  [REMITOS kzlsdru=2 aufkstat=0] ords={r[0]}  pos={r[1]}  val={r[2]}")

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

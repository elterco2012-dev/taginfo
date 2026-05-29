"""
TagInfo v21 — sb105 kzerl remitos, f090 headers direct, per-order kredlim.
SOLO LECTURA.
"""

import pyodbc
from datetime import date, datetime

DSN = "MSPA"
OUTPUT_FILE = "taginfo_v21.txt"
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

    log(f"TagInfo v21 — {datetime.now()}")
    log(f"DSN: {DSN}  |  Fecha: {today}  |  SOLO LECTURA")
    log("=" * 70)

    conn = get_conn()
    cur = conn.cursor()
    log("Conexión OK\n")

    # ============================================================
    # 1. REMITOS — sb105 con kzerl='0'
    # ============================================================
    log("=== REMITOS — sb105 kzerl='0' ===")

    # kzerl distribution en sb105
    for r in run(cur, "sb105 kzerl dist", f"""
        SELECT kzerl, COUNT(*) cnt
        FROM sb105 WHERE firma = {FIRMA}
        GROUP BY kzerl ORDER BY kzerl
    """):
        log(f"  sb105.kzerl={r[0]}  cnt={r[1]}")

    # Remitos abiertos: sb104 header + sb105 posiciones abiertas
    for r in run(cur, "remitos sb104+sb105 kzerl=0", f"""
        SELECT COUNT(DISTINCT s5.liefnr) docs, COUNT(*) pos, SUM(s5.liefposwe) val
        FROM sb104 s4, sb105 s5
        WHERE s4.firma = {FIRMA} AND s5.firma = {FIRMA}
          AND s4.liefnr = s5.liefnr
          AND s5.kzerl = '0'
    """):
        log(f"  sb104+sb105 kzerl='0': docs={r[0]}  pos={r[1]}  val={r[2]}")

    # Sin join a sb104
    for r in run(cur, "remitos sb105 solo kzerl=0", f"""
        SELECT COUNT(DISTINCT liefnr) docs, COUNT(*) pos, SUM(liefposwe) val
        FROM sb105 WHERE firma = {FIRMA} AND kzerl = '0'
    """):
        log(f"  sb105 solo kzerl='0': docs={r[0]}  pos={r[1]}  val={r[2]}")

    # sb105 kzerl distribution detail
    for r in run(cur, "sb105 kzerl='1'", f"""
        SELECT COUNT(DISTINCT liefnr) docs, COUNT(*) pos
        FROM sb105 WHERE firma = {FIRMA} AND kzerl = '1'
    """):
        log(f"  sb105 kzerl='1': docs={r[0]}  pos={r[1]}")

    # ============================================================
    # 2. f090 HEADERS DIRECTO — aufkstat=0 sin join a f092
    # ============================================================
    log("\n=== f090 headers aufkstat=0 ===")

    # f090 kzerl distribution
    for r in run(cur, "f090 kzerl dist", f"""
        SELECT kzerl, COUNT(*) cnt FROM f090
        WHERE firma = {FIRMA} AND aufkstat = 0
        GROUP BY kzerl ORDER BY kzerl
    """):
        log(f"  f090 aufkstat=0 kzerl={r[0]}  cnt={r[1]}")

    # f090 aufkstat=0 headers total
    for r in run(cur, "f090 aufkstat=0 kzerl0", f"""
        SELECT COUNT(*) ords FROM f090
        WHERE firma = {FIRMA} AND aufkstat = 0 AND kzerl = '0'
    """):
        log(f"  f090 aufkstat=0 kzerl='0' headers: ords={r[0]}")

    # f090 aufkstat=0 kzerl='0' con posiciones en f092
    for r in run(cur, "f090+f092 aufkstat0 todos posstat", f"""
        SELECT p.posstat, COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND h.aufkstat = 0 AND h.kzerl = '0' AND p.kzerl = '0'
        GROUP BY p.posstat ORDER BY p.posstat
    """):
        log(f"  aufkstat=0 h.kzerl='0' posstat={r[0]}  ords={r[1]}  pos={r[2]}  val={r[3]}")

    # ============================================================
    # 3. BLOQUEADOS — check por-orden (no por cliente acumulado)
    # ============================================================
    log("\n=== BLOQUEADOS — per-order kredlim check ===")

    kredlim_rows = run(cur, "kredlim per kdnr", f"""
        SELECT kdnr, kredlim FROM kund WHERE firma = {FIRMA} AND kredlim > 0
    """)
    kredlim_map = {r[0]: r[1] for r in kredlim_rows}

    # Per-order total (sum of positions for that specific order)
    order_rows = run(cur, "per-order total", f"""
        SELECT h.auftrag, h.kdnr, SUM(p.poswert) order_total
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND h.aufkstat = 0 AND p.posstat = 0 AND p.kzerl = '0'
        GROUP BY h.auftrag, h.kdnr
    """)
    log(f"  Per-order rows: {len(order_rows)}")

    over_order = [(r[0], r[1]) for r in order_rows
                  if kredlim_map.get(r[1], 0) > 0 and r[2] is not None and r[2] > kredlim_map.get(r[1], 0)]
    under_order = [(r[0], r[1]) for r in order_rows
                   if not (kredlim_map.get(r[1], 0) > 0 and r[2] is not None and r[2] > kredlim_map.get(r[1], 0))]

    log(f"  per-order over_limit={len(over_order)}  under_limit={len(under_order)}")

    if over_order:
        in_o = ','.join(str(r[0]) for r in over_order)
        for r in run(cur, "BLOQUEADOS per-order", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p
            WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
              AND h.auftrag = p.auftrag
              AND h.aufkstat = 0 AND p.posstat = 0 AND p.kzerl = '0'
              AND h.auftrag IN ({in_o})
        """):
            log(f"  BLOQUEADOS (per-order): ords={r[0]}  pos={r[1]}  val={r[2]}")

    if under_order:
        in_u = ','.join(str(r[0]) for r in under_order)
        for r in run(cur, "BACKORDERS per-order", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p
            WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
              AND h.auftrag = p.auftrag
              AND h.aufkstat = 0 AND p.posstat = 0 AND p.kzerl = '0'
              AND h.auftrag IN ({in_u})
        """):
            log(f"  BACKORDERS (per-order): ords={r[0]}  pos={r[1]}  val={r[2]}")

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

    # Remitos from sb105
    for r in run(cur, "snap remitos sb105", f"""
        SELECT COUNT(DISTINCT liefnr) docs, COUNT(*) pos, SUM(liefposwe) val
        FROM sb105 WHERE firma = {FIRMA} AND kzerl = '0'
    """):
        log(f"  [REMITOS sb105 kzerl='0'] docs={r[0]}  pos={r[1]}  val={r[2]}")

    # Bloqueados/backorders fresh at snapshot
    order_snap = run(cur, "snap per-order totals", f"""
        SELECT h.auftrag, h.kdnr, SUM(p.poswert) order_total
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND h.aufkstat = 0 AND p.posstat = 0 AND p.kzerl = '0'
        GROUP BY h.auftrag, h.kdnr
    """)
    over_s = [r[0] for r in order_snap
              if kredlim_map.get(r[1], 0) > 0 and r[2] is not None and r[2] > kredlim_map.get(r[1], 0)]
    under_s = [r[0] for r in order_snap
               if not (kredlim_map.get(r[1], 0) > 0 and r[2] is not None and r[2] > kredlim_map.get(r[1], 0))]

    if over_s:
        for r in run(cur, "snap bloqueados", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p
            WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
              AND h.auftrag = p.auftrag
              AND h.aufkstat = 0 AND p.posstat = 0 AND p.kzerl = '0'
              AND h.auftrag IN ({','.join(str(x) for x in over_s)})
        """):
            log(f"  [BLOQUEADOS per-order] ords={r[0]}  pos={r[1]}  val={r[2]}")

    if under_s:
        for r in run(cur, "snap backorders", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p
            WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
              AND h.auftrag = p.auftrag
              AND h.aufkstat = 0 AND p.posstat = 0 AND p.kzerl = '0'
              AND h.auftrag IN ({','.join(str(x) for x in under_s)})
        """):
            log(f"  [BACKORDERS per-order] ords={r[0]}  pos={r[1]}  val={r[2]}")

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

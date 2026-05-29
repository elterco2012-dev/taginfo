"""
TagInfo v24 — remitos via sb105+f092 posstat=8, backords aufkstat=0 only.
SOLO LECTURA.
"""

import pyodbc
from datetime import date, datetime

DSN = "MSPA"
OUTPUT_FILE = "taginfo_v24.txt"
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

    log(f"TagInfo v24 — {datetime.now()}")
    log(f"DSN: {DSN}  |  Fecha: {today}  |  SOLO LECTURA")
    log("=" * 70)

    conn = get_conn()
    cur = conn.cursor()
    log("Conexión OK\n")

    kredlim_rows = run(cur, "kredlim per kdnr", f"""
        SELECT kdnr, kredlim FROM kund WHERE firma = {FIRMA} AND kredlim > 0
    """)
    kredlim_map = {r[0]: r[1] for r in kredlim_rows}

    # ============================================================
    # 1. REMITOS — sb105 linked to f092 posstat=8
    # ============================================================
    log("=== REMITOS — sb105 join f092 posstat=8 ===")

    # sb105 JOIN f092 where posstat=8
    for r in run(cur, "sb105+f092 posstat=8", f"""
        SELECT COUNT(DISTINCT s5.liefnr) docs, COUNT(*) pos, SUM(s5.liefposwe) val
        FROM sb105 s5, f092 p
        WHERE s5.firma = {FIRMA} AND p.firma = {FIRMA}
          AND s5.auftrag = p.auftrag AND s5.posnr = p.posnr
          AND p.posstat = 8 AND p.kzerl = '0'
    """):
        log(f"  sb105+f092 posstat=8: docs={r[0]}  pos={r[1]}  val={r[2]}")

    # sb105 JOIN f092 JOIN f090 posstat=8
    for r in run(cur, "sb105+f092+f090 posstat=8", f"""
        SELECT COUNT(DISTINCT s5.liefnr) docs, COUNT(*) pos, SUM(s5.liefposwe) val
        FROM sb105 s5, f092 p, f090 h
        WHERE s5.firma = {FIRMA} AND p.firma = {FIRMA} AND h.firma = {FIRMA}
          AND s5.auftrag = p.auftrag AND s5.posnr = p.posnr
          AND h.auftrag = p.auftrag
          AND p.posstat = 8 AND p.kzerl = '0'
    """):
        log(f"  sb105+f092+f090 posstat=8: docs={r[0]}  pos={r[1]}  val={r[2]}")

    # sb105 JOIN f090 aufkstat=8
    for r in run(cur, "sb105+f090 aufkstat=8", f"""
        SELECT COUNT(DISTINCT s5.liefnr) docs, COUNT(*) pos, SUM(s5.liefposwe) val
        FROM sb105 s5, f090 h
        WHERE s5.firma = {FIRMA} AND h.firma = {FIRMA}
          AND s5.auftrag = h.auftrag
          AND h.aufkstat = 8
    """):
        log(f"  sb105+f090 aufkstat=8: docs={r[0]}  pos={r[1]}  val={r[2]}")

    # sb105 JOIN f090 aufkstat=8 belegart=11
    for r in run(cur, "sb105+f090 aufkstat=8 bel11", f"""
        SELECT COUNT(DISTINCT s5.liefnr) docs, COUNT(*) pos, SUM(s5.liefposwe) val
        FROM sb105 s5, f090 h
        WHERE s5.firma = {FIRMA} AND h.firma = {FIRMA}
          AND s5.auftrag = h.auftrag
          AND h.aufkstat = 8 AND h.belegart = 11
    """):
        log(f"  sb105+f090 aufkstat=8 bel=11: docs={r[0]}  pos={r[1]}  val={r[2]}")

    # sb105 JOIN f092 posstat=8 AND sb105.kzerl='0'
    for r in run(cur, "sb105+f092 posstat=8 kzerl0", f"""
        SELECT COUNT(DISTINCT s5.liefnr) docs, COUNT(*) pos, SUM(s5.liefposwe) val
        FROM sb105 s5, f092 p
        WHERE s5.firma = {FIRMA} AND p.firma = {FIRMA}
          AND s5.auftrag = p.auftrag AND s5.posnr = p.posnr
          AND p.posstat = 8 AND p.kzerl = '0'
          AND s5.kzerl = '0'
    """):
        log(f"  sb105+f092 posstat=8 s5.kzerl=0: docs={r[0]}  pos={r[1]}  val={r[2]}")

    # ============================================================
    # 2. BACKORDERS/BLOQUEADOS — aufkstat=0 ONLY
    # ============================================================
    log("\n=== BACKORDERS/BLOQUEADOS — aufkstat=0 ONLY ===")

    # Base: aufkstat=0, belegart=11, termin<=TODAY, liefme<>0
    totals_0 = run(cur, "per-kdnr aufkstat=0", f"""
        SELECT h.kdnr, SUM(p.poswert) total_open
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND p.termin <= TODAY AND p.liefme <> 0
          AND h.belegart = 11 AND h.aufkstat = 0
        GROUP BY h.kdnr
    """)
    log(f"  Customers aufkstat=0: {len(totals_0)}")

    over_0 = [r[0] for r in totals_0
              if kredlim_map.get(r[0], 0) > 0 and r[1] is not None and r[1] > kredlim_map.get(r[0], 0)]
    under_0 = [r[0] for r in totals_0
               if not (kredlim_map.get(r[0], 0) > 0 and r[1] is not None and r[1] > kredlim_map.get(r[0], 0))]
    log(f"  over={len(over_0)}  under={len(under_0)}")

    if over_0:
        for r in run(cur, "BLOQUEADOS aufkstat=0", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p
            WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
              AND h.auftrag = p.auftrag
              AND p.termin <= TODAY AND p.liefme <> 0
              AND h.belegart = 11 AND h.aufkstat = 0
              AND h.kdnr IN ({','.join(str(k) for k in over_0)})
        """):
            log(f"  BLOQUEADOS (aufkstat=0): ords={r[0]}  pos={r[1]}  val={r[2]}")

    if under_0:
        for r in run(cur, "BACKORDERS aufkstat=0", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p
            WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
              AND h.auftrag = p.auftrag
              AND p.termin <= TODAY AND p.liefme <> 0
              AND h.belegart = 11 AND h.aufkstat = 0
              AND h.kdnr IN ({','.join(str(k) for k in under_0)})
        """):
            log(f"  BACKORDERS (aufkstat=0): ords={r[0]}  pos={r[1]}  val={r[2]}")

    # Also try: aufkstat=0, ALL termin (no termin filter), belegart=11, liefme<>0
    log("\n--- sin filtro de termin ---")
    totals_nt = run(cur, "per-kdnr aufkstat=0 no termin", f"""
        SELECT h.kdnr, SUM(p.poswert) total_open
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND p.liefme <> 0 AND h.belegart = 11 AND h.aufkstat = 0
        GROUP BY h.kdnr
    """)
    log(f"  Customers (no termin): {len(totals_nt)}")

    over_nt = [r[0] for r in totals_nt
               if kredlim_map.get(r[0], 0) > 0 and r[1] is not None and r[1] > kredlim_map.get(r[0], 0)]
    under_nt = [r[0] for r in totals_nt
                if not (kredlim_map.get(r[0], 0) > 0 and r[1] is not None and r[1] > kredlim_map.get(r[0], 0))]
    log(f"  over={len(over_nt)}  under={len(under_nt)}")

    if over_nt:
        for r in run(cur, "BLOQUEADOS no termin", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p
            WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
              AND h.auftrag = p.auftrag
              AND p.liefme <> 0 AND h.belegart = 11 AND h.aufkstat = 0
              AND h.kdnr IN ({','.join(str(k) for k in over_nt)})
        """):
            log(f"  BLOQUEADOS (no termin): ords={r[0]}  pos={r[1]}  val={r[2]}")

    if under_nt:
        for r in run(cur, "BACKORDERS no termin", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p
            WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
              AND h.auftrag = p.auftrag
              AND p.liefme <> 0 AND h.belegart = 11 AND h.aufkstat = 0
              AND h.kdnr IN ({','.join(str(k) for k in under_nt)})
        """):
            log(f"  BACKORDERS (no termin): ords={r[0]}  pos={r[1]}  val={r[2]}")

    # ============================================================
    # 3. SNAPSHOT COMPLETO
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

    # Remitos: sb105+f092 posstat=8
    for r in run(cur, "snap remitos", f"""
        SELECT COUNT(DISTINCT s5.liefnr) docs, COUNT(*) pos, SUM(s5.liefposwe) val
        FROM sb105 s5, f092 p
        WHERE s5.firma = {FIRMA} AND p.firma = {FIRMA}
          AND s5.auftrag = p.auftrag AND s5.posnr = p.posnr
          AND p.posstat = 8 AND p.kzerl = '0'
    """):
        log(f"  [REMITOS sb105+posstat=8] docs={r[0]}  pos={r[1]}  val={r[2]}")

    # Bloqueados/backorders aufkstat=0 fresh
    totals_snap = run(cur, "snap per-kdnr", f"""
        SELECT h.kdnr, SUM(p.poswert) total_open
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND p.liefme <> 0 AND h.belegart = 11 AND h.aufkstat = 0
        GROUP BY h.kdnr
    """)
    over_s = [r[0] for r in totals_snap
              if kredlim_map.get(r[0], 0) > 0 and r[1] is not None and r[1] > kredlim_map.get(r[0], 0)]
    under_s = [r[0] for r in totals_snap
               if not (kredlim_map.get(r[0], 0) > 0 and r[1] is not None and r[1] > kredlim_map.get(r[0], 0))]

    if over_s:
        for r in run(cur, "snap bloqueados", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p
            WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
              AND h.auftrag = p.auftrag
              AND p.liefme <> 0 AND h.belegart = 11 AND h.aufkstat = 0
              AND h.kdnr IN ({','.join(str(x) for x in over_s)})
        """):
            log(f"  [BLOQUEADOS] ords={r[0]}  pos={r[1]}  val={r[2]}")

    if under_s:
        for r in run(cur, "snap backorders", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p
            WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
              AND h.auftrag = p.auftrag
              AND p.liefme <> 0 AND h.belegart = 11 AND h.aufkstat = 0
              AND h.kdnr IN ({','.join(str(x) for x in under_s)})
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

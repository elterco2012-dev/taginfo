"""
TagInfo v27 — sb105 kzerl='0' join f090 por aufkstat, credlim any-belegart.
SOLO LECTURA.
"""

import pyodbc
from datetime import date, datetime

DSN = "MSPA"
OUTPUT_FILE = "taginfo_v27.txt"
FIRMA = 1


def get_conn():
    return pyodbc.connect(f"DSN={DSN};", autocommit=True)


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

    log(f"TagInfo v27 — {datetime.now()}")
    log(f"DSN: {DSN}  |  Fecha: {today}  |  SOLO LECTURA")
    log("=" * 70)

    conn = get_conn()
    cur = conn.cursor()
    log("Conexión OK\n")

    kredlim_rows = run(cur, "kredlim", f"SELECT kdnr, kredlim FROM kund WHERE firma={FIRMA} AND kredlim > 0")
    kredlim_map = {r[0]: r[1] for r in kredlim_rows}

    # ============================================================
    # 1. REMITOS — sb105 kzerl='0' JOIN f090 por aufkstat
    # ============================================================
    log("=== REMITOS — sb105 kzerl=0 JOIN f090 por aufkstat ===")

    # Distribution by aufkstat
    log("\nsb105 kzerl=0 JOIN f090 — aufkstat distribution:")
    for r in run(cur, "sb105 kzerl=0 aufkstat dist", f"""
        SELECT h.aufkstat, COUNT(DISTINCT s5.liefnr) docs, COUNT(*) pos, SUM(s5.liefposwe) val
        FROM sb105 s5, f090 h
        WHERE s5.firma={FIRMA} AND h.firma={FIRMA}
          AND s5.auftrag=h.auftrag
          AND s5.kzerl='0'
        GROUP BY h.aufkstat ORDER BY h.aufkstat
    """):
        log(f"  aufkstat={r[0]}  docs={r[1]}  pos={r[2]}  val={r[3]}")

    # aufkstat=0 specifically
    for r in run(cur, "sb105 kzerl=0 aufkstat=0", f"""
        SELECT COUNT(DISTINCT s5.liefnr) docs, COUNT(*) pos, SUM(s5.liefposwe) val
        FROM sb105 s5, f090 h
        WHERE s5.firma={FIRMA} AND h.firma={FIRMA}
          AND s5.auftrag=h.auftrag
          AND s5.kzerl='0' AND h.aufkstat=0
    """):
        log(f"  sb105 kzerl=0 aufkstat=0: docs={r[0]}  pos={r[1]}  val={r[2]}")

    # aufkstat=8 specifically
    for r in run(cur, "sb105 kzerl=0 aufkstat=8", f"""
        SELECT COUNT(DISTINCT s5.liefnr) docs, COUNT(*) pos, SUM(s5.liefposwe) val
        FROM sb105 s5, f090 h
        WHERE s5.firma={FIRMA} AND h.firma={FIRMA}
          AND s5.auftrag=h.auftrag
          AND s5.kzerl='0' AND h.aufkstat=8
    """):
        log(f"  sb105 kzerl=0 aufkstat=8: docs={r[0]}  pos={r[1]}  val={r[2]}")

    # aufkstat NOT IN (9) — not yet invoiced
    for r in run(cur, "sb105 kzerl=0 aufkstat<>9", f"""
        SELECT COUNT(DISTINCT s5.liefnr) docs, COUNT(*) pos, SUM(s5.liefposwe) val
        FROM sb105 s5, f090 h
        WHERE s5.firma={FIRMA} AND h.firma={FIRMA}
          AND s5.auftrag=h.auftrag
          AND s5.kzerl='0' AND h.aufkstat<>9
    """):
        log(f"  sb105 kzerl=0 aufkstat<>9: docs={r[0]}  pos={r[1]}  val={r[2]}")

    # Also try join via f092 (through posstat)
    for r in run(cur, "sb105+f092 kzerl=0 posstat=0", f"""
        SELECT COUNT(DISTINCT s5.liefnr) docs, COUNT(*) pos, SUM(s5.liefposwe) val
        FROM sb105 s5, f092 p
        WHERE s5.firma={FIRMA} AND p.firma={FIRMA}
          AND s5.auftrag=p.auftrag AND s5.posnr=p.posnr
          AND s5.kzerl='0' AND p.posstat=0
    """):
        log(f"  sb105+f092 s5.kzerl=0 p.posstat=0: docs={r[0]}  pos={r[1]}  val={r[2]}")

    # sb105 kzerl=0 + f092 posstat=0 + f090 aufkstat=0
    for r in run(cur, "sb105+f092+f090 kzerl=0 posstat=0 aufkstat=0", f"""
        SELECT COUNT(DISTINCT s5.liefnr) docs, COUNT(*) pos, SUM(s5.liefposwe) val
        FROM sb105 s5, f092 p, f090 h
        WHERE s5.firma={FIRMA} AND p.firma={FIRMA} AND h.firma={FIRMA}
          AND s5.auftrag=p.auftrag AND s5.posnr=p.posnr
          AND h.auftrag=p.auftrag
          AND s5.kzerl='0' AND p.posstat=0 AND h.aufkstat=0
    """):
        log(f"  sb105+f092+f090 kzerl=0 posstat=0 aufkstat=0: docs={r[0]}  pos={r[1]}  val={r[2]}")

    # sb105 kzerl=0 distribution by f092.posstat
    log("\nsb105 kzerl=0 + f092 posstat distribution:")
    for r in run(cur, "sb105 kzerl=0 f092 posstat dist", f"""
        SELECT p.posstat, COUNT(DISTINCT s5.liefnr) docs, COUNT(*) pos, SUM(s5.liefposwe) val
        FROM sb105 s5, f092 p
        WHERE s5.firma={FIRMA} AND p.firma={FIRMA}
          AND s5.auftrag=p.auftrag AND s5.posnr=p.posnr
          AND s5.kzerl='0'
        GROUP BY p.posstat ORDER BY p.posstat
    """):
        log(f"  posstat={r[0]}  docs={r[1]}  pos={r[2]}  val={r[3]}")

    # ============================================================
    # 2. BACKORDERS/BLOQUEADOS — credlim check from ALL belegart
    # ============================================================
    log("\n=== BLOQUEADOS/BACKORDERS — credlim ALL belegart, count bel=11 ===")

    # Step 1: per-customer total using ALL belegart orders (any aufkstat<>8)
    totals_all_bel = run(cur, "per-kdnr ALL belegart", f"""
        SELECT h.kdnr, SUM(p.poswert) total_open
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.kzerl='0'
          AND h.aufkstat<>8
        GROUP BY h.kdnr
    """)

    over_ab = [r[0] for r in totals_all_bel if kredlim_map.get(r[0],0)>0 and r[1] and r[1]>kredlim_map.get(r[0],0)]
    under_ab = [r[0] for r in totals_all_bel if not(kredlim_map.get(r[0],0)>0 and r[1] and r[1]>kredlim_map.get(r[0],0))]
    log(f"  ALL belegart customers: {len(totals_all_bel)}  over={len(over_ab)}  under={len(under_ab)}")

    # Count belegart=11 orders for over-limit customers
    if over_ab:
        for r in run(cur, "BLOQ count bel=11 only", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.aufkstat<>8 AND h.belegart=11
              AND h.kdnr IN ({','.join(str(k) for k in over_ab)})
        """):
            log(f"  BLOQUEADOS (all-bel credlim, count bel=11): ords={r[0]}  pos={r[1]}  val={r[2]}")

    if under_ab:
        for r in run(cur, "BACK count bel=11 only", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.aufkstat<>8 AND h.belegart=11
              AND h.kdnr IN ({','.join(str(k) for k in under_ab)})
        """):
            log(f"  BACKORDERS (all-bel credlim, count bel=11): ords={r[0]}  pos={r[1]}  val={r[2]}")

    # Also try: credlim from ALL open (any aufkstat), count bel=11 aufkstat<>8
    log("\n--- credlim from ALL aufkstat, count bel=11 aufkstat<>8 ---")
    totals_any = run(cur, "per-kdnr any aufkstat", f"""
        SELECT h.kdnr, SUM(p.poswert) total_open
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.kzerl='0'
        GROUP BY h.kdnr
    """)
    over_any = [r[0] for r in totals_any if kredlim_map.get(r[0],0)>0 and r[1] and r[1]>kredlim_map.get(r[0],0)]
    under_any = [r[0] for r in totals_any if not(kredlim_map.get(r[0],0)>0 and r[1] and r[1]>kredlim_map.get(r[0],0))]
    log(f"  ANY aufkstat customers: {len(totals_any)}  over={len(over_any)}  under={len(under_any)}")

    if over_any:
        for r in run(cur, "BLOQ any-aufkstat credlim bel=11 count", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.aufkstat<>8 AND h.belegart=11
              AND h.kdnr IN ({','.join(str(k) for k in over_any)})
        """):
            log(f"  BLOQUEADOS (any credlim, bel=11): ords={r[0]}  pos={r[1]}  val={r[2]}")

    if under_any:
        for r in run(cur, "BACK any-aufkstat credlim bel=11 count", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.aufkstat<>8 AND h.belegart=11
              AND h.kdnr IN ({','.join(str(k) for k in under_any)})
        """):
            log(f"  BACKORDERS (any credlim, bel=11): ords={r[0]}  pos={r[1]}  val={r[2]}")

    # ============================================================
    # 3. SNAPSHOT COMPLETO
    # ============================================================
    log("\n=== SNAPSHOT COMPLETO ===")
    ts = datetime.now()

    for r in run(cur, "snap produccion", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND h.aufkstat=2 AND p.posstat=2 AND p.kzerl='0'
    """):
        log(f"  [PRODUCCION] ords={r[0]}  pos={r[1]}  val={r[2]}")

    # Remitos best candidate at snapshot time
    for r in run(cur, "snap remitos sb105 kzerl=0 f090", f"""
        SELECT h.aufkstat, COUNT(DISTINCT s5.liefnr) docs, COUNT(*) pos, SUM(s5.liefposwe) val
        FROM sb105 s5, f090 h
        WHERE s5.firma={FIRMA} AND h.firma={FIRMA}
          AND s5.auftrag=h.auftrag AND s5.kzerl='0'
        GROUP BY h.aufkstat ORDER BY h.aufkstat
    """):
        log(f"  [REMITOS by aufkstat] aufkstat={r[0]}  docs={r[1]}  pos={r[2]}  val={r[3]}")

    # Fresh bloqueados/backorders
    totals_snap = run(cur, "snap per-kdnr bel=11 aufkstat<>8", f"""
        SELECT h.kdnr, SUM(p.poswert) total_open
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.kzerl='0'
          AND h.aufkstat<>8 AND h.belegart=11
        GROUP BY h.kdnr
    """)
    over_s=[r[0] for r in totals_snap if kredlim_map.get(r[0],0)>0 and r[1] and r[1]>kredlim_map.get(r[0],0)]
    under_s=[r[0] for r in totals_snap if not(kredlim_map.get(r[0],0)>0 and r[1] and r[1]>kredlim_map.get(r[0],0))]
    if over_s:
        for r in run(cur, "snap bloqueados", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.aufkstat<>8 AND h.belegart=11
              AND h.kdnr IN ({','.join(str(x) for x in over_s)})
        """):
            log(f"  [BLOQUEADOS bel=11 aufkstat<>8] ords={r[0]}  pos={r[1]}  val={r[2]}")
    if under_s:
        for r in run(cur, "snap backorders", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.aufkstat<>8 AND h.belegart=11
              AND h.kdnr IN ({','.join(str(x) for x in under_s)})
        """):
            log(f"  [BACKORDERS bel=11 aufkstat<>8] ords={r[0]}  pos={r[1]}  val={r[2]}")

    for r in run(cur, "snap venta", f"""
        SELECT COUNT(DISTINCT renr) docs, COUNT(*) pos, SUM(netwert) val
        FROM sbas WHERE firma={FIRMA} AND redat=TODAY AND belegart IN (8,11)
    """):
        log(f"  [VENTA bel8+11] docs={r[0]}  pos={r[1]}  val={r[2]}")

    log(f"  Timestamp: {ts}")

    conn.close()

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\nListo → {OUTPUT_FILE}")


if __name__ == "__main__":
    main()

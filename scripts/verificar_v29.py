"""
TagInfo v29 — aufkstat=4 para Remitos, credlim bel(6,7,11) sobre aufkstat=0 para Backorders/Bloqueados.
SOLO LECTURA.
"""

import pyodbc
from datetime import date, datetime

DSN = "MSPA"
OUTPUT_FILE = "taginfo_v29.txt"
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

    log(f"TagInfo v29 — {datetime.now()}")
    log(f"DSN: {DSN}  |  Fecha: {today}  |  SOLO LECTURA")
    log("=" * 70)

    conn = get_conn()
    cur = conn.cursor()
    log("Conexión OK\n")

    kredlim_rows = run(cur, "kredlim", f"SELECT kdnr, kredlim FROM kund WHERE firma={FIRMA} AND kredlim > 0")
    kredlim_map = {r[0]: r[1] for r in kredlim_rows}

    # ============================================================
    # 1. REMITOS — aufkstat=4 hypothesis + other angles
    # ============================================================
    log("=== REMITOS — aufkstat=4 y otras hipótesis ===")

    # a) KEY TEST: sb105 kzerl=0 JOIN f090 aufkstat=4
    for r in run(cur, "sb105 kzerl=0 f090 aufkstat=4", f"""
        SELECT COUNT(DISTINCT s5.liefnr) docs, COUNT(*) pos, SUM(s5.liefposwe) val
        FROM sb105 s5, f090 h
        WHERE s5.firma={FIRMA} AND h.firma={FIRMA}
          AND s5.auftrag=h.auftrag
          AND s5.kzerl='0' AND h.aufkstat=4
    """):
        log(f"  sb105 kzerl=0 f090.aufkstat=4: docs={r[0]}  pos={r[1]}  val={r[2]}")

    # b) f090+f092 bel=11 aufkstat=4 kzerl=0
    for r in run(cur, "f092 bel=11 aufkstat=4 kzerl=0", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag
          AND h.belegart=11 AND h.aufkstat=4 AND p.kzerl='0'
    """):
        log(f"  f090+f092 bel=11 aufkstat=4 kzerl=0: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # c) f090 aufkstat=4 ALL belegart
    for r in run(cur, "f090 aufkstat=4 ALL bel kzerl=0", f"""
        SELECT h.belegart, COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag
          AND h.aufkstat=4 AND p.kzerl='0'
        GROUP BY h.belegart ORDER BY h.belegart
    """):
        log(f"  aufkstat=4 belegart={r[0]}  ords={r[1]}  pos={r[2]}  val={r[3]}")

    # d) sb105 kzerl=0 aufkstat=4 via belegart dist
    for r in run(cur, "sb105 kzerl=0 aufkstat=4 sb104 join", f"""
        SELECT COUNT(DISTINCT s5.liefnr) docs, COUNT(*) pos, SUM(s5.liefposwe) val
        FROM sb105 s5, f090 h, sb104 s4
        WHERE s5.firma={FIRMA} AND h.firma={FIRMA} AND s4.firma={FIRMA}
          AND s5.auftrag=h.auftrag AND s5.liefnr=s4.liefnr
          AND s5.kzerl='0' AND h.aufkstat=4
    """):
        log(f"  sb105 kzerl=0 f090.aufkstat=4 + sb104: docs={r[0]}  pos={r[1]}  val={r[2]}")

    # e) kzerl=None (12 docs) — what are they?
    for r in run(cur, "sb105 kzerl=NULL + f090 aufkstat", f"""
        SELECT h.aufkstat, COUNT(DISTINCT s5.liefnr) docs, COUNT(*) pos, SUM(s5.liefposwe) val
        FROM sb105 s5, f090 h
        WHERE s5.firma={FIRMA} AND h.firma={FIRMA}
          AND s5.auftrag=h.auftrag AND s5.kzerl IS NULL
        GROUP BY h.aufkstat ORDER BY h.aufkstat
    """):
        log(f"  sb105 kzerl=NULL aufkstat={r[0]}  docs={r[1]}  pos={r[2]}  val={r[3]}")

    # f) Combine: sb105 (kzerl=0 OR kzerl IS NULL) + aufkstat=4
    for r in run(cur, "sb105 kzerl=0 OR NULL + aufkstat=4", f"""
        SELECT COUNT(DISTINCT s5.liefnr) docs, COUNT(*) pos, SUM(s5.liefposwe) val
        FROM sb105 s5, f090 h
        WHERE s5.firma={FIRMA} AND h.firma={FIRMA}
          AND s5.auftrag=h.auftrag
          AND (s5.kzerl='0' OR s5.kzerl IS NULL) AND h.aufkstat=4
    """):
        log(f"  sb105 kzerl=0 OR NULL aufkstat=4: docs={r[0]}  pos={r[1]}  val={r[2]}")

    # g) What are aufkstat=4 orders? Show sample auftrag numbers and dates
    log("\n--- f090 aufkstat=4 bel=11 sample ---")
    for r in run(cur, "f090 aufkstat=4 bel=11 sample", f"""
        SELECT h.auftrag, h.kdnr, h.termin, h.aufkstat
        FROM f090 h
        WHERE h.firma={FIRMA} AND h.belegart=11 AND h.aufkstat=4
        ORDER BY h.auftrag
    """):
        log(f"  auftrag={r[0]}  kdnr={r[1]}  termin={r[2]}  aufkstat={r[3]}")

    # h) f092 posstat distribution for aufkstat=4
    log("\n--- f092 posstat dist for bel=11 aufkstat=4 ---")
    for r in run(cur, "f092 posstat dist aufkstat=4", f"""
        SELECT p.posstat, COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag
          AND h.belegart=11 AND h.aufkstat=4
        GROUP BY p.posstat ORDER BY p.posstat
    """):
        log(f"  aufkstat=4 posstat={r[0]}  ords={r[1]}  pos={r[2]}  val={r[3]}")

    # i) Try sbas belegart=41 (unknown belegart — could be remito type?)
    for r in run(cur, "sbas belegart=41 TODAY", f"""
        SELECT COUNT(DISTINCT renr) docs, COUNT(*) pos, SUM(netwert) val
        FROM sbas WHERE firma={FIRMA} AND redat=TODAY AND belegart=41
    """):
        log(f"  sbas belegart=41 TODAY: docs={r[0]}  pos={r[1]}  val={r[2]}")

    # j) sbas belegart=48 (315 docs = same as sb104 kzsofort=0)
    for r in run(cur, "sbas belegart=48 TODAY", f"""
        SELECT COUNT(DISTINCT renr) docs, COUNT(*) pos, SUM(netwert) val
        FROM sbas WHERE firma={FIRMA} AND redat=TODAY AND belegart=48
    """):
        log(f"  sbas belegart=48 TODAY: docs={r[0]}  pos={r[1]}  val={r[2]}")

    # k) Also try: sb105 kzerl=0 with f092 posstat=8 (posstat=8 = liefschein, 25 docs)
    #    but maybe without the date filter — and see if it gives ~18
    for r in run(cur, "sb105 kzerl=0 f092 posstat=8 f090 bel=11", f"""
        SELECT COUNT(DISTINCT s5.liefnr) docs, COUNT(*) pos, SUM(s5.liefposwe) val
        FROM sb105 s5, f092 p, f090 h
        WHERE s5.firma={FIRMA} AND p.firma={FIRMA} AND h.firma={FIRMA}
          AND s5.auftrag=p.auftrag AND s5.posnr=p.posnr
          AND p.auftrag=h.auftrag
          AND s5.kzerl='0' AND p.posstat=8 AND h.belegart=11
    """):
        log(f"  sb105 kzerl=0 posstat=8 bel=11: docs={r[0]}  pos={r[1]}  val={r[2]}")

    # l) sb105 kzerl=0 + f092 posstat IN (3,8) f090 bel=11
    for r in run(cur, "sb105 kzerl=0 f092 posstat IN(3,8) bel=11", f"""
        SELECT COUNT(DISTINCT s5.liefnr) docs, COUNT(*) pos, SUM(s5.liefposwe) val
        FROM sb105 s5, f092 p, f090 h
        WHERE s5.firma={FIRMA} AND p.firma={FIRMA} AND h.firma={FIRMA}
          AND s5.auftrag=p.auftrag AND s5.posnr=p.posnr
          AND p.auftrag=h.auftrag
          AND s5.kzerl='0' AND p.posstat IN (3,8) AND h.belegart=11
    """):
        log(f"  sb105 kzerl=0 posstat IN(3,8) bel=11: docs={r[0]}  pos={r[1]}  val={r[2]}")

    # m) f090 aufkstat=4 → sb105 liefnr count (not joining f092)
    for r in run(cur, "sb105 ANY kzerl f090 aufkstat=4", f"""
        SELECT s5.kzerl, COUNT(DISTINCT s5.liefnr) docs, COUNT(*) pos, SUM(s5.liefposwe) val
        FROM sb105 s5, f090 h
        WHERE s5.firma={FIRMA} AND h.firma={FIRMA}
          AND s5.auftrag=h.auftrag AND h.aufkstat=4
        GROUP BY s5.kzerl ORDER BY s5.kzerl
    """):
        log(f"  aufkstat=4 sb105 kzerl={r[0]}  docs={r[1]}  pos={r[2]}  val={r[3]}")

    # ============================================================
    # 2. BACKORDERS/BLOQUEADOS — bel(6,7,11) kredlim split on aufkstat=0
    # ============================================================
    log("\n=== BACKORDERS/BLOQUEADOS — kredlim bel(6,7,11), count aufkstat=0 ===")

    # Step 1: per-customer total using bel IN (6,7,11) aufkstat<>8
    totals_6711 = run(cur, "per-kdnr bel(6,7,11) aufkstat<>8", f"""
        SELECT h.kdnr, SUM(p.poswert) total_open
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.kzerl='0'
          AND h.aufkstat<>8 AND h.belegart IN (6,7,11)
        GROUP BY h.kdnr
    """)
    over_6711 = [r[0] for r in totals_6711 if kredlim_map.get(r[0],0)>0 and r[1] and r[1]>kredlim_map.get(r[0],0)]
    under_6711 = [r[0] for r in totals_6711 if not(kredlim_map.get(r[0],0)>0 and r[1] and r[1]>kredlim_map.get(r[0],0))]
    log(f"  bel(6,7,11) aufkstat<>8 customers={len(totals_6711)}  over={len(over_6711)}  under={len(under_6711)}")

    # a) BLOQUEADOS: over-kredlim, count bel=11 aufkstat=0 ONLY
    if over_6711:
        for r in run(cur, "BLOQ bel(6,7,11) kredlim → count bel=11 aufkstat=0", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.belegart=11 AND h.aufkstat=0
              AND h.kdnr IN ({','.join(str(k) for k in over_6711)})
        """):
            log(f"  BLOQ bel(6,7,11) kredlim → bel=11 aufkstat=0: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # b) BACKORDERS: under-kredlim, count bel=11 aufkstat=0 ONLY
    if under_6711:
        for r in run(cur, "BACK bel(6,7,11) kredlim → count bel=11 aufkstat=0", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.belegart=11 AND h.aufkstat=0
              AND h.kdnr IN ({','.join(str(k) for k in under_6711)})
        """):
            log(f"  BACK bel(6,7,11) kredlim → bel=11 aufkstat=0: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # c) BLOQUEADOS with bel=11 aufkstat<>8 (previous best = 38)
    if over_6711:
        for r in run(cur, "BLOQ bel(6,7,11) kredlim → bel=11 aufkstat<>8", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.belegart=11 AND h.aufkstat<>8
              AND h.kdnr IN ({','.join(str(k) for k in over_6711)})
        """):
            log(f"  BLOQ bel(6,7,11) kredlim → bel=11 aufkstat<>8: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # d) BACKORDERS: under-kredlim, bel=11 aufkstat<>8
    if under_6711:
        for r in run(cur, "BACK bel(6,7,11) kredlim → bel=11 aufkstat<>8", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.belegart=11 AND h.aufkstat<>8
              AND h.kdnr IN ({','.join(str(k) for k in under_6711)})
        """):
            log(f"  BACK bel(6,7,11) kredlim → bel=11 aufkstat<>8: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # e) Total bel=11 aufkstat=0 (all customers, no kredlim)
    for r in run(cur, "TOTAL bel=11 aufkstat=0", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.kzerl='0'
          AND h.belegart=11 AND h.aufkstat=0
    """):
        log(f"  TOTAL bel=11 aufkstat=0: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # f) aufkstat=0 breakdown by belegart
    log("\n--- f090 aufkstat=0 belegart dist ---")
    for r in run(cur, "f090 aufkstat=0 belegart dist", f"""
        SELECT h.belegart, COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos_kzerl0, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.kzerl='0'
          AND h.aufkstat=0
        GROUP BY h.belegart ORDER BY h.belegart
    """):
        log(f"  aufkstat=0 belegart={r[0]}  ords={r[1]}  pos={r[2]}  val={r[3]}")

    # g) Over-kredlim from bel=11 aufkstat<>8, count aufkstat=0 (alternative)
    totals_b11 = run(cur, "per-kdnr bel=11 aufkstat<>8", f"""
        SELECT h.kdnr, SUM(p.poswert) total_open
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.kzerl='0'
          AND h.aufkstat<>8 AND h.belegart=11
        GROUP BY h.kdnr
    """)
    over_b11 = [r[0] for r in totals_b11 if kredlim_map.get(r[0],0)>0 and r[1] and r[1]>kredlim_map.get(r[0],0)]
    under_b11 = [r[0] for r in totals_b11 if not(kredlim_map.get(r[0],0)>0 and r[1] and r[1]>kredlim_map.get(r[0],0))]
    log(f"  bel=11 aufkstat<>8 over={len(over_b11)}  under={len(under_b11)}")

    if over_b11:
        for r in run(cur, "BLOQ bel=11 kredlim → aufkstat=0", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.belegart=11 AND h.aufkstat=0
              AND h.kdnr IN ({','.join(str(k) for k in over_b11)})
        """):
            log(f"  BLOQ bel=11 kredlim → aufkstat=0: ords={r[0]}  pos={r[1]}  val={r[2]}")

    if under_b11:
        for r in run(cur, "BACK bel=11 kredlim → aufkstat=0", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.belegart=11 AND h.aufkstat=0
              AND h.kdnr IN ({','.join(str(k) for k in under_b11)})
        """):
            log(f"  BACK bel=11 kredlim → aufkstat=0: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # h) aufkstat=0 distribution per kredlim status using ALL belegart
    totals_any = run(cur, "per-kdnr ALL bel aufkstat=0", f"""
        SELECT h.kdnr, SUM(p.poswert) total_open
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.kzerl='0'
          AND h.aufkstat=0
        GROUP BY h.kdnr
    """)
    over_any0 = [r[0] for r in totals_any if kredlim_map.get(r[0],0)>0 and r[1] and r[1]>kredlim_map.get(r[0],0)]
    under_any0 = [r[0] for r in totals_any if not(kredlim_map.get(r[0],0)>0 and r[1] and r[1]>kredlim_map.get(r[0],0))]
    log(f"  aufkstat=0 ALL bel customers={len(totals_any)}  over={len(over_any0)}  under={len(under_any0)}")

    if over_any0:
        for r in run(cur, "BLOQ aufkstat=0 kredlim → bel=11 aufkstat=0", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.belegart=11 AND h.aufkstat=0
              AND h.kdnr IN ({','.join(str(k) for k in over_any0)})
        """):
            log(f"  BLOQ aufkstat=0 kredlim(any bel) → bel=11: ords={r[0]}  pos={r[1]}  val={r[2]}")

    if under_any0:
        for r in run(cur, "BACK aufkstat=0 kredlim → bel=11 aufkstat=0", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.belegart=11 AND h.aufkstat=0
              AND h.kdnr IN ({','.join(str(k) for k in under_any0)})
        """):
            log(f"  BACK aufkstat=0 kredlim(any bel) → bel=11: ords={r[0]}  pos={r[1]}  val={r[2]}")

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

    # Remitos: best candidate aufkstat=4
    for r in run(cur, "snap remitos aufkstat=4", f"""
        SELECT COUNT(DISTINCT s5.liefnr) docs, COUNT(*) pos, SUM(s5.liefposwe) val
        FROM sb105 s5, f090 h
        WHERE s5.firma={FIRMA} AND h.firma={FIRMA}
          AND s5.auftrag=h.auftrag
          AND s5.kzerl='0' AND h.aufkstat=4
    """):
        log(f"  [REMITOS sb105 kzerl=0 aufkstat=4] docs={r[0]}  pos={r[1]}  val={r[2]}")

    # Also backup: f090+f092 aufkstat=4
    for r in run(cur, "snap remitos f092 aufkstat=4", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND h.aufkstat=4 AND p.kzerl='0'
    """):
        log(f"  [REMITOS f092 aufkstat=4 kzerl=0] ords={r[0]}  pos={r[1]}  val={r[2]}")

    # Bloqueados: bel(6,7,11) kredlim → bel=11 aufkstat<>8
    totals_snap = run(cur, "snap per-kdnr bel(6,7,11) aufkstat<>8", f"""
        SELECT h.kdnr, SUM(p.poswert) total_open
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.kzerl='0'
          AND h.aufkstat<>8 AND h.belegart IN (6,7,11)
        GROUP BY h.kdnr
    """)
    over_snap = [r[0] for r in totals_snap if kredlim_map.get(r[0],0)>0 and r[1] and r[1]>kredlim_map.get(r[0],0)]
    under_snap = [r[0] for r in totals_snap if not(kredlim_map.get(r[0],0)>0 and r[1] and r[1]>kredlim_map.get(r[0],0))]

    if over_snap:
        for r in run(cur, "snap bloqueados bel=11 aufkstat<>8", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.belegart=11 AND h.aufkstat<>8
              AND h.kdnr IN ({','.join(str(k) for k in over_snap)})
        """):
            log(f"  [BLOQUEADOS bel(6,7,11) kredlim] ords={r[0]}  pos={r[1]}  val={r[2]}")

    if under_snap:
        for r in run(cur, "snap backorders bel=11 aufkstat<>8", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.belegart=11 AND h.aufkstat<>8
              AND h.kdnr IN ({','.join(str(k) for k in under_snap)})
        """):
            log(f"  [BACKORDERS bel(6,7,11) kredlim] ords={r[0]}  pos={r[1]}  val={r[2]}")

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

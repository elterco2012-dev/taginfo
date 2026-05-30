"""
TagInfo v28 — Exhaustive: Remitos (many filters), Backorders termin<TODAY, Bloqueados combos.
SOLO LECTURA.
"""

import pyodbc
from datetime import date, datetime

DSN = "MSPA"
OUTPUT_FILE = "taginfo_v28.txt"
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

    log(f"TagInfo v28 — {datetime.now()}")
    log(f"DSN: {DSN}  |  Fecha: {today}  |  SOLO LECTURA")
    log("=" * 70)

    conn = get_conn()
    cur = conn.cursor()
    log("Conexión OK\n")

    kredlim_rows = run(cur, "kredlim", f"SELECT kdnr, kredlim FROM kund WHERE firma={FIRMA} AND kredlim > 0")
    kredlim_map = {r[0]: r[1] for r in kredlim_rows}

    # ============================================================
    # 1. REMITOS — exhaustive combinations
    # ============================================================
    log("=== REMITOS — combinaciones exhaustivas ===")

    # a) Distribution: how many sb105 positions per liefnr (kzerl=0)
    log("\n--- sb105 kzerl=0 positions-per-liefnr distribution ---")
    for r in run(cur, "sb105 kzerl=0 pos-per-liefnr", f"""
        SELECT npos, COUNT(*) liefnrs FROM (
            SELECT s5.liefnr liefnr, COUNT(*) npos
            FROM sb105 s5
            WHERE s5.firma={FIRMA} AND s5.kzerl='0'
            GROUP BY s5.liefnr
        ) t GROUP BY npos ORDER BY npos
    """):
        log(f"  positions_per_liefnr={r[0]}  count_liefnrs={r[1]}")

    # b) sb105 kzerl=0 + sb104 liefdat = TODAY
    for r in run(cur, "sb105 kzerl=0 sb104 TODAY", f"""
        SELECT COUNT(DISTINCT s5.liefnr) docs, COUNT(*) pos, SUM(s5.liefposwe) val
        FROM sb105 s5, sb104 s4
        WHERE s5.firma={FIRMA} AND s4.firma={FIRMA}
          AND s5.liefnr=s4.liefnr
          AND s5.kzerl='0' AND s4.liefdat=TODAY
    """):
        log(f"  sb105 kzerl=0 sb104 TODAY: docs={r[0]}  pos={r[1]}  val={r[2]}")

    # c) sb105 kzerl=0 + sb104 liefdat=TODAY + aufkstat distribution
    log("\n--- sb105 kzerl=0 + sb104 TODAY + f090 aufkstat dist ---")
    for r in run(cur, "sb105 kzerl=0 sb104 TODAY aufkstat dist", f"""
        SELECT h.aufkstat, COUNT(DISTINCT s5.liefnr) docs, COUNT(*) pos, SUM(s5.liefposwe) val
        FROM sb105 s5, sb104 s4, f090 h
        WHERE s5.firma={FIRMA} AND s4.firma={FIRMA} AND h.firma={FIRMA}
          AND s5.liefnr=s4.liefnr
          AND s5.auftrag=h.auftrag
          AND s5.kzerl='0' AND s4.liefdat=TODAY
        GROUP BY h.aufkstat ORDER BY h.aufkstat
    """):
        log(f"  aufkstat={r[0]}  docs={r[1]}  pos={r[2]}  val={r[3]}")

    # d) sb105 NOT IN sbas — delivery notes not yet invoiced
    for r in run(cur, "sb105 kzerl=0 NOT IN sbas", f"""
        SELECT COUNT(DISTINCT s5.liefnr) docs, COUNT(*) pos, SUM(s5.liefposwe) val
        FROM sb105 s5
        WHERE s5.firma={FIRMA} AND s5.kzerl='0'
          AND NOT EXISTS (
            SELECT 1 FROM sbas sa WHERE sa.firma={FIRMA} AND sa.liefnr=s5.liefnr
          )
    """):
        log(f"  sb105 kzerl=0 NOT IN sbas: docs={r[0]}  pos={r[1]}  val={r[2]}")

    # e) sb105 + f090 aufkstat=8, further filtered by sb104.liefdat = TODAY
    for r in run(cur, "sb105 f090 aufkstat=8 sb104 TODAY", f"""
        SELECT COUNT(DISTINCT s5.liefnr) docs, COUNT(*) pos, SUM(s5.liefposwe) val
        FROM sb105 s5, f090 h, sb104 s4
        WHERE s5.firma={FIRMA} AND h.firma={FIRMA} AND s4.firma={FIRMA}
          AND s5.auftrag=h.auftrag
          AND s5.liefnr=s4.liefnr
          AND s5.kzerl='0' AND h.aufkstat=8 AND s4.liefdat=TODAY
    """):
        log(f"  sb105 f090 aufkstat=8 sb104 TODAY: docs={r[0]}  pos={r[1]}  val={r[2]}")

    # f) f092 posstat=8 — how many sb105 positions per f092 row
    log("\n--- f092 posstat=8 + sb105 detail ---")
    for r in run(cur, "f092 posstat=8 + sb105 sb104 TODAY", f"""
        SELECT COUNT(DISTINCT s5.liefnr) docs, COUNT(*) pos, SUM(s5.liefposwe) val
        FROM f092 p, sb105 s5, sb104 s4
        WHERE p.firma={FIRMA} AND s5.firma={FIRMA} AND s4.firma={FIRMA}
          AND p.auftrag=s5.auftrag AND p.posnr=s5.posnr
          AND s5.liefnr=s4.liefnr
          AND p.posstat=8 AND s5.kzerl='0' AND s4.liefdat=TODAY
    """):
        log(f"  f092 posstat=8 + sb105 + sb104 TODAY: docs={r[0]}  pos={r[1]}  val={r[2]}")

    # g) sbas distribution: all belegart, any redat — what's "open"?
    log("\n--- sbas belegart+redat distribution (last look) ---")
    for r in run(cur, "sbas belegart dist all dates", f"""
        SELECT belegart, COUNT(DISTINCT renr) docs, COUNT(*) pos, SUM(netwert) val
        FROM sbas WHERE firma={FIRMA}
        GROUP BY belegart ORDER BY belegart
    """):
        log(f"  belegart={r[0]}  docs={r[1]}  pos={r[2]}  val={r[3]}")

    # h) sbas redat=TODAY distribution
    log("\n--- sbas redat=TODAY belegart dist ---")
    for r in run(cur, "sbas TODAY belegart dist", f"""
        SELECT belegart, COUNT(DISTINCT renr) docs, COUNT(*) pos, SUM(netwert) val
        FROM sbas WHERE firma={FIRMA} AND redat=TODAY
        GROUP BY belegart ORDER BY belegart
    """):
        log(f"  belegart={r[0]}  docs={r[1]}  pos={r[2]}  val={r[3]}")

    # i) Check if f090 has a Lieferschein-related status: count aufkstat values for belegart=11
    log("\n--- f090 aufkstat distribution belegart=11 ---")
    for r in run(cur, "f090 aufkstat dist bel=11", f"""
        SELECT aufkstat, COUNT(*) ords
        FROM f090 WHERE firma={FIRMA} AND belegart=11
        GROUP BY aufkstat ORDER BY aufkstat
    """):
        log(f"  aufkstat={r[0]}  ords={r[1]}")

    # j) Try: sbas liefnr IS NOT NULL, redat=TODAY — delivery-referenced invoices today
    for r in run(cur, "sbas liefnr IS NOT NULL TODAY", f"""
        SELECT COUNT(DISTINCT liefnr) docs, COUNT(DISTINCT renr) invoices, COUNT(*) pos, SUM(netwert) val
        FROM sbas WHERE firma={FIRMA} AND redat=TODAY AND liefnr IS NOT NULL
    """):
        log(f"  sbas liefnr NOT NULL TODAY: docs(liefnr)={r[0]}  invoices={r[1]}  pos={r[2]}  val={r[3]}")

    # k) sbas liefnr IS NOT NULL, no date filter — total open liefnr in sbas
    for r in run(cur, "sbas liefnr IS NOT NULL ALL", f"""
        SELECT COUNT(DISTINCT liefnr) docs, COUNT(*) pos, SUM(netwert) val
        FROM sbas WHERE firma={FIRMA} AND liefnr IS NOT NULL
    """):
        log(f"  sbas liefnr NOT NULL ALL: docs={r[0]}  pos={r[1]}  val={r[2]}")

    # l) sb105 liefnr in sbas TODAY
    for r in run(cur, "sb105 kzerl=0 IN sbas TODAY", f"""
        SELECT COUNT(DISTINCT s5.liefnr) docs, COUNT(*) pos, SUM(s5.liefposwe) val
        FROM sb105 s5
        WHERE s5.firma={FIRMA} AND s5.kzerl='0'
          AND EXISTS (
            SELECT 1 FROM sbas sa WHERE sa.firma={FIRMA} AND sa.liefnr=s5.liefnr AND sa.redat=TODAY
          )
    """):
        log(f"  sb105 kzerl=0 IN sbas TODAY: docs={r[0]}  pos={r[1]}  val={r[2]}")

    # m) sb105 all kzerl values distribution
    log("\n--- sb105 kzerl distribution ---")
    for r in run(cur, "sb105 kzerl dist", f"""
        SELECT kzerl, COUNT(DISTINCT liefnr) docs, COUNT(*) pos, SUM(liefposwe) val
        FROM sb105 WHERE firma={FIRMA}
        GROUP BY kzerl ORDER BY kzerl
    """):
        log(f"  kzerl={r[0]}  docs={r[1]}  pos={r[2]}  val={r[3]}")

    # n) Try kzerl='1' (maybe '1' = open in this ERP?)
    for r in run(cur, "sb105 kzerl=1", f"""
        SELECT COUNT(DISTINCT liefnr) docs, COUNT(*) pos, SUM(liefposwe) val
        FROM sb105 WHERE firma={FIRMA} AND kzerl='1'
    """):
        log(f"  sb105 kzerl=1: docs={r[0]}  pos={r[1]}  val={r[2]}")

    # o) sb105 kzerl=' ' (space)
    for r in run(cur, "sb105 kzerl=space", f"""
        SELECT COUNT(DISTINCT liefnr) docs, COUNT(*) pos, SUM(liefposwe) val
        FROM sb105 WHERE firma={FIRMA} AND kzerl=' '
    """):
        log(f"  sb105 kzerl=SPACE: docs={r[0]}  pos={r[1]}  val={r[2]}")

    # p) sb105 today (via sb104.liefdat) all kzerl values
    log("\n--- sb105 + sb104 TODAY all kzerl ---")
    for r in run(cur, "sb105 sb104 TODAY all kzerl", f"""
        SELECT s5.kzerl, COUNT(DISTINCT s5.liefnr) docs, COUNT(*) pos, SUM(s5.liefposwe) val
        FROM sb105 s5, sb104 s4
        WHERE s5.firma={FIRMA} AND s4.firma={FIRMA}
          AND s5.liefnr=s4.liefnr AND s4.liefdat=TODAY
        GROUP BY s5.kzerl ORDER BY s5.kzerl
    """):
        log(f"  liefdat=TODAY kzerl={r[0]}  docs={r[1]}  pos={r[2]}  val={r[3]}")

    # q) f092 posstat distribution with f090 belegart=11
    log("\n--- f092 posstat dist for bel=11 aufkstat<>8 ---")
    for r in run(cur, "f092 posstat dist bel=11", f"""
        SELECT p.posstat, COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag
          AND h.belegart=11 AND h.aufkstat<>8
          AND p.kzerl='0'
        GROUP BY p.posstat ORDER BY p.posstat
    """):
        log(f"  posstat={r[0]}  ords={r[1]}  pos={r[2]}  val={r[3]}")

    # ============================================================
    # 2. BACKORDERS — termin < TODAY (Plazos VIEJOS = past due)
    # ============================================================
    log("\n=== BACKORDERS — termin < TODAY (Plazos viejos) ===")

    # a) f092.termin < TODAY (past due)
    for r in run(cur, "f092.termin < TODAY bel=11 aufkstat<>8 liefme<>0", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag
          AND h.belegart=11 AND h.aufkstat<>8
          AND p.termin < TODAY AND p.liefme<>0 AND p.kzerl='0'
    """):
        log(f"  f092.termin<TODAY bel=11 aufkstat<>8 liefme<>0: ords={r[0]}  pos={r[1]}  val={r[2]}")

    for r in run(cur, "f092.termin < TODAY bel=11 aufkstat<>8", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag
          AND h.belegart=11 AND h.aufkstat<>8
          AND p.termin < TODAY AND p.kzerl='0'
    """):
        log(f"  f092.termin<TODAY bel=11 aufkstat<>8: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # b) f090.termin < TODAY
    for r in run(cur, "f090.termin < TODAY bel=11 aufkstat<>8", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag
          AND h.belegart=11 AND h.aufkstat<>8
          AND h.termin < TODAY AND p.kzerl='0'
    """):
        log(f"  f090.termin<TODAY bel=11 aufkstat<>8: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # c) f092.termin <= TODAY (includes today)
    for r in run(cur, "f092.termin <= TODAY bel=11 aufkstat<>8 liefme<>0", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag
          AND h.belegart=11 AND h.aufkstat<>8
          AND p.termin <= TODAY AND p.liefme<>0 AND p.kzerl='0'
    """):
        log(f"  f092.termin<=TODAY bel=11 aufkstat<>8 liefme<>0: ords={r[0]}  pos={r[1]}  val={r[2]}")

    for r in run(cur, "f092.termin <= TODAY bel=11 aufkstat<>8", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag
          AND h.belegart=11 AND h.aufkstat<>8
          AND p.termin <= TODAY AND p.kzerl='0'
    """):
        log(f"  f092.termin<=TODAY bel=11 aufkstat<>8: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # d) aufkstat=0 specifically (backorder blocked state?)
    for r in run(cur, "f092.termin<TODAY bel=11 aufkstat=0 liefme<>0", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag
          AND h.belegart=11 AND h.aufkstat=0
          AND p.termin < TODAY AND p.liefme<>0 AND p.kzerl='0'
    """):
        log(f"  f092.termin<TODAY bel=11 aufkstat=0 liefme<>0: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # e) All belegart, termin < TODAY
    for r in run(cur, "f092.termin<TODAY ALL bel aufkstat<>8 liefme<>0", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag
          AND h.aufkstat<>8
          AND p.termin < TODAY AND p.liefme<>0 AND p.kzerl='0'
    """):
        log(f"  f092.termin<TODAY ALL bel aufkstat<>8 liefme<>0: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # f) f092.termin distribution for bel=11 aufkstat<>8 to understand spread
    log("\n--- f092.termin range dist bel=11 aufkstat<>8 kzerl=0 ---")
    for r in run(cur, "f092 termin dist bel=11", f"""
        SELECT CASE
            WHEN p.termin < TODAY THEN 'PAST'
            WHEN p.termin = TODAY THEN 'TODAY'
            WHEN p.termin > TODAY THEN 'FUTURE'
            ELSE 'NULL'
        END termin_group,
        COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag
          AND h.belegart=11 AND h.aufkstat<>8
          AND p.kzerl='0'
        GROUP BY 1 ORDER BY 1
    """):
        log(f"  termin={r[0]}  ords={r[1]}  pos={r[2]}  val={r[3]}")

    # ============================================================
    # 3. BLOQUEADOS — multiple approaches
    # ============================================================
    log("\n=== BLOQUEADOS — múltiples enfoques ===")

    # a) Standard: 2-step kredlim, bel=11, aufkstat<>8
    totals_b11 = run(cur, "per-kdnr bel=11 aufkstat<>8", f"""
        SELECT h.kdnr, SUM(p.poswert) total_open
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.kzerl='0'
          AND h.aufkstat<>8 AND h.belegart=11
        GROUP BY h.kdnr
    """)
    over_b11 = [r[0] for r in totals_b11 if kredlim_map.get(r[0],0)>0 and r[1] and r[1]>kredlim_map.get(r[0],0)]
    under_b11 = [r[0] for r in totals_b11 if not(kredlim_map.get(r[0],0)>0 and r[1] and r[1]>kredlim_map.get(r[0],0))]
    log(f"  bel=11 aufkstat<>8 customers={len(totals_b11)}  over={len(over_b11)}  under={len(under_b11)}")

    # b) 2-step kredlim from bel=11 aufkstat<>8, but count aufkstat=0 (blocked only)
    if over_b11:
        for r in run(cur, "BLOQ bel=11 aufkstat=0", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.aufkstat=0 AND h.belegart=11
              AND h.kdnr IN ({','.join(str(k) for k in over_b11)})
        """):
            log(f"  BLOQ kredlim bel=11 aufkstat=0: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # c) Total belegart=11 aufkstat<>8 per customer, split by aufkstat=0
    for r in run(cur, "bel=11 aufkstat=0 ALL kdnr", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.kzerl='0'
          AND h.belegart=11 AND h.aufkstat=0
    """):
        log(f"  ALL kdnr bel=11 aufkstat=0: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # d) bel IN (6,7,11) kredlim check vs count bel=11 only
    totals_bel6711 = run(cur, "per-kdnr bel IN(6,7,11) aufkstat<>8", f"""
        SELECT h.kdnr, SUM(p.poswert) total_open
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.kzerl='0'
          AND h.aufkstat<>8 AND h.belegart IN (6,7,11)
        GROUP BY h.kdnr
    """)
    over_6711 = [r[0] for r in totals_bel6711 if kredlim_map.get(r[0],0)>0 and r[1] and r[1]>kredlim_map.get(r[0],0)]
    log(f"  bel IN(6,7,11) over-limit customers={len(over_6711)}")
    if over_6711:
        for r in run(cur, "BLOQ bel(6,7,11) kredlim count bel=11", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.aufkstat<>8 AND h.belegart=11
              AND h.kdnr IN ({','.join(str(k) for k in over_6711)})
        """):
            log(f"  BLOQ bel(6,7,11) kredlim → count bel=11: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # e) Kredlim check from bel=11 only, count ALL aufkstat<>8 belegart
    if over_b11:
        for r in run(cur, "BLOQ kredlim bel=11 count ALL bel", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.aufkstat<>8
              AND h.kdnr IN ({','.join(str(k) for k in over_b11)})
        """):
            log(f"  BLOQ bel=11 kredlim → count ALL bel: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # f) Try: kredlim from bel=11 aufkstat<>8, termin-independent
    #    Count with termin < TODAY = bloqueados, termin >= TODAY = backorders (alternative split)
    if over_b11:
        for r in run(cur, "BLOQ bel=11 aufkstat<>8 termin<TODAY", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.aufkstat<>8 AND h.belegart=11
              AND p.termin < TODAY
              AND h.kdnr IN ({','.join(str(k) for k in over_b11)})
        """):
            log(f"  BLOQ bel=11 kredlim termin<TODAY: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # g) Try counting DISTINCT orders for termin<TODAY + NOT over kredlim = backorders
    if under_b11:
        for r in run(cur, "BACK bel=11 aufkstat<>8 termin<TODAY", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.aufkstat<>8 AND h.belegart=11
              AND p.termin < TODAY
              AND h.kdnr IN ({','.join(str(k) for k in under_b11)})
        """):
            log(f"  BACK bel=11 NOT-kredlim termin<TODAY: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # h) termin<TODAY ALL kdnr (no kredlim split)
    for r in run(cur, "ALL termin<TODAY bel=11 aufkstat<>8", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.kzerl='0'
          AND h.aufkstat<>8 AND h.belegart=11
          AND p.termin < TODAY
    """):
        log(f"  ALL termin<TODAY bel=11 aufkstat<>8: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # i) termin<TODAY liefme<>0 ALL kdnr
    for r in run(cur, "ALL termin<TODAY bel=11 aufkstat<>8 liefme<>0", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.kzerl='0'
          AND h.aufkstat<>8 AND h.belegart=11
          AND p.termin < TODAY AND p.liefme<>0
    """):
        log(f"  ALL termin<TODAY bel=11 aufkstat<>8 liefme<>0: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # j) Try f090.termin < TODAY (header-level)
    for r in run(cur, "f090.termin<TODAY bel=11 aufkstat<>8", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.kzerl='0'
          AND h.aufkstat<>8 AND h.belegart=11
          AND h.termin < TODAY
    """):
        log(f"  f090.termin<TODAY bel=11 aufkstat<>8: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # k) What if backorders = termin<TODAY and bloqueados = aufkstat=0?
    #    Test independently
    for r in run(cur, "bel=11 aufkstat=0 (bloqueado state?)", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.kzerl='0'
          AND h.aufkstat=0 AND h.belegart=11
    """):
        log(f"  bel=11 aufkstat=0: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # ============================================================
    # 4. SNAPSHOT
    # ============================================================
    log("\n=== SNAPSHOT COMPLETO ===")
    ts = datetime.now()

    for r in run(cur, "snap produccion", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND h.aufkstat=2 AND p.posstat=2 AND p.kzerl='0'
    """):
        log(f"  [PRODUCCION] ords={r[0]}  pos={r[1]}  val={r[2]}")

    # Remitos best candidate: sb105 kzerl=0 NOT IN sbas
    for r in run(cur, "snap remitos sb105 kzerl=0 NOT IN sbas", f"""
        SELECT COUNT(DISTINCT s5.liefnr) docs, COUNT(*) pos, SUM(s5.liefposwe) val
        FROM sb105 s5
        WHERE s5.firma={FIRMA} AND s5.kzerl='0'
          AND NOT EXISTS (
            SELECT 1 FROM sbas sa WHERE sa.firma={FIRMA} AND sa.liefnr=s5.liefnr
          )
    """):
        log(f"  [REMITOS sb105 NOT IN sbas] docs={r[0]}  pos={r[1]}  val={r[2]}")

    # Backorders: termin < TODAY, no kredlim split
    for r in run(cur, "snap backorders termin<TODAY", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.kzerl='0'
          AND h.aufkstat<>8 AND h.belegart=11
          AND p.termin < TODAY AND p.liefme<>0
    """):
        log(f"  [BACKORDERS termin<TODAY liefme<>0] ords={r[0]}  pos={r[1]}  val={r[2]}")

    # Bloqueados: kredlim 2-step
    totals_snap = run(cur, "snap per-kdnr bel=11 aufkstat<>8", f"""
        SELECT h.kdnr, SUM(p.poswert) total_open
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.kzerl='0'
          AND h.aufkstat<>8 AND h.belegart=11
        GROUP BY h.kdnr
    """)
    over_s = [r[0] for r in totals_snap if kredlim_map.get(r[0],0)>0 and r[1] and r[1]>kredlim_map.get(r[0],0)]
    under_s = [r[0] for r in totals_snap if not(kredlim_map.get(r[0],0)>0 and r[1] and r[1]>kredlim_map.get(r[0],0))]
    if over_s:
        for r in run(cur, "snap bloqueados", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.aufkstat<>8 AND h.belegart=11
              AND h.kdnr IN ({','.join(str(x) for x in over_s)})
        """):
            log(f"  [BLOQUEADOS bel=11] ords={r[0]}  pos={r[1]}  val={r[2]}")
    if under_s:
        for r in run(cur, "snap backorders", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.aufkstat<>8 AND h.belegart=11
              AND h.kdnr IN ({','.join(str(x) for x in under_s)})
        """):
            log(f"  [BACKORDERS bel=11] ords={r[0]}  pos={r[1]}  val={r[2]}")

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

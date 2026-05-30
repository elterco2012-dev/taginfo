"""
TagInfo v31 — syscolumns para descubrir campos, buscar campo bloqueo credito, remitos via refrenr.
SOLO LECTURA.
"""

import pyodbc
from datetime import date, datetime

DSN = "MSPA"
OUTPUT_FILE = "taginfo_v31.txt"
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

    log(f"TagInfo v31 — {datetime.now()}")
    log(f"DSN: {DSN}  |  Fecha: {today}  |  SOLO LECTURA")
    log("=" * 70)

    conn = get_conn()
    cur = conn.cursor()
    log("Conexión OK\n")

    kredlim_rows = run(cur, "kredlim", f"SELECT kdnr, kredlim FROM kund WHERE firma={FIRMA} AND kredlim > 0")
    kredlim_map = {r[0]: r[1] for r in kredlim_rows}

    # ============================================================
    # 1. DISCOVER COLUMNS VIA INFORMIX SYSTEM TABLES
    # ============================================================
    log("=== COLUMNAS VIA syscolumns ===")

    for tbl in ["f090", "f092", "sb104", "sb105", "sbas"]:
        rows = run(cur, f"syscolumns {tbl}", f"""
            SELECT c.colname, c.coltype, c.collength
            FROM syscolumns c, systables t
            WHERE c.tabid = t.tabid AND t.tabname = '{tbl}'
            ORDER BY c.colno
        """)
        if rows:
            log(f"\n{tbl} columns:")
            for r in rows:
                log(f"  {r[0]}  type={r[1]}  len={r[2]}")
        else:
            log(f"\n{tbl}: no rows from syscolumns")

    # ============================================================
    # 2. REMITOS — try sbas refrenr / refenr as delivery note link
    # ============================================================
    log("\n=== REMITOS — sbas refrenr/refenr links ===")

    # Check if sbas has refrenr field linking to sb104 liefnr
    for r in run(cur, "sbas refrenr > 0 TODAY", f"""
        SELECT COUNT(DISTINCT refrenr) docs, COUNT(*) pos, SUM(netwert) val
        FROM sbas WHERE firma={FIRMA} AND redat=TODAY AND refrenr > 0
    """):
        log(f"  sbas refrenr>0 TODAY: docs={r[0]}  pos={r[1]}  val={r[2]}")

    for r in run(cur, "sbas refrenr TODAY belegart dist", f"""
        SELECT belegart, COUNT(DISTINCT refrenr) docs, COUNT(*) pos
        FROM sbas WHERE firma={FIRMA} AND redat=TODAY AND refrenr > 0
        GROUP BY belegart ORDER BY belegart
    """):
        log(f"  sbas TODAY refrenr>0 belegart={r[0]}  docs={r[1]}  pos={r[2]}")

    # sb105 kzerl=0 where liefnr NOT IN sbas.refrenr (TODAY)
    sbas_refrenr_today = run(cur, "sbas refrenr today list", f"""
        SELECT DISTINCT refrenr FROM sbas WHERE firma={FIRMA} AND redat=TODAY AND refrenr > 0
    """)
    sbas_refr_set = {r[0] for r in sbas_refrenr_today}
    log(f"  sbas refrenr TODAY distinct: {len(sbas_refr_set)}")

    sbas_refrenr_all = run(cur, "sbas refrenr all list", f"""
        SELECT DISTINCT refrenr FROM sbas WHERE firma={FIRMA} AND refrenr > 0
    """)
    sbas_refr_all = {r[0] for r in sbas_refrenr_all}
    log(f"  sbas refrenr ALL distinct: {len(sbas_refr_all)}")

    sb105_open = run(cur, "sb105 kzerl=0 liefnr", f"""
        SELECT liefnr, COUNT(*) pos, SUM(liefposwe) val
        FROM sb105 WHERE firma={FIRMA} AND kzerl='0'
        GROUP BY liefnr
    """)

    not_refr_today = [(r[0],r[1],r[2]) for r in sb105_open if r[0] not in sbas_refr_set]
    not_refr_all = [(r[0],r[1],r[2]) for r in sb105_open if r[0] not in sbas_refr_all]
    log(f"  sb105 kzerl=0 NOT in sbas.refrenr TODAY: docs={len(not_refr_today)}  pos={sum(r[1] for r in not_refr_today)}  val={sum(r[2] for r in not_refr_today if r[2]):.2f}")
    log(f"  sb105 kzerl=0 NOT in sbas.refrenr ALL: docs={len(not_refr_all)}  pos={sum(r[1] for r in not_refr_all)}  val={sum(r[2] for r in not_refr_all if r[2]):.2f}")

    # Also try: sbas with renr linking back to sb104 (different field)
    for r in run(cur, "sbas renr linking sb104 TODAY", f"""
        SELECT COUNT(DISTINCT s4.liefnr) docs, COUNT(*) pos, SUM(s5.liefposwe) val
        FROM sbas sa, sb104 s4, sb105 s5
        WHERE sa.firma={FIRMA} AND s4.firma={FIRMA} AND s5.firma={FIRMA}
          AND sa.renr=s4.liefnr AND s4.liefnr=s5.liefnr
          AND sa.redat=TODAY AND s5.kzerl='0'
    """):
        log(f"  sbas.renr=sb104.liefnr TODAY + sb105 kzerl=0: docs={r[0]}  pos={r[1]}  val={r[2]}")

    # Try: sb105 kzerl=0 liefnr where sb104.liefnr NOT IN sbas.renr (any date)
    sbas_renr_all = run(cur, "sbas renr all list", f"""
        SELECT DISTINCT renr FROM sbas WHERE firma={FIRMA} AND renr > 0
    """)
    sbas_renr_set = {r[0] for r in sbas_renr_all}
    log(f"  sbas renr ALL distinct: {len(sbas_renr_set)}")

    not_renr_all = [(r[0],r[1],r[2]) for r in sb105_open if r[0] not in sbas_renr_set]
    log(f"  sb105 kzerl=0 liefnr NOT in sbas.renr ALL: docs={len(not_renr_all)}  pos={sum(r[1] for r in not_renr_all)}  val={sum(r[2] for r in not_renr_all if r[2]):.2f}")

    # ============================================================
    # 3. BLOQUEADOS — try COUNT(DISTINCT posnr) for positions
    # ============================================================
    log("\n=== BLOQUEADOS — COUNT DISTINCT posnr vs COUNT(*) ===")

    totals_6711 = run(cur, "per-kdnr bel(6,7,11) aufkstat<>8", f"""
        SELECT h.kdnr, SUM(p.poswert) total_open
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.kzerl='0'
          AND h.aufkstat<>8 AND h.belegart IN (6,7,11)
        GROUP BY h.kdnr
    """)
    over_6711 = [r[0] for r in totals_6711 if kredlim_map.get(r[0],0)>0 and r[1] and r[1]>kredlim_map.get(r[0],0)]
    under_6711 = [r[0] for r in totals_6711 if not(kredlim_map.get(r[0],0)>0 and r[1] and r[1]>kredlim_map.get(r[0],0))]
    log(f"  bel(6,7,11) over={len(over_6711)}  under={len(under_6711)}")

    if over_6711:
        in_over = ','.join(str(k) for k in over_6711)
        for r in run(cur, "BLOQ count(*) vs distinct posnr bel=11 aufkstat<>8", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos_all, COUNT(DISTINCT p.posnr) pos_dist
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.belegart=11 AND h.aufkstat<>8
              AND h.kdnr IN ({in_over})
        """):
            log(f"  BLOQ bel=11 aufkstat<>8: ords={r[0]}  pos_all={r[1]}  pos_distinct_posnr={r[2]}")

        # Try ALL belegart for bloqueados count (maybe not just bel=11)
        for r in run(cur, "BLOQ ALL belegart aufkstat<>8 over-6711", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.aufkstat<>8 AND h.belegart IN (6,7,11)
              AND h.kdnr IN ({in_over})
        """):
            log(f"  BLOQ bel(6,7,11) aufkstat<>8: ords={r[0]}  pos={r[1]}  val={r[2]}")

        # aufkstat=0 specifically, bel IN (6,7,11)
        for r in run(cur, "BLOQ bel(6,7,11) aufkstat=0 over-6711", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.aufkstat=0 AND h.belegart IN (6,7,11)
              AND h.kdnr IN ({in_over})
        """):
            log(f"  BLOQ bel(6,7,11) aufkstat=0: ords={r[0]}  pos={r[1]}  val={r[2]}")

    if under_6711:
        in_under = ','.join(str(k) for k in under_6711)
        for r in run(cur, "BACK bel(6,7,11) aufkstat<>8 under-6711", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.aufkstat<>8 AND h.belegart IN (6,7,11)
              AND h.kdnr IN ({in_under})
        """):
            log(f"  BACK bel(6,7,11) aufkstat<>8: ords={r[0]}  pos={r[1]}  val={r[2]}")

        for r in run(cur, "BACK bel(6,7,11) aufkstat=0 under-6711", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.aufkstat=0 AND h.belegart IN (6,7,11)
              AND h.kdnr IN ({in_under})
        """):
            log(f"  BACK bel(6,7,11) aufkstat=0: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # ============================================================
    # 4. BLOQUEADOS — try with f090 only (no f092 join) for pos count
    # ============================================================
    log("\n=== BLOQUEADOS/BACKORDERS — f090 only (no f092) ===")

    # What if screen counts f090 headers and uses anzpos field?
    # Check f090.anzpos or similar - try querying it
    for r in run(cur, "f090 aufkstat=0 bel=11 count", f"""
        SELECT COUNT(*) ords FROM f090 WHERE firma={FIRMA} AND belegart=11 AND aufkstat=0
    """):
        log(f"  f090 only bel=11 aufkstat=0: {r[0]}")

    # Try: f090 bel=11 aufkstat<>8 with over-kredlim using SUM from f090 alone
    # Get per-kdnr totals from f090 (no f092 join, use f090 values if any)
    # Actually let's check if f090 has a value field
    for r in run(cur, "f090 bel=11 aufkstat=0 sum auftragswert", f"""
        SELECT COUNT(DISTINCT auftrag) ords, SUM(auftragswert) val
        FROM f090 WHERE firma={FIRMA} AND belegart=11 AND aufkstat=0
    """):
        log(f"  f090 bel=11 aufkstat=0 auftragswert: ords={r[0]}  val={r[1]}")

    # Maybe the credit limit check uses cumoffwert (cumulated open order value)?
    for r in run(cur, "f090 aufkstat=0 bel=11 cumoffwert", f"""
        SELECT COUNT(DISTINCT auftrag) ords, SUM(cumoffwert) val
        FROM f090 WHERE firma={FIRMA} AND belegart=11 AND aufkstat=0
    """):
        log(f"  f090 bel=11 aufkstat=0 cumoffwert: ords={r[0]}  val={r[1]}")

    # Try f090 with offwert
    for r in run(cur, "f090 aufkstat=0 bel=11 offwert", f"""
        SELECT COUNT(DISTINCT auftrag) ords, SUM(offwert) val
        FROM f090 WHERE firma={FIRMA} AND belegart=11 AND aufkstat=0
    """):
        log(f"  f090 bel=11 aufkstat=0 offwert: ords={r[0]}  val={r[1]}")

    # ============================================================
    # 5. CHECK OTHER POTENTIAL TABLES FOR RECEIVABLES/CREDIT
    # ============================================================
    log("\n=== TABLAS CANDIDATAS PARA CRÉDITO (kfbuc, kfkonto, etc.) ===")

    for tbl in ["kfbuc", "kfkonto", "kfpos", "kfsal", "knfbuc"]:
        for r in run(cur, f"check {tbl}", f"SELECT COUNT(*) FROM {tbl} WHERE firma={FIRMA}"):
            log(f"  {tbl}: {r[0]} rows")

    # ============================================================
    # 6. SNAPSHOT
    # ============================================================
    log("\n=== SNAPSHOT COMPLETO ===")
    ts = datetime.now()

    for r in run(cur, "snap produccion", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND h.aufkstat=2 AND p.posstat=2 AND p.kzerl='0'
    """):
        log(f"  [PRODUCCION] ords={r[0]}  pos={r[1]}  val={r[2]}")

    # Remitos 2-step: sb105 kzerl=0 NOT in sbas.refrenr TODAY
    sbas_r2 = run(cur, "snap sbas refrenr today", f"SELECT DISTINCT refrenr FROM sbas WHERE firma={FIRMA} AND redat=TODAY AND refrenr > 0")
    sbas_r2_set = {r[0] for r in sbas_r2}
    sb105_s2 = run(cur, "snap sb105 kzerl=0", f"SELECT liefnr, COUNT(*) pos, SUM(liefposwe) val FROM sb105 WHERE firma={FIRMA} AND kzerl='0' GROUP BY liefnr")
    rem_not = [(r[0],r[1],r[2]) for r in sb105_s2 if r[0] not in sbas_r2_set]
    log(f"  [REMITOS sb105 kzerl=0 NOT in sbas.refrenr TODAY] docs={len(rem_not)}  pos={sum(r[1] for r in rem_not)}  val={sum(r[2] for r in rem_not if r[2]):.2f}")

    # Bloqueados
    tots = run(cur, "snap per-kdnr bel(6,7,11)", f"""
        SELECT h.kdnr, SUM(p.poswert) total_open
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.kzerl='0'
          AND h.aufkstat<>8 AND h.belegart IN (6,7,11)
        GROUP BY h.kdnr
    """)
    over_s = [r[0] for r in tots if kredlim_map.get(r[0],0)>0 and r[1] and r[1]>kredlim_map.get(r[0],0)]
    under_s = [r[0] for r in tots if not(kredlim_map.get(r[0],0)>0 and r[1] and r[1]>kredlim_map.get(r[0],0))]

    if over_s:
        for r in run(cur, "snap bloqueados bel=11 aufkstat<>8", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.belegart=11 AND h.aufkstat<>8
              AND h.kdnr IN ({','.join(str(k) for k in over_s)})
        """):
            log(f"  [BLOQUEADOS bel(6,7,11) kredlim → bel=11 aufkstat<>8] ords={r[0]}  pos={r[1]}  val={r[2]}")

        for r in run(cur, "snap bloqueados bel(6,7,11) aufkstat<>8", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.belegart IN (6,7,11) AND h.aufkstat<>8
              AND h.kdnr IN ({','.join(str(k) for k in over_s)})
        """):
            log(f"  [BLOQUEADOS bel(6,7,11) kredlim → bel(6,7,11) aufkstat<>8] ords={r[0]}  pos={r[1]}  val={r[2]}")

    if under_s:
        for r in run(cur, "snap backorders bel=11 aufkstat<>8", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.belegart=11 AND h.aufkstat<>8
              AND h.kdnr IN ({','.join(str(k) for k in under_s)})
        """):
            log(f"  [BACKORDERS bel(6,7,11) kredlim → bel=11 aufkstat<>8] ords={r[0]}  pos={r[1]}  val={r[2]}")

        for r in run(cur, "snap backorders bel(6,7,11) aufkstat<>8", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.belegart IN (6,7,11) AND h.aufkstat<>8
              AND h.kdnr IN ({','.join(str(k) for k in under_s)})
        """):
            log(f"  [BACKORDERS bel(6,7,11) kredlim → bel(6,7,11) aufkstat<>8] ords={r[0]}  pos={r[1]}  val={r[2]}")

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

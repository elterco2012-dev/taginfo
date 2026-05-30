"""
TagInfo v30 — Descubrir columnas de tablas, Remitos 2-step Python, Bloqueados campos de bloqueo.
SOLO LECTURA.
"""

import pyodbc
from datetime import date, datetime

DSN = "MSPA"
OUTPUT_FILE = "taginfo_v30.txt"
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


def describe(cursor, label, sql):
    """Run query and return (colnames, rows)."""
    print(f"  describe {label}...")
    try:
        cursor.execute(sql)
        cols = [d[0] for d in cursor.description]
        rows = cursor.fetchall()
        return cols, rows
    except Exception as e:
        print(f"    SQL ERROR describe [{label}]: {e}")
        return [], []


def main():
    lines = []
    log = lines.append
    today = date.today()

    log(f"TagInfo v30 — {datetime.now()}")
    log(f"DSN: {DSN}  |  Fecha: {today}  |  SOLO LECTURA")
    log("=" * 70)

    conn = get_conn()
    cur = conn.cursor()
    log("Conexión OK\n")

    kredlim_rows = run(cur, "kredlim", f"SELECT kdnr, kredlim FROM kund WHERE firma={FIRMA} AND kredlim > 0")
    kredlim_map = {r[0]: r[1] for r in kredlim_rows}

    # ============================================================
    # 1. DISCOVER TABLE COLUMNS
    # ============================================================
    log("=== COLUMNAS DE TABLAS ===")

    for tbl in ["f090", "f092", "sb104", "sb105", "sbas"]:
        cols, rows = describe(cur, tbl, f"SELECT FIRST 1 * FROM {tbl} WHERE firma={FIRMA}")
        if cols:
            log(f"\n{tbl} columns ({len(cols)}):")
            # Print in groups of 8
            for i in range(0, len(cols), 8):
                log(f"  {', '.join(cols[i:i+8])}")
        else:
            log(f"\n{tbl}: ERROR or no rows")

    # ============================================================
    # 2. REMITOS — 2-step Python: liefnr in sbas vs sb105 kzerl=0
    # ============================================================
    log("\n=== REMITOS — 2-step Python ===")

    # Step 1: Get all liefnr currently invoiced in sbas TODAY
    sbas_liefnr_today = run(cur, "sbas liefnr TODAY", f"""
        SELECT DISTINCT liefnr FROM sbas WHERE firma={FIRMA} AND redat=TODAY AND liefnr > 0
    """)
    sbas_lnr_set_today = {r[0] for r in sbas_liefnr_today}
    log(f"  sbas liefnr > 0 TODAY: {len(sbas_lnr_set_today)} distinct")

    # Step 2: Get all liefnr in sbas (any date)
    sbas_liefnr_all = run(cur, "sbas liefnr ALL", f"""
        SELECT DISTINCT liefnr FROM sbas WHERE firma={FIRMA} AND liefnr > 0
    """)
    sbas_lnr_set_all = {r[0] for r in sbas_liefnr_all}
    log(f"  sbas liefnr > 0 ALL dates: {len(sbas_lnr_set_all)} distinct")

    # Step 3: Get sb105 kzerl=0 liefnr + val + pos
    sb105_open = run(cur, "sb105 kzerl=0 liefnr list", f"""
        SELECT liefnr, COUNT(*) pos, SUM(liefposwe) val
        FROM sb105 WHERE firma={FIRMA} AND kzerl='0'
        GROUP BY liefnr
    """)
    log(f"  sb105 kzerl=0 distinct liefnr: {len(sb105_open)}")

    # Step 4: Not in sbas TODAY
    not_in_today = [(r[0], r[1], r[2]) for r in sb105_open if r[0] not in sbas_lnr_set_today]
    not_in_all = [(r[0], r[1], r[2]) for r in sb105_open if r[0] not in sbas_lnr_set_all]
    total_pos_not_today = sum(r[1] for r in not_in_today)
    total_val_not_today = sum(r[2] for r in not_in_today if r[2])
    total_pos_not_all = sum(r[1] for r in not_in_all)
    total_val_not_all = sum(r[2] for r in not_in_all if r[2])

    log(f"  sb105 kzerl=0 NOT in sbas TODAY: docs={len(not_in_today)}  pos={total_pos_not_today}  val={total_val_not_today:.2f}")
    log(f"  sb105 kzerl=0 NOT in sbas ALL: docs={len(not_in_all)}  pos={total_pos_not_all}  val={total_val_not_all:.2f}")

    # Step 5: Also check sb105 kzerl=0 + aufkstat=8 NOT in sbas
    sb105_open_aufk8 = run(cur, "sb105 kzerl=0 aufkstat=8 liefnr", f"""
        SELECT s5.liefnr, COUNT(*) pos, SUM(s5.liefposwe) val
        FROM sb105 s5, f090 h
        WHERE s5.firma={FIRMA} AND h.firma={FIRMA}
          AND s5.auftrag=h.auftrag AND s5.kzerl='0' AND h.aufkstat=8
        GROUP BY s5.liefnr
    """)
    not_8_today = [(r[0],r[1],r[2]) for r in sb105_open_aufk8 if r[0] not in sbas_lnr_set_today]
    not_8_all = [(r[0],r[1],r[2]) for r in sb105_open_aufk8 if r[0] not in sbas_lnr_set_all]
    log(f"  sb105 kzerl=0 aufkstat=8 NOT in sbas TODAY: docs={len(not_8_today)}  pos={sum(r[1] for r in not_8_today)}  val={sum(r[2] for r in not_8_today if r[2]):.2f}")
    log(f"  sb105 kzerl=0 aufkstat=8 NOT in sbas ALL: docs={len(not_8_all)}  pos={sum(r[1] for r in not_8_all if True)}  val={sum(r[2] for r in not_8_all if r[2]):.2f}")

    # Step 6: Also check kzerl=None
    sb105_none = run(cur, "sb105 kzerl=None liefnr", f"""
        SELECT liefnr, COUNT(*) pos, SUM(liefposwe) val
        FROM sb105 WHERE firma={FIRMA} AND kzerl IS NULL
        GROUP BY liefnr
    """)
    not_none_today = [(r[0],r[1],r[2]) for r in sb105_none if r[0] not in sbas_lnr_set_today]
    log(f"  sb105 kzerl=NULL NOT in sbas TODAY: docs={len(not_none_today)}  pos={sum(r[1] for r in not_none_today)}")

    # ============================================================
    # 3. REMITOS — other angles to investigate
    # ============================================================
    log("\n=== REMITOS — current sb105 aufkstat=8 count ===")

    # How many sb105 kzerl=0 aufkstat=8 NOW?
    for r in run(cur, "sb105 kzerl=0 aufkstat=8 NOW", f"""
        SELECT COUNT(DISTINCT s5.liefnr) docs, COUNT(*) pos, SUM(s5.liefposwe) val
        FROM sb105 s5, f090 h
        WHERE s5.firma={FIRMA} AND h.firma={FIRMA}
          AND s5.auftrag=h.auftrag AND s5.kzerl='0' AND h.aufkstat=8
    """):
        log(f"  sb105 kzerl=0 aufkstat=8: docs={r[0]}  pos={r[1]}  val={r[2]}")

    # f092 posstat=8 NOW
    for r in run(cur, "f092 posstat=8 NOW", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.posstat=8 AND h.belegart=11 AND p.kzerl='0'
    """):
        log(f"  f092 posstat=8 bel=11 kzerl=0 NOW: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # ============================================================
    # 4. BACKORDERS/BLOQUEADOS — investigate f090 block fields
    # ============================================================
    log("\n=== BLOQUEADOS/BACKORDERS — campos de bloqueo en f090 ===")

    # Look at aufkstat=0 orders raw data to find block-related fields
    # We'll check several candidate field names that might indicate credit block
    block_field_candidates = [
        "msperr", "zsperr", "kreditsperr", "sperrkz", "liesperre",
        "sperr", "kzsperr", "spergrund", "kzsperre"
    ]
    for field in block_field_candidates:
        cols, rows = describe(cur, f"f090.{field}", f"""
            SELECT {field}, COUNT(*) cnt FROM f090
            WHERE firma={FIRMA} AND belegart=11 AND aufkstat=0
            GROUP BY {field} ORDER BY {field}
        """)
        if rows:
            for r in rows:
                log(f"  f090.{field}={r[0]}  cnt={r[1]}")
        # If error, run() already printed SQL ERROR

    # Try to select a sample aufkstat=0 row with ALL columns via Python describe
    cols_f090, rows_f090 = describe(cur, "f090 aufkstat=0 sample", f"""
        SELECT FIRST 3 * FROM f090 WHERE firma={FIRMA} AND belegart=11 AND aufkstat=0
    """)
    if cols_f090:
        log(f"\n  f090 aufkstat=0 sample columns: {', '.join(cols_f090)}")
        for row in rows_f090:
            vals = {cols_f090[i]: row[i] for i in range(len(cols_f090))}
            # Show non-null, non-zero, non-empty interesting fields
            interesting = {k: v for k, v in vals.items() if v is not None and v != 0 and v != '' and v != '0'}
            log(f"  row: {interesting}")

    # ============================================================
    # 5. BACKORDERS/BLOQUEADOS — more combinations
    # ============================================================
    log("\n=== BACKORDERS/BLOQUEADOS — más combinaciones ===")

    # a) Total bel=11 aufkstat=0 NOW (will be different from morning)
    for r in run(cur, "bel=11 aufkstat=0 total NOW", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.kzerl='0'
          AND h.belegart=11 AND h.aufkstat=0
    """):
        log(f"  bel=11 aufkstat=0 total: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # b) bel(6,7,11) kredlim, count bel=11 aufkstat=0
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
        for r in run(cur, "BLOQ bel(6,7,11) → bel=11 aufkstat<>8", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.belegart=11 AND h.aufkstat<>8
              AND h.kdnr IN ({','.join(str(k) for k in over_6711)})
        """):
            log(f"  BLOQ bel(6,7,11) kredlim → bel=11 aufkstat<>8: ords={r[0]}  pos={r[1]}  val={r[2]}")

        for r in run(cur, "BLOQ bel(6,7,11) → ALL bel aufkstat<>8", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.aufkstat<>8
              AND h.kdnr IN ({','.join(str(k) for k in over_6711)})
        """):
            log(f"  BLOQ bel(6,7,11) kredlim → ALL bel aufkstat<>8: ords={r[0]}  pos={r[1]}  val={r[2]}")

        for r in run(cur, "BLOQ bel(6,7,11) → bel=11 aufkstat=0", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.belegart=11 AND h.aufkstat=0
              AND h.kdnr IN ({','.join(str(k) for k in over_6711)})
        """):
            log(f"  BLOQ bel(6,7,11) kredlim → bel=11 aufkstat=0: ords={r[0]}  pos={r[1]}  val={r[2]}")

    if under_6711:
        for r in run(cur, "BACK bel(6,7,11) → bel=11 aufkstat=0", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.belegart=11 AND h.aufkstat=0
              AND h.kdnr IN ({','.join(str(k) for k in under_6711)})
        """):
            log(f"  BACK bel(6,7,11) kredlim → bel=11 aufkstat=0: ords={r[0]}  pos={r[1]}  val={r[2]}")

        for r in run(cur, "BACK bel(6,7,11) → bel=11 aufkstat<>8", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.belegart=11 AND h.aufkstat<>8
              AND h.kdnr IN ({','.join(str(k) for k in under_6711)})
        """):
            log(f"  BACK bel(6,7,11) kredlim → bel=11 aufkstat<>8: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # c) What about bel NOT IN (8,16)?
    totals_not8_16 = run(cur, "per-kdnr bel NOT IN(8,16) aufkstat<>8", f"""
        SELECT h.kdnr, SUM(p.poswert) total_open
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.kzerl='0'
          AND h.aufkstat<>8 AND h.belegart NOT IN (8,16)
        GROUP BY h.kdnr
    """)
    over_not = [r[0] for r in totals_not8_16 if kredlim_map.get(r[0],0)>0 and r[1] and r[1]>kredlim_map.get(r[0],0)]
    under_not = [r[0] for r in totals_not8_16 if not(kredlim_map.get(r[0],0)>0 and r[1] and r[1]>kredlim_map.get(r[0],0))]
    log(f"  bel NOT IN(8,16) over={len(over_not)}  under={len(under_not)}")

    if over_not:
        for r in run(cur, "BLOQ not(8,16) kredlim → bel=11 aufkstat<>8", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.belegart=11 AND h.aufkstat<>8
              AND h.kdnr IN ({','.join(str(k) for k in over_not)})
        """):
            log(f"  BLOQ NOT(8,16) kredlim → bel=11 aufkstat<>8: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # d) f090 ALL belegart aufkstat<>8 (use full exposure for kredlim check)
    totals_full = run(cur, "per-kdnr ALL bel aufkstat<>8", f"""
        SELECT h.kdnr, SUM(p.poswert) total_open
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.kzerl='0'
          AND h.aufkstat<>8
        GROUP BY h.kdnr
    """)
    over_full = [r[0] for r in totals_full if kredlim_map.get(r[0],0)>0 and r[1] and r[1]>kredlim_map.get(r[0],0)]
    under_full = [r[0] for r in totals_full if not(kredlim_map.get(r[0],0)>0 and r[1] and r[1]>kredlim_map.get(r[0],0))]
    log(f"  ALL bel aufkstat<>8 over={len(over_full)}  under={len(under_full)}")

    if over_full:
        for r in run(cur, "BLOQ ALL bel kredlim → bel=11 aufkstat<>8", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.belegart=11 AND h.aufkstat<>8
              AND h.kdnr IN ({','.join(str(k) for k in over_full)})
        """):
            log(f"  BLOQ ALL bel kredlim → bel=11 aufkstat<>8: ords={r[0]}  pos={r[1]}  val={r[2]}")

        for r in run(cur, "BLOQ ALL bel kredlim → bel=11 aufkstat=0", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.belegart=11 AND h.aufkstat=0
              AND h.kdnr IN ({','.join(str(k) for k in over_full)})
        """):
            log(f"  BLOQ ALL bel kredlim → bel=11 aufkstat=0: ords={r[0]}  pos={r[1]}  val={r[2]}")

    if under_full:
        for r in run(cur, "BACK ALL bel kredlim → bel=11 aufkstat=0", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.belegart=11 AND h.aufkstat=0
              AND h.kdnr IN ({','.join(str(k) for k in under_full)})
        """):
            log(f"  BACK ALL bel kredlim → bel=11 aufkstat=0: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # e) Try counting f090 HEADER only (no f092 join) for bloqueados
    totals_hdr = run(cur, "per-kdnr f090 only bel=11 aufkstat<>8", f"""
        SELECT kdnr, COUNT(*) total_ords
        FROM f090 WHERE firma={FIRMA} AND belegart=11 AND aufkstat<>8
        GROUP BY kdnr
    """)
    # (just for count comparison)
    log(f"  f090 header-only bel=11 aufkstat<>8 distinct kdnr: {len(totals_hdr)}")

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

    # Remitos: 2-step
    sb105_snap = run(cur, "snap sb105 kzerl=0", f"""
        SELECT liefnr, COUNT(*) pos, SUM(liefposwe) val
        FROM sb105 WHERE firma={FIRMA} AND kzerl='0'
        GROUP BY liefnr
    """)
    sbas_snap = run(cur, "snap sbas liefnr today", f"SELECT DISTINCT liefnr FROM sbas WHERE firma={FIRMA} AND redat=TODAY AND liefnr > 0")
    sbas_snap_set = {r[0] for r in sbas_snap}
    snap_not_invoiced = [(r[0],r[1],r[2]) for r in sb105_snap if r[0] not in sbas_snap_set]
    log(f"  [REMITOS sb105 kzerl=0 NOT in sbas TODAY] docs={len(snap_not_invoiced)}  pos={sum(r[1] for r in snap_not_invoiced)}  val={sum(r[2] for r in snap_not_invoiced if r[2]):.2f}")

    # Bloqueados (best so far: bel(6,7,11) kredlim → bel=11 aufkstat<>8)
    totals_s = run(cur, "snap per-kdnr bel(6,7,11)", f"""
        SELECT h.kdnr, SUM(p.poswert) total_open
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.kzerl='0'
          AND h.aufkstat<>8 AND h.belegart IN (6,7,11)
        GROUP BY h.kdnr
    """)
    over_s = [r[0] for r in totals_s if kredlim_map.get(r[0],0)>0 and r[1] and r[1]>kredlim_map.get(r[0],0)]
    under_s = [r[0] for r in totals_s if not(kredlim_map.get(r[0],0)>0 and r[1] and r[1]>kredlim_map.get(r[0],0))]

    if over_s:
        for r in run(cur, "snap bloqueados", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.belegart=11 AND h.aufkstat<>8
              AND h.kdnr IN ({','.join(str(k) for k in over_s)})
        """):
            log(f"  [BLOQUEADOS bel(6,7,11) kredlim] ords={r[0]}  pos={r[1]}  val={r[2]}")
    if under_s:
        for r in run(cur, "snap backorders", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.belegart=11 AND h.aufkstat<>8
              AND h.kdnr IN ({','.join(str(k) for k in under_s)})
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

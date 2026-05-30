"""
TagInfo v26 — remitos sb104 flags (kzsofort/kzprog/reflsnr), backords belegart IN (6,7,11).
SOLO LECTURA.
"""

import pyodbc
from datetime import date, datetime

DSN = "MSPA"
OUTPUT_FILE = "taginfo_v26.txt"
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

    log(f"TagInfo v26 — {datetime.now()}")
    log(f"DSN: {DSN}  |  Fecha: {today}  |  SOLO LECTURA")
    log("=" * 70)

    conn = get_conn()
    cur = conn.cursor()
    log("Conexión OK\n")

    kredlim_rows = run(cur, "kredlim", f"SELECT kdnr, kredlim FROM kund WHERE firma={FIRMA} AND kredlim > 0")
    kredlim_map = {r[0]: r[1] for r in kredlim_rows}

    # ============================================================
    # 1. sb104 FLAGS — kzsofort, kzprog, pagnr distributions
    # ============================================================
    log("=== sb104 FLAGS ===")

    for col in ['kzsofort', 'kzprog', 'pagnr']:
        for r in run(cur, f"sb104 {col} dist", f"""
            SELECT {col}, COUNT(*) cnt, COUNT(DISTINCT liefnr) docs
            FROM sb104 WHERE firma={FIRMA}
            GROUP BY {col} ORDER BY {col}
        """):
            log(f"  sb104.{col}={r[0]}  cnt={r[1]}  docs={r[2]}")

    # kzsofort=0 joined to sb105 (delivery pending)
    for r in run(cur, "sb104 kzsofort=0 + sb105", f"""
        SELECT COUNT(DISTINCT s4.liefnr) docs, COUNT(*) pos, SUM(s5.liefposwe) val
        FROM sb104 s4, sb105 s5
        WHERE s4.firma={FIRMA} AND s5.firma={FIRMA}
          AND s4.liefnr=s5.liefnr AND s4.kzsofort=0
    """):
        log(f"  sb104 kzsofort=0 +sb105: docs={r[0]}  pos={r[1]}  val={r[2]}")

    # kzprog=0 joined to sb105
    for r in run(cur, "sb104 kzprog=0 + sb105", f"""
        SELECT COUNT(DISTINCT s4.liefnr) docs, COUNT(*) pos, SUM(s5.liefposwe) val
        FROM sb104 s4, sb105 s5
        WHERE s4.firma={FIRMA} AND s5.firma={FIRMA}
          AND s4.liefnr=s5.liefnr AND s4.kzprog=0
    """):
        log(f"  sb104 kzprog=0 +sb105: docs={r[0]}  pos={r[1]}  val={r[2]}")

    # sb104 liefdat=TODAY — sum liefwe
    for r in run(cur, "sb104 liefdat=TODAY liefwe", f"""
        SELECT COUNT(*) cnt, SUM(liefwe) val FROM sb104
        WHERE firma={FIRMA} AND liefdat=TODAY
    """):
        log(f"  sb104 liefdat=TODAY: cnt={r[0]}  val={r[1]}")

    # sb104 kzsofort/kzprog TODAY
    for col in ['kzsofort', 'kzprog']:
        for r in run(cur, f"sb104 {col} dist TODAY", f"""
            SELECT {col}, COUNT(*) cnt, COUNT(DISTINCT liefnr) docs, SUM(liefwe) val
            FROM sb104 WHERE firma={FIRMA} AND liefdat=TODAY
            GROUP BY {col} ORDER BY {col}
        """):
            log(f"  sb104 TODAY {col}={r[0]}  cnt={r[1]}  docs={r[2]}  val={r[3]}")

    # ============================================================
    # 2. sb105 reflsnr — remitos no devueltos
    # ============================================================
    log("\n=== sb105 reflsnr distribution ===")

    for r in run(cur, "sb105 reflsnr dist", f"""
        SELECT reflsnr, COUNT(*) cnt
        FROM sb105 WHERE firma={FIRMA}
        GROUP BY reflsnr ORDER BY cnt DESC
    """):
        if r[0] is None or r[0] == 0:
            log(f"  sb105 reflsnr={r[0]}  cnt={r[1]}")

    for r in run(cur, "sb105 reflsnr IS NULL count", f"""
        SELECT COUNT(DISTINCT liefnr) docs, COUNT(*) pos, SUM(liefposwe) val
        FROM sb105 WHERE firma={FIRMA} AND reflsnr IS NULL
    """):
        log(f"  sb105 reflsnr IS NULL: docs={r[0]}  pos={r[1]}  val={r[2]}")

    for r in run(cur, "sb105 reflsnr=0 count", f"""
        SELECT COUNT(DISTINCT liefnr) docs, COUNT(*) pos, SUM(liefposwe) val
        FROM sb105 WHERE firma={FIRMA} AND reflsnr=0
    """):
        log(f"  sb105 reflsnr=0: docs={r[0]}  pos={r[1]}  val={r[2]}")

    # sb104 TODAY + sb105 reflsnr=0
    for r in run(cur, "sb104 TODAY + sb105 reflsnr=0", f"""
        SELECT COUNT(DISTINCT s4.liefnr) docs, COUNT(*) pos, SUM(s5.liefposwe) val
        FROM sb104 s4, sb105 s5
        WHERE s4.firma={FIRMA} AND s5.firma={FIRMA}
          AND s4.liefnr=s5.liefnr
          AND s4.liefdat=TODAY AND s5.reflsnr=0
    """):
        log(f"  sb104 TODAY + sb105 reflsnr=0: docs={r[0]}  pos={r[1]}  val={r[2]}")

    # sb104 TODAY + sb105 reflsnr IS NULL
    for r in run(cur, "sb104 TODAY + sb105 reflsnr IS NULL", f"""
        SELECT COUNT(DISTINCT s4.liefnr) docs, COUNT(*) pos, SUM(s5.liefposwe) val
        FROM sb104 s4, sb105 s5
        WHERE s4.firma={FIRMA} AND s5.firma={FIRMA}
          AND s4.liefnr=s5.liefnr
          AND s4.liefdat=TODAY AND s5.reflsnr IS NULL
    """):
        log(f"  sb104 TODAY + sb105 reflsnr IS NULL: docs={r[0]}  pos={r[1]}  val={r[2]}")

    # ============================================================
    # 3. BACKORDERS/BLOQUEADOS — belegart combos
    # ============================================================
    log("\n=== BACKORDERS/BLOQUEADOS — belegart combos ===")

    belegart_combos = [
        ("bel IN (6,7,11)",   "h.belegart IN (6,7,11)"),
        ("bel IN (7,11)",     "h.belegart IN (7,11)"),
        ("bel IN (6,11)",     "h.belegart IN (6,11)"),
        ("bel=11 only",       "h.belegart=11"),
        ("bel NOT IN (8,16)", "h.belegart NOT IN (8,16)"),
    ]

    for label, bel_where in belegart_combos:
        rows = run(cur, f"base {label} aufkstat<>8", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.aufkstat<>8 AND {bel_where}
        """)
        for r in rows:
            log(f"  [{label} aufkstat<>8]: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # Kredlim split for bel IN (6,7,11) aufkstat<>8
    log("\n--- Kredlim split bel IN (6,7,11) aufkstat<>8 ---")
    totals_c = run(cur, "per-kdnr bel(6,7,11)", f"""
        SELECT h.kdnr, SUM(p.poswert) total_open
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.kzerl='0'
          AND h.aufkstat<>8 AND h.belegart IN (6,7,11)
        GROUP BY h.kdnr
    """)
    over_c=[r[0] for r in totals_c if kredlim_map.get(r[0],0)>0 and r[1] and r[1]>kredlim_map.get(r[0],0)]
    under_c=[r[0] for r in totals_c if not(kredlim_map.get(r[0],0)>0 and r[1] and r[1]>kredlim_map.get(r[0],0))]
    log(f"  Customers={len(totals_c)}  over={len(over_c)}  under={len(under_c)}")
    if over_c:
        for r in run(cur, "BLOQ bel(6,7,11)", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.aufkstat<>8 AND h.belegart IN (6,7,11)
              AND h.kdnr IN ({','.join(str(k) for k in over_c)})
        """):
            log(f"  BLOQUEADOS bel(6,7,11): ords={r[0]}  pos={r[1]}  val={r[2]}")
    if under_c:
        for r in run(cur, "BACK bel(6,7,11)", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.aufkstat<>8 AND h.belegart IN (6,7,11)
              AND h.kdnr IN ({','.join(str(k) for k in under_c)})
        """):
            log(f"  BACKORDERS bel(6,7,11): ords={r[0]}  pos={r[1]}  val={r[2]}")

    # Also bel NOT IN (8,16)
    log("\n--- Kredlim split bel NOT IN (8,16) aufkstat<>8 ---")
    totals_d = run(cur, "per-kdnr bel NOT(8,16)", f"""
        SELECT h.kdnr, SUM(p.poswert) total_open
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.kzerl='0'
          AND h.aufkstat<>8 AND h.belegart NOT IN (8,16)
        GROUP BY h.kdnr
    """)
    over_d=[r[0] for r in totals_d if kredlim_map.get(r[0],0)>0 and r[1] and r[1]>kredlim_map.get(r[0],0)]
    under_d=[r[0] for r in totals_d if not(kredlim_map.get(r[0],0)>0 and r[1] and r[1]>kredlim_map.get(r[0],0))]
    log(f"  Customers={len(totals_d)}  over={len(over_d)}  under={len(under_d)}")
    if over_d:
        for r in run(cur, "BLOQ NOT(8,16)", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.aufkstat<>8 AND h.belegart NOT IN (8,16)
              AND h.kdnr IN ({','.join(str(k) for k in over_d)})
        """):
            log(f"  BLOQUEADOS NOT(8,16): ords={r[0]}  pos={r[1]}  val={r[2]}")
    if under_d:
        for r in run(cur, "BACK NOT(8,16)", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.aufkstat<>8 AND h.belegart NOT IN (8,16)
              AND h.kdnr IN ({','.join(str(k) for k in under_d)})
        """):
            log(f"  BACKORDERS NOT(8,16): ords={r[0]}  pos={r[1]}  val={r[2]}")

    # ============================================================
    # 4. SNAPSHOT COMPLETO
    # ============================================================
    log("\n=== SNAPSHOT COMPLETO ===")
    ts = datetime.now()

    for r in run(cur, "snap produccion", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND h.aufkstat=2 AND p.posstat=2 AND p.kzerl='0'
    """):
        log(f"  [PRODUCCION] ords={r[0]}  pos={r[1]}  val={r[2]}")

    for r in run(cur, "snap remitos sb105+posstat8", f"""
        SELECT COUNT(DISTINCT s5.liefnr) docs, COUNT(*) pos, SUM(s5.liefposwe) val
        FROM sb105 s5, f092 p WHERE s5.firma={FIRMA} AND p.firma={FIRMA}
          AND s5.auftrag=p.auftrag AND s5.posnr=p.posnr
          AND p.posstat=8 AND p.kzerl='0'
    """):
        log(f"  [REMITOS posstat=8 sb105] docs={r[0]}  pos={r[1]}  val={r[2]}")

    # Bloqueados/backorders best combo fresh
    totals_snap = run(cur, "snap per-kdnr bel(6,7,11)", f"""
        SELECT h.kdnr, SUM(p.poswert) total_open
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.kzerl='0'
          AND h.aufkstat<>8 AND h.belegart IN (6,7,11)
        GROUP BY h.kdnr
    """)
    over_s=[r[0] for r in totals_snap if kredlim_map.get(r[0],0)>0 and r[1] and r[1]>kredlim_map.get(r[0],0)]
    under_s=[r[0] for r in totals_snap if not(kredlim_map.get(r[0],0)>0 and r[1] and r[1]>kredlim_map.get(r[0],0))]
    if over_s:
        for r in run(cur, "snap bloqueados", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.aufkstat<>8 AND h.belegart IN (6,7,11)
              AND h.kdnr IN ({','.join(str(x) for x in over_s)})
        """):
            log(f"  [BLOQUEADOS bel(6,7,11)] ords={r[0]}  pos={r[1]}  val={r[2]}")
    if under_s:
        for r in run(cur, "snap backorders", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.aufkstat<>8 AND h.belegart IN (6,7,11)
              AND h.kdnr IN ({','.join(str(x) for x in under_s)})
        """):
            log(f"  [BACKORDERS bel(6,7,11)] ords={r[0]}  pos={r[1]}  val={r[2]}")

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

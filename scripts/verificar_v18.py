"""
TagInfo v18 — remitos posstat, backorders termin, bloqueados 2-step Python.
SOLO LECTURA.
"""

import pyodbc
from datetime import date, datetime

DSN = "MSPA"
OUTPUT_FILE = "taginfo_v18.txt"
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

    log(f"TagInfo v18 — {datetime.now()}")
    log(f"DSN: {DSN}  |  Fecha: {today}  |  SOLO LECTURA")
    log("=" * 70)

    conn = get_conn()
    cur = conn.cursor()
    log("Conexión OK\n")

    # ============================================================
    # 1. REMITOS — refrenr IS NULL (fix from v17)
    # ============================================================
    log("=== REMITOS — kzlsdru=2 refrenr IS NULL ===")

    for r in run(cur, "remitos kzlsdru2 refrenr NULL all", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND p.kzlsdru = 2 AND p.refrenr IS NULL AND p.kzerl = '0'
    """):
        log(f"  kzlsdru=2 refrenr IS NULL all posstat: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # Distribution by posstat for kzlsdru=2 refrenr IS NULL
    log("\nkzlsdru=2 refrenr IS NULL — posstat distribution:")
    for r in run(cur, "kzlsdru2 NULL posstat dist", f"""
        SELECT p.posstat, COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND p.kzlsdru = 2 AND p.refrenr IS NULL AND p.kzerl = '0'
        GROUP BY p.posstat
        ORDER BY p.posstat
    """):
        log(f"  posstat={r[0]}  ords={r[1]}  pos={r[2]}  val={r[3]}")

    # posstat=8 specifically (shipped/ausgeliefert)
    for r in run(cur, "posstat8 all", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND p.posstat = 8 AND p.kzerl = '0'
    """):
        log(f"  posstat=8 all: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # kzlsdru=2 AND posstat=8
    for r in run(cur, "kzlsdru2 posstat8", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND p.kzlsdru = 2 AND p.posstat = 8 AND p.kzerl = '0'
    """):
        log(f"  kzlsdru=2 posstat=8: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # posstat=8 AND refrenr IS NULL
    for r in run(cur, "posstat8 refrenr NULL", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND p.posstat = 8 AND p.refrenr IS NULL AND p.kzerl = '0'
    """):
        log(f"  posstat=8 refrenr IS NULL: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # All posstat distribution (with kzerl='0')
    log("\nAll posstat distribution (kzerl='0'):")
    for r in run(cur, "posstat all dist", f"""
        SELECT p.posstat, COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag AND p.kzerl = '0'
        GROUP BY p.posstat
        ORDER BY p.posstat
    """):
        log(f"  posstat={r[0]}  ords={r[1]}  pos={r[2]}")

    # ============================================================
    # 2. BACKORDERS — termin < TODAY
    # ============================================================
    log("\n=== BACKORDERS — termin distribution ===")

    for r in run(cur, "aufkstat0 termin<TODAY", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND h.aufkstat = 0 AND p.posstat = 0 AND p.kzerl = '0'
          AND h.termin < TODAY
    """):
        log(f"  aufkstat=0 termin<TODAY: ords={r[0]}  pos={r[1]}  val={r[2]}")

    for r in run(cur, "aufkstat0 termin=TODAY", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND h.aufkstat = 0 AND p.posstat = 0 AND p.kzerl = '0'
          AND h.termin = TODAY
    """):
        log(f"  aufkstat=0 termin=TODAY: ords={r[0]}  pos={r[1]}  val={r[2]}")

    for r in run(cur, "aufkstat0 termin>TODAY", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND h.aufkstat = 0 AND p.posstat = 0 AND p.kzerl = '0'
          AND h.termin > TODAY
    """):
        log(f"  aufkstat=0 termin>TODAY: ords={r[0]}  pos={r[1]}  val={r[2]}")

    log("\naufkstat=0 termin distribution:")
    for r in run(cur, "aufkstat0 termin dist", f"""
        SELECT h.termin, COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND h.aufkstat = 0 AND p.posstat = 0 AND p.kzerl = '0'
        GROUP BY h.termin
        ORDER BY h.termin
    """):
        log(f"  termin={r[0]}  ords={r[1]}  pos={r[2]}")

    # ============================================================
    # 3. BLOQUEADOS — 2-step Python approach
    # ============================================================
    log("\n=== BLOQUEADOS — 2-step Python ===")

    # Step 1: per-customer total open
    totals_rows = run(cur, "kdnr open totals", f"""
        SELECT h.kdnr, SUM(p.poswert) total_open
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND h.aufkstat = 0 AND p.posstat = 0 AND p.kzerl = '0'
        GROUP BY h.kdnr
    """)
    log(f"  Step1: {len(totals_rows)} customers with open orders")

    # Step 2: kredlim per customer
    kredlim_rows = run(cur, "kredlim per kdnr", f"""
        SELECT kdnr, kredlim FROM kund
        WHERE firma = {FIRMA} AND kredlim > 0
    """)
    kredlim_map = {r[0]: r[1] for r in kredlim_rows}
    log(f"  Step2: {len(kredlim_map)} customers with kredlim>0")

    # Step 3: calculate in Python
    over_limit_kdnr = []
    under_limit_kdnr = []
    for r in totals_rows:
        kdnr, total_open = r[0], r[1]
        kl = kredlim_map.get(kdnr, 0)
        if kl > 0 and total_open is not None and total_open > kl:
            over_limit_kdnr.append(kdnr)
        else:
            under_limit_kdnr.append(kdnr)

    log(f"  Python calc: over_limit={len(over_limit_kdnr)}  under_limit={len(under_limit_kdnr)}")

    # Step 4: query for over-limit customers
    if over_limit_kdnr:
        in_list = ','.join(str(k) for k in over_limit_kdnr)
        for r in run(cur, "bloq IN over_limit", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p
            WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
              AND h.auftrag = p.auftrag
              AND h.aufkstat = 0 AND p.posstat = 0 AND p.kzerl = '0'
              AND h.kdnr IN ({in_list})
        """):
            log(f"  BLOQUEADOS: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # Step 5: under-limit — split by termin for backorders
    if under_limit_kdnr:
        in_list2 = ','.join(str(k) for k in under_limit_kdnr)
        for r in run(cur, "backord under_limit termin<TODAY", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p
            WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
              AND h.auftrag = p.auftrag
              AND h.aufkstat = 0 AND p.posstat = 0 AND p.kzerl = '0'
              AND h.kdnr IN ({in_list2})
              AND h.termin < TODAY
        """):
            log(f"  BACKORDERS (under_limit + termin<TODAY): ords={r[0]}  pos={r[1]}  val={r[2]}")

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

    for r in run(cur, "snap remitos posstat8", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND p.posstat = 8 AND p.refrenr IS NULL AND p.kzerl = '0'
    """):
        log(f"  [REMITOS posstat=8 refrenr NULL] ords={r[0]}  pos={r[1]}  val={r[2]}")

    if over_limit_kdnr:
        in_list = ','.join(str(k) for k in over_limit_kdnr)
        for r in run(cur, "snap bloqueados", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p
            WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
              AND h.auftrag = p.auftrag
              AND h.aufkstat = 0 AND p.posstat = 0 AND p.kzerl = '0'
              AND h.kdnr IN ({in_list})
        """):
            log(f"  [BLOQUEADOS] ords={r[0]}  pos={r[1]}  val={r[2]}")

    if under_limit_kdnr:
        in_list2 = ','.join(str(k) for k in under_limit_kdnr)
        for r in run(cur, "snap backorders", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p
            WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
              AND h.auftrag = p.auftrag
              AND h.aufkstat = 0 AND p.posstat = 0 AND p.kzerl = '0'
              AND h.kdnr IN ({in_list2})
              AND h.termin < TODAY
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

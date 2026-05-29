"""
TagInfo v17 — remitos kzlsdru=2+refrenr=0, bloqueados via derived table.
SOLO LECTURA.
"""

import pyodbc
from datetime import date, datetime

DSN = "MSPA"
OUTPUT_FILE = "taginfo_v17.txt"
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

    log(f"TagInfo v17 — {datetime.now()}")
    log(f"DSN: {DSN}  |  Fecha: {today}  |  SOLO LECTURA")
    log("=" * 70)

    conn = get_conn()
    cur = conn.cursor()
    log("Conexión OK\n")

    # ============================================================
    # 1. REMITOS — kzlsdru=2 AND refrenr=0 (sin factura)
    # ============================================================
    log("=== REMITOS — kzlsdru=2 refrenr=0 ===")

    for r in run(cur, "remitos kzlsdru2 refrenr0", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND p.kzlsdru = 2
          AND p.refrenr = 0
          AND p.kzerl = '0'
    """):
        log(f"  kzlsdru=2 refrenr=0: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # kzlsdru=2 sin importar refrenr
    for r in run(cur, "remitos kzlsdru2 all", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND p.kzlsdru = 2
          AND p.kzerl = '0'
    """):
        log(f"  kzlsdru=2 all: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # kzlsdru=2 refrenr dist
    log("\nkzlsdru=2 refrenr distribution:")
    for r in run(cur, "kzlsdru2 refrenr dist", f"""
        SELECT refrenr, COUNT(*) cnt, COUNT(DISTINCT auftrag) ords
        FROM f092
        WHERE firma = {FIRMA} AND kzerl = '0' AND kzlsdru = 2
        GROUP BY refrenr
        ORDER BY refrenr
    """):
        log(f"  refrenr={r[0]}  cnt={r[1]}  ords={r[2]}")

    # kzlsdru=2 refrenr=0 por aufkstat
    log("\nkzlsdru=2 refrenr=0 por aufkstat:")
    for r in run(cur, "kzlsdru2 por aufkstat", f"""
        SELECT h.aufkstat, COUNT(DISTINCT h.auftrag) ords,
               COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND p.kzlsdru = 2 AND p.refrenr = 0
          AND p.kzerl = '0'
        GROUP BY h.aufkstat
        ORDER BY h.aufkstat
    """):
        log(f"  aufkstat={r[0]}  ords={r[1]}  pos={r[2]}  val={r[3]}")

    # ============================================================
    # 2. BLOQUEADOS — derived table approach (Informix compatible)
    # ============================================================
    log("\n=== BLOQUEADOS — derived table totals ===")

    for r in run(cur, "bloq derived>kredlim", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p, kund k,
             (SELECT h2.kdnr kdnr2, SUM(p2.poswert) total_open
              FROM f090 h2, f092 p2
              WHERE h2.firma = {FIRMA} AND p2.firma = {FIRMA}
                AND h2.auftrag = p2.auftrag
                AND h2.aufkstat = 0 AND p2.posstat = 0 AND p2.kzerl = '0'
              GROUP BY h2.kdnr) totals
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA} AND k.firma = {FIRMA}
          AND h.auftrag = p.auftrag AND h.kdnr = k.kdnr
          AND h.kdnr = totals.kdnr2
          AND h.aufkstat = 0 AND p.posstat = 0 AND p.kzerl = '0'
          AND totals.total_open > k.kredlim
    """):
        log(f"  derived open>kredlim: ords={r[0]}  pos={r[1]}  val={r[2]}")

    for r in run(cur, "back derived<=kredlim", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p, kund k,
             (SELECT h2.kdnr kdnr2, SUM(p2.poswert) total_open
              FROM f090 h2, f092 p2
              WHERE h2.firma = {FIRMA} AND p2.firma = {FIRMA}
                AND h2.auftrag = p2.auftrag
                AND h2.aufkstat = 0 AND p2.posstat = 0 AND p2.kzerl = '0'
              GROUP BY h2.kdnr) totals
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA} AND k.firma = {FIRMA}
          AND h.auftrag = p.auftrag AND h.kdnr = k.kdnr
          AND h.kdnr = totals.kdnr2
          AND h.aufkstat = 0 AND p.posstat = 0 AND p.kzerl = '0'
          AND totals.total_open <= k.kredlim
    """):
        log(f"  derived open<=kredlim: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # Verify: bloqueados + backorders should equal total aufkstat=0
    for r in run(cur, "aufkstat0 total", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND h.aufkstat = 0 AND p.posstat = 0 AND p.kzerl = '0'
    """):
        log(f"  aufkstat=0 total: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # ============================================================
    # 3. STATUS < -1
    # ============================================================
    log("\n=== STATUS < -1 ===")

    for r in run(cur, "aufkstat<-1", f"""
        SELECT h.aufkstat, COUNT(DISTINCT h.auftrag) ords,
               COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND h.aufkstat < -1 AND p.kzerl = '0'
        GROUP BY h.aufkstat
        ORDER BY h.aufkstat
    """):
        log(f"  aufkstat={r[0]}  ords={r[1]}  pos={r[2]}  val={r[3]}")

    # Try with posstat filter too
    for r in run(cur, "aufkstat<-1 posstat0", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND h.aufkstat < -1 AND p.posstat = 0 AND p.kzerl = '0'
    """):
        log(f"  aufkstat<-1 posstat=0: ords={r[0]}  pos={r[1]}  val={r[2]}")

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

    for r in run(cur, "snap remitos kzlsdru2", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND p.kzlsdru = 2 AND p.refrenr = 0 AND p.kzerl = '0'
    """):
        log(f"  [REMITOS kzlsdru=2 refrenr=0] ords={r[0]}  pos={r[1]}  val={r[2]}")

    for r in run(cur, "snap bloqueados", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p, kund k,
             (SELECT h2.kdnr kdnr2, SUM(p2.poswert) total_open
              FROM f090 h2, f092 p2
              WHERE h2.firma = {FIRMA} AND p2.firma = {FIRMA}
                AND h2.auftrag = p2.auftrag
                AND h2.aufkstat = 0 AND p2.posstat = 0 AND p2.kzerl = '0'
              GROUP BY h2.kdnr) totals
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA} AND k.firma = {FIRMA}
          AND h.auftrag = p.auftrag AND h.kdnr = k.kdnr
          AND h.kdnr = totals.kdnr2
          AND h.aufkstat = 0 AND p.posstat = 0 AND p.kzerl = '0'
          AND totals.total_open > k.kredlim
    """):
        log(f"  [BLOQUEADOS derived>kredlim] ords={r[0]}  pos={r[1]}  val={r[2]}")

    for r in run(cur, "snap backorders", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p, kund k,
             (SELECT h2.kdnr kdnr2, SUM(p2.poswert) total_open
              FROM f090 h2, f092 p2
              WHERE h2.firma = {FIRMA} AND p2.firma = {FIRMA}
                AND h2.auftrag = p2.auftrag
                AND h2.aufkstat = 0 AND p2.posstat = 0 AND p2.kzerl = '0'
              GROUP BY h2.kdnr) totals
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA} AND k.firma = {FIRMA}
          AND h.auftrag = p.auftrag AND h.kdnr = k.kdnr
          AND h.kdnr = totals.kdnr2
          AND h.aufkstat = 0 AND p.posstat = 0 AND p.kzerl = '0'
          AND totals.total_open <= k.kredlim
    """):
        log(f"  [BACKORDERS derived<=kredlim] ords={r[0]}  pos={r[1]}  val={r[2]}")

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

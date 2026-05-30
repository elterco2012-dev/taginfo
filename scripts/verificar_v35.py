"""
TagInfo v35 - TERMIN FILTER: Backorders/Bloqueados usan termin?
"Plazos viejos" = termin <= TODAY? termin < TODAY? termin = TODAY?
Distribucion de termin en los ordenes aufkstat=0 bel(6,7,11).
SOLO LECTURA.
"""

import pyodbc
from datetime import date, datetime

DSN = "MSPA"
OUTPUT_FILE = "taginfo_v35.txt"
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

    log(f"TagInfo v35 - TERMIN FILTER - {datetime.now()}")
    log(f"DSN: {DSN}  |  Fecha: {today}  |  SOLO LECTURA")
    log("=" * 70)

    conn = get_conn()
    cur = conn.cursor()
    log("Conexion OK\n")

    # Kredlim setup
    kredlim_rows = run(cur, "kredlim", f"SELECT kdnr, kredlim FROM kund WHERE firma={FIRMA} AND kredlim > 0")
    kredlim_map = {r[0]: r[1] for r in kredlim_rows}

    totals_6711 = run(cur, "per-kdnr bel(6,7,11)", f"""
        SELECT h.kdnr, SUM(p.poswert)
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.kzerl='0'
          AND h.aufkstat<>8 AND h.belegart IN (6,7,11)
        GROUP BY h.kdnr
    """)
    over  = [r[0] for r in totals_6711 if kredlim_map.get(r[0],0)>0 and r[1] and r[1]>kredlim_map.get(r[0],0)]
    under = [r[0] for r in totals_6711 if not(kredlim_map.get(r[0],0)>0 and r[1] and r[1]>kredlim_map.get(r[0],0))]
    log(f"  over_kredlim={len(over)}  under_kredlim={len(under)}\n")

    def fmt_in(lst): return ",".join(str(k) for k in lst)

    # ============================================================
    # 1. DISTRIBUCION DE TERMIN en bel(6,7,11) aufkstat=0 kzerl='0'
    # ============================================================
    log("=== DISTRIBUCION termin en bel(6,7,11) aufkstat=0 ===")

    # termin distribution: past / today / future
    for r in run(cur, "termin < TODAY", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.kzerl='0'
          AND h.aufkstat=0 AND h.belegart IN (6,7,11)
          AND p.termin < TODAY
    """):
        log(f"  termin < TODAY: ords={r[0]}  pos={r[1]}  val={r[2]}")

    for r in run(cur, "termin = TODAY", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.kzerl='0'
          AND h.aufkstat=0 AND h.belegart IN (6,7,11)
          AND p.termin = TODAY
    """):
        log(f"  termin = TODAY: ords={r[0]}  pos={r[1]}  val={r[2]}")

    for r in run(cur, "termin <= TODAY", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.kzerl='0'
          AND h.aufkstat=0 AND h.belegart IN (6,7,11)
          AND p.termin <= TODAY
    """):
        log(f"  termin <= TODAY: ords={r[0]}  pos={r[1]}  val={r[2]}")

    for r in run(cur, "termin > TODAY", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.kzerl='0'
          AND h.aufkstat=0 AND h.belegart IN (6,7,11)
          AND p.termin > TODAY
    """):
        log(f"  termin > TODAY: ords={r[0]}  pos={r[1]}  val={r[2]}")

    for r in run(cur, "termin IS NULL", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.kzerl='0'
          AND h.aufkstat=0 AND h.belegart IN (6,7,11)
          AND p.termin IS NULL
    """):
        log(f"  termin IS NULL: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # ============================================================
    # 2. BACKORDERS con distintos filtros de termin (NOT IN over)
    # ============================================================
    log("\n=== BACKORDERS (NOT IN over) con filtros termin ===")

    if over:
        for r in run(cur, "BACK termin<TODAY NOT IN over", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.aufkstat=0 AND h.belegart IN (6,7,11)
              AND p.termin < TODAY
              AND h.kdnr NOT IN ({fmt_in(over)})
        """):
            log(f"  termin<TODAY NOT IN over: ords={r[0]}  pos={r[1]}  val={r[2]}")

        for r in run(cur, "BACK termin=TODAY NOT IN over", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.aufkstat=0 AND h.belegart IN (6,7,11)
              AND p.termin = TODAY
              AND h.kdnr NOT IN ({fmt_in(over)})
        """):
            log(f"  termin=TODAY NOT IN over: ords={r[0]}  pos={r[1]}  val={r[2]}")

        for r in run(cur, "BACK termin<=TODAY NOT IN over", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.aufkstat=0 AND h.belegart IN (6,7,11)
              AND p.termin <= TODAY
              AND h.kdnr NOT IN ({fmt_in(over)})
        """):
            log(f"  termin<=TODAY NOT IN over: ords={r[0]}  pos={r[1]}  val={r[2]}")

        for r in run(cur, "BACK no-termin NOT IN over", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.aufkstat=0 AND h.belegart IN (6,7,11)
              AND h.kdnr NOT IN ({fmt_in(over)})
        """):
            log(f"  no-termin NOT IN over: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # ============================================================
    # 3. BLOQUEADOS con distintos filtros de termin (IN over)
    # ============================================================
    log("\n=== BLOQUEADOS (IN over) con filtros termin ===")

    if over:
        for r in run(cur, "BLOQ termin<TODAY IN over", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.aufkstat=0 AND h.belegart IN (6,7,11)
              AND p.termin < TODAY
              AND h.kdnr IN ({fmt_in(over)})
        """):
            log(f"  termin<TODAY IN over: ords={r[0]}  pos={r[1]}  val={r[2]}")

        for r in run(cur, "BLOQ termin=TODAY IN over", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.aufkstat=0 AND h.belegart IN (6,7,11)
              AND p.termin = TODAY
              AND h.kdnr IN ({fmt_in(over)})
        """):
            log(f"  termin=TODAY IN over: ords={r[0]}  pos={r[1]}  val={r[2]}")

        for r in run(cur, "BLOQ termin<=TODAY IN over", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.aufkstat=0 AND h.belegart IN (6,7,11)
              AND p.termin <= TODAY
              AND h.kdnr IN ({fmt_in(over)})
        """):
            log(f"  termin<=TODAY IN over: ords={r[0]}  pos={r[1]}  val={r[2]}")

        for r in run(cur, "BLOQ no-termin IN over", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.aufkstat=0 AND h.belegart IN (6,7,11)
              AND h.kdnr IN ({fmt_in(over)})
        """):
            log(f"  no-termin IN over: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # ============================================================
    # 4. SNAPSHOT SIMULTANEO
    # ============================================================
    print("\n*** TOMAR SCREENSHOT DE PANTALLA AHORA ***\n")
    log("\n=== SNAPSHOT SIMULTANEO ===")
    ts = datetime.now()
    log(f"  Timestamp: {ts}")

    # BACKORDERS: los 4 candidatos
    if over:
        for r in run(cur, "BACK termin<TODAY", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.aufkstat=0 AND h.belegart IN (6,7,11)
              AND p.termin < TODAY AND h.kdnr NOT IN ({fmt_in(over)})
        """):
            log(f"  [BACK termin<TODAY] ords={r[0]}  pos={r[1]}  val={r[2]}")

        for r in run(cur, "BACK termin<=TODAY", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.aufkstat=0 AND h.belegart IN (6,7,11)
              AND p.termin <= TODAY AND h.kdnr NOT IN ({fmt_in(over)})
        """):
            log(f"  [BACK termin<=TODAY] ords={r[0]}  pos={r[1]}  val={r[2]}")

    # BLOQUEADOS: los 4 candidatos
    if over:
        for r in run(cur, "BLOQ termin<TODAY", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.aufkstat=0 AND h.belegart IN (6,7,11)
              AND p.termin < TODAY AND h.kdnr IN ({fmt_in(over)})
        """):
            log(f"  [BLOQ termin<TODAY] ords={r[0]}  pos={r[1]}  val={r[2]}")

        for r in run(cur, "BLOQ termin<=TODAY", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.aufkstat=0 AND h.belegart IN (6,7,11)
              AND p.termin <= TODAY AND h.kdnr IN ({fmt_in(over)})
        """):
            log(f"  [BLOQ termin<=TODAY] ords={r[0]}  pos={r[1]}  val={r[2]}")

        for r in run(cur, "BLOQ no-termin", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.aufkstat=0 AND h.belegart IN (6,7,11)
              AND h.kdnr IN ({fmt_in(over)})
        """):
            log(f"  [BLOQ no-termin] ords={r[0]}  pos={r[1]}  val={r[2]}")

    # REMITOS, PRODUCCION, VENTA
    for r in run(cur, "REMITOS", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND h.belegart=11 AND h.aufkstat=4
    """):
        log(f"  [REMITOS aufkstat=4] ords={r[0]}  pos={r[1]}  val={r[2]}")

    for r in run(cur, "PRODUCCION", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND h.aufkstat=2 AND p.posstat=2 AND p.kzerl='0'
    """):
        log(f"  [PRODUCCION] ords={r[0]}  pos={r[1]}  val={r[2]}")

    for r in run(cur, "VENTA", f"""
        SELECT COUNT(DISTINCT renr) docs, COUNT(*) pos, SUM(netwert) val
        FROM sbas WHERE firma={FIRMA} AND redat=TODAY AND belegart IN (8,11)
    """):
        log(f"  [VENTA] docs={r[0]}  pos={r[1]}  val={r[2]}")

    log(f"  End Timestamp: {datetime.now()}")

    conn.close()

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\nListo -> {OUTPUT_FILE}")


if __name__ == "__main__":
    main()

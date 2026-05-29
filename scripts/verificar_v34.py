"""
TagInfo v34 — Hipótesis final: Backorders=bel=7 aufkstat=0? Bloqueados=bel=11 aufkstat=0 over-limit?
Analizar la composición exacta belegart x aufkstat x kredlim.
SOLO LECTURA.
"""

import pyodbc
from datetime import date, datetime

DSN = "MSPA"
OUTPUT_FILE = "taginfo_v34.txt"
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

    log(f"TagInfo v34 — {datetime.now()}")
    log(f"DSN: {DSN}  |  Fecha: {today}  |  SOLO LECTURA")
    log("=" * 70)

    conn = get_conn()
    cur = conn.cursor()
    log("Conexión OK\n")

    kredlim_rows = run(cur, "kredlim", f"SELECT kdnr, kredlim FROM kund WHERE firma={FIRMA} AND kredlim > 0")
    kredlim_map = {r[0]: r[1] for r in kredlim_rows}

    # ============================================================
    # 1. ANALISIS COMPLETO DE aufkstat=0 por belegart
    # ============================================================
    log("=== aufkstat=0 por belegart y credlim ===")

    # All aufkstat=0 by belegart NOW
    for r in run(cur, "aufkstat=0 belegart dist NOW", f"""
        SELECT h.belegart, COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.kzerl='0'
          AND h.aufkstat=0
        GROUP BY h.belegart ORDER BY h.belegart
    """):
        log(f"  belegart={r[0]}  ords={r[1]}  pos={r[2]}  val={r[3]}")

    # Total aufkstat=0 all belegart
    for r in run(cur, "aufkstat=0 TOTAL all belegart", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.kzerl='0'
          AND h.aufkstat=0
    """):
        log(f"  TOTAL aufkstat=0 all bel: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # ============================================================
    # 2. BACKORDERS — hipótesis: bel=7 aufkstat=0 (OR bel NOT IN (8,16) aufkstat=0)?
    # ============================================================
    log("\n=== BACKORDERS — hipótesis belegart ===")

    # bel=7 aufkstat=0 only
    for r in run(cur, "bel=7 aufkstat=0", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.kzerl='0'
          AND h.aufkstat=0 AND h.belegart=7
    """):
        log(f"  bel=7 aufkstat=0: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # bel IN (6,7) aufkstat=0 (plazos = standard orders?)
    for r in run(cur, "bel IN(6,7) aufkstat=0", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.kzerl='0'
          AND h.aufkstat=0 AND h.belegart IN (6,7)
    """):
        log(f"  bel IN(6,7) aufkstat=0: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # bel=11 aufkstat=0 all customers (no kredlim split)
    for r in run(cur, "bel=11 aufkstat=0 ALL", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.kzerl='0'
          AND h.aufkstat=0 AND h.belegart=11
    """):
        log(f"  bel=11 aufkstat=0 ALL: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # bel NOT IN (8,16) aufkstat=0
    for r in run(cur, "bel NOT IN(8,16) aufkstat=0", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.kzerl='0'
          AND h.aufkstat=0 AND h.belegart NOT IN (8,16)
    """):
        log(f"  bel NOT IN(8,16) aufkstat=0: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # ============================================================
    # 3. CREDIT LIMIT — different bases for bloqueados
    # ============================================================
    log("\n=== CREDIT LIMIT — bases diferentes ===")

    # Base: bel=11 aufkstat<>8 (only sales orders)
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

    # Bloqueados: over_b11 → bel=11 aufkstat=0
    if over_b11:
        for r in run(cur, "BLOQ bel=11 base → bel=11 aufkstat=0", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.aufkstat=0 AND h.belegart=11
              AND h.kdnr IN ({','.join(str(k) for k in over_b11)})
        """):
            log(f"  BLOQ bel=11 kredlim→bel=11 aufkstat=0: ords={r[0]}  pos={r[1]}  val={r[2]}")

        for r in run(cur, "BLOQ bel=11 base → bel IN(6,7,11) aufkstat=0", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.aufkstat=0 AND h.belegart IN (6,7,11)
              AND h.kdnr IN ({','.join(str(k) for k in over_b11)})
        """):
            log(f"  BLOQ bel=11 kredlim→bel(6,7,11) aufkstat=0: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # Base: bel(6,7,11) aufkstat<>8
    totals_6711 = run(cur, "per-kdnr bel(6,7,11) aufkstat<>8", f"""
        SELECT h.kdnr, SUM(p.poswert) total_open
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.kzerl='0'
          AND h.aufkstat<>8 AND h.belegart IN (6,7,11)
        GROUP BY h.kdnr
    """)
    over_6711 = [r[0] for r in totals_6711 if kredlim_map.get(r[0],0)>0 and r[1] and r[1]>kredlim_map.get(r[0],0)]
    under_6711 = [r[0] for r in totals_6711 if not(kredlim_map.get(r[0],0)>0 and r[1] and r[1]>kredlim_map.get(r[0],0))]
    log(f"  bel(6,7,11) aufkstat<>8 over={len(over_6711)}  under={len(under_6711)}")

    if over_6711:
        # Bloqueados: bel=11 aufkstat=0 (just positions from bel=11)
        for r in run(cur, "BLOQ bel(6,7,11) base → bel=11 aufkstat=0", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.aufkstat=0 AND h.belegart=11
              AND h.kdnr IN ({','.join(str(k) for k in over_6711)})
        """):
            log(f"  BLOQ bel(6,7,11) kredlim→bel=11 aufkstat=0: ords={r[0]}  pos={r[1]}  val={r[2]}")

        # Bloqueados: bel(6,7,11) aufkstat=0
        for r in run(cur, "BLOQ bel(6,7,11) base → bel(6,7,11) aufkstat=0", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.aufkstat=0 AND h.belegart IN (6,7,11)
              AND h.kdnr IN ({','.join(str(k) for k in over_6711)})
        """):
            log(f"  BLOQ bel(6,7,11) kredlim→bel(6,7,11) aufkstat=0: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # ============================================================
    # 4. BACKORDERS — using NOT IN over_6711 (captures all under-limit)
    # ============================================================
    log("\n=== BACKORDERS — usando NOT IN over_6711 ===")

    if over_6711:
        # All bel=11 aufkstat=0 NOT in over-limit
        for r in run(cur, "bel=11 aufkstat=0 NOT IN over_6711", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.aufkstat=0 AND h.belegart=11
              AND h.kdnr NOT IN ({','.join(str(k) for k in over_6711)})
        """):
            log(f"  bel=11 aufkstat=0 NOT IN over_6711: ords={r[0]}  pos={r[1]}  val={r[2]}")

        # bel(6,7,11) aufkstat=0 NOT in over-limit
        for r in run(cur, "bel(6,7,11) aufkstat=0 NOT IN over_6711", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.aufkstat=0 AND h.belegart IN (6,7,11)
              AND h.kdnr NOT IN ({','.join(str(k) for k in over_6711)})
        """):
            log(f"  bel(6,7,11) aufkstat=0 NOT IN over_6711: ords={r[0]}  pos={r[1]}  val={r[2]}")

    if over_b11:
        for r in run(cur, "bel=11 aufkstat=0 NOT IN over_b11", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.aufkstat=0 AND h.belegart=11
              AND h.kdnr NOT IN ({','.join(str(k) for k in over_b11)})
        """):
            log(f"  bel=11 aufkstat=0 NOT IN over_b11: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # ============================================================
    # 5. SNAPSHOT SIMULTANEO — tomar screenshot ahora
    # ============================================================
    print("\n*** TOMAR SCREENSHOT DE PANTALLA AHORA ***\n")
    log("\n=== SNAPSHOT SIMULTANEO ===")
    ts = datetime.now()
    log(f"  Timestamp: {ts}")

    # REMITOS
    for r in run(cur, "REMITOS", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND h.belegart=11 AND h.aufkstat=4
    """):
        log(f"  [REMITOS aufkstat=4] ords={r[0]}  pos={r[1]}  val={r[2]}")

    # PRODUCCION
    for r in run(cur, "PRODUCCION", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND h.aufkstat=2 AND p.posstat=2 AND p.kzerl='0'
    """):
        log(f"  [PRODUCCION] ords={r[0]}  pos={r[1]}  val={r[2]}")

    # BLOQUEADOS — try several
    if over_6711:
        for r in run(cur, "BLOQ bel(6,7,11)→bel(6,7,11) aufkstat=0", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.aufkstat=0 AND h.belegart IN (6,7,11)
              AND h.kdnr IN ({','.join(str(k) for k in over_6711)})
        """):
            log(f"  [BLOQ bel(6,7,11)kredlim→bel(6,7,11)aufkstat=0] ords={r[0]}  pos={r[1]}  val={r[2]}")

        for r in run(cur, "BLOQ bel(6,7,11)→bel=11 aufkstat=0", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.aufkstat=0 AND h.belegart=11
              AND h.kdnr IN ({','.join(str(k) for k in over_6711)})
        """):
            log(f"  [BLOQ bel(6,7,11)kredlim→bel=11 aufkstat=0] ords={r[0]}  pos={r[1]}  val={r[2]}")

    # BACKORDERS
    if over_6711:
        for r in run(cur, "BACK bel=11 aufkstat=0 NOT IN over", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.aufkstat=0 AND h.belegart=11
              AND h.kdnr NOT IN ({','.join(str(k) for k in over_6711)})
        """):
            log(f"  [BACK bel=11 aufkstat=0 NOT IN over_6711] ords={r[0]}  pos={r[1]}  val={r[2]}")

        for r in run(cur, "BACK bel(6,7,11) aufkstat=0 NOT IN over", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.aufkstat=0 AND h.belegart IN (6,7,11)
              AND h.kdnr NOT IN ({','.join(str(k) for k in over_6711)})
        """):
            log(f"  [BACK bel(6,7,11) aufkstat=0 NOT IN over_6711] ords={r[0]}  pos={r[1]}  val={r[2]}")

    # VENTA
    for r in run(cur, "VENTA", f"""
        SELECT COUNT(DISTINCT renr) docs, COUNT(*) pos, SUM(netwert) val
        FROM sbas WHERE firma={FIRMA} AND redat=TODAY AND belegart IN (8,11)
    """):
        log(f"  [VENTA] docs={r[0]}  pos={r[1]}  val={r[2]}")

    log(f"  End Timestamp: {datetime.now()}")

    conn.close()

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\nListo → {OUTPUT_FILE}")


if __name__ == "__main__":
    main()

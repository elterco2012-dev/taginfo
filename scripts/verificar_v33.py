"""
TagInfo v33 — CONFIRMACION FINAL: todas las queries en un snapshot simultáneo.
TOMAR SCREENSHOT DE PANTALLA EXACTAMENTE CUANDO APAREZCA "=== SNAPSHOT ===" en consola.
SOLO LECTURA.
"""

import pyodbc
from datetime import date, datetime

DSN = "MSPA"
OUTPUT_FILE = "taginfo_v33.txt"
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

    log(f"TagInfo v33 CONFIRMACION — {datetime.now()}")
    log(f"DSN: {DSN}  |  Fecha: {today}  |  SOLO LECTURA")
    log("=" * 70)

    conn = get_conn()
    cur = conn.cursor()
    log("Conexión OK\n")

    kredlim_rows = run(cur, "kredlim", f"SELECT kdnr, kredlim FROM kund WHERE firma={FIRMA} AND kredlim > 0")
    kredlim_map = {r[0]: r[1] for r in kredlim_rows}

    # Credit limit base: bel(6,7,11) aufkstat<>8
    totals_6711 = run(cur, "per-kdnr bel(6,7,11)", f"""
        SELECT h.kdnr, SUM(p.poswert) total_open
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.kzerl='0'
          AND h.aufkstat<>8 AND h.belegart IN (6,7,11)
        GROUP BY h.kdnr
    """)
    over_6711 = [r[0] for r in totals_6711 if kredlim_map.get(r[0],0)>0 and r[1] and r[1]>kredlim_map.get(r[0],0)]
    under_6711 = [r[0] for r in totals_6711 if not(kredlim_map.get(r[0],0)>0 and r[1] and r[1]>kredlim_map.get(r[0],0))]

    # ============================================================
    # SNAPSHOT SIMULTANEO — TOMAR SCREENSHOT AHORA
    # ============================================================
    print("\n*** TOMAR SCREENSHOT DE PANTALLA AHORA ***\n")
    log("\n=== SNAPSHOT SIMULTANEO ===")
    ts = datetime.now()
    log(f"  Timestamp: {ts}")

    # 1. BACKORDERS — bel(6,7,11) kredlim → bel=11 aufkstat=0
    if under_6711:
        for r in run(cur, "BACKORDERS", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.belegart=11 AND h.aufkstat=0
              AND h.kdnr IN ({','.join(str(k) for k in under_6711)})
        """):
            log(f"  [BACKORDERS bel(6,7,11)kredlim→bel=11 aufkstat=0] ords={r[0]}  pos={r[1]}  val={r[2]}")

    # 2. BLOQUEADOS — bel(6,7,11) kredlim → bel(6,7,11) aufkstat=0
    if over_6711:
        for r in run(cur, "BLOQUEADOS", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.belegart IN (6,7,11) AND h.aufkstat=0
              AND h.kdnr IN ({','.join(str(k) for k in over_6711)})
        """):
            log(f"  [BLOQUEADOS bel(6,7,11)kredlim→bel(6,7,11) aufkstat=0] ords={r[0]}  pos={r[1]}  val={r[2]}")

    # 3. BLOQUEADO STATUS<-1 — always 0
    for r in run(cur, "BLOQUEADO STATUS<-1", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND h.aufkstat < -1 AND p.kzerl='0'
    """):
        log(f"  [BLOQUEADO STATUS<-1] ords={r[0]}  pos={r[1]}  val={r[2]}")

    # 4. PEDIDOS FUTUROS — aufkstat<>8, bel=11, termin>TODAY
    for r in run(cur, "PEDIDOS FUTUROS", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.kzerl='0'
          AND h.belegart=11 AND h.aufkstat<>8
          AND p.termin > TODAY AND p.liefme<>0
    """):
        log(f"  [PEDIDOS FUTUROS termin>TODAY] ords={r[0]}  pos={r[1]}  val={r[2]}")

    # 5. PRODUCCION — aufkstat=2, posstat=2
    for r in run(cur, "PRODUCCION", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND h.aufkstat=2 AND p.posstat=2 AND p.kzerl='0'
    """):
        log(f"  [PRODUCCION aufkstat=2 posstat=2] ords={r[0]}  pos={r[1]}  val={r[2]}")

    # 6. REMITOS — posstat=5 / aufkstat=4 (delivery notes awaiting invoice)
    for r in run(cur, "REMITOS posstat=5", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND h.belegart=11 AND p.posstat=5
    """):
        log(f"  [REMITOS bel=11 posstat=5] ords={r[0]}  pos={r[1]}  val={r[2]}")

    # Also via aufkstat=4 (should be same)
    for r in run(cur, "REMITOS aufkstat=4", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND h.belegart=11 AND h.aufkstat=4
    """):
        log(f"  [REMITOS bel=11 aufkstat=4] ords={r[0]}  pos={r[1]}  val={r[2]}")

    # Also via sb105 for docs/pos comparison
    # Get auftrag list with aufkstat=4
    aut4 = run(cur, "auftrag aufkstat=4", f"SELECT DISTINCT auftrag FROM f090 WHERE firma={FIRMA} AND belegart=11 AND aufkstat=4")
    if aut4:
        in_aut4 = ','.join(str(r[0]) for r in aut4)
        for r in run(cur, "REMITOS sb105 via aufkstat=4", f"""
            SELECT COUNT(DISTINCT liefnr) docs, COUNT(*) pos, SUM(liefposwe) val
            FROM sb105 WHERE firma={FIRMA} AND auftrag IN ({in_aut4})
        """):
            log(f"  [REMITOS sb105 via aufkstat=4] docs={r[0]}  pos={r[1]}  val={r[2]}")

    # 7. VENTA
    for r in run(cur, "VENTA", f"""
        SELECT COUNT(DISTINCT renr) docs, COUNT(*) pos, SUM(netwert) val
        FROM sbas WHERE firma={FIRMA} AND redat=TODAY AND belegart IN (8,11)
    """):
        log(f"  [VENTA bel IN(8,11) redat=TODAY] docs={r[0]}  pos={r[1]}  val={r[2]}")

    log(f"\n  End Timestamp: {datetime.now()}")

    # ============================================================
    # ADDITIONAL CHECKS — Bloqueados with different position counts
    # ============================================================
    log("\n=== CHECKS ADICIONALES ===")

    # Check: what if Bloqueados NUMBER POS uses COUNT(DISTINCT auftrag) for ords
    # and positions from f092 WITHOUT kzerl filter?
    if over_6711:
        for r in run(cur, "BLOQ bel(6,7,11) aufkstat=0 no kzerl", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag
              AND h.belegart IN (6,7,11) AND h.aufkstat=0
              AND h.kdnr IN ({','.join(str(k) for k in over_6711)})
        """):
            log(f"  BLOQ bel(6,7,11) aufkstat=0 (no kzerl): ords={r[0]}  pos={r[1]}  val={r[2]}")

    # Total aufkstat=0 bel=11 no kzerl
    for r in run(cur, "TOTAL aufkstat=0 bel=11 NO kzerl", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND h.belegart=11 AND h.aufkstat=0
    """):
        log(f"  TOTAL bel=11 aufkstat=0 (no kzerl): ords={r[0]}  pos={r[1]}  val={r[2]}")

    # Bloqueados using ALL belegart for counting (not just 6,7,11)
    if over_6711:
        for r in run(cur, "BLOQ ALL bel aufkstat=0 over-kredlim", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.aufkstat=0
              AND h.kdnr IN ({','.join(str(k) for k in over_6711)})
        """):
            log(f"  BLOQ ALL bel aufkstat=0 over-kredlim: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # Backorders: check distinct kdnr count
    if under_6711:
        for r in run(cur, "BACK distinct kdnr bel=11 aufkstat=0", f"""
            SELECT COUNT(DISTINCT h.kdnr) customers, COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.belegart=11 AND h.aufkstat=0
              AND h.kdnr IN ({','.join(str(k) for k in under_6711)})
        """):
            log(f"  BACK kdnr={r[0]}  ords={r[1]}  pos={r[2]}")

    # f092 posstat distribution NOW
    log("\n--- f092 posstat dist bel=11 aufkstat<>8 NOW ---")
    for r in run(cur, "f092 posstat dist NOW", f"""
        SELECT p.posstat, COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND h.belegart=11 AND h.aufkstat<>8
        GROUP BY p.posstat ORDER BY p.posstat
    """):
        log(f"  posstat={r[0]}  ords={r[1]}  pos={r[2]}  val={r[3]}")

    # f090 aufkstat dist NOW bel=11
    log("\n--- f090 aufkstat dist bel=11 NOW ---")
    for r in run(cur, "f090 aufkstat dist NOW", f"""
        SELECT aufkstat, COUNT(*) ords FROM f090
        WHERE firma={FIRMA} AND belegart=11
        GROUP BY aufkstat ORDER BY aufkstat
    """):
        log(f"  aufkstat={r[0]}  ords={r[1]}")

    conn.close()

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\nListo → {OUTPUT_FILE}")


if __name__ == "__main__":
    main()

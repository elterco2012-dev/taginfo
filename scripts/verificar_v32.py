"""
TagInfo v32 — posstat=5 Remitos, backorders liefme filter, bloqueados sin kzerl.
SOLO LECTURA.
"""

import pyodbc
from datetime import date, datetime

DSN = "MSPA"
OUTPUT_FILE = "taginfo_v32.txt"
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

    log(f"TagInfo v32 — {datetime.now()}")
    log(f"DSN: {DSN}  |  Fecha: {today}  |  SOLO LECTURA")
    log("=" * 70)

    conn = get_conn()
    cur = conn.cursor()
    log("Conexión OK\n")

    kredlim_rows = run(cur, "kredlim", f"SELECT kdnr, kredlim FROM kund WHERE firma={FIRMA} AND kredlim > 0")
    kredlim_map = {r[0]: r[1] for r in kredlim_rows}

    # ============================================================
    # 1. REMITOS — posstat=5 hypothesis (KEY)
    # ============================================================
    log("=== REMITOS — posstat=5 y aufkstat=4 ===")

    # a) f092 posstat=5 all belegart — count NOW
    for r in run(cur, "f092 posstat=5 ALL bel kzerl=0", f"""
        SELECT h.belegart, COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.posstat=5 AND p.kzerl='0'
        GROUP BY h.belegart ORDER BY h.belegart
    """):
        log(f"  posstat=5 belegart={r[0]}  ords={r[1]}  pos={r[2]}  val={r[3]}")

    # b) f092 posstat=5 total
    for r in run(cur, "f092 posstat=5 total kzerl=0", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.posstat=5 AND p.kzerl='0'
    """):
        log(f"  f092 posstat=5 total kzerl=0: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # c) f092 posstat=5 ANY kzerl
    for r in run(cur, "f092 posstat=5 any kzerl", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.posstat=5
    """):
        log(f"  f092 posstat=5 total ANY kzerl: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # d) f090 aufkstat=4 count NOW
    for r in run(cur, "f090 aufkstat=4 count NOW", f"""
        SELECT h.belegart, COUNT(DISTINCT h.auftrag) ords
        FROM f090 h
        WHERE h.firma={FIRMA} AND h.aufkstat=4
        GROUP BY h.belegart ORDER BY h.belegart
    """):
        log(f"  aufkstat=4 belegart={r[0]}  ords={r[1]}")

    # e) sb105 ANY kzerl JOIN f090 aufkstat=4 NOW
    for r in run(cur, "sb105 any kzerl aufkstat=4 NOW", f"""
        SELECT s5.kzerl, COUNT(DISTINCT s5.liefnr) docs, COUNT(*) pos, SUM(s5.liefposwe) val
        FROM sb105 s5, f090 h
        WHERE s5.firma={FIRMA} AND h.firma={FIRMA}
          AND s5.auftrag=h.auftrag AND h.aufkstat=4
        GROUP BY s5.kzerl ORDER BY s5.kzerl
    """):
        log(f"  sb105 aufkstat=4 kzerl={r[0]}  docs={r[1]}  pos={r[2]}  val={r[3]}")

    # f) f092 posstat dist NOW (all aufkstat<>8, bel=11)
    log("\n--- f092 posstat dist NOW bel=11 aufkstat<>8 ---")
    for r in run(cur, "f092 posstat dist bel=11 aufkstat<>8 NOW", f"""
        SELECT p.posstat, COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag
          AND h.belegart=11 AND h.aufkstat<>8
        GROUP BY p.posstat ORDER BY p.posstat
    """):
        log(f"  posstat={r[0]}  ords={r[1]}  pos={r[2]}  val={r[3]}")

    # g) f092 posstat=5 NOT in sbas (2-step): get auftrag list then check
    poststat5_orders = run(cur, "f092 posstat=5 order list", f"""
        SELECT DISTINCT h.auftrag
        FROM f090 h, f092 p
        WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.posstat=5 AND h.belegart=11
    """)
    sbas_auftrag_today = run(cur, "sbas auftrag today", f"""
        SELECT DISTINCT auftrag FROM sbas WHERE firma={FIRMA} AND redat=TODAY AND auftrag > 0
    """)
    sbas_aut_set = {r[0] for r in sbas_auftrag_today}
    poststat5_set = {r[0] for r in poststat5_orders}
    not_in_sbas_auftrag = poststat5_set - sbas_aut_set
    log(f"\n  posstat=5 bel=11 orders: {len(poststat5_set)}")
    log(f"  sbas.auftrag TODAY distinct: {len(sbas_aut_set)}")
    log(f"  posstat=5 NOT in sbas.auftrag TODAY: {len(not_in_sbas_auftrag)} orders")

    if not_in_sbas_auftrag:
        in_list = ','.join(str(a) for a in not_in_sbas_auftrag)
        for r in run(cur, "posstat=5 NOT in sbas TODAY detail", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p
            WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.posstat=5
              AND h.auftrag IN ({in_list})
        """):
            log(f"  posstat=5 NOT in sbas TODAY: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # h) sb105 via posstat=5 orders
    if not_in_sbas_auftrag:
        in_list = ','.join(str(a) for a in not_in_sbas_auftrag)
        for r in run(cur, "sb105 for posstat=5 NOT in sbas", f"""
            SELECT COUNT(DISTINCT s5.liefnr) docs, COUNT(*) pos, SUM(s5.liefposwe) val
            FROM sb105 s5
            WHERE s5.firma={FIRMA}
              AND s5.auftrag IN ({in_list})
        """):
            log(f"  sb105 for posstat=5 NOT sbas: docs={r[0]}  pos={r[1]}  val={r[2]}")

    # i) f092 posstat=5 IN sbas TODAY
    if poststat5_set and sbas_aut_set:
        in_sbas = poststat5_set & sbas_aut_set
        log(f"  posstat=5 orders IN sbas TODAY: {len(in_sbas)}")

    # j) f090 aufkstat distribution NOW
    log("\n--- f090 aufkstat dist bel=11 NOW ---")
    for r in run(cur, "f090 aufkstat dist bel=11 NOW", f"""
        SELECT aufkstat, COUNT(*) ords FROM f090
        WHERE firma={FIRMA} AND belegart=11
        GROUP BY aufkstat ORDER BY aufkstat
    """):
        log(f"  aufkstat={r[0]}  ords={r[1]}")

    # k) Try sb105 liefnr grouped, looking for those matching screen value
    #    Top-20 sb105 kzerl=0 liefnr by value
    log("\n--- sb105 kzerl=0 top liefnr by value ---")
    for r in run(cur, "sb105 kzerl=0 top by val", f"""
        SELECT liefnr, COUNT(*) pos, SUM(liefposwe) val
        FROM sb105 WHERE firma={FIRMA} AND kzerl='0'
        GROUP BY liefnr ORDER BY 3 DESC
    """):
        log(f"  liefnr={r[0]}  pos={r[1]}  val={r[2]}")

    # ============================================================
    # 2. BACKORDERS — liefme filters to get to 67 positions (orders=28 confirmed)
    # ============================================================
    log("\n=== BACKORDERS — liefme/poswert filters (orders=28 confirmed) ===")

    # Credit base: bel(6,7,11) aufkstat<>8
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

    if under_6711:
        in_under = ','.join(str(k) for k in under_6711)

        # Base (already confirmed 28 orders)
        for r in run(cur, "BACK bel=11 aufkstat=0 kzerl=0", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.belegart=11 AND h.aufkstat=0
              AND h.kdnr IN ({in_under})
        """):
            log(f"  BACK bel=11 aufkstat=0 kzerl=0: ords={r[0]}  pos={r[1]}  val={r[2]}")

        # With liefme<>0
        for r in run(cur, "BACK bel=11 aufkstat=0 liefme<>0", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.belegart=11 AND h.aufkstat=0
              AND p.liefme<>0 AND h.kdnr IN ({in_under})
        """):
            log(f"  BACK bel=11 aufkstat=0 liefme<>0: ords={r[0]}  pos={r[1]}  val={r[2]}")

        # With liefme IS NOT NULL
        for r in run(cur, "BACK bel=11 aufkstat=0 liefme NOT NULL", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.belegart=11 AND h.aufkstat=0
              AND p.liefme IS NOT NULL AND h.kdnr IN ({in_under})
        """):
            log(f"  BACK bel=11 aufkstat=0 liefme IS NOT NULL: ords={r[0]}  pos={r[1]}  val={r[2]}")

        # With poswert>0
        for r in run(cur, "BACK bel=11 aufkstat=0 poswert>0", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.belegart=11 AND h.aufkstat=0
              AND p.poswert>0 AND h.kdnr IN ({in_under})
        """):
            log(f"  BACK bel=11 aufkstat=0 poswert>0: ords={r[0]}  pos={r[1]}  val={r[2]}")

        # COUNT DISTINCT posnr
        for r in run(cur, "BACK bel=11 aufkstat=0 COUNT DISTINCT posnr", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(DISTINCT p.posnr) pos_dist, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.belegart=11 AND h.aufkstat=0
              AND h.kdnr IN ({in_under})
        """):
            log(f"  BACK bel=11 aufkstat=0 COUNT DISTINCT posnr: ords={r[0]}  pos_dist={r[1]}  val={r[2]}")

        # posstat=0
        for r in run(cur, "BACK bel=11 aufkstat=0 posstat=0", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.belegart=11 AND h.aufkstat=0 AND p.posstat=0
              AND h.kdnr IN ({in_under})
        """):
            log(f"  BACK bel=11 aufkstat=0 posstat=0: ords={r[0]}  pos={r[1]}  val={r[2]}")

        # liefme<>0 AND posstat=0
        for r in run(cur, "BACK bel=11 aufkstat=0 posstat=0 liefme<>0", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.belegart=11 AND h.aufkstat=0 AND p.posstat=0
              AND p.liefme<>0 AND h.kdnr IN ({in_under})
        """):
            log(f"  BACK bel=11 aufkstat=0 posstat=0 liefme<>0: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # ============================================================
    # 3. BLOQUEADOS — without kzerl filter + other combos
    # ============================================================
    log("\n=== BLOQUEADOS — sin filtro kzerl, otras combos ===")

    if over_6711:
        in_over = ','.join(str(k) for k in over_6711)

        # Without kzerl filter (might give more positions)
        for r in run(cur, "BLOQ bel(6,7,11) aufkstat=0 NO kzerl filter", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag
              AND h.aufkstat=0 AND h.belegart IN (6,7,11)
              AND h.kdnr IN ({in_over})
        """):
            log(f"  BLOQ bel(6,7,11) aufkstat=0 NO kzerl: ords={r[0]}  pos={r[1]}  val={r[2]}")

        # aufkstat=0 bel=11 without kzerl
        for r in run(cur, "BLOQ bel=11 aufkstat=0 NO kzerl", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag
              AND h.aufkstat=0 AND h.belegart=11
              AND h.kdnr IN ({in_over})
        """):
            log(f"  BLOQ bel=11 aufkstat=0 NO kzerl: ords={r[0]}  pos={r[1]}  val={r[2]}")

        # aufkstat=0 bel=11 kzerl=0 (reference)
        for r in run(cur, "BLOQ bel=11 aufkstat=0 kzerl=0", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.aufkstat=0 AND h.belegart=11
              AND h.kdnr IN ({in_over})
        """):
            log(f"  BLOQ bel=11 aufkstat=0 kzerl=0: ords={r[0]}  pos={r[1]}  val={r[2]}")

        # liefme<>0 filter
        for r in run(cur, "BLOQ bel=11 aufkstat=0 kzerl=0 liefme<>0", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.aufkstat=0 AND h.belegart=11 AND p.liefme<>0
              AND h.kdnr IN ({in_over})
        """):
            log(f"  BLOQ bel=11 aufkstat=0 kzerl=0 liefme<>0: ords={r[0]}  pos={r[1]}  val={r[2]}")

        # bel=11 aufkstat<>8 NO kzerl (all positions including completed)
        for r in run(cur, "BLOQ bel=11 aufkstat<>8 NO kzerl", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag
              AND h.belegart=11 AND h.aufkstat<>8
              AND h.kdnr IN ({in_over})
        """):
            log(f"  BLOQ bel=11 aufkstat<>8 NO kzerl: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # What is total bel(6,7,11) aufkstat=0 (no kredlim)?
    for r in run(cur, "TOTAL bel(6,7,11) aufkstat=0 kzerl=0", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.kzerl='0'
          AND h.aufkstat=0 AND h.belegart IN (6,7,11)
    """):
        log(f"  TOTAL bel(6,7,11) aufkstat=0 kzerl=0: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # bel=11 aufkstat=0 total (no kredlim filter)
    for r in run(cur, "TOTAL bel=11 aufkstat=0 NO kzerl", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag
          AND h.aufkstat=0 AND h.belegart=11
    """):
        log(f"  TOTAL bel=11 aufkstat=0 NO kzerl: ords={r[0]}  pos={r[1]}  val={r[2]}")

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

    # Remitos: posstat=5 NOT in sbas TODAY
    p5_orders = run(cur, "snap posstat=5", f"""
        SELECT DISTINCT h.auftrag FROM f090 h, f092 p
        WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.posstat=5 AND h.belegart=11
    """)
    sbas_aut = run(cur, "snap sbas auftrag today", f"SELECT DISTINCT auftrag FROM sbas WHERE firma={FIRMA} AND redat=TODAY AND auftrag > 0")
    sbas_aut_s = {r[0] for r in sbas_aut}
    p5_not_sbas = {r[0] for r in p5_orders} - sbas_aut_s
    if p5_not_sbas:
        in_p5 = ','.join(str(a) for a in p5_not_sbas)
        for r in run(cur, "snap remitos posstat=5 NOT sbas", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.posstat=5
              AND h.auftrag IN ({in_p5})
        """):
            log(f"  [REMITOS posstat=5 NOT sbas TODAY] ords={r[0]}  pos={r[1]}  val={r[2]}")
    else:
        log(f"  [REMITOS posstat=5 NOT sbas TODAY] ords=0  pos=0  val=0")

    # Also snap: sb105 via posstat=5 orders NOT in sbas
    if p5_not_sbas:
        in_p5 = ','.join(str(a) for a in p5_not_sbas)
        for r in run(cur, "snap remitos sb105 via posstat=5", f"""
            SELECT COUNT(DISTINCT s5.liefnr) docs, COUNT(*) pos, SUM(s5.liefposwe) val
            FROM sb105 s5 WHERE s5.firma={FIRMA}
              AND s5.auftrag IN ({in_p5})
        """):
            log(f"  [REMITOS sb105 via posstat=5 NOT sbas] docs={r[0]}  pos={r[1]}  val={r[2]}")

    # Bloqueados: bel(6,7,11) kredlim → bel(6,7,11) aufkstat=0 kzerl=0
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
        for r in run(cur, "snap bloqueados bel(6,7,11) aufkstat=0", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.belegart IN (6,7,11) AND h.aufkstat=0
              AND h.kdnr IN ({','.join(str(k) for k in over_s)})
        """):
            log(f"  [BLOQUEADOS bel(6,7,11) aufkstat=0] ords={r[0]}  pos={r[1]}  val={r[2]}")

    if under_s:
        for r in run(cur, "snap backorders bel=11 aufkstat=0", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.belegart=11 AND h.aufkstat=0
              AND h.kdnr IN ({','.join(str(k) for k in under_s)})
        """):
            log(f"  [BACKORDERS bel=11 aufkstat=0] ords={r[0]}  pos={r[1]}  val={r[2]}")

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

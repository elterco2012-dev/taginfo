"""
TagInfo v25 — prueba masiva de combinaciones para remitos y backorders.
SOLO LECTURA.
"""

import pyodbc
from datetime import date, datetime

DSN = "MSPA"
OUTPUT_FILE = "taginfo_v25.txt"
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

    log(f"TagInfo v25 — {datetime.now()}")
    log(f"DSN: {DSN}  |  Fecha: {today}  |  SOLO LECTURA")
    log("=" * 70)

    conn = get_conn()
    cur = conn.cursor()
    log("Conexión OK\n")

    kredlim_rows = run(cur, "kredlim", f"SELECT kdnr, kredlim FROM kund WHERE firma={FIRMA} AND kredlim > 0")
    kredlim_map = {r[0]: r[1] for r in kredlim_rows}

    # ============================================================
    # 1. REMITOS — todas las combinaciones posibles
    # ============================================================
    log("=== REMITOS — combinaciones ===")

    # sb104 belegart distribution
    log("\nsb104 belegart dist:")
    for r in run(cur, "sb104 belegart dist", f"""
        SELECT belegart, COUNT(*) cnt FROM sb104 WHERE firma={FIRMA}
        GROUP BY belegart ORDER BY belegart
    """):
        log(f"  sb104 belegart={r[0]}  cnt={r[1]}")

    # sbas belegart=7 today (delivery notes in sbas?)
    for r in run(cur, "sbas belegart=7 today", f"""
        SELECT COUNT(DISTINCT renr) docs, COUNT(*) pos, SUM(netwert) val
        FROM sbas WHERE firma={FIRMA} AND redat=TODAY AND belegart=7
    """):
        log(f"  sbas belegart=7 TODAY: docs={r[0]}  pos={r[1]}  val={r[2]}")

    # sbas ALL belegart dist today
    log("\nsbas belegart dist TODAY:")
    for r in run(cur, "sbas belegart dist today", f"""
        SELECT belegart, COUNT(DISTINCT renr) docs, COUNT(*) pos, SUM(netwert) val
        FROM sbas WHERE firma={FIRMA} AND redat=TODAY
        GROUP BY belegart ORDER BY belegart
    """):
        log(f"  sbas belegart={r[0]}  docs={r[1]}  pos={r[2]}  val={r[3]}")

    # posstat=3 in f092 (Lieferschein erstellt?)
    for r in run(cur, "posstat=3", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.posstat=3 AND p.kzerl='0'
    """):
        log(f"  posstat=3: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # posstat=3+8 combined
    for r in run(cur, "posstat=3+8", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.posstat IN (3,8) AND p.kzerl='0'
    """):
        log(f"  posstat IN (3,8): ords={r[0]}  pos={r[1]}  val={r[2]}")

    # sb105 posstat=3 join
    for r in run(cur, "sb105+f092 posstat=3", f"""
        SELECT COUNT(DISTINCT s5.liefnr) docs, COUNT(*) pos, SUM(s5.liefposwe) val
        FROM sb105 s5, f092 p WHERE s5.firma={FIRMA} AND p.firma={FIRMA}
          AND s5.auftrag=p.auftrag AND s5.posnr=p.posnr
          AND p.posstat=3 AND p.kzerl='0'
    """):
        log(f"  sb105+f092 posstat=3: docs={r[0]}  pos={r[1]}  val={r[2]}")

    # sb105 posstat=3+8 join
    for r in run(cur, "sb105+f092 posstat=3+8", f"""
        SELECT COUNT(DISTINCT s5.liefnr) docs, COUNT(*) pos, SUM(s5.liefposwe) val
        FROM sb105 s5, f092 p WHERE s5.firma={FIRMA} AND p.firma={FIRMA}
          AND s5.auftrag=p.auftrag AND s5.posnr=p.posnr
          AND p.posstat IN (3,8) AND p.kzerl='0'
    """):
        log(f"  sb105+f092 posstat IN (3,8): docs={r[0]}  pos={r[1]}  val={r[2]}")

    # sb105 posstat=8 with reflsnr IS NULL
    for r in run(cur, "sb105+f092 posstat=8 reflsnr NULL", f"""
        SELECT COUNT(DISTINCT s5.liefnr) docs, COUNT(*) pos, SUM(s5.liefposwe) val
        FROM sb105 s5, f092 p WHERE s5.firma={FIRMA} AND p.firma={FIRMA}
          AND s5.auftrag=p.auftrag AND s5.posnr=p.posnr
          AND p.posstat=8 AND p.kzerl='0'
          AND s5.reflsnr IS NULL
    """):
        log(f"  sb105+f092 posstat=8 reflsnr IS NULL: docs={r[0]}  pos={r[1]}  val={r[2]}")

    # sb105 posstat=8 by lieflfdnr=1 (first delivery only)
    for r in run(cur, "sb105+f092 posstat=8 lfdnr=1", f"""
        SELECT COUNT(DISTINCT s5.liefnr) docs, COUNT(*) pos, SUM(s5.liefposwe) val
        FROM sb105 s5, f092 p WHERE s5.firma={FIRMA} AND p.firma={FIRMA}
          AND s5.auftrag=p.auftrag AND s5.posnr=p.posnr
          AND p.posstat=8 AND p.kzerl='0'
          AND s5.lieflfdnr=1
    """):
        log(f"  sb105+f092 posstat=8 lieflfdnr=1: docs={r[0]}  pos={r[1]}  val={r[2]}")

    # sb104 join sb105 kzerl='0' with sb104 belegart filter
    log("\nsb104+sb105 kzerl=0 por belegart:")
    for r in run(cur, "sb104+sb105 belegart dist kzerl0", f"""
        SELECT s4.belegart, COUNT(DISTINCT s4.liefnr) docs, COUNT(*) pos, SUM(s5.liefposwe) val
        FROM sb104 s4, sb105 s5 WHERE s4.firma={FIRMA} AND s5.firma={FIRMA}
          AND s4.liefnr=s5.liefnr AND s5.kzerl='0'
        GROUP BY s4.belegart ORDER BY s4.belegart
    """):
        log(f"  sb104 belegart={r[0]}  docs={r[1]}  pos={r[2]}  val={r[3]}")

    # f092 with kzlsdru=2 AND posstat=8 (shipped with delivery note)
    for r in run(cur, "f092 kzlsdru=2 posstat=8", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.posstat=8 AND p.kzlsdru=2 AND p.kzerl='0'
    """):
        log(f"  kzlsdru=2 posstat=8: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # Try f092 kzlsdru=2 posstat=8 via sb105 (count liefnr)
    for r in run(cur, "sb105 kzlsdru=2 posstat=8", f"""
        SELECT COUNT(DISTINCT s5.liefnr) docs, COUNT(*) pos, SUM(s5.liefposwe) val
        FROM sb105 s5, f092 p WHERE s5.firma={FIRMA} AND p.firma={FIRMA}
          AND s5.auftrag=p.auftrag AND s5.posnr=p.posnr
          AND p.posstat=8 AND p.kzlsdru=2 AND p.kzerl='0'
    """):
        log(f"  sb105 kzlsdru=2 posstat=8: docs={r[0]}  pos={r[1]}  val={r[2]}")

    # ============================================================
    # 2. BACKORDERS/BLOQUEADOS — todas las combinaciones
    # ============================================================
    log("\n=== BACKORDERS/BLOQUEADOS — combinaciones ===")

    combos = [
        ("aufkstat=0 bel=11 liefme<>0 termin=TODAY",
         f"h.aufkstat=0 AND h.belegart=11 AND p.liefme<>0 AND p.termin=TODAY"),
        ("aufkstat=0 bel=11 NO liefme NO termin",
         f"h.aufkstat=0 AND h.belegart=11"),
        ("aufkstat=0 bel=11 liefme IS NULL OR <>0",
         f"h.aufkstat=0 AND h.belegart=11 AND (p.liefme IS NULL OR p.liefme<>0)"),
        ("aufkstat<>8 bel=11 liefme<>0 termin=TODAY",
         f"h.aufkstat<>8 AND h.belegart=11 AND p.liefme<>0 AND p.termin=TODAY"),
        ("aufkstat<>8 bel=11 NO liefme NO termin",
         f"h.aufkstat<>8 AND h.belegart=11"),
        ("aufkstat=0 ALL belegart liefme<>0 termin=TODAY",
         f"h.aufkstat=0 AND p.liefme<>0 AND p.termin=TODAY"),
        ("aufkstat=0 ALL belegart NO liefme NO termin",
         f"h.aufkstat=0"),
        ("aufkstat IN (0,-1) bel=11 liefme<>0",
         f"h.aufkstat IN (0,-1) AND h.belegart=11 AND p.liefme<>0"),
    ]

    for label, where in combos:
        rows = run(cur, f"base {label}", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0' AND {where}
        """)
        for r in rows:
            log(f"  [{label}]: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # Kredlim split for most promising combos
    log("\n--- Kredlim split (aufkstat=0 bel=11 NO liefme NO termin) ---")
    totals_a = run(cur, "per-kdnr A", f"""
        SELECT h.kdnr, SUM(p.poswert) total_open
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.kzerl='0'
          AND h.aufkstat=0 AND h.belegart=11
        GROUP BY h.kdnr
    """)
    over_a = [r[0] for r in totals_a if kredlim_map.get(r[0],0)>0 and r[1] and r[1]>kredlim_map.get(r[0],0)]
    under_a = [r[0] for r in totals_a if not(kredlim_map.get(r[0],0)>0 and r[1] and r[1]>kredlim_map.get(r[0],0))]
    log(f"  Customers={len(totals_a)}  over={len(over_a)}  under={len(under_a)}")
    if over_a:
        for r in run(cur, "BLOQ A", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.aufkstat=0 AND h.belegart=11
              AND h.kdnr IN ({','.join(str(k) for k in over_a)})
        """):
            log(f"  BLOQUEADOS A: ords={r[0]}  pos={r[1]}  val={r[2]}")
    if under_a:
        for r in run(cur, "BACK A", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.aufkstat=0 AND h.belegart=11
              AND h.kdnr IN ({','.join(str(k) for k in under_a)})
        """):
            log(f"  BACKORDERS A: ords={r[0]}  pos={r[1]}  val={r[2]}")

    log("\n--- Kredlim split (aufkstat<>8 bel=11 NO liefme NO termin) ---")
    totals_b = run(cur, "per-kdnr B", f"""
        SELECT h.kdnr, SUM(p.poswert) total_open
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.kzerl='0'
          AND h.aufkstat<>8 AND h.belegart=11
        GROUP BY h.kdnr
    """)
    over_b = [r[0] for r in totals_b if kredlim_map.get(r[0],0)>0 and r[1] and r[1]>kredlim_map.get(r[0],0)]
    under_b = [r[0] for r in totals_b if not(kredlim_map.get(r[0],0)>0 and r[1] and r[1]>kredlim_map.get(r[0],0))]
    log(f"  Customers={len(totals_b)}  over={len(over_b)}  under={len(under_b)}")
    if over_b:
        for r in run(cur, "BLOQ B", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.aufkstat<>8 AND h.belegart=11
              AND h.kdnr IN ({','.join(str(k) for k in over_b)})
        """):
            log(f"  BLOQUEADOS B: ords={r[0]}  pos={r[1]}  val={r[2]}")
    if under_b:
        for r in run(cur, "BACK B", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.aufkstat<>8 AND h.belegart=11
              AND h.kdnr IN ({','.join(str(k) for k in under_b)})
        """):
            log(f"  BACKORDERS B: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # ============================================================
    # 3. SNAPSHOT COMPLETO
    # ============================================================
    log("\n=== SNAPSHOT COMPLETO ===")
    ts = datetime.now()

    for r in run(cur, "snap produccion", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND h.aufkstat=2 AND p.posstat=2 AND p.kzerl='0'
    """):
        log(f"  [PRODUCCION] ords={r[0]}  pos={r[1]}  val={r[2]}")

    # Remitos candidates
    for r in run(cur, "snap remitos posstat=8 sb105", f"""
        SELECT COUNT(DISTINCT s5.liefnr) docs, COUNT(*) pos, SUM(s5.liefposwe) val
        FROM sb105 s5, f092 p WHERE s5.firma={FIRMA} AND p.firma={FIRMA}
          AND s5.auftrag=p.auftrag AND s5.posnr=p.posnr
          AND p.posstat=8 AND p.kzerl='0'
    """):
        log(f"  [REMITOS posstat=8 sb105] docs={r[0]}  pos={r[1]}  val={r[2]}")

    for r in run(cur, "snap remitos posstat=3+8 sb105", f"""
        SELECT COUNT(DISTINCT s5.liefnr) docs, COUNT(*) pos, SUM(s5.liefposwe) val
        FROM sb105 s5, f092 p WHERE s5.firma={FIRMA} AND p.firma={FIRMA}
          AND s5.auftrag=p.auftrag AND s5.posnr=p.posnr
          AND p.posstat IN (3,8) AND p.kzerl='0'
    """):
        log(f"  [REMITOS posstat=3+8 sb105] docs={r[0]}  pos={r[1]}  val={r[2]}")

    # Bloqueados fresh
    totals_snap = run(cur, "snap per-kdnr", f"""
        SELECT h.kdnr, SUM(p.poswert) total_open
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.kzerl='0'
          AND h.aufkstat<>8 AND h.belegart=11
        GROUP BY h.kdnr
    """)
    over_s=[r[0] for r in totals_snap if kredlim_map.get(r[0],0)>0 and r[1] and r[1]>kredlim_map.get(r[0],0)]
    under_s=[r[0] for r in totals_snap if not(kredlim_map.get(r[0],0)>0 and r[1] and r[1]>kredlim_map.get(r[0],0))]

    if over_s:
        for r in run(cur, "snap bloqueados", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.aufkstat<>8 AND h.belegart=11
              AND h.kdnr IN ({','.join(str(x) for x in over_s)})
        """):
            log(f"  [BLOQUEADOS aufkstat<>8 bel=11] ords={r[0]}  pos={r[1]}  val={r[2]}")
    if under_s:
        for r in run(cur, "snap backorders", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.aufkstat<>8 AND h.belegart=11
              AND h.kdnr IN ({','.join(str(x) for x in under_s)})
        """):
            log(f"  [BACKORDERS aufkstat<>8 bel=11] ords={r[0]}  pos={r[1]}  val={r[2]}")

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

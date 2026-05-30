"""
TagInfo v36 - HIPOTESIS CREDITO Y LIEFME
1. Base credito bel=11 SOLO vs bel(6,7,11)
2. bel=6 como NEGATIVO en credito (devoluciones reducen exposicion)
3. Filtro liefme<>0 en Backorders/Bloqueados
4. Combinaciones: base-credito x liefme
SOLO LECTURA.
"""

import pyodbc
from datetime import date, datetime

DSN = "MSPA"
OUTPUT_FILE = "taginfo_v36.txt"
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

    log(f"TagInfo v36 - CREDITO Y LIEFME - {datetime.now()}")
    log(f"DSN: {DSN}  |  Fecha: {today}  |  SOLO LECTURA")
    log("=" * 70)

    conn = get_conn()
    cur = conn.cursor()
    log("Conexion OK\n")

    kredlim_rows = run(cur, "kredlim", f"SELECT kdnr, kredlim FROM kund WHERE firma={FIRMA} AND kredlim > 0")
    kredlim_map = {r[0]: r[1] for r in kredlim_rows}
    def fmt_in(lst): return ",".join(str(k) for k in lst)

    # ============================================================
    # HIPOTESIS A: base credito bel=11 SOLO (no bel 6,7)
    # ============================================================
    log("=== A) BASE CREDITO bel=11 SOLO ===")

    totals_b11 = run(cur, "per-kdnr bel=11 aufkstat<>8", f"""
        SELECT h.kdnr, SUM(p.poswert)
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.kzerl='0'
          AND h.aufkstat<>8 AND h.belegart=11
        GROUP BY h.kdnr
    """)
    over_b11  = [r[0] for r in totals_b11 if kredlim_map.get(r[0],0)>0 and r[1] and r[1]>kredlim_map.get(r[0],0)]
    under_b11 = [r[0] for r in totals_b11 if not(kredlim_map.get(r[0],0)>0 and r[1] and r[1]>kredlim_map.get(r[0],0))]
    log(f"  base bel=11: over={len(over_b11)}  under={len(under_b11)}")

    # Con base bel=11: Bloqueados y Backorders (bel 6,7,11 aufkstat=0)
    if over_b11:
        for r in run(cur, "BLOQ base-b11 bel(6,7,11)", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.aufkstat=0 AND h.belegart IN (6,7,11)
              AND h.kdnr IN ({fmt_in(over_b11)})
        """):
            log(f"  BLOQ base-b11 bel(6,7,11) noliefme: ords={r[0]}  pos={r[1]}  val={r[2]}")

        for r in run(cur, "BACK base-b11 bel(6,7,11)", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.aufkstat=0 AND h.belegart IN (6,7,11)
              AND h.kdnr NOT IN ({fmt_in(over_b11)})
        """):
            log(f"  BACK base-b11 bel(6,7,11) noliefme: ords={r[0]}  pos={r[1]}  val={r[2]}")
    else:
        # over_b11 is empty: ALL aufkstat=0 bel(6,7,11) = Backorders
        for r in run(cur, "ALL base-b11=empty bel(6,7,11)", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.aufkstat=0 AND h.belegart IN (6,7,11)
        """):
            log(f"  BACK base-b11=empty (all) bel(6,7,11) noliefme: ords={r[0]}  pos={r[1]}  val={r[2]}")

        for r in run(cur, "ALL base-b11=empty bel(6,7,11) liefme<>0", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.aufkstat=0 AND h.belegart IN (6,7,11)
              AND p.liefme <> 0
        """):
            log(f"  BACK base-b11=empty (all) bel(6,7,11) liefme<>0: ords={r[0]}  pos={r[1]}  val={r[2]}")

        for r in run(cur, "ALL base-b11=empty bel=11 liefme<>0", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.aufkstat=0 AND h.belegart=11
              AND p.liefme <> 0
        """):
            log(f"  BACK base-b11=empty bel=11 liefme<>0: ords={r[0]}  pos={r[1]}  val={r[2]}")

        for r in run(cur, "ALL base-b11=empty bel=7 liefme<>0", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.aufkstat=0 AND h.belegart=7
              AND p.liefme <> 0
        """):
            log(f"  BACK base-b11=empty bel=7 liefme<>0: ords={r[0]}  pos={r[1]}  val={r[2]}")

        for r in run(cur, "ALL base-b11=empty bel=6 liefme<>0", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.aufkstat=0 AND h.belegart=6
              AND p.liefme <> 0
        """):
            log(f"  BACK base-b11=empty bel=6 liefme<>0: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # ============================================================
    # HIPOTESIS B: bel=6 NEGATIVO en credito (devoluciones reducen exposicion)
    # ============================================================
    log("\n=== B) BASE CREDITO bel=6 NEGATIVO (devoluciones) ===")

    # Para simular bel=6 negativo necesitamos calcular en Python:
    # exposicion = SUM(poswert where bel in 7,11) - SUM(poswert where bel=6)
    raw_by_kdnr_bel = run(cur, "por-kdnr-bel all 6,7,11", f"""
        SELECT h.kdnr, h.belegart, SUM(p.poswert) total
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.kzerl='0'
          AND h.aufkstat<>8 AND h.belegart IN (6,7,11)
        GROUP BY h.kdnr, h.belegart
    """)

    # Build net exposure per customer: bel 7,11 positive, bel 6 negative
    net_exp = {}
    for r in raw_by_kdnr_bel:
        kdnr, bel, tot = r[0], r[1], float(r[2]) if r[2] else 0.0
        if bel == 6:
            net_exp[kdnr] = net_exp.get(kdnr, 0.0) - tot
        else:
            net_exp[kdnr] = net_exp.get(kdnr, 0.0) + tot

    over_neg  = [k for k,v in net_exp.items() if kredlim_map.get(k,0)>0 and v>kredlim_map.get(k,0)]
    under_neg = [k for k,v in net_exp.items() if not(kredlim_map.get(k,0)>0 and v>kredlim_map.get(k,0))]
    log(f"  base bel6-neg: over={len(over_neg)}  under={len(under_neg)}")

    if over_neg:
        for r in run(cur, "BLOQ base-neg bel(6,7,11)", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.aufkstat=0 AND h.belegart IN (6,7,11)
              AND h.kdnr IN ({fmt_in(over_neg)})
        """):
            log(f"  BLOQ base-neg bel(6,7,11) noliefme: ords={r[0]}  pos={r[1]}  val={r[2]}")

        for r in run(cur, "BACK base-neg bel(6,7,11)", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.aufkstat=0 AND h.belegart IN (6,7,11)
              AND h.kdnr NOT IN ({fmt_in(over_neg)})
        """):
            log(f"  BACK base-neg bel(6,7,11) noliefme: ords={r[0]}  pos={r[1]}  val={r[2]}")
    else:
        for r in run(cur, "ALL base-neg=empty bel(6,7,11)", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.aufkstat=0 AND h.belegart IN (6,7,11)
        """):
            log(f"  BACK base-neg=empty all bel(6,7,11): ords={r[0]}  pos={r[1]}  val={r[2]}")

    # ============================================================
    # HIPOTESIS C: LIEFME<>0 filter en posiciones
    # ============================================================
    log("\n=== C) FILTRO liefme<>0 EN POSICIONES ===")

    # Standard over/under (bel 6,7,11)
    totals_6711 = run(cur, "per-kdnr bel(6,7,11)", f"""
        SELECT h.kdnr, SUM(p.poswert)
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.kzerl='0'
          AND h.aufkstat<>8 AND h.belegart IN (6,7,11)
        GROUP BY h.kdnr
    """)
    over  = [r[0] for r in totals_6711 if kredlim_map.get(r[0],0)>0 and r[1] and r[1]>kredlim_map.get(r[0],0)]
    under = [r[0] for r in totals_6711 if not(kredlim_map.get(r[0],0)>0 and r[1] and r[1]>kredlim_map.get(r[0],0))]
    log(f"  base bel(6,7,11): over={len(over)}  under={len(under)}")

    if over:
        for r in run(cur, "BLOQ liefme<>0 IN over", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.aufkstat=0 AND h.belegart IN (6,7,11)
              AND p.liefme <> 0
              AND h.kdnr IN ({fmt_in(over)})
        """):
            log(f"  BLOQ base-6711 bel(6,7,11) liefme<>0: ords={r[0]}  pos={r[1]}  val={r[2]}")

        for r in run(cur, "BACK liefme<>0 NOT IN over", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.aufkstat=0 AND h.belegart IN (6,7,11)
              AND p.liefme <> 0
              AND h.kdnr NOT IN ({fmt_in(over)})
        """):
            log(f"  BACK base-6711 bel(6,7,11) liefme<>0: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # ============================================================
    # HIPOTESIS D: liefme distribution en bel(6,7,11) aufkstat=0
    # ============================================================
    log("\n=== D) DISTRIBUCION liefme en bel(6,7,11) aufkstat=0 ===")

    for r in run(cur, "liefme=0", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.kzerl='0'
          AND h.aufkstat=0 AND h.belegart IN (6,7,11)
          AND p.liefme = 0
    """):
        log(f"  liefme=0: ords={r[0]}  pos={r[1]}  val={r[2]}")

    for r in run(cur, "liefme>0", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.kzerl='0'
          AND h.aufkstat=0 AND h.belegart IN (6,7,11)
          AND p.liefme > 0
    """):
        log(f"  liefme>0: ords={r[0]}  pos={r[1]}  val={r[2]}")

    for r in run(cur, "liefme<0", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.kzerl='0'
          AND h.aufkstat=0 AND h.belegart IN (6,7,11)
          AND p.liefme < 0
    """):
        log(f"  liefme<0: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # liefme dist by belegart
    log("\n  liefme dist por belegart:")
    for r in run(cur, "liefme dist por belegart", f"""
        SELECT h.belegart,
               SUM(CASE WHEN p.liefme = 0 THEN 1 ELSE 0 END) pos_liefme0,
               SUM(CASE WHEN p.liefme > 0 THEN 1 ELSE 0 END) pos_liefme_pos,
               SUM(CASE WHEN p.liefme < 0 THEN 1 ELSE 0 END) pos_liefme_neg
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.kzerl='0'
          AND h.aufkstat=0 AND h.belegart IN (6,7,11)
        GROUP BY h.belegart ORDER BY h.belegart
    """):
        log(f"  bel={r[0]}  pos_liefme=0:{r[1]}  pos_liefme>0:{r[2]}  pos_liefme<0:{r[3]}")

    # ============================================================
    # HIPOTESIS E: base credito bel(6,7,11) + liefme<>0
    # ============================================================
    log("\n=== E) BASE CREDITO bel(6,7,11) liefme<>0 ===")

    totals_liefme = run(cur, "per-kdnr bel(6,7,11) liefme<>0", f"""
        SELECT h.kdnr, SUM(p.poswert)
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.kzerl='0'
          AND h.aufkstat<>8 AND h.belegart IN (6,7,11)
          AND p.liefme <> 0
        GROUP BY h.kdnr
    """)
    over_lm  = [r[0] for r in totals_liefme if kredlim_map.get(r[0],0)>0 and r[1] and r[1]>kredlim_map.get(r[0],0)]
    under_lm = [r[0] for r in totals_liefme if not(kredlim_map.get(r[0],0)>0 and r[1] and r[1]>kredlim_map.get(r[0],0))]
    log(f"  base bel(6,7,11)+liefme<>0: over={len(over_lm)}  under={len(under_lm)}")

    if over_lm:
        for r in run(cur, "BLOQ base-lm bel(6,7,11) liefme<>0", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.aufkstat=0 AND h.belegart IN (6,7,11)
              AND p.liefme <> 0
              AND h.kdnr IN ({fmt_in(over_lm)})
        """):
            log(f"  BLOQ base-lm bel(6,7,11) liefme<>0: ords={r[0]}  pos={r[1]}  val={r[2]}")

        for r in run(cur, "BACK base-lm bel(6,7,11) liefme<>0", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.aufkstat=0 AND h.belegart IN (6,7,11)
              AND p.liefme <> 0
              AND h.kdnr NOT IN ({fmt_in(over_lm)})
        """):
            log(f"  BACK base-lm bel(6,7,11) liefme<>0: ords={r[0]}  pos={r[1]}  val={r[2]}")
    else:
        for r in run(cur, "ALL base-lm=empty bel(6,7,11) liefme<>0", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.aufkstat=0 AND h.belegart IN (6,7,11)
              AND p.liefme <> 0
        """):
            log(f"  BACK base-lm=empty all bel(6,7,11) liefme<>0: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # ============================================================
    # SNAPSHOT SIMULTANEO
    # ============================================================
    print("\n*** TOMAR SCREENSHOT DE PANTALLA AHORA ***\n")
    log("\n=== SNAPSHOT SIMULTANEO ===")
    ts = datetime.now()
    log(f"  Timestamp: {ts}")

    # Usar cada hipotesis
    # A) base bel=11: over_b11
    log(f"  [A] base-b11 over={len(over_b11)}")
    if over_b11:
        for r in run(cur, "snap BLOQ base-b11", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.aufkstat=0 AND h.belegart IN (6,7,11)
              AND h.kdnr IN ({fmt_in(over_b11)})
        """):
            log(f"  [BLOQ base-b11] ords={r[0]}  pos={r[1]}  val={r[2]}")
        for r in run(cur, "snap BACK base-b11", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.aufkstat=0 AND h.belegart IN (6,7,11)
              AND h.kdnr NOT IN ({fmt_in(over_b11)})
        """):
            log(f"  [BACK base-b11] ords={r[0]}  pos={r[1]}  val={r[2]}")
    else:
        # base-b11 over=0 -> all = backorders; try with liefme<>0
        for r in run(cur, "snap BACK base-b11=empty bel(6,7,11)", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.aufkstat=0 AND h.belegart IN (6,7,11)
        """):
            log(f"  [BACK base-b11=empty all] ords={r[0]}  pos={r[1]}  val={r[2]}")
        for r in run(cur, "snap BACK base-b11=empty liefme<>0", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.aufkstat=0 AND h.belegart IN (6,7,11)
              AND p.liefme <> 0
        """):
            log(f"  [BACK base-b11=empty liefme<>0] ords={r[0]}  pos={r[1]}  val={r[2]}")

    # B) base bel6-neg
    log(f"  [B] base-neg over={len(over_neg)}")
    if over_neg:
        for r in run(cur, "snap BLOQ base-neg", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.aufkstat=0 AND h.belegart IN (6,7,11)
              AND h.kdnr IN ({fmt_in(over_neg)})
        """):
            log(f"  [BLOQ base-neg] ords={r[0]}  pos={r[1]}  val={r[2]}")
        for r in run(cur, "snap BACK base-neg", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.aufkstat=0 AND h.belegart IN (6,7,11)
              AND h.kdnr NOT IN ({fmt_in(over_neg)})
        """):
            log(f"  [BACK base-neg] ords={r[0]}  pos={r[1]}  val={r[2]}")

    # C) base bel(6,7,11) + liefme<>0
    log(f"  [E] base-lm over={len(over_lm)}")
    if over_lm:
        for r in run(cur, "snap BLOQ base-lm", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.aufkstat=0 AND h.belegart IN (6,7,11)
              AND p.liefme <> 0
              AND h.kdnr IN ({fmt_in(over_lm)})
        """):
            log(f"  [BLOQ base-lm] ords={r[0]}  pos={r[1]}  val={r[2]}")
        for r in run(cur, "snap BACK base-lm", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.aufkstat=0 AND h.belegart IN (6,7,11)
              AND p.liefme <> 0
              AND h.kdnr NOT IN ({fmt_in(over_lm)})
        """):
            log(f"  [BACK base-lm] ords={r[0]}  pos={r[1]}  val={r[2]}")
    else:
        for r in run(cur, "snap ALL base-lm=empty liefme<>0", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.aufkstat=0 AND h.belegart IN (6,7,11)
              AND p.liefme <> 0
        """):
            log(f"  [BACK base-lm=empty liefme<>0] ords={r[0]}  pos={r[1]}  val={r[2]}")

    # Standard Remitos, Produccion, Venta
    for r in run(cur, "REMITOS", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND h.belegart=11 AND h.aufkstat=4
    """):
        log(f"  [REMITOS] ords={r[0]}  pos={r[1]}  val={r[2]}")

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

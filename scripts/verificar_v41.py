"""
TagInfo v41 - ARTNR DISTINCT + campos f092 restantes
1. COUNT(DISTINCT artnr) para los 14 bel=7+11 NOT OVER ordenes
2. artnr dist: cuantos articulos aparecen en >1 orden (repetidos)
3. f092 campos: dispmenge, dispos, kzliefme, mzliefme, lagmenge, etc
4. f092 pospos como DISTINCT
5. Hipotesis: SUM valor por artnr distinto
SOLO LECTURA.
"""

import pyodbc
from datetime import date, datetime

DSN = "MSPA"
OUTPUT_FILE = "taginfo_v41.txt"
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

    log(f"TagInfo v41 - ARTNR DISTINCT - {datetime.now()}")
    log(f"DSN: {DSN}  |  Fecha: {today}  |  SOLO LECTURA")
    log("=" * 70)

    conn = get_conn()
    cur = conn.cursor()
    log("Conexion OK\n")

    kredlim_rows = run(cur, "kredlim", f"SELECT kdnr, kredlim FROM kund WHERE firma={FIRMA} AND kredlim > 0")
    kredlim_map = {r[0]: r[1] for r in kredlim_rows}

    totals_6711 = run(cur, "per-kdnr bel(6,7,11)", f"""
        SELECT h.kdnr, SUM(p.poswert)
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.kzerl='0'
          AND h.aufkstat<>8 AND h.belegart IN (6,7,11)
        GROUP BY h.kdnr
    """)
    over = [r[0] for r in totals_6711 if kredlim_map.get(r[0],0)>0 and r[1] and r[1]>kredlim_map.get(r[0],0)]
    def fmt_in(lst): return ",".join(str(k) for k in lst)

    orders_b711 = run(cur, "orders bel=7+11 NOT OVER", f"""
        SELECT DISTINCT h.auftrag FROM f090 h, f092 p
        WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.kzerl='0'
          AND h.aufkstat=0 AND h.belegart IN (7,11)
          AND h.kdnr NOT IN ({fmt_in(over)})
    """)
    aut_b711 = [r[0] for r in orders_b711]
    log(f"  bel=7+11 NOT OVER: {len(aut_b711)} orders\n")

    # ============================================================
    # 1. COUNT(DISTINCT artnr) en los 14 ordenes
    # ============================================================
    log("=== COUNT(DISTINCT artnr) en bel=7+11 NOT OVER ===")

    if aut_b711:
        for r in run(cur, "distinct artnr kzerl=0", f"""
            SELECT COUNT(DISTINCT p.artnr) distinct_art, COUNT(*) total_pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.auftrag IN ({fmt_in(aut_b711)})
        """):
            log(f"  COUNT(DISTINCT artnr) kzerl='0': distinct={r[0]}  total_pos={r[1]}  val={r[2]}")

        # Articulos que aparecen en mas de 1 orden
        for r in run(cur, "artnr en >1 orden", f"""
            SELECT p.artnr, COUNT(DISTINCT h.auftrag) num_ords, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.auftrag IN ({fmt_in(aut_b711)})
            GROUP BY p.artnr
            ORDER BY num_ords DESC, p.artnr
        """):
            if r[1] > 1:
                log(f"  artnr={r[0]}  aparece_en={r[1]}_ordenes  val_total={r[2]}")

        # Lista de todos los artnr con su posicion en el orden
        log("\n  todos artnr:")
        for r in run(cur, "lista artnr", f"""
            SELECT h.auftrag, p.pospos, p.artnr, p.poswert
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.auftrag IN ({fmt_in(aut_b711)})
            ORDER BY h.auftrag, p.pospos
        """):
            log(f"    {r[0]} pospos={r[1]} artnr={r[2]} val={r[3]}")

    # ============================================================
    # 2. f092 CAMPOS adicionales: dispmenge, kzliefme, etc
    # ============================================================
    log("\n=== f092 campos adicionales ===")

    if aut_b711:
        fields_to_try = [
            ("dispmenge", f"SELECT SUM(p.dispmenge) FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA} AND h.auftrag=p.auftrag AND p.kzerl='0' AND h.auftrag IN ({fmt_in(aut_b711)})"),
            ("dispos",    f"SELECT SUM(p.dispos) FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA} AND h.auftrag=p.auftrag AND p.kzerl='0' AND h.auftrag IN ({fmt_in(aut_b711)})"),
            ("kzliefme",  f"SELECT p.kzliefme, COUNT(*) FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA} AND h.auftrag=p.auftrag AND p.kzerl='0' AND h.auftrag IN ({fmt_in(aut_b711)}) GROUP BY p.kzliefme"),
            ("lagmenge",  f"SELECT SUM(p.lagmenge) FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA} AND h.auftrag=p.auftrag AND p.kzerl='0' AND h.auftrag IN ({fmt_in(aut_b711)})"),
            ("verfmenge", f"SELECT SUM(p.verfmenge) FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA} AND h.auftrag=p.auftrag AND p.kzerl='0' AND h.auftrag IN ({fmt_in(aut_b711)})"),
            ("konsmenge", f"SELECT SUM(p.konsmenge) FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA} AND h.auftrag=p.auftrag AND p.kzerl='0' AND h.auftrag IN ({fmt_in(aut_b711)})"),
            ("kzruestand",f"SELECT p.kzruestand, COUNT(*) FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA} AND h.auftrag=p.auftrag AND p.kzerl='0' AND h.auftrag IN ({fmt_in(aut_b711)}) GROUP BY p.kzruestand"),
            ("rueckstand",f"SELECT p.rueckstand, COUNT(*) FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA} AND h.auftrag=p.auftrag AND p.kzerl='0' AND h.auftrag IN ({fmt_in(aut_b711)}) GROUP BY p.rueckstand"),
            ("sperre",    f"SELECT p.sperre, COUNT(*) FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA} AND h.auftrag=p.auftrag AND p.kzerl='0' AND h.auftrag IN ({fmt_in(aut_b711)}) GROUP BY p.sperre"),
            ("sperrkz",   f"SELECT p.sperrkz, COUNT(*) FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA} AND h.auftrag=p.auftrag AND p.kzerl='0' AND h.auftrag IN ({fmt_in(aut_b711)}) GROUP BY p.sperrkz"),
            ("kzsperre",  f"SELECT p.kzsperre, COUNT(*) FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA} AND h.auftrag=p.auftrag AND p.kzerl='0' AND h.auftrag IN ({fmt_in(aut_b711)}) GROUP BY p.kzsperre"),
            ("lzmenge",   f"SELECT SUM(p.lzmenge) FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA} AND h.auftrag=p.auftrag AND p.kzerl='0' AND h.auftrag IN ({fmt_in(aut_b711)})"),
        ]
        for fname, sql in fields_to_try:
            rows = run(cur, f"f092.{fname}", sql)
            if rows:
                log(f"  f092.{fname} EXISTS: {rows}")

    # ============================================================
    # 3. VALOR ALTERNATIVO: poswert vs netwert en full bel(6,7,11)
    # ============================================================
    log("\n=== VALOR: netwert vs poswert comparacion full ===")

    # For all bel(6,7,11) aufkstat=0 NOT OVER
    for r in run(cur, "netwert full bel(6,7,11) NOT OVER", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.netwert) nval, SUM(p.poswert) pval
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.kzerl='0'
          AND h.aufkstat=0 AND h.belegart IN (6,7,11)
          AND h.kdnr NOT IN ({fmt_in(over)})
    """):
        log(f"  bel(6,7,11) NOT OVER: ords={r[0]} pos={r[1]} netwert={r[2]} poswert={r[3]}")

    # ============================================================
    # 4. Hipotesis: la pantalla usa bel=7 SOLAMENTE para Backorders?
    #    Y cuenta artnr distinct o pospos distinct?
    # ============================================================
    log("\n=== bel=7 SOLO NOT OVER distinct pos variants ===")

    for r in run(cur, "bel=7 NOT OVER distinct artnr", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(DISTINCT p.artnr) art, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.kzerl='0'
          AND h.aufkstat=0 AND h.belegart=7
          AND h.kdnr NOT IN ({fmt_in(over)})
    """):
        log(f"  bel=7 NOT OVER: ords={r[0]} distinct_artnr={r[1]} pos={r[2]} val={r[3]}")

    for r in run(cur, "bel=7+11 NOT OVER distinct artnr", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(DISTINCT p.artnr) art, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.kzerl='0'
          AND h.aufkstat=0 AND h.belegart IN (7,11)
          AND h.kdnr NOT IN ({fmt_in(over)})
    """):
        log(f"  bel=7+11 NOT OVER: ords={r[0]} distinct_artnr={r[1]} pos={r[2]} val={r[3]}")

    # Same for bel(6,7,11) NOT OVER
    for r in run(cur, "bel(6,7,11) NOT OVER distinct artnr", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(DISTINCT p.artnr) art, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.kzerl='0'
          AND h.aufkstat=0 AND h.belegart IN (6,7,11)
          AND h.kdnr NOT IN ({fmt_in(over)})
    """):
        log(f"  bel(6,7,11) NOT OVER: ords={r[0]} distinct_artnr={r[1]} pos={r[2]} val={r[3]}")

    # ============================================================
    # 5. f090 more field name variants
    # ============================================================
    log("\n=== f090 mas variantes de nombre de campo ===")

    if aut_b711:
        f090_more = [
            ("anzpos",      f"SELECT auftrag, anzpos FROM f090 WHERE firma={FIRMA} AND auftrag IN ({fmt_in(aut_b711[:5])})"),
            ("nrpos",       f"SELECT auftrag, nrpos FROM f090 WHERE firma={FIRMA} AND auftrag IN ({fmt_in(aut_b711[:5])})"),
            ("aufwert",     f"SELECT auftrag, aufwert FROM f090 WHERE firma={FIRMA} AND auftrag IN ({fmt_in(aut_b711[:5])})"),
            ("geswert",     f"SELECT auftrag, geswert FROM f090 WHERE firma={FIRMA} AND auftrag IN ({fmt_in(aut_b711[:5])})"),
            ("aufrgswert",  f"SELECT auftrag, aufrgswert FROM f090 WHERE firma={FIRMA} AND auftrag IN ({fmt_in(aut_b711[:5])})"),
            ("sumwert",     f"SELECT auftrag, sumwert FROM f090 WHERE firma={FIRMA} AND auftrag IN ({fmt_in(aut_b711[:5])})"),
            ("bruttowert",  f"SELECT auftrag, bruttowert FROM f090 WHERE firma={FIRMA} AND auftrag IN ({fmt_in(aut_b711[:5])})"),
        ]
        for fname, sql in f090_more:
            rows = run(cur, f"f090.{fname}", sql)
            if rows:
                log(f"  f090.{fname} EXISTS: {rows}")

    # ============================================================
    # 6. SNAPSHOT
    # ============================================================
    print("\n*** TOMAR SCREENSHOT DE PANTALLA AHORA ***\n")
    log("\n=== SNAPSHOT ===")
    ts = datetime.now()
    log(f"  Timestamp: {ts}")

    for r in run(cur, "snap BACK bel=7+11 NOT OVER", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos,
               COUNT(DISTINCT p.artnr) dist_artnr, SUM(p.poswert) val
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.kzerl='0'
          AND h.aufkstat=0 AND h.belegart IN (7,11)
          AND h.kdnr NOT IN ({fmt_in(over)})
    """):
        log(f"  [BACK bel=7+11 NOT OVER] ords={r[0]}  pos={r[1]}  dist_artnr={r[2]}  val={r[3]}")

    for r in run(cur, "snap BACK bel(6,7,11) NOT OVER", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos,
               COUNT(DISTINCT p.artnr) dist_artnr, SUM(p.poswert) val
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.kzerl='0'
          AND h.aufkstat=0 AND h.belegart IN (6,7,11)
          AND h.kdnr NOT IN ({fmt_in(over)})
    """):
        log(f"  [BACK bel(6,7,11) NOT OVER] ords={r[0]}  pos={r[1]}  dist_artnr={r[2]}  val={r[3]}")

    for r in run(cur, "snap BLOQ bel(6,7,11) IN over", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos,
               COUNT(DISTINCT p.artnr) dist_artnr, SUM(p.poswert) val
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.kzerl='0'
          AND h.aufkstat=0 AND h.belegart IN (6,7,11)
          AND h.kdnr IN ({fmt_in(over)})
    """):
        log(f"  [BLOQ bel(6,7,11) IN over] ords={r[0]}  pos={r[1]}  dist_artnr={r[2]}  val={r[3]}")

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

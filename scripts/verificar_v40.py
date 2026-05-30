"""
TagInfo v40 - TABLA PRE-CALCULADA + f090 columnas + f092 offene Menge
1. Buscar tabla de snapshot: taginfo, tageinfo, tagesinfo, plazo, rueckst, etc
2. Leer columnas extras de f090 para los 14 ordenes (valor header, posanz)
3. f092: columns offmenge, restmenge, etc para ver si hay campo distinto a poswert
4. Combinaciones finales Backorders/Bloqueados
SOLO LECTURA.
"""

import pyodbc
from datetime import date, datetime

DSN = "MSPA"
OUTPUT_FILE = "taginfo_v40.txt"
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

    log(f"TagInfo v40 - TABLA PRE-CALC + f090 cols - {datetime.now()}")
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

    # Get the 14 bel=7+11 NOT OVER orders
    orders_b711 = run(cur, "orders bel=7+11 NOT OVER", f"""
        SELECT DISTINCT h.auftrag
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.kzerl='0'
          AND h.aufkstat=0 AND h.belegart IN (7,11)
          AND h.kdnr NOT IN ({fmt_in(over)})
    """)
    aut_b711 = [r[0] for r in orders_b711]
    log(f"  bel=7+11 NOT OVER count: {len(aut_b711)}\n")

    # ============================================================
    # 1. BUSCAR TABLA PRE-CALCULADA
    # ============================================================
    log("=== BUSCAR TABLA PRE-CALCULADA ===")

    pre_tables = [
        "taginfo",
        "tageinfo",
        "tagesinfo",
        "tagsinfo",
        "tagesinf",
        "tagsinfo2",
        "daily_info",
        "dailyinfo",
        "sales_info",
        "salesinfo",
        "plazo",
        "plazos",
        "rueckst",
        "rueckstand",
        "backorder",
        "backorders",
        "sinfo",
        "pinfo",
        "tb_taginfo",
        "tb_sales",
        "w_taginfo",
        "rep_backorder",
    ]
    for tbl in pre_tables:
        rows = run(cur, f"SELECT {tbl}", f"SELECT FIRST 1 * FROM {tbl} WHERE firma={FIRMA}")
        if rows:
            log(f"  ENCONTRADA: {tbl} -> {rows[0]}")
        # SQL ERROR printed by run() means table doesn't exist

    # ============================================================
    # 2. f090 COLUMNAS EXTRAS para los 14 ordenes
    # ============================================================
    log("\n=== f090 columnas extras para los 14 ordenes ===")

    if aut_b711:
        # Try auftragswert (order total value stored in header)
        for r in run(cur, "f090 auftragswert", f"""
            SELECT auftrag, auftragswert FROM f090
            WHERE firma={FIRMA} AND auftrag IN ({fmt_in(aut_b711)})
            ORDER BY auftrag
        """):
            log(f"  {r[0]}: auftragswert={r[1]}")

        # Try geswert (Gesamtwert = total value)
        for r in run(cur, "f090 geswert", f"""
            SELECT auftrag, geswert FROM f090
            WHERE firma={FIRMA} AND auftrag IN ({fmt_in(aut_b711)})
            ORDER BY auftrag
        """):
            log(f"  {r[0]}: geswert={r[1]}")

        # Try wert
        for r in run(cur, "f090 wert", f"""
            SELECT auftrag, wert FROM f090
            WHERE firma={FIRMA} AND auftrag IN ({fmt_in(aut_b711)})
            ORDER BY auftrag
        """):
            log(f"  {r[0]}: wert={r[1]}")

        # Try nettowert or netwert
        for r in run(cur, "f090 nettowert", f"""
            SELECT auftrag, nettowert FROM f090
            WHERE firma={FIRMA} AND auftrag IN ({fmt_in(aut_b711)})
            ORDER BY auftrag
        """):
            log(f"  {r[0]}: nettowert={r[1]}")

        # Try posanz (Positionsanzahl = number of positions)
        for r in run(cur, "f090 posanz", f"""
            SELECT auftrag, posanz FROM f090
            WHERE firma={FIRMA} AND auftrag IN ({fmt_in(aut_b711)})
            ORDER BY auftrag
        """):
            log(f"  {r[0]}: posanz={r[1]}")

        # Try offposanz (offene Positionsanzahl = open positions count)
        for r in run(cur, "f090 offposanz", f"""
            SELECT auftrag, offposanz FROM f090
            WHERE firma={FIRMA} AND auftrag IN ({fmt_in(aut_b711)})
            ORDER BY auftrag
        """):
            log(f"  {r[0]}: offposanz={r[1]}")

        # Try offwert (offener Wert = open value)
        for r in run(cur, "f090 offwert", f"""
            SELECT auftrag, offwert FROM f090
            WHERE firma={FIRMA} AND auftrag IN ({fmt_in(aut_b711)})
            ORDER BY auftrag
        """):
            log(f"  {r[0]}: offwert={r[1]}")

    # ============================================================
    # 3. f092 COLUMNAS EXTRAS: offmenge, restmenge, resmenge, etc
    # ============================================================
    log("\n=== f092 columnas extras (offene/Rest-menge) ===")

    if aut_b711:
        # Try offmenge (offene Menge = open quantity)
        for r in run(cur, "f092 offmenge", f"""
            SELECT h.auftrag, COUNT(*) pos, SUM(p.offmenge) omenge, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.auftrag IN ({fmt_in(aut_b711)})
            GROUP BY h.auftrag ORDER BY h.auftrag
        """):
            log(f"  {r[0]}: pos={r[1]}  offmenge={r[2]}  poswert={r[3]}")

        # Try restmenge
        for r in run(cur, "f092 restmenge", f"""
            SELECT h.auftrag, COUNT(*) pos, SUM(p.restmenge) rmenge
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.auftrag IN ({fmt_in(aut_b711)})
            GROUP BY h.auftrag ORDER BY h.auftrag
        """):
            log(f"  {r[0]}: pos={r[1]}  restmenge={r[2]}")

        # Try resmenge
        for r in run(cur, "f092 resmenge", f"""
            SELECT COUNT(*) pos, SUM(p.resmenge) rmenge
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.auftrag IN ({fmt_in(aut_b711)})
        """):
            log(f"  total resmenge: pos={r[0]}  resmenge={r[1]}")

        # offwert at position level
        for r in run(cur, "f092 offwert", f"""
            SELECT COUNT(*) pos, SUM(p.offwert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.auftrag IN ({fmt_in(aut_b711)})
        """):
            log(f"  total offwert: pos={r[0]}  offwert={r[1]}")

    # ============================================================
    # 4. bel=7+11 NOT OVER: contar con kzerl como INTEGER
    # (kzerl distribution mostro integer 0, no string '0')
    # ============================================================
    log("\n=== bel=7+11 NOT OVER con kzerl=0 (integer) ===")

    # Try with integer comparison
    for r in run(cur, "bel=7+11 NOT OVER kzerl=0 int", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.kzerl=0
          AND h.aufkstat=0 AND h.belegart IN (7,11)
          AND h.kdnr NOT IN ({fmt_in(over)})
    """):
        log(f"  bel=7+11 NOT OVER kzerl=0 (int): ords={r[0]}  pos={r[1]}  val={r[2]}")

    # What about kzerl IS NULL?
    for r in run(cur, "bel=7+11 NOT OVER kzerl NULL", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.kzerl IS NULL
          AND h.aufkstat=0 AND h.belegart IN (7,11)
          AND h.kdnr NOT IN ({fmt_in(over)})
    """):
        log(f"  bel=7+11 NOT OVER kzerl IS NULL: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # ============================================================
    # 5. f092 posstat=0 + poswert > 0 para los 14 ordenes
    # ============================================================
    log("\n=== f092 posstat=0 + poswert>0 para bel=7+11 NOT OVER ===")

    if aut_b711:
        for r in run(cur, "bel=7+11 posstat=0 poswert>0", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND p.posstat=0 AND p.poswert > 0
              AND h.auftrag IN ({fmt_in(aut_b711)})
        """):
            log(f"  posstat=0 poswert>0: ords={r[0]}  pos={r[1]}  val={r[2]}")

        # all positions grouped by auftrag showing posstat and poswert per pos
        for r in run(cur, "detail per auftrag posstat+poswert", f"""
            SELECT h.auftrag, p.posstat,
                   SUM(CASE WHEN p.poswert>0 THEN 1 ELSE 0 END) pos_with_val,
                   SUM(CASE WHEN p.poswert=0 THEN 1 ELSE 0 END) pos_zero_val,
                   COUNT(*) total_pos,
                   SUM(p.poswert) total_val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.auftrag IN ({fmt_in(aut_b711)})
            GROUP BY h.auftrag, p.posstat
            ORDER BY h.auftrag, p.posstat
        """):
            log(f"  auftrag={r[0]} posstat={r[1]} pos_w_val={r[2]} pos_zero={r[3]} total={r[4]} val={r[5]}")

    # ============================================================
    # 6. Resumen: cuantos de los 14 ordenes tienen poswert>0 vs =0
    # Y el subset que da 1070283
    # ============================================================
    log("\n=== SUBSET valor: bel=7+11 NOT OVER con poswert>0 por orden ===")

    if aut_b711:
        for r in run(cur, "por-orden valor total bel=7+11", f"""
            SELECT h.auftrag, h.belegart, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.auftrag IN ({fmt_in(aut_b711)})
            GROUP BY h.auftrag, h.belegart
            ORDER BY val DESC
        """):
            log(f"  {r[0]} bel={r[1]} pos={r[2]} val={r[3]}")

    # ============================================================
    # 7. SNAPSHOT SIMULTANEO
    # ============================================================
    print("\n*** TOMAR SCREENSHOT DE PANTALLA AHORA ***\n")
    log("\n=== SNAPSHOT SIMULTANEO ===")
    ts = datetime.now()
    log(f"  Timestamp: {ts}")

    # Standard combos
    for r in run(cur, "snap BACK bel=7+11 NOT OVER", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.kzerl='0'
          AND h.aufkstat=0 AND h.belegart IN (7,11)
          AND h.kdnr NOT IN ({fmt_in(over)})
    """):
        log(f"  [BACK bel=7+11 NOT OVER] ords={r[0]}  pos={r[1]}  val={r[2]}")

    for r in run(cur, "snap BACK bel(6,7,11) NOT OVER", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.kzerl='0'
          AND h.aufkstat=0 AND h.belegart IN (6,7,11)
          AND h.kdnr NOT IN ({fmt_in(over)})
    """):
        log(f"  [BACK bel(6,7,11) NOT OVER] ords={r[0]}  pos={r[1]}  val={r[2]}")

    for r in run(cur, "snap BLOQ bel(6,7,11) IN over", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.kzerl='0'
          AND h.aufkstat=0 AND h.belegart IN (6,7,11)
          AND h.kdnr IN ({fmt_in(over)})
    """):
        log(f"  [BLOQ bel(6,7,11) IN over] ords={r[0]}  pos={r[1]}  val={r[2]}")

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

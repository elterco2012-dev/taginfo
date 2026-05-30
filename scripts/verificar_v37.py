"""
TagInfo v37 - DETALLE ORDENES + HIPOTESIS aufkstat=-1 + posstat
1. Listar los 37 ordenes individuales (bel 6,7,11 aufkstat=0) con sus propiedades
2. aufkstat=-1 como Bloqueados (status automatico ERP)
3. posstat=0 como filtro adicional en Backorders
4. Distribucion por kdnr, belegart, posstat de los 37 ordenes
SOLO LECTURA.
"""

import pyodbc
from datetime import date, datetime

DSN = "MSPA"
OUTPUT_FILE = "taginfo_v37.txt"
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

    log(f"TagInfo v37 - DETALLE ORDENES - {datetime.now()}")
    log(f"DSN: {DSN}  |  Fecha: {today}  |  SOLO LECTURA")
    log("=" * 70)

    conn = get_conn()
    cur = conn.cursor()
    log("Conexion OK\n")

    kredlim_rows = run(cur, "kredlim", f"SELECT kdnr, kredlim FROM kund WHERE firma={FIRMA} AND kredlim > 0")
    kredlim_map = {r[0]: r[1] for r in kredlim_rows}
    def fmt_in(lst): return ",".join(str(k) for k in lst)

    totals_6711 = run(cur, "per-kdnr bel(6,7,11)", f"""
        SELECT h.kdnr, SUM(p.poswert)
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.kzerl='0'
          AND h.aufkstat<>8 AND h.belegart IN (6,7,11)
        GROUP BY h.kdnr
    """)
    over  = [r[0] for r in totals_6711 if kredlim_map.get(r[0],0)>0 and r[1] and r[1]>kredlim_map.get(r[0],0)]
    under = [r[0] for r in totals_6711 if not(kredlim_map.get(r[0],0)>0 and r[1] and r[1]>kredlim_map.get(r[0],0))]
    log(f"  over={len(over)}  under={len(under)}\n")

    # ============================================================
    # 1. LISTAR CADA ORDEN bel(6,7,11) aufkstat=0 kzerl='0'
    # ============================================================
    log("=== LISTADO INDIVIDUAL bel(6,7,11) aufkstat=0 ===")
    log("  auftrag  bel  kdnr  kredlim  poscount  poscount_ps0  val  val_ps0  posstat_dist")

    ords = run(cur, "list ordenes", f"""
        SELECT h.auftrag, h.belegart, h.kdnr,
               COUNT(*) poscount,
               SUM(p.poswert) val
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.kzerl='0'
          AND h.aufkstat=0 AND h.belegart IN (6,7,11)
        GROUP BY h.auftrag, h.belegart, h.kdnr
        ORDER BY h.belegart, h.kdnr, h.auftrag
    """)
    for r in ords:
        auftrag, bel, kdnr, pos, val = r
        kl = kredlim_map.get(kdnr, 0)
        over_flag = "OVER" if kl > 0 and val and float(val) > kl else "ok"
        log(f"  {auftrag}  bel={bel}  kdnr={kdnr}  kredlim={kl}  pos={pos}  val={val}  {over_flag}")

    log(f"\n  TOTAL ordenes listados: {len(ords)}")

    # posstat distribution within each belegart for aufkstat=0
    log("\n=== POSSTAT en bel(6,7,11) aufkstat=0 ===")
    for r in run(cur, "posstat dist bel(6,7,11) aufkstat=0", f"""
        SELECT h.belegart, p.posstat, COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.kzerl='0'
          AND h.aufkstat=0 AND h.belegart IN (6,7,11)
        GROUP BY h.belegart, p.posstat ORDER BY h.belegart, p.posstat
    """):
        log(f"  bel={r[0]}  posstat={r[1]}  ords={r[2]}  pos={r[3]}  val={r[4]}")

    # ============================================================
    # 2. HIPOTESIS aufkstat=-1 para BLOQUEADOS
    # ============================================================
    log("\n=== HIPOTESIS aufkstat=-1 = BLOQUEADOS ===")

    for r in run(cur, "aufkstat=-1 bel(6,7,11)", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.kzerl='0'
          AND h.aufkstat=-1 AND h.belegart IN (6,7,11)
    """):
        log(f"  aufkstat=-1 bel(6,7,11): ords={r[0]}  pos={r[1]}  val={r[2]}")

    for r in run(cur, "aufkstat=-1 all bel", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.kzerl='0'
          AND h.aufkstat=-1
    """):
        log(f"  aufkstat=-1 all bel: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # aufkstat distribution near 0
    log("\n  aufkstat distribution -3 to 3 bel(6,7,11):")
    for r in run(cur, "aufkstat dist -3..3", f"""
        SELECT h.aufkstat, COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.kzerl='0'
          AND h.belegart IN (6,7,11)
          AND h.aufkstat BETWEEN -3 AND 3
        GROUP BY h.aufkstat ORDER BY h.aufkstat
    """):
        log(f"    aufkstat={r[0]}  ords={r[1]}  pos={r[2]}  val={r[3]}")

    # ============================================================
    # 3. POSSTAT=0 como filtro adicional
    # ============================================================
    log("\n=== POSSTAT=0 COMO FILTRO EN BACKORDERS ===")

    if over:
        for r in run(cur, "BACK posstat=0 NOT IN over", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.aufkstat=0 AND h.belegart IN (6,7,11)
              AND p.posstat=0
              AND h.kdnr NOT IN ({fmt_in(over)})
        """):
            log(f"  BACK bel(6,7,11) posstat=0 NOT IN over: ords={r[0]}  pos={r[1]}  val={r[2]}")

        for r in run(cur, "BLOQ posstat=0 IN over", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.aufkstat=0 AND h.belegart IN (6,7,11)
              AND p.posstat=0
              AND h.kdnr IN ({fmt_in(over)})
        """):
            log(f"  BLOQ bel(6,7,11) posstat=0 IN over: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # Total posstat=0 bel(6,7,11) aufkstat=0
    for r in run(cur, "total posstat=0 bel(6,7,11) aufkstat=0", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.kzerl='0'
          AND h.aufkstat=0 AND h.belegart IN (6,7,11)
          AND p.posstat=0
    """):
        log(f"  TOTAL bel(6,7,11) aufkstat=0 posstat=0: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # ============================================================
    # 4. DISTRIBUCION POR KDNR de los 37 ordenes
    #    (ver si los 14 de la pantalla son un subconjunto de clientes)
    # ============================================================
    log("\n=== KDNR distribution: over vs under en bel(6,7,11) aufkstat=0 ===")
    log("  Ordenes over-kredlim:")
    over_set = set(over)
    for r in ords:
        auftrag, bel, kdnr, pos, val = r
        if kdnr in over_set:
            log(f"    auftrag={auftrag} bel={bel} kdnr={kdnr} pos={pos} val={val}")
    log("  Ordenes NOT over-kredlim:")
    for r in ords:
        auftrag, bel, kdnr, pos, val = r
        if kdnr not in over_set:
            log(f"    auftrag={auftrag} bel={bel} kdnr={kdnr} pos={pos} val={val}")

    # ============================================================
    # SNAPSHOT SIMULTANEO
    # ============================================================
    print("\n*** TOMAR SCREENSHOT DE PANTALLA AHORA ***\n")
    log("\n=== SNAPSHOT SIMULTANEO ===")
    ts = datetime.now()
    log(f"  Timestamp: {ts}")

    # aufkstat=-1 for Bloqueados
    for r in run(cur, "snap BLOQ aufkstat=-1", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.kzerl='0'
          AND h.aufkstat=-1 AND h.belegart IN (6,7,11)
    """):
        log(f"  [BLOQ aufkstat=-1] ords={r[0]}  pos={r[1]}  val={r[2]}")

    # Backorders sin over: aufkstat=0
    for r in run(cur, "snap BACK aufkstat=0 all", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.kzerl='0'
          AND h.aufkstat=0 AND h.belegart IN (6,7,11)
    """):
        log(f"  [BACK aufkstat=0 all bel(6,7,11)] ords={r[0]}  pos={r[1]}  val={r[2]}")

    for r in run(cur, "snap BACK posstat=0", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.kzerl='0'
          AND h.aufkstat=0 AND h.belegart IN (6,7,11) AND p.posstat=0
    """):
        log(f"  [BACK aufkstat=0 bel(6,7,11) posstat=0] ords={r[0]}  pos={r[1]}  val={r[2]}")

    # Standard Remitos, Produccion, Venta
    for r in run(cur, "REMITOS", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND h.belegart=11 AND h.aufkstat=4
    """):
        log(f"  [REMITOS] ords={r[0]}  pos={r[1]}  val={r[2]}")

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

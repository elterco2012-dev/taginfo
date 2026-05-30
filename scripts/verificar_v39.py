"""
TagInfo v39 - LIEFSP FIELD + credit block via kund.liefsp
Hipotesis: Bloqueados = kund.liefsp indica bloqueo credito
           Backorders = bel=7+11 aufkstat=0 kzerl='0' + kund.liefsp='0'
SOLO LECTURA.
"""

import pyodbc
from datetime import date, datetime

DSN = "MSPA"
OUTPUT_FILE = "taginfo_v39.txt"
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

    log(f"TagInfo v39 - LIEFSP - {datetime.now()}")
    log(f"DSN: {DSN}  |  Fecha: {today}  |  SOLO LECTURA")
    log("=" * 70)

    conn = get_conn()
    cur = conn.cursor()
    log("Conexion OK\n")

    kredlim_rows = run(cur, "kredlim", f"SELECT kdnr, kredlim FROM kund WHERE firma={FIRMA} AND kredlim > 0")
    kredlim_map = {r[0]: r[1] for r in kredlim_rows}

    # Standard credit base bel(6,7,11)
    totals_6711 = run(cur, "per-kdnr bel(6,7,11)", f"""
        SELECT h.kdnr, SUM(p.poswert)
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.kzerl='0'
          AND h.aufkstat<>8 AND h.belegart IN (6,7,11)
        GROUP BY h.kdnr
    """)
    over_6711 = [r[0] for r in totals_6711 if kredlim_map.get(r[0],0)>0 and r[1] and r[1]>kredlim_map.get(r[0],0)]
    def fmt_in(lst): return ",".join(str(k) for k in lst)

    # ============================================================
    # 1. LIEFSP distribution in kund for customers with aufkstat=0 orders
    # ============================================================
    log("=== LIEFSP distribution en kund ===")

    # All liefsp values
    for r in run(cur, "liefsp dist all kund", f"""
        SELECT liefsp, COUNT(*) cnt FROM kund WHERE firma={FIRMA}
        GROUP BY liefsp ORDER BY liefsp
    """):
        log(f"  liefsp={r[0]}  cnt={r[1]}")

    # liefsp for customers with aufkstat=0 bel(6,7,11) orders
    log("\n  liefsp for customers with bel(6,7,11) aufkstat=0 orders:")
    for r in run(cur, "liefsp para clientes con aufkstat=0", f"""
        SELECT k.liefsp, COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p, kund k
        WHERE h.firma={FIRMA} AND p.firma={FIRMA} AND k.firma={FIRMA}
          AND h.auftrag=p.auftrag AND h.kdnr=k.kdnr
          AND p.kzerl='0' AND h.aufkstat=0 AND h.belegart IN (6,7,11)
        GROUP BY k.liefsp ORDER BY k.liefsp
    """):
        log(f"  liefsp={r[0]}  ords={r[1]}  pos={r[2]}  val={r[3]}")

    # ============================================================
    # 2. HIPOTESIS BACKORDERS = bel(6,7,11) aufkstat=0 kzerl='0' liefsp='0'
    # ============================================================
    log("\n=== BACKORDERS via kund.liefsp='0' ===")

    # bel(6,7,11) aufkstat=0 liefsp='0'
    for r in run(cur, "BACK bel(6,7,11) aufkstat=0 liefsp=0", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p, kund k
        WHERE h.firma={FIRMA} AND p.firma={FIRMA} AND k.firma={FIRMA}
          AND h.auftrag=p.auftrag AND h.kdnr=k.kdnr
          AND p.kzerl='0' AND h.aufkstat=0 AND h.belegart IN (6,7,11)
          AND k.liefsp='0'
    """):
        log(f"  bel(6,7,11) aufkstat=0 liefsp='0': ords={r[0]}  pos={r[1]}  val={r[2]}")

    # bel=7+11 aufkstat=0 liefsp='0'
    for r in run(cur, "BACK bel=7+11 aufkstat=0 liefsp=0", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p, kund k
        WHERE h.firma={FIRMA} AND p.firma={FIRMA} AND k.firma={FIRMA}
          AND h.auftrag=p.auftrag AND h.kdnr=k.kdnr
          AND p.kzerl='0' AND h.aufkstat=0 AND h.belegart IN (7,11)
          AND k.liefsp='0'
    """):
        log(f"  bel=7+11 aufkstat=0 liefsp='0': ords={r[0]}  pos={r[1]}  val={r[2]}")

    # bel=11 aufkstat=0 liefsp='0'
    for r in run(cur, "BACK bel=11 aufkstat=0 liefsp=0", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p, kund k
        WHERE h.firma={FIRMA} AND p.firma={FIRMA} AND k.firma={FIRMA}
          AND h.auftrag=p.auftrag AND h.kdnr=k.kdnr
          AND p.kzerl='0' AND h.aufkstat=0 AND h.belegart=11
          AND k.liefsp='0'
    """):
        log(f"  bel=11 aufkstat=0 liefsp='0': ords={r[0]}  pos={r[1]}  val={r[2]}")

    # ============================================================
    # 3. HIPOTESIS BLOQUEADOS = bel(6,7,11) aufkstat=0 liefsp != '0'
    # ============================================================
    log("\n=== BLOQUEADOS via kund.liefsp != '0' ===")

    # Try all specific non-zero liefsp values
    for liefsp_val in ["'1'", "'2'", "'3'", "'9'"]:
        for r in run(cur, f"BLOQ liefsp={liefsp_val}", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p, kund k
            WHERE h.firma={FIRMA} AND p.firma={FIRMA} AND k.firma={FIRMA}
              AND h.auftrag=p.auftrag AND h.kdnr=k.kdnr
              AND p.kzerl='0' AND h.aufkstat=0 AND h.belegart IN (6,7,11)
              AND k.liefsp={liefsp_val}
        """):
            log(f"  BLOQ bel(6,7,11) aufkstat=0 liefsp={liefsp_val}: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # ============================================================
    # 4. LIEFSP para CADA kdnr en los 37 ordenes aufkstat=0
    # ============================================================
    log("\n=== LIEFSP por kdnr en los 37 ordenes aufkstat=0 ===")

    # Get all unique kdnr in aufkstat=0 bel(6,7,11) orders
    kdnr_rows = run(cur, "kdnr en aufkstat=0", f"""
        SELECT DISTINCT h.kdnr, h.belegart, h.auftrag
        FROM f090 h WHERE h.firma={FIRMA}
          AND h.aufkstat=0 AND h.belegart IN (6,7,11)
        ORDER BY h.belegart, h.kdnr
    """)
    kdnrs = list(set(r[0] for r in kdnr_rows))

    if kdnrs:
        for r in run(cur, "liefsp por kdnr", f"""
            SELECT k.kdnr, k.liefsp, k.kredlim
            FROM kund k WHERE k.firma={FIRMA}
              AND k.kdnr IN ({fmt_in(kdnrs)})
            ORDER BY k.liefsp, k.kdnr
        """):
            kl = float(r[2]) if r[2] else 0
            over = "OVER" if kredlim_map.get(r[0],0)>0 and kl>kredlim_map.get(r[0],0) else "ok"
            log(f"  kdnr={r[0]}  liefsp={r[1]}  kredlim={r[2]}  {over}")

    # ============================================================
    # 5. BACKORDERS usando liefsp='0' + diferentes belegart
    #    Con distribucion por belegart
    # ============================================================
    log("\n=== BACK liefsp='0' por belegart ===")

    for r in run(cur, "dist belegart liefsp=0 aufkstat=0", f"""
        SELECT h.belegart, COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p, kund k
        WHERE h.firma={FIRMA} AND p.firma={FIRMA} AND k.firma={FIRMA}
          AND h.auftrag=p.auftrag AND h.kdnr=k.kdnr
          AND p.kzerl='0' AND h.aufkstat=0 AND h.belegart IN (6,7,11)
          AND k.liefsp='0'
        GROUP BY h.belegart ORDER BY h.belegart
    """):
        log(f"  bel={r[0]}  ords={r[1]}  pos={r[2]}  val={r[3]}")

    # ============================================================
    # 6. Misma logica para BLOQ — dist belegart por liefsp
    # ============================================================
    log("\n=== BLOQ liefsp<>'0' belegart dist ===")

    for r in run(cur, "dist belegart liefsp<>0 aufkstat=0", f"""
        SELECT h.belegart, k.liefsp, COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p, kund k
        WHERE h.firma={FIRMA} AND p.firma={FIRMA} AND k.firma={FIRMA}
          AND h.auftrag=p.auftrag AND h.kdnr=k.kdnr
          AND p.kzerl='0' AND h.aufkstat=0 AND h.belegart IN (6,7,11)
          AND k.liefsp<>'0'
        GROUP BY h.belegart, k.liefsp ORDER BY k.liefsp, h.belegart
    """):
        log(f"  bel={r[0]}  liefsp={r[1]}  ords={r[2]}  pos={r[3]}  val={r[4]}")

    # ============================================================
    # 7. SNAPSHOT SIMULTANEO
    # ============================================================
    print("\n*** TOMAR SCREENSHOT DE PANTALLA AHORA ***\n")
    log("\n=== SNAPSHOT SIMULTANEO ===")
    ts = datetime.now()
    log(f"  Timestamp: {ts}")

    # BACK via liefsp='0', various belegart combos
    for r in run(cur, "snap BACK bel(6,7,11) liefsp=0", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p, kund k
        WHERE h.firma={FIRMA} AND p.firma={FIRMA} AND k.firma={FIRMA}
          AND h.auftrag=p.auftrag AND h.kdnr=k.kdnr
          AND p.kzerl='0' AND h.aufkstat=0 AND h.belegart IN (6,7,11)
          AND k.liefsp='0'
    """):
        log(f"  [BACK bel(6,7,11) liefsp='0'] ords={r[0]}  pos={r[1]}  val={r[2]}")

    for r in run(cur, "snap BACK bel=7+11 liefsp=0", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p, kund k
        WHERE h.firma={FIRMA} AND p.firma={FIRMA} AND k.firma={FIRMA}
          AND h.auftrag=p.auftrag AND h.kdnr=k.kdnr
          AND p.kzerl='0' AND h.aufkstat=0 AND h.belegart IN (7,11)
          AND k.liefsp='0'
    """):
        log(f"  [BACK bel=7+11 liefsp='0'] ords={r[0]}  pos={r[1]}  val={r[2]}")

    # BLOQ via liefsp!='0' for various combos
    for r in run(cur, "snap BLOQ bel(6,7,11) liefsp<>0", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p, kund k
        WHERE h.firma={FIRMA} AND p.firma={FIRMA} AND k.firma={FIRMA}
          AND h.auftrag=p.auftrag AND h.kdnr=k.kdnr
          AND p.kzerl='0' AND h.aufkstat=0 AND h.belegart IN (6,7,11)
          AND k.liefsp<>'0'
    """):
        log(f"  [BLOQ bel(6,7,11) liefsp<>'0'] ords={r[0]}  pos={r[1]}  val={r[2]}")

    for r in run(cur, "snap BLOQ bel=7+11 liefsp<>0", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p, kund k
        WHERE h.firma={FIRMA} AND p.firma={FIRMA} AND k.firma={FIRMA}
          AND h.auftrag=p.auftrag AND h.kdnr=k.kdnr
          AND p.kzerl='0' AND h.aufkstat=0 AND h.belegart IN (7,11)
          AND k.liefsp<>'0'
    """):
        log(f"  [BLOQ bel=7+11 liefsp<>'0'] ords={r[0]}  pos={r[1]}  val={r[2]}")

    # REMITOS, PRODUCCION, VENTA
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

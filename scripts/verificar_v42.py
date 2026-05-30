"""
TagInfo v42 - F103 TABLE EXPLORATION
taginfo_offes.sql usa f103 (no f090!) con formula:
  round(f103.sollme * f092.poswert / f092.auftme, 2) ums
Explorar f103: estructura, relacion con f090, backorders y bloqueados.
SOLO LECTURA.
"""

import pyodbc
from datetime import date, datetime

DSN = "MSPA"
OUTPUT_FILE = "taginfo_v42.txt"
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

    log(f"TagInfo v42 - F103 TABLE - {datetime.now()}")
    log(f"DSN: {DSN}  |  Fecha: {today}  |  SOLO LECTURA")
    log("=" * 70)

    conn = get_conn()
    cur = conn.cursor()
    log("Conexion OK\n")

    # ============================================================
    # 1. F103 - cuantos registros tiene?
    # ============================================================
    log("=== F103 COUNT ===")
    for r in run(cur, "f103 count all", f"SELECT COUNT(*) FROM f103 WHERE firma={FIRMA}"):
        log(f"  f103 total rows: {r[0]}")

    # ============================================================
    # 2. F103 - columnas disponibles (probar names)
    # ============================================================
    log("\n=== F103 COLUMNAS DISPONIBLES ===")
    # Try columns seen in taginfo_offes.sql and common names
    col_tests = [
        ("auftrag", f"SELECT auftrag FROM f103 WHERE firma={FIRMA} AND ROWNUM<=1"),
        ("posnr", f"SELECT posnr FROM f103 WHERE firma={FIRMA} AND ROWNUM<=1"),
        ("sollme", f"SELECT sollme FROM f103 WHERE firma={FIRMA} AND ROWNUM<=1"),
        ("artnr", f"SELECT artnr FROM f103 WHERE firma={FIRMA} AND ROWNUM<=1"),
        ("kdnr", f"SELECT kdnr FROM f103 WHERE firma={FIRMA} AND ROWNUM<=1"),
        ("belegart", f"SELECT belegart FROM f103 WHERE firma={FIRMA} AND ROWNUM<=1"),
        ("aufkstat", f"SELECT aufkstat FROM f103 WHERE firma={FIRMA} AND ROWNUM<=1"),
        ("posstat", f"SELECT posstat FROM f103 WHERE firma={FIRMA} AND ROWNUM<=1"),
        ("kzerl", f"SELECT kzerl FROM f103 WHERE firma={FIRMA} AND ROWNUM<=1"),
        ("liefdat", f"SELECT liefdat FROM f103 WHERE firma={FIRMA} AND ROWNUM<=1"),
        ("termin", f"SELECT termin FROM f103 WHERE firma={FIRMA} AND ROWNUM<=1"),
        ("offmenge", f"SELECT offmenge FROM f103 WHERE firma={FIRMA} AND ROWNUM<=1"),
        ("restmenge", f"SELECT restmenge FROM f103 WHERE firma={FIRMA} AND ROWNUM<=1"),
        ("dispmenge", f"SELECT dispmenge FROM f103 WHERE firma={FIRMA} AND ROWNUM<=1"),
        ("liefme", f"SELECT liefme FROM f103 WHERE firma={FIRMA} AND ROWNUM<=1"),
        ("aufmenge", f"SELECT aufmenge FROM f103 WHERE firma={FIRMA} AND ROWNUM<=1"),
        ("auftme", f"SELECT auftme FROM f103 WHERE firma={FIRMA} AND ROWNUM<=1"),
        ("menge", f"SELECT menge FROM f103 WHERE firma={FIRMA} AND ROWNUM<=1"),
        ("wert", f"SELECT wert FROM f103 WHERE firma={FIRMA} AND ROWNUM<=1"),
        ("poswert", f"SELECT poswert FROM f103 WHERE firma={FIRMA} AND ROWNUM<=1"),
        ("netwert", f"SELECT netwert FROM f103 WHERE firma={FIRMA} AND ROWNUM<=1"),
        ("vstueli", f"SELECT vstueli FROM f103 WHERE firma={FIRMA} AND ROWNUM<=1"),
        ("liefsp", f"SELECT liefsp FROM f103 WHERE firma={FIRMA} AND ROWNUM<=1"),
    ]
    # Use FIRST 1 syntax for Informix
    col_tests2 = [
        ("auftrag", f"SELECT FIRST 1 auftrag FROM f103 WHERE firma={FIRMA}"),
        ("posnr", f"SELECT FIRST 1 posnr FROM f103 WHERE firma={FIRMA}"),
        ("sollme", f"SELECT FIRST 1 sollme FROM f103 WHERE firma={FIRMA}"),
        ("artnr", f"SELECT FIRST 1 artnr FROM f103 WHERE firma={FIRMA}"),
        ("kdnr", f"SELECT FIRST 1 kdnr FROM f103 WHERE firma={FIRMA}"),
        ("belegart", f"SELECT FIRST 1 belegart FROM f103 WHERE firma={FIRMA}"),
        ("aufkstat", f"SELECT FIRST 1 aufkstat FROM f103 WHERE firma={FIRMA}"),
        ("posstat", f"SELECT FIRST 1 posstat FROM f103 WHERE firma={FIRMA}"),
        ("kzerl", f"SELECT FIRST 1 kzerl FROM f103 WHERE firma={FIRMA}"),
        ("liefdat", f"SELECT FIRST 1 liefdat FROM f103 WHERE firma={FIRMA}"),
        ("termin", f"SELECT FIRST 1 termin FROM f103 WHERE firma={FIRMA}"),
        ("offmenge", f"SELECT FIRST 1 offmenge FROM f103 WHERE firma={FIRMA}"),
        ("restmenge", f"SELECT FIRST 1 restmenge FROM f103 WHERE firma={FIRMA}"),
        ("dispmenge", f"SELECT FIRST 1 dispmenge FROM f103 WHERE firma={FIRMA}"),
        ("liefme", f"SELECT FIRST 1 liefme FROM f103 WHERE firma={FIRMA}"),
        ("aufmenge", f"SELECT FIRST 1 aufmenge FROM f103 WHERE firma={FIRMA}"),
        ("auftme", f"SELECT FIRST 1 auftme FROM f103 WHERE firma={FIRMA}"),
        ("menge", f"SELECT FIRST 1 menge FROM f103 WHERE firma={FIRMA}"),
        ("wert", f"SELECT FIRST 1 wert FROM f103 WHERE firma={FIRMA}"),
        ("poswert", f"SELECT FIRST 1 poswert FROM f103 WHERE firma={FIRMA}"),
        ("netwert", f"SELECT FIRST 1 netwert FROM f103 WHERE firma={FIRMA}"),
        ("vstueli", f"SELECT FIRST 1 vstueli FROM f103 WHERE firma={FIRMA}"),
        ("liefsp", f"SELECT FIRST 1 liefsp FROM f103 WHERE firma={FIRMA}"),
        ("kbetrag", f"SELECT FIRST 1 kbetrag FROM f103 WHERE firma={FIRMA}"),
        ("preis", f"SELECT FIRST 1 preis FROM f103 WHERE firma={FIRMA}"),
        ("rabatt", f"SELECT FIRST 1 rabatt FROM f103 WHERE firma={FIRMA}"),
        ("stat", f"SELECT FIRST 1 stat FROM f103 WHERE firma={FIRMA}"),
        ("status", f"SELECT FIRST 1 status FROM f103 WHERE firma={FIRMA}"),
    ]
    available_cols = []
    for colname, sql in col_tests2:
        rows = run(cur, f"col {colname}", sql)
        if rows:
            available_cols.append(colname)
            log(f"  OK: f103.{colname} = {rows[0][0]}")
        else:
            log(f"  NO: f103.{colname}")

    # ============================================================
    # 3. F103 join f092 - formula taginfo_offes.sql
    #    round(f103.sollme * f092.poswert / f092.auftme, 2) ums
    # ============================================================
    log("\n=== F103 JOIN F092: formula offes ===")

    # Total usando formula de taginfo_offes.sql
    for r in run(cur, "sum formula offes", f"""
        SELECT COUNT(DISTINCT f103.auftrag) ords, COUNT(*) pos,
               SUM(ROUND(f103.sollme * f092.poswert / f092.auftme, 2)) val
        FROM f103, f092
        WHERE f103.firma={FIRMA} AND f092.firma={FIRMA}
          AND f103.auftrag=f092.auftrag AND f103.posnr=f092.posnr
    """):
        log(f"  f103+f092 total: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # Con kzerl='0'
    for r in run(cur, "f103+f092 kzerl=0", f"""
        SELECT COUNT(DISTINCT f103.auftrag) ords, COUNT(*) pos,
               SUM(ROUND(f103.sollme * f092.poswert / f092.auftme, 2)) val
        FROM f103, f092
        WHERE f103.firma={FIRMA} AND f092.firma={FIRMA}
          AND f103.auftrag=f092.auftrag AND f103.posnr=f092.posnr
          AND f092.kzerl='0'
    """):
        log(f"  f103+f092 kzerl='0': ords={r[0]}  pos={r[1]}  val={r[2]}")

    # ============================================================
    # 4. F103 - ver si tiene belegart y aufkstat propios
    #    o si hay que joinear con f090
    # ============================================================
    log("\n=== F103 JOIN F090 + F092 ===")

    # f103 + f090 + f092 con aufkstat=0 bel(7,11)
    for r in run(cur, "f103+f090+f092 aufkstat=0 bel(7,11)", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos,
               SUM(ROUND(f103.sollme * f092.poswert / f092.auftme, 2)) val
        FROM f103, f090 h, f092
        WHERE f103.firma={FIRMA} AND h.firma={FIRMA} AND f092.firma={FIRMA}
          AND f103.auftrag=h.auftrag AND f103.auftrag=f092.auftrag
          AND f103.posnr=f092.posnr
          AND f092.kzerl='0' AND h.aufkstat=0 AND h.belegart IN (7,11)
    """):
        log(f"  f103+f090+f092 aufkstat=0 bel(7,11) kzerl='0': ords={r[0]}  pos={r[1]}  val={r[2]}")

    # f103 + f090 + f092 con aufkstat=0 bel(6,7,11)
    for r in run(cur, "f103+f090+f092 aufkstat=0 bel(6,7,11)", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos,
               SUM(ROUND(f103.sollme * f092.poswert / f092.auftme, 2)) val
        FROM f103, f090 h, f092
        WHERE f103.firma={FIRMA} AND h.firma={FIRMA} AND f092.firma={FIRMA}
          AND f103.auftrag=h.auftrag AND f103.auftrag=f092.auftrag
          AND f103.posnr=f092.posnr
          AND f092.kzerl='0' AND h.aufkstat=0 AND h.belegart IN (6,7,11)
    """):
        log(f"  f103+f090+f092 aufkstat=0 bel(6,7,11) kzerl='0': ords={r[0]}  pos={r[1]}  val={r[2]}")

    # ============================================================
    # 5. KREDLIM WORKAROUND + F103
    # ============================================================
    log("\n=== KREDLIM + F103 ===")

    kredlim_rows = run(cur, "kredlim", f"SELECT kdnr, kredlim FROM kund WHERE firma={FIRMA} AND kredlim > 0")
    kredlim_map = {r[0]: r[1] for r in kredlim_rows}

    # totals por kdnr usando formula f103
    totals_f103 = run(cur, "per-kdnr f103 bel(6,7,11) aufkstat=0", f"""
        SELECT h.kdnr, SUM(ROUND(f103.sollme * f092.poswert / f092.auftme, 2))
        FROM f103, f090 h, f092
        WHERE f103.firma={FIRMA} AND h.firma={FIRMA} AND f092.firma={FIRMA}
          AND f103.auftrag=h.auftrag AND f103.auftrag=f092.auftrag
          AND f103.posnr=f092.posnr
          AND f092.kzerl='0' AND h.aufkstat=0 AND h.belegart IN (6,7,11)
        GROUP BY h.kdnr
    """)
    over_f103 = [r[0] for r in totals_f103 if kredlim_map.get(r[0],0)>0 and r[1] and float(r[1])>kredlim_map.get(r[0],0)]
    log(f"  over_f103 (kdnrs sobre kredlim): {over_f103}")

    def fmt_in(lst): return ",".join(str(k) for k in lst)

    # BACKORDERS via f103 (NOT IN over)
    if over_f103:
        for r in run(cur, "BACK f103 NOT IN over bel(7,11)", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos,
                   SUM(ROUND(f103.sollme * f092.poswert / f092.auftme, 2)) val
            FROM f103, f090 h, f092
            WHERE f103.firma={FIRMA} AND h.firma={FIRMA} AND f092.firma={FIRMA}
              AND f103.auftrag=h.auftrag AND f103.auftrag=f092.auftrag
              AND f103.posnr=f092.posnr
              AND f092.kzerl='0' AND h.aufkstat=0 AND h.belegart IN (7,11)
              AND h.kdnr NOT IN ({fmt_in(over_f103)})
        """):
            log(f"  BACK f103 bel(7,11) NOT IN over: ords={r[0]}  pos={r[1]}  val={r[2]}")

        for r in run(cur, "BLOQ f103 IN over bel(7,11)", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos,
                   SUM(ROUND(f103.sollme * f092.poswert / f092.auftme, 2)) val
            FROM f103, f090 h, f092
            WHERE f103.firma={FIRMA} AND h.firma={FIRMA} AND f092.firma={FIRMA}
              AND f103.auftrag=h.auftrag AND f103.auftrag=f092.auftrag
              AND f103.posnr=f092.posnr
              AND f092.kzerl='0' AND h.aufkstat=0 AND h.belegart IN (7,11)
              AND h.kdnr IN ({fmt_in(over_f103)})
        """):
            log(f"  BLOQ f103 bel(7,11) IN over: ords={r[0]}  pos={r[1]}  val={r[2]}")
    else:
        log("  (no over_f103 customers today)")
        for r in run(cur, "BACK f103 all bel(7,11) aufkstat=0", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos,
                   SUM(ROUND(f103.sollme * f092.poswert / f092.auftme, 2)) val
            FROM f103, f090 h, f092
            WHERE f103.firma={FIRMA} AND h.firma={FIRMA} AND f092.firma={FIRMA}
              AND f103.auftrag=h.auftrag AND f103.auftrag=f092.auftrag
              AND f103.posnr=f092.posnr
              AND f092.kzerl='0' AND h.aufkstat=0 AND h.belegart IN (7,11)
        """):
            log(f"  BACK f103 all bel(7,11) aufkstat=0: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # ============================================================
    # 6. TAMBIEN usando f103 SOLO (sin join f090) si tiene belegart/aufkstat
    # ============================================================
    log("\n=== F103 STANDALONE (si tiene cols propias) ===")
    # Try: does f103 have aufkstat?
    for r in run(cur, "f103 aufkstat dist", f"""
        SELECT aufkstat, COUNT(*) FROM f103 WHERE firma={FIRMA}
        GROUP BY aufkstat ORDER BY aufkstat
    """):
        log(f"  f103 aufkstat={r[0]} cnt={r[1]}")

    for r in run(cur, "f103 belegart dist", f"""
        SELECT belegart, COUNT(*) FROM f103 WHERE firma={FIRMA}
        GROUP BY belegart ORDER BY belegart
    """):
        log(f"  f103 belegart={r[0]} cnt={r[1]}")

    # ============================================================
    # 7. SNAPSHOT SIMULTANEO - targets: 14 ords, 16 pos, 1,070,283 val
    # ============================================================
    print("\n*** TOMAR SCREENSHOT DE PANTALLA AHORA ***\n")
    log("\n=== SNAPSHOT SIMULTANEO ===")
    ts = datetime.now()
    log(f"  Timestamp: {ts}")
    log("  TARGET: Backorders = 14 ords / 16 pos / 1,070,283 val")
    log("  TARGET: Bloqueados = 0 / 0 / 0")

    # Formula taginfo_offes.sql con kredlim workaround
    totals_snap = run(cur, "snap per-kdnr bel(6,7,11) aufkstat=0 f103", f"""
        SELECT h.kdnr, SUM(ROUND(f103.sollme * f092.poswert / f092.auftme, 2))
        FROM f103, f090 h, f092
        WHERE f103.firma={FIRMA} AND h.firma={FIRMA} AND f092.firma={FIRMA}
          AND f103.auftrag=h.auftrag AND f103.auftrag=f092.auftrag
          AND f103.posnr=f092.posnr
          AND f092.kzerl='0' AND h.aufkstat=0 AND h.belegart IN (6,7,11)
        GROUP BY h.kdnr
    """)
    over_snap = [r[0] for r in totals_snap if kredlim_map.get(r[0],0)>0 and r[1] and float(r[1])>kredlim_map.get(r[0],0)]

    for r in run(cur, "snap BACK bel(7,11) f103 NOT over", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos,
               SUM(ROUND(f103.sollme * f092.poswert / f092.auftme, 2)) val
        FROM f103, f090 h, f092
        WHERE f103.firma={FIRMA} AND h.firma={FIRMA} AND f092.firma={FIRMA}
          AND f103.auftrag=h.auftrag AND f103.auftrag=f092.auftrag
          AND f103.posnr=f092.posnr
          AND f092.kzerl='0' AND h.aufkstat=0 AND h.belegart IN (7,11)
          {("AND h.kdnr NOT IN (" + fmt_in(over_snap) + ")") if over_snap else ""}
    """):
        log(f"  [BACK bel(7,11) f103] ords={r[0]}  pos={r[1]}  val={r[2]}")

    if over_snap:
        for r in run(cur, "snap BLOQ bel(7,11) f103 IN over", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos,
                   SUM(ROUND(f103.sollme * f092.poswert / f092.auftme, 2)) val
            FROM f103, f090 h, f092
            WHERE f103.firma={FIRMA} AND h.firma={FIRMA} AND f092.firma={FIRMA}
              AND f103.auftrag=h.auftrag AND f103.auftrag=f092.auftrag
              AND f103.posnr=f092.posnr
              AND f092.kzerl='0' AND h.aufkstat=0 AND h.belegart IN (7,11)
              AND h.kdnr IN ({fmt_in(over_snap)})
        """):
            log(f"  [BLOQ bel(7,11) f103] ords={r[0]}  pos={r[1]}  val={r[2]}")
    else:
        log("  [BLOQ] 0 customers over kredlim today")

    # Standard metrics
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

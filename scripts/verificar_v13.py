"""
TagInfo v13 — bloqueados aufkstat2 no-prod, remitos belegart6/7/15, backorders f092.
SOLO LECTURA.
"""

import pyodbc
from datetime import date, datetime

DSN = "MSPA"
OUTPUT_FILE = "taginfo_v13.txt"
FIRMA = 1


def get_conn():
    return pyodbc.connect(f"DSN={DSN};", autocommit=True)


def run(cursor, label, sql):
    print(f"  {label}...")
    try:
        cursor.execute(sql)
        return cursor.fetchall()
    except Exception as e:
        print(f"    SQL ERROR: {e}")
        return []


def main():
    lines = []
    log = lines.append
    today = date.today()

    log(f"TagInfo v13 — {datetime.now()}")
    log(f"DSN: {DSN}  |  Fecha: {today}  |  SOLO LECTURA")
    log("=" * 70)

    conn = get_conn()
    cur = conn.cursor()
    log("Conexión OK\n")

    # ============================================================
    # 1. f092 COLUMNAS — buscar rueckst, bestand, etc.
    # ============================================================
    log("=== f092 COLUMNAS ===")
    for r in run(cur, "f092 cols", """
        SELECT c.colno, c.colname, c.coltype
        FROM syscolumns c, systables t
        WHERE c.tabid = t.tabid AND t.tabname = 'f092'
        ORDER BY c.colno
    """):
        log(f"  [{r[0]}] {r[1]}  type={r[2]}")

    # ============================================================
    # 2. BLOQUEADOS — aufkstat=2, posstat != 2 (hipótesis nueva)
    # ============================================================
    log("\n=== BLOQUEADOS — aufkstat=2, posstat != 2 ===")

    # Total aufkstat=2 todos posstat
    for r in run(cur, "aufkstat2 total", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND h.aufkstat = 2
          AND p.kzerl = '0'
    """):
        log(f"  aufkstat=2 TOTAL: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # aufkstat=2, posstat != 2 (bloqueados NO produccion)
    for r in run(cur, "aufkstat2 posstat no 2", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND h.aufkstat = 2
          AND p.posstat <> 2
          AND p.kzerl = '0'
    """):
        log(f"  aufkstat=2 posstat!=2 (bloqueados): ords={r[0]}  pos={r[1]}  val={r[2]}")

    # aufkstat=2, posstat = 2 (produccion — control)
    for r in run(cur, "aufkstat2 posstat 2", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND h.aufkstat = 2
          AND p.posstat = 2
          AND p.kzerl = '0'
    """):
        log(f"  aufkstat=2 posstat=2 (produccion control): ords={r[0]}  pos={r[1]}  val={r[2]}")

    # aufkstat=2 desglose completo por posstat (sin filtro posstat)
    log("\naufkstat=2 por posstat:")
    for r in run(cur, "aufkstat2 x posstat full", f"""
        SELECT p.posstat, COUNT(DISTINCT h.auftrag) ords,
               COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND h.aufkstat = 2
          AND p.kzerl = '0'
        GROUP BY p.posstat ORDER BY p.posstat
    """):
        log(f"  posstat={r[0]}  ords={r[1]}  pos={r[2]}  val={r[3]}")

    # ============================================================
    # 3. BACKORDERS — probar distintas combinaciones
    # ============================================================
    log("\n=== BACKORDERS — distintos filtros ===")

    # aufkstat=0, posstat=0, kzerl='0' (total sin termin)
    for r in run(cur, "aufkstat0 total", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND h.aufkstat = 0
          AND p.posstat = 0 AND p.kzerl = '0'
    """):
        log(f"  aufkstat0 total: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # backorders = kund.kredlim = 0 (sin crédito otorgado)
    for r in run(cur, "kredlim=0 backorders", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p, kund k
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA} AND k.firma = {FIRMA}
          AND h.auftrag = p.auftrag AND h.kdnr = k.kdnr
          AND h.aufkstat = 0
          AND p.posstat = 0 AND p.kzerl = '0'
          AND k.kredlim = 0
    """):
        log(f"  kredlim=0: ords={r[0]}  pos={r[1]}  val={r[2]}")

    for r in run(cur, "kredlim>0 normal", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p, kund k
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA} AND k.firma = {FIRMA}
          AND h.auftrag = p.auftrag AND h.kdnr = k.kdnr
          AND h.aufkstat = 0
          AND p.posstat = 0 AND p.kzerl = '0'
          AND k.kredlim > 0
    """):
        log(f"  kredlim>0: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # ============================================================
    # 4. REMITOS — sbas belegart=6 y belegart=7 HOY
    # ============================================================
    log("\n=== REMITOS — sbas belegart 6 y 7 HOY ===")

    for bg in [6, 7, 8, 15]:
        for r in run(cur, f"sbas bg={bg} hoy", f"""
            SELECT COUNT(DISTINCT renr) docs, COUNT(*) pos, SUM(netwert) val
            FROM sbas
            WHERE firma = {FIRMA} AND redat = TODAY AND belegart = {bg}
        """):
            log(f"  belegart={bg} hoy: docs={r[0]}  pos={r[1]}  val={r[2]}")

    # sbas todos belegart de hoy (uno a uno para evitar GROUP BY)
    log("\nsbas HOY — todos belegart con data:")
    for bg in range(1, 20):
        for r in run(cur, f"sbas hoy bg{bg}", f"""
            SELECT COUNT(*) cnt FROM sbas
            WHERE firma = {FIRMA} AND redat = TODAY AND belegart = {bg}
        """):
            if r[0] > 0:
                for r2 in run(cur, f"sbas hoy bg{bg} detail", f"""
                    SELECT COUNT(DISTINCT renr) docs, COUNT(*) pos, SUM(netwert) val
                    FROM sbas
                    WHERE firma = {FIRMA} AND redat = TODAY AND belegart = {bg}
                """):
                    log(f"  belegart={bg}: docs={r2[0]}  pos={r2[1]}  val={r2[2]}")
                break

    # ============================================================
    # 5. REMITOS — pauf con liefwe > 0 usando query simple
    # ============================================================
    log("\n=== pauf — ANÁLISIS LIEFWE ===")

    # pauf versdat = TODAY
    for r in run(cur, "pauf versdat today", f"""
        SELECT COUNT(*) cnt, COUNT(DISTINCT liefnr) liefers,
               COUNT(DISTINCT auftrag) ords
        FROM pauf WHERE firma = {FIRMA} AND versdat = TODAY
    """):
        log(f"  pauf versdat=HOY: cnt={r[0]}  liefers={r[1]}  ords={r[2]}")

    # pauf con auftrag en f090 con aufkstat=8
    for r in run(cur, "pauf join aufkstat8", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(v.liefwe) val
        FROM f090 h, pauf v
        WHERE h.firma = {FIRMA} AND v.firma = {FIRMA}
          AND h.auftrag = v.auftrag
          AND h.aufkstat = 8
    """):
        log(f"  pauf+aufkstat8: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # ============================================================
    # 6. SNAPSHOT COMPLETO CON NUEVA HIPOTESIS
    # ============================================================
    log("\n=== SNAPSHOT NUEVA HIPÓTESIS ===")
    ts = datetime.now()

    for r in run(cur, "snap bloqueados", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND h.aufkstat = 2
          AND p.posstat <> 2
          AND p.kzerl = '0'
    """):
        log(f"  [BLOQUEADOS aufkstat=2 posstat!=2] ords={r[0]}  pos={r[1]}  val={r[2]}")

    for r in run(cur, "snap backorders", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND h.aufkstat = 0
          AND p.posstat = 0 AND p.kzerl = '0'
    """):
        log(f"  [BACKORDERS aufkstat=0 posstat=0] ords={r[0]}  pos={r[1]}  val={r[2]}")

    for r in run(cur, "snap produccion", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND h.aufkstat = 2
          AND p.posstat = 2 AND p.kzerl = '0'
    """):
        log(f"  [PRODUCCION aufkstat=2 posstat=2] ords={r[0]}  pos={r[1]}  val={r[2]}")

    for r in run(cur, "snap status<-1", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND h.aufkstat < -1
          AND p.kzerl = '0'
    """):
        log(f"  [STATUS<-1] ords={r[0]}  pos={r[1]}  val={r[2]}")

    for r in run(cur, "snap venta 8+11", f"""
        SELECT COUNT(DISTINCT renr) docs, COUNT(*) pos, SUM(netwert) val
        FROM sbas
        WHERE firma = {FIRMA} AND redat = TODAY AND belegart IN (8, 11)
    """):
        log(f"  [VENTA bel8+11] docs={r[0]}  pos={r[1]}  val={r[2]}")

    for r in run(cur, "snap venta 11 only", f"""
        SELECT COUNT(DISTINCT renr) docs, COUNT(*) pos, SUM(netwert) val
        FROM sbas
        WHERE firma = {FIRMA} AND redat = TODAY AND belegart = 11
    """):
        log(f"  [VENTA bel11] docs={r[0]}  pos={r[1]}  val={r[2]}")

    log(f"\n  Timestamp: {ts}")

    conn.close()

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\nListo → {OUTPUT_FILE}")


if __name__ == "__main__":
    main()

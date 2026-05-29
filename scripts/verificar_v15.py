"""
TagInfo v15 — opos (offene Posten), msperr/zsperr, bloqueados con opos+orders.
SOLO LECTURA.
"""

import pyodbc
from datetime import date, datetime

DSN = "MSPA"
OUTPUT_FILE = "taginfo_v15.txt"
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

    log(f"TagInfo v15 — {datetime.now()}")
    log(f"DSN: {DSN}  |  Fecha: {today}  |  SOLO LECTURA")
    log("=" * 70)

    conn = get_conn()
    cur = conn.cursor()
    log("Conexión OK\n")

    # ============================================================
    # 1. opos — COLUMNAS Y ESTRUCTURA
    # ============================================================
    log("=== opos — COLUMNAS ===")
    for r in run(cur, "opos cols", """
        SELECT c.colno, c.colname, c.coltype
        FROM syscolumns c, systables t
        WHERE c.tabid = t.tabid AND t.tabname = 'opos'
        ORDER BY c.colno
    """):
        log(f"  [{r[0]}] {r[1]}  type={r[2]}")

    for r in run(cur, "opos count", f"SELECT COUNT(*) FROM opos WHERE firma = {FIRMA}"):
        log(f"  opos FILAS: {r[0]}")

    # ============================================================
    # 2. opos — ANÁLISIS DE DATOS (remitos/facturas abiertas?)
    # ============================================================
    log("\n=== opos — ANÁLISIS ===")

    # Distribución por tipo de documento
    for r in run(cur, "opos belegart dist", f"""
        SELECT belegart, COUNT(*) cnt, COUNT(DISTINCT renr) docs
        FROM opos WHERE firma = {FIRMA}
        GROUP BY belegart ORDER BY belegart
    """):
        log(f"  opos belegart={r[0]}  cnt={r[1]}  docs={r[2]}")

    # Totales de opos
    for r in run(cur, "opos totales", f"""
        SELECT COUNT(DISTINCT renr) docs, COUNT(*) pos,
               SUM(betrag) betrag_total
        FROM opos WHERE firma = {FIRMA}
    """):
        log(f"  opos total: docs={r[0]}  pos={r[1]}  betrag={r[2]}")

    # opos hoy (documentos emitidos hoy)
    for r in run(cur, "opos hoy redat", f"""
        SELECT COUNT(DISTINCT renr) docs, COUNT(*) pos, SUM(betrag) val
        FROM opos WHERE firma = {FIRMA} AND redat = TODAY
    """):
        log(f"  opos hoy (redat=TODAY): docs={r[0]}  pos={r[1]}  val={r[2]}")

    # opos con auftrag (órdenes relacionadas)
    for r in run(cur, "opos con auftrag", f"""
        SELECT COUNT(DISTINCT auftrag) ords, COUNT(DISTINCT renr) docs,
               COUNT(*) pos, SUM(betrag) val
        FROM opos WHERE firma = {FIRMA} AND auftrag > 0
    """):
        log(f"  opos auftrag>0: ords={r[0]}  docs={r[1]}  pos={r[2]}  val={r[3]}")

    # opos sin pagar — hipótesis remitos/facturas abiertas
    for r in run(cur, "opos offen campo", f"""
        SELECT COUNT(DISTINCT renr) docs, COUNT(*) pos, SUM(betrag) val
        FROM opos WHERE firma = {FIRMA} AND offen > 0
    """):
        log(f"  opos offen>0: docs={r[0]}  pos={r[1]}  val={r[2]}")

    # ============================================================
    # 3. msperr — tabla de bloqueo
    # ============================================================
    log("\n=== msperr — COLUMNAS Y DATOS ===")
    for r in run(cur, "msperr cols", """
        SELECT c.colno, c.colname, c.coltype
        FROM syscolumns c, systables t
        WHERE c.tabid = t.tabid AND t.tabname = 'msperr'
        ORDER BY c.colno
    """):
        log(f"  [{r[0]}] {r[1]}  type={r[2]}")

    for r in run(cur, "msperr count", f"SELECT COUNT(*) FROM msperr WHERE firma = {FIRMA}"):
        log(f"  msperr FILAS: {r[0]}")

    # ============================================================
    # 4. zsperr — tabla de bloqueo pago
    # ============================================================
    log("\n=== zsperr — COLUMNAS Y DATOS ===")
    for r in run(cur, "zsperr cols", """
        SELECT c.colno, c.colname, c.coltype
        FROM syscolumns c, systables t
        WHERE c.tabid = t.tabid AND t.tabname = 'zsperr'
        ORDER BY c.colno
    """):
        log(f"  [{r[0]}] {r[1]}  type={r[2]}")

    for r in run(cur, "zsperr count", f"SELECT COUNT(*) FROM zsperr WHERE firma = {FIRMA}"):
        log(f"  zsperr FILAS: {r[0]}")

    # ============================================================
    # 5. BLOQUEADOS — credito con COALESCE fix
    # ============================================================
    log("\n=== BLOQUEADOS — open_orders con COALESCE ===")

    for r in run(cur, "bloq coalesce>kredlim", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p, kund k
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA} AND k.firma = {FIRMA}
          AND h.auftrag = p.auftrag AND h.kdnr = k.kdnr
          AND h.aufkstat = 0
          AND p.posstat = 0 AND p.kzerl = '0'
          AND COALESCE((SELECT SUM(p2.poswert)
               FROM f090 h2, f092 p2
               WHERE h2.firma = {FIRMA} AND p2.firma = {FIRMA}
                 AND h2.auftrag = p2.auftrag
                 AND h2.kdnr = h.kdnr
                 AND h2.aufkstat = 0
                 AND p2.posstat = 0 AND p2.kzerl = '0'), 0) > k.kredlim
    """):
        log(f"  COALESCE open>kredlim: ords={r[0]}  pos={r[1]}  val={r[2]}")

    for r in run(cur, "back coalesce<=kredlim", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p, kund k
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA} AND k.firma = {FIRMA}
          AND h.auftrag = p.auftrag AND h.kdnr = k.kdnr
          AND h.aufkstat = 0
          AND p.posstat = 0 AND p.kzerl = '0'
          AND COALESCE((SELECT SUM(p2.poswert)
               FROM f090 h2, f092 p2
               WHERE h2.firma = {FIRMA} AND p2.firma = {FIRMA}
                 AND h2.auftrag = p2.auftrag
                 AND h2.kdnr = h.kdnr
                 AND h2.aufkstat = 0
                 AND p2.posstat = 0 AND p2.kzerl = '0'), 0) <= k.kredlim
    """):
        log(f"  COALESCE open<=kredlim: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # ============================================================
    # 6. SNAPSHOT SIMULTÁNEO
    # ============================================================
    log("\n=== SNAPSHOT SIMULTÁNEO ===")
    ts = datetime.now()

    for r in run(cur, "snap produccion", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND h.aufkstat = 2 AND p.posstat = 2 AND p.kzerl = '0'
    """):
        log(f"  [PRODUCCION] ords={r[0]}  pos={r[1]}  val={r[2]}")

    for r in run(cur, "snap bloqueados", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p, kund k
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA} AND k.firma = {FIRMA}
          AND h.auftrag = p.auftrag AND h.kdnr = k.kdnr
          AND h.aufkstat = 0 AND p.posstat = 0 AND p.kzerl = '0'
          AND COALESCE((SELECT SUM(p2.poswert)
               FROM f090 h2, f092 p2
               WHERE h2.firma = {FIRMA} AND p2.firma = {FIRMA}
                 AND h2.auftrag = p2.auftrag AND h2.kdnr = h.kdnr
                 AND h2.aufkstat = 0 AND p2.posstat = 0 AND p2.kzerl = '0'), 0) > k.kredlim
    """):
        log(f"  [BLOQUEADOS open>kredlim] ords={r[0]}  pos={r[1]}  val={r[2]}")

    for r in run(cur, "snap backorders", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p, kund k
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA} AND k.firma = {FIRMA}
          AND h.auftrag = p.auftrag AND h.kdnr = k.kdnr
          AND h.aufkstat = 0 AND p.posstat = 0 AND p.kzerl = '0'
          AND COALESCE((SELECT SUM(p2.poswert)
               FROM f090 h2, f092 p2
               WHERE h2.firma = {FIRMA} AND p2.firma = {FIRMA}
                 AND h2.auftrag = p2.auftrag AND h2.kdnr = h.kdnr
                 AND h2.aufkstat = 0 AND p2.posstat = 0 AND p2.kzerl = '0'), 0) <= k.kredlim
    """):
        log(f"  [BACKORDERS open<=kredlim] ords={r[0]}  pos={r[1]}  val={r[2]}")

    for r in run(cur, "snap opos remitos", f"""
        SELECT COUNT(DISTINCT renr) docs, COUNT(*) pos, SUM(betrag) val
        FROM opos WHERE firma = {FIRMA} AND offen > 0
    """):
        log(f"  [REMITOS opos offen>0] docs={r[0]}  pos={r[1]}  val={r[2]}")

    for r in run(cur, "snap venta", f"""
        SELECT COUNT(DISTINCT renr) docs, COUNT(*) pos, SUM(netwert) val
        FROM sbas WHERE firma = {FIRMA} AND redat = TODAY AND belegart IN (8, 11)
    """):
        log(f"  [VENTA bel8+11] docs={r[0]}  pos={r[1]}  val={r[2]}")

    log(f"  Timestamp: {ts}")

    conn.close()

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\nListo → {OUTPUT_FILE}")


if __name__ == "__main__":
    main()

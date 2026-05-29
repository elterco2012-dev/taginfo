"""
TagInfo v14 — bloqueados por kredlim correlated, kund flags ma/kkind/kzsond, f090.kz*.
SOLO LECTURA.
"""

import pyodbc
from datetime import date, datetime

DSN = "MSPA"
OUTPUT_FILE = "taginfo_v14.txt"
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

    log(f"TagInfo v14 — {datetime.now()}")
    log(f"DSN: {DSN}  |  Fecha: {today}  |  SOLO LECTURA")
    log("=" * 70)

    conn = get_conn()
    cur = conn.cursor()
    log("Conexión OK\n")

    # ============================================================
    # 1. kund FLAGS potenciales de bloqueo de crédito
    # ============================================================
    log("=== kund FLAGS DE CRÉDITO ===")

    # ma = Mahnung (dunning — clientes en mora)
    for r in run(cur, "kund ma dist", f"""
        SELECT ma, COUNT(*) cnt FROM kund
        WHERE firma = {FIRMA} GROUP BY ma ORDER BY ma
    """):
        log(f"  kund.ma={r[0]}  cnt={r[1]}")

    # kkind = tipo de crédito
    for r in run(cur, "kund kkind dist", f"""
        SELECT kkind, COUNT(*) cnt FROM kund
        WHERE firma = {FIRMA} GROUP BY kkind ORDER BY kkind
    """):
        log(f"  kund.kkind={r[0]}  cnt={r[1]}")

    # kzsond = condición especial
    for r in run(cur, "kund kzsond dist", f"""
        SELECT kzsond, COUNT(*) cnt FROM kund
        WHERE firma = {FIRMA} GROUP BY kzsond ORDER BY kzsond
    """):
        log(f"  kund.kzsond='{r[0]}'  cnt={r[1]}")

    # delkred = Delkredere
    for r in run(cur, "kund delkred dist", f"""
        SELECT delkred, COUNT(*) cnt FROM kund
        WHERE firma = {FIRMA} GROUP BY delkred ORDER BY delkred
    """):
        log(f"  kund.delkred={r[0]}  cnt={r[1]}")

    # ============================================================
    # 2. BLOQUEADOS — cliente total abierto > kredlim
    # ============================================================
    log("\n=== BLOQUEADOS — open_total > kund.kredlim ===")

    # Ordenes donde la suma de TODAS las posiciones abiertas del cliente > kredlim
    for r in run(cur, "bloq sum open > kredlim", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p, kund k
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA} AND k.firma = {FIRMA}
          AND h.auftrag = p.auftrag AND h.kdnr = k.kdnr
          AND h.aufkstat = 0
          AND p.posstat = 0 AND p.kzerl = '0'
          AND k.kredlim > 0
          AND (SELECT SUM(p2.poswert)
               FROM f090 h2, f092 p2
               WHERE h2.firma = {FIRMA} AND p2.firma = {FIRMA}
                 AND h2.auftrag = p2.auftrag
                 AND h2.kdnr = h.kdnr
                 AND h2.aufkstat = 0
                 AND p2.posstat = 0 AND p2.kzerl = '0') > k.kredlim
    """):
        log(f"  open_total>kredlim: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # Backorders: clientes con open_total <= kredlim
    for r in run(cur, "back sum open <= kredlim", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p, kund k
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA} AND k.firma = {FIRMA}
          AND h.auftrag = p.auftrag AND h.kdnr = k.kdnr
          AND h.aufkstat = 0
          AND p.posstat = 0 AND p.kzerl = '0'
          AND k.kredlim > 0
          AND (SELECT SUM(p2.poswert)
               FROM f090 h2, f092 p2
               WHERE h2.firma = {FIRMA} AND p2.firma = {FIRMA}
                 AND h2.auftrag = p2.auftrag
                 AND h2.kdnr = h.kdnr
                 AND h2.aufkstat = 0
                 AND p2.posstat = 0 AND p2.kzerl = '0') <= k.kredlim
    """):
        log(f"  open_total<=kredlim: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # ============================================================
    # 3. f090 CAMPOS kz — distribución para aufkstat=0
    # ============================================================
    log("\n=== f090.kz* para aufkstat=0 ===")

    for kz in ['kz0', 'kz1', 'kz2', 'kz3', 'kz4', 'kz5']:
        for r in run(cur, f"f090 {kz} dist aufkstat0", f"""
            SELECT {kz}, COUNT(*) cnt FROM f090
            WHERE firma = {FIRMA} AND aufkstat = 0
            GROUP BY {kz} ORDER BY {kz}
        """):
            if r[0] is not None and str(r[0]).strip() not in ('', '0', '00', '000'):
                log(f"  aufkstat=0 {kz}='{r[0]}'  cnt={r[1]}")

    # ============================================================
    # 4. TABLAS SYSTABLES — buscar tabla de crédito
    # ============================================================
    log("\n=== SYSTABLES — tablas con 'kred' o 'sperr' o 'opap' ===")
    for r in run(cur, "systables kred/sperr", """
        SELECT tabname, tabid FROM systables
        WHERE tabtype = 'T'
          AND (tabname LIKE '%kred%'
            OR tabname LIKE '%sperr%'
            OR tabname LIKE '%opap%'
            OR tabname LIKE '%offp%'
            OR tabname LIKE '%kont%'
            OR tabname LIKE '%boni%'
            OR tabname LIKE '%mahn%')
        ORDER BY tabname
    """):
        log(f"  tabla={r[0]}  tabid={r[1]}")

    # Buscar más tablas candidatas
    for r in run(cur, "systables misc", """
        SELECT tabname FROM systables
        WHERE tabtype = 'T' AND tabid > 99
          AND (tabname LIKE 'op%'
            OR tabname LIKE 'bu%'
            OR tabname LIKE 'fi%'
            OR tabname LIKE 'deb%')
        ORDER BY tabname
    """):
        log(f"  tabla={r[0]}")

    # ============================================================
    # 5. kund.ma = flag de mora — órdenes bloqueadas
    # ============================================================
    log("\n=== BLOQUEADOS via kund.ma (mora/dunning) ===")
    for r in run(cur, "aufkstat0 kund.ma>0", f"""
        SELECT k.ma, COUNT(DISTINCT h.auftrag) ords,
               COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p, kund k
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA} AND k.firma = {FIRMA}
          AND h.auftrag = p.auftrag AND h.kdnr = k.kdnr
          AND h.aufkstat = 0
          AND p.posstat = 0 AND p.kzerl = '0'
        GROUP BY k.ma ORDER BY k.ma
    """):
        log(f"  ma={r[0]}  ords={r[1]}  pos={r[2]}  val={r[3]}")

    # ============================================================
    # 6. SNAPSHOT SIMULTÁNEO
    # ============================================================
    log("\n=== SNAPSHOT ===")
    ts = datetime.now()

    for r in run(cur, "snap produccion", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND h.aufkstat = 2 AND p.posstat = 2 AND p.kzerl = '0'
    """):
        log(f"  [PRODUCCION] ords={r[0]}  pos={r[1]}  val={r[2]}")

    for r in run(cur, "snap aufkstat0", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND h.aufkstat = 0 AND p.posstat = 0 AND p.kzerl = '0'
    """):
        log(f"  [AUFKSTAT=0 total] ords={r[0]}  pos={r[1]}  val={r[2]}")

    for r in run(cur, "snap venta", f"""
        SELECT COUNT(DISTINCT renr) docs, COUNT(*) pos, SUM(netwert) val
        FROM sbas WHERE firma = {FIRMA} AND redat = TODAY AND belegart IN (8, 11)
    """):
        log(f"  [VENTA] docs={r[0]}  pos={r[1]}  val={r[2]}")

    log(f"  Timestamp: {ts}")

    conn.close()

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\nListo → {OUTPUT_FILE}")


if __name__ == "__main__":
    main()

"""
TagInfo v16 — remitos via f092.kzlsdru+refrenr, bloqueados NVL fix.
SOLO LECTURA.
"""

import pyodbc
from datetime import date, datetime

DSN = "MSPA"
OUTPUT_FILE = "taginfo_v16.txt"
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

    log(f"TagInfo v16 — {datetime.now()}")
    log(f"DSN: {DSN}  |  Fecha: {today}  |  SOLO LECTURA")
    log("=" * 70)

    conn = get_conn()
    cur = conn.cursor()
    log("Conexión OK\n")

    # ============================================================
    # 1. f092 FLAGS DE REMITO — kzlsdru, refrenr, reflspos
    # ============================================================
    log("=== f092 FLAGS REMITO ===")

    # kzlsdru (Lieferschein gedruckt = remito impreso)
    for r in run(cur, "kzlsdru dist", f"""
        SELECT kzlsdru, COUNT(*) cnt, COUNT(DISTINCT auftrag) ords
        FROM f092 WHERE firma = {FIRMA} AND kzerl = '0'
        GROUP BY kzlsdru ORDER BY kzlsdru
    """):
        log(f"  kzlsdru={r[0]}  cnt={r[1]}  ords={r[2]}")

    # refrenr (referencia a factura)
    for r in run(cur, "refrenr dist", f"""
        SELECT refrenr, COUNT(*) cnt, COUNT(DISTINCT auftrag) ords
        FROM f092 WHERE firma = {FIRMA} AND kzerl = '0' AND kzlsdru = 1
        GROUP BY refrenr ORDER BY refrenr
    """):
        log(f"  refrenr={r[0]}  cnt={r[1]}  ords={r[2]}")

    # reflspos (referencia posicion lieferschein)
    for r in run(cur, "reflspos>0 kzerl0", f"""
        SELECT COUNT(*) cnt, COUNT(DISTINCT auftrag) ords
        FROM f092 WHERE firma = {FIRMA} AND kzerl = '0' AND reflspos > 0
    """):
        log(f"  reflspos>0 kzerl='0': cnt={r[0]}  ords={r[1]}")

    # ============================================================
    # 2. REMITOS — kzlsdru=1 AND refrenr=0 (sin factura)
    # ============================================================
    log("\n=== REMITOS — kzlsdru=1 sin factura ===")

    for r in run(cur, "remitos kzlsdru1 refrenr0", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND p.kzlsdru = 1
          AND p.refrenr = 0
          AND p.kzerl = '0'
    """):
        log(f"  kzlsdru=1 refrenr=0: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # kzlsdru=1 sin importar refrenr
    for r in run(cur, "remitos kzlsdru1 all", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND p.kzlsdru = 1
          AND p.kzerl = '0'
    """):
        log(f"  kzlsdru=1 total: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # kzlsdru=1, refrenr=0, por aufkstat
    log("\nkzlsdru=1 refrenr=0 por aufkstat:")
    for r in run(cur, "kzlsdru1 por aufkstat", f"""
        SELECT h.aufkstat, COUNT(DISTINCT h.auftrag) ords,
               COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND p.kzlsdru = 1 AND p.refrenr = 0
          AND p.kzerl = '0'
        GROUP BY h.aufkstat ORDER BY h.aufkstat
    """):
        log(f"  aufkstat={r[0]}  ords={r[1]}  pos={r[2]}  val={r[3]}")

    # ============================================================
    # 3. BLOQUEADOS — con NVL (Informix) en lugar de COALESCE
    # ============================================================
    log("\n=== BLOQUEADOS — con NVL (Informix syntax) ===")

    for r in run(cur, "bloq NVL>kredlim", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p, kund k
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA} AND k.firma = {FIRMA}
          AND h.auftrag = p.auftrag AND h.kdnr = k.kdnr
          AND h.aufkstat = 0 AND p.posstat = 0 AND p.kzerl = '0'
          AND NVL((SELECT SUM(p2.poswert)
               FROM f090 h2, f092 p2
               WHERE h2.firma = {FIRMA} AND p2.firma = {FIRMA}
                 AND h2.auftrag = p2.auftrag AND h2.kdnr = h.kdnr
                 AND h2.aufkstat = 0 AND p2.posstat = 0 AND p2.kzerl = '0'), 0) > k.kredlim
    """):
        log(f"  NVL open>kredlim: ords={r[0]}  pos={r[1]}  val={r[2]}")

    for r in run(cur, "back NVL<=kredlim", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p, kund k
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA} AND k.firma = {FIRMA}
          AND h.auftrag = p.auftrag AND h.kdnr = k.kdnr
          AND h.aufkstat = 0 AND p.posstat = 0 AND p.kzerl = '0'
          AND NVL((SELECT SUM(p2.poswert)
               FROM f090 h2, f092 p2
               WHERE h2.firma = {FIRMA} AND p2.firma = {FIRMA}
                 AND h2.auftrag = p2.auftrag AND h2.kdnr = h.kdnr
                 AND h2.aufkstat = 0 AND p2.posstat = 0 AND p2.kzerl = '0'), 0) <= k.kredlim
    """):
        log(f"  NVL open<=kredlim: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # ============================================================
    # 4. SNAPSHOT COMPLETO — todas las categorías
    # ============================================================
    log("\n=== SNAPSHOT COMPLETO ===")
    ts = datetime.now()

    for r in run(cur, "snap produccion", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND h.aufkstat = 2 AND p.posstat = 2 AND p.kzerl = '0'
    """):
        log(f"  [PRODUCCION] ords={r[0]}  pos={r[1]}  val={r[2]}")

    for r in run(cur, "snap remitos", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND p.kzlsdru = 1 AND p.refrenr = 0 AND p.kzerl = '0'
    """):
        log(f"  [REMITOS kzlsdru=1 refrenr=0] ords={r[0]}  pos={r[1]}  val={r[2]}")

    for r in run(cur, "snap bloqueados", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p, kund k
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA} AND k.firma = {FIRMA}
          AND h.auftrag = p.auftrag AND h.kdnr = k.kdnr
          AND h.aufkstat = 0 AND p.posstat = 0 AND p.kzerl = '0'
          AND NVL((SELECT SUM(p2.poswert) FROM f090 h2, f092 p2
               WHERE h2.firma = {FIRMA} AND p2.firma = {FIRMA}
                 AND h2.auftrag = p2.auftrag AND h2.kdnr = h.kdnr
                 AND h2.aufkstat = 0 AND p2.posstat = 0 AND p2.kzerl = '0'), 0) > k.kredlim
    """):
        log(f"  [BLOQUEADOS NVL>kredlim] ords={r[0]}  pos={r[1]}  val={r[2]}")

    for r in run(cur, "snap backorders", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p, kund k
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA} AND k.firma = {FIRMA}
          AND h.auftrag = p.auftrag AND h.kdnr = k.kdnr
          AND h.aufkstat = 0 AND p.posstat = 0 AND p.kzerl = '0'
          AND NVL((SELECT SUM(p2.poswert) FROM f090 h2, f092 p2
               WHERE h2.firma = {FIRMA} AND p2.firma = {FIRMA}
                 AND h2.auftrag = p2.auftrag AND h2.kdnr = h.kdnr
                 AND h2.aufkstat = 0 AND p2.posstat = 0 AND p2.kzerl = '0'), 0) <= k.kredlim
    """):
        log(f"  [BACKORDERS NVL<=kredlim] ords={r[0]}  pos={r[1]}  val={r[2]}")

    for r in run(cur, "snap venta", f"""
        SELECT COUNT(DISTINCT renr) docs, COUNT(*) pos, SUM(netwert) val
        FROM sbas WHERE firma = {FIRMA} AND redat = TODAY AND belegart IN (8, 11)
    """):
        log(f"  [VENTA bel8+11] docs={r[0]}  pos={r[1]}  val={r[2]}")

    for r in run(cur, "snap status<-1", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag AND h.aufkstat < -1 AND p.kzerl = '0'
    """):
        log(f"  [STATUS<-1 aufkstat<-1] ords={r[0]}  pos={r[1]}  val={r[2]}")

    log(f"  Timestamp: {ts}")

    conn.close()

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\nListo → {OUTPUT_FILE}")


if __name__ == "__main__":
    main()

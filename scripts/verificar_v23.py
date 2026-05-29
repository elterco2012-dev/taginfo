"""
TagInfo v23 — termin<=TODAY para backords, aufkstat=8 para remitos.
SOLO LECTURA.
"""

import pyodbc
from datetime import date, datetime

DSN = "MSPA"
OUTPUT_FILE = "taginfo_v23.txt"
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

    log(f"TagInfo v23 — {datetime.now()}")
    log(f"DSN: {DSN}  |  Fecha: {today}  |  SOLO LECTURA")
    log("=" * 70)

    conn = get_conn()
    cur = conn.cursor()
    log("Conexión OK\n")

    kredlim_rows = run(cur, "kredlim per kdnr", f"""
        SELECT kdnr, kredlim FROM kund WHERE firma = {FIRMA} AND kredlim > 0
    """)
    kredlim_map = {r[0]: r[1] for r in kredlim_rows}

    # ============================================================
    # 1. BASE — termin <= TODAY (incluye ayer y hoy)
    # ============================================================
    log("=== BASE termin<=TODAY belegart=11 liefme<>0 ===")

    for r in run(cur, "base termin<=TODAY aufkstat<>8", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND p.termin <= TODAY AND p.liefme <> 0
          AND h.belegart = 11 AND h.aufkstat <> 8
    """):
        log(f"  base termin<=TODAY aufkstat<>8: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # aufkstat dist for termin<=TODAY
    log("\naufkstat dist termin<=TODAY bel=11 liefme<>0:")
    for r in run(cur, "aufkstat dist <=TODAY", f"""
        SELECT h.aufkstat, COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND p.termin <= TODAY AND p.liefme <> 0 AND h.belegart = 11
        GROUP BY h.aufkstat ORDER BY h.aufkstat
    """):
        log(f"  aufkstat={r[0]}  ords={r[1]}  pos={r[2]}")

    # Split kredlim with termin<=TODAY, aufkstat<>8
    totals_le = run(cur, "per-kdnr totals termin<=TODAY", f"""
        SELECT h.kdnr, SUM(p.poswert) total_open
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND p.termin <= TODAY AND p.liefme <> 0
          AND h.belegart = 11 AND h.aufkstat <> 8
        GROUP BY h.kdnr
    """)
    over_le = [r[0] for r in totals_le
               if kredlim_map.get(r[0], 0) > 0 and r[1] is not None and r[1] > kredlim_map.get(r[0], 0)]
    under_le = [r[0] for r in totals_le
                if not (kredlim_map.get(r[0], 0) > 0 and r[1] is not None and r[1] > kredlim_map.get(r[0], 0))]
    log(f"\n  Customers termin<=TODAY: {len(totals_le)}  over={len(over_le)}  under={len(under_le)}")

    if over_le:
        for r in run(cur, "BLOQUEADOS <=TODAY", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p
            WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
              AND h.auftrag = p.auftrag
              AND p.termin <= TODAY AND p.liefme <> 0
              AND h.belegart = 11 AND h.aufkstat <> 8
              AND h.kdnr IN ({','.join(str(k) for k in over_le)})
        """):
            log(f"  BLOQUEADOS (<=TODAY): ords={r[0]}  pos={r[1]}  val={r[2]}")

    if under_le:
        for r in run(cur, "BACKORDERS <=TODAY", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p
            WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
              AND h.auftrag = p.auftrag
              AND p.termin <= TODAY AND p.liefme <> 0
              AND h.belegart = 11 AND h.aufkstat <> 8
              AND h.kdnr IN ({','.join(str(k) for k in under_le)})
        """):
            log(f"  BACKORDERS (<=TODAY): ords={r[0]}  pos={r[1]}  val={r[2]}")

    # ============================================================
    # 2. REMITOS — aufkstat=8 (despachadas, no facturadas)
    # ============================================================
    log("\n=== REMITOS — aufkstat=8 ===")

    # f090 aufkstat=8 — all belegart
    for r in run(cur, "aufkstat=8 all belegart", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND h.aufkstat = 8 AND p.kzerl = '0'
    """):
        log(f"  aufkstat=8 all: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # aufkstat=8 belegart dist
    for r in run(cur, "aufkstat=8 belegart dist", f"""
        SELECT h.belegart, COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND h.aufkstat = 8 AND p.kzerl = '0'
        GROUP BY h.belegart ORDER BY h.belegart
    """):
        log(f"  aufkstat=8 belegart={r[0]}  ords={r[1]}  pos={r[2]}  val={r[3]}")

    # aufkstat=8 posstat dist
    for r in run(cur, "aufkstat=8 posstat dist", f"""
        SELECT p.posstat, COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND h.aufkstat = 8 AND p.kzerl = '0'
        GROUP BY p.posstat ORDER BY p.posstat
    """):
        log(f"  aufkstat=8 posstat={r[0]}  ords={r[1]}  pos={r[2]}  val={r[3]}")

    # aufkstat=8 belegart=11 specifically
    for r in run(cur, "aufkstat=8 belegart=11", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND h.aufkstat = 8 AND h.belegart = 11 AND p.kzerl = '0'
    """):
        log(f"  aufkstat=8 belegart=11: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # ============================================================
    # 3. REMITOS — posstat=8 (despachado a nivel posicion)
    # ============================================================
    log("\n=== REMITOS — posstat=8 ===")

    for r in run(cur, "posstat=8 all", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND p.posstat = 8 AND p.kzerl = '0'
    """):
        log(f"  posstat=8 all: ords={r[0]}  pos={r[1]}  val={r[2]}")

    for r in run(cur, "posstat=8 belegart=11", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND p.posstat = 8 AND h.belegart = 11 AND p.kzerl = '0'
    """):
        log(f"  posstat=8 belegart=11: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # posstat=8 belegart dist
    for r in run(cur, "posstat=8 belegart dist", f"""
        SELECT h.belegart, COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND p.posstat = 8 AND p.kzerl = '0'
        GROUP BY h.belegart ORDER BY h.belegart
    """):
        log(f"  posstat=8 belegart={r[0]}  ords={r[1]}  pos={r[2]}  val={r[3]}")

    # ============================================================
    # 4. SNAPSHOT COMPLETO
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

    # Remitos: aufkstat=8 all
    for r in run(cur, "snap remitos aufkstat8", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND h.aufkstat = 8 AND p.kzerl = '0'
    """):
        log(f"  [REMITOS aufkstat=8] ords={r[0]}  pos={r[1]}  val={r[2]}")

    # Bloqueados/backorders with termin<=TODAY
    totals_snap = run(cur, "snap per-kdnr", f"""
        SELECT h.kdnr, SUM(p.poswert) total_open
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND p.termin <= TODAY AND p.liefme <> 0
          AND h.belegart = 11 AND h.aufkstat <> 8
        GROUP BY h.kdnr
    """)
    over_s = [r[0] for r in totals_snap
              if kredlim_map.get(r[0], 0) > 0 and r[1] is not None and r[1] > kredlim_map.get(r[0], 0)]
    under_s = [r[0] for r in totals_snap
               if not (kredlim_map.get(r[0], 0) > 0 and r[1] is not None and r[1] > kredlim_map.get(r[0], 0))]

    if over_s:
        for r in run(cur, "snap bloqueados", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p
            WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
              AND h.auftrag = p.auftrag
              AND p.termin <= TODAY AND p.liefme <> 0
              AND h.belegart = 11 AND h.aufkstat <> 8
              AND h.kdnr IN ({','.join(str(x) for x in over_s)})
        """):
            log(f"  [BLOQUEADOS] ords={r[0]}  pos={r[1]}  val={r[2]}")

    if under_s:
        for r in run(cur, "snap backorders", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p
            WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
              AND h.auftrag = p.auftrag
              AND p.termin <= TODAY AND p.liefme <> 0
              AND h.belegart = 11 AND h.aufkstat <> 8
              AND h.kdnr IN ({','.join(str(x) for x in under_s)})
        """):
            log(f"  [BACKORDERS] ords={r[0]}  pos={r[1]}  val={r[2]}")

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
        log(f"  [STATUS<-1] ords={r[0]}  pos={r[1]}  val={r[2]}")

    log(f"  Timestamp: {ts}")

    conn.close()

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\nListo → {OUTPUT_FILE}")


if __name__ == "__main__":
    main()

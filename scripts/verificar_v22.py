"""
TagInfo v22 — backorders/bloqueados con f092.termin+liefme+belegart,
               remitos via sb104 liefdat=TODAY.
SOLO LECTURA.
"""

import pyodbc
from datetime import date, datetime

DSN = "MSPA"
OUTPUT_FILE = "taginfo_v22.txt"
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

    log(f"TagInfo v22 — {datetime.now()}")
    log(f"DSN: {DSN}  |  Fecha: {today}  |  SOLO LECTURA")
    log("=" * 70)

    conn = get_conn()
    cur = conn.cursor()
    log("Conexión OK\n")

    # ============================================================
    # 1. BACKORDERS base — f092.termin=TODAY, liefme<>0, belegart=11
    # ============================================================
    log("=== BASE BACKORDERS — termin=TODAY liefme<>0 belegart=11 ===")

    # Total base (aufkstat <> 8)
    for r in run(cur, "base backords aufkstat<>8", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND p.termin = TODAY
          AND p.liefme <> 0
          AND h.belegart = 11
          AND h.aufkstat <> 8
    """):
        log(f"  base aufkstat<>8: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # belegart distribution for context
    log("\nbelegart distribution aufkstat<>8 termin=TODAY liefme<>0:")
    for r in run(cur, "belegart dist", f"""
        SELECT h.belegart, COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND p.termin = TODAY AND p.liefme <> 0
          AND h.aufkstat <> 8
        GROUP BY h.belegart ORDER BY h.belegart
    """):
        log(f"  belegart={r[0]}  ords={r[1]}  pos={r[2]}")

    # aufkstat distribution for base
    log("\naufkstat dist belegart=11 termin=TODAY liefme<>0:")
    for r in run(cur, "aufkstat dist bel11", f"""
        SELECT h.aufkstat, COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND p.termin = TODAY AND p.liefme <> 0
          AND h.belegart = 11
        GROUP BY h.aufkstat ORDER BY h.aufkstat
    """):
        log(f"  aufkstat={r[0]}  ords={r[1]}  pos={r[2]}  val={r[3]}")

    # ============================================================
    # 2. BLOQUEADOS/BACKORDERS split por kredlim
    # ============================================================
    log("\n=== BLOQUEADOS/BACKORDERS split kredlim ===")

    kredlim_rows = run(cur, "kredlim per kdnr", f"""
        SELECT kdnr, kredlim FROM kund WHERE firma = {FIRMA} AND kredlim > 0
    """)
    kredlim_map = {r[0]: r[1] for r in kredlim_rows}

    # Per-customer total from base query (belegart=11, aufkstat<>8, termin=TODAY, liefme<>0)
    totals_base = run(cur, "per-kdnr totals base", f"""
        SELECT h.kdnr, SUM(p.poswert) total_open
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND p.termin = TODAY AND p.liefme <> 0
          AND h.belegart = 11 AND h.aufkstat <> 8
        GROUP BY h.kdnr
    """)
    log(f"  Customers in base: {len(totals_base)}")

    over = [r[0] for r in totals_base
            if kredlim_map.get(r[0], 0) > 0 and r[1] is not None and r[1] > kredlim_map.get(r[0], 0)]
    under = [r[0] for r in totals_base
             if not (kredlim_map.get(r[0], 0) > 0 and r[1] is not None and r[1] > kredlim_map.get(r[0], 0))]
    log(f"  over_limit={len(over)}  under_limit={len(under)}")

    if over:
        in_o = ','.join(str(k) for k in over)
        for r in run(cur, "BLOQUEADOS", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p
            WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
              AND h.auftrag = p.auftrag
              AND p.termin = TODAY AND p.liefme <> 0
              AND h.belegart = 11 AND h.aufkstat <> 8
              AND h.kdnr IN ({in_o})
        """):
            log(f"  BLOQUEADOS: ords={r[0]}  pos={r[1]}  val={r[2]}")

    if under:
        in_u = ','.join(str(k) for k in under)
        for r in run(cur, "BACKORDERS", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p
            WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
              AND h.auftrag = p.auftrag
              AND p.termin = TODAY AND p.liefme <> 0
              AND h.belegart = 11 AND h.aufkstat <> 8
              AND h.kdnr IN ({in_u})
        """):
            log(f"  BACKORDERS: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # ============================================================
    # 3. REMITOS — sb104 liefdat=TODAY joined sb105
    # ============================================================
    log("\n=== REMITOS — sb104 liefdat=TODAY ===")

    for r in run(cur, "sb104 liefdat=TODAY count", f"""
        SELECT COUNT(*) cnt FROM sb104 WHERE firma = {FIRMA} AND liefdat = TODAY
    """):
        log(f"  sb104 liefdat=TODAY: cnt={r[0]}")

    # sb104 TODAY joined sb105 open
    for r in run(cur, "remitos sb104+sb105 TODAY", f"""
        SELECT COUNT(DISTINCT s4.liefnr) docs, COUNT(*) pos, SUM(s5.liefposwe) val
        FROM sb104 s4, sb105 s5
        WHERE s4.firma = {FIRMA} AND s5.firma = {FIRMA}
          AND s4.liefnr = s5.liefnr
          AND s4.liefdat = TODAY
          AND s5.kzerl = '0'
    """):
        log(f"  sb104+sb105 liefdat=TODAY kzerl='0': docs={r[0]}  pos={r[1]}  val={r[2]}")

    # Also try sb104 TODAY, all sb105 positions
    for r in run(cur, "remitos sb104+sb105 TODAY all", f"""
        SELECT COUNT(DISTINCT s4.liefnr) docs, COUNT(*) pos, SUM(s5.liefposwe) val
        FROM sb104 s4, sb105 s5
        WHERE s4.firma = {FIRMA} AND s5.firma = {FIRMA}
          AND s4.liefnr = s5.liefnr
          AND s4.liefdat = TODAY
    """):
        log(f"  sb104+sb105 liefdat=TODAY all: docs={r[0]}  pos={r[1]}  val={r[2]}")

    # sb104 with aufdat=TODAY
    for r in run(cur, "sb104 aufdat=TODAY count", f"""
        SELECT COUNT(*) cnt FROM sb104 WHERE firma = {FIRMA} AND aufdat = TODAY
    """):
        log(f"  sb104 aufdat=TODAY: cnt={r[0]}")

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

    # Remitos fresh
    for r in run(cur, "snap remitos", f"""
        SELECT COUNT(DISTINCT s4.liefnr) docs, COUNT(*) pos, SUM(s5.liefposwe) val
        FROM sb104 s4, sb105 s5
        WHERE s4.firma = {FIRMA} AND s5.firma = {FIRMA}
          AND s4.liefnr = s5.liefnr
          AND s4.liefdat = TODAY AND s5.kzerl = '0'
    """):
        log(f"  [REMITOS sb104 TODAY+sb105 kzerl=0] docs={r[0]}  pos={r[1]}  val={r[2]}")

    # Bloqueados/backorders fresh
    totals_snap = run(cur, "snap per-kdnr totals", f"""
        SELECT h.kdnr, SUM(p.poswert) total_open
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND p.termin = TODAY AND p.liefme <> 0
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
              AND p.termin = TODAY AND p.liefme <> 0
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
              AND p.termin = TODAY AND p.liefme <> 0
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

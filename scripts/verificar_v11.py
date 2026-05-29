"""
TagInfo v11 — kund credito, sbas belegart fix, aufkstat8 posstat, remitos confirm.
SOLO LECTURA.
"""

import pyodbc
from datetime import date, datetime

DSN = "MSPA"
OUTPUT_FILE = "taginfo_v11.txt"
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

    log(f"TagInfo v11 — {datetime.now()}")
    log(f"DSN: {DSN}  |  Fecha: {today}  |  SOLO LECTURA")
    log("=" * 70)

    conn = get_conn()
    cur = conn.cursor()
    log("Conexión OK\n")

    # ============================================================
    # 1. REMITOS — sbas belegart=8 hoy (sin GROUP BY, simple)
    # ============================================================
    log("=== REMITOS sbas belegart=8 hoy ===")
    for r in run(cur, "sbas belegart8 hoy count", f"""
        SELECT COUNT(DISTINCT renr) docs, COUNT(*) pos, SUM(netwert) val
        FROM sbas
        WHERE firma = {FIRMA} AND redat = TODAY AND belegart = 8
    """):
        log(f"  belegart=8 hoy: docs={r[0]}  pos={r[1]}  val={r[2]}")

    for r in run(cur, "sbas belegart11 hoy count", f"""
        SELECT COUNT(DISTINCT renr) docs, COUNT(*) pos, SUM(netwert) val
        FROM sbas
        WHERE firma = {FIRMA} AND redat = TODAY AND belegart = 11
    """):
        log(f"  belegart=11 hoy: docs={r[0]}  pos={r[1]}  val={r[2]}")

    # sbas belegart=8 reciente (last 7 days)
    for r in run(cur, "sbas belegart8 week", f"""
        SELECT COUNT(DISTINCT renr) docs, COUNT(*) pos, SUM(netwert) val
        FROM sbas
        WHERE firma = {FIRMA} AND redat >= TODAY - 7 AND belegart = 8
    """):
        log(f"  belegart=8 7dias: docs={r[0]}  pos={r[1]}  val={r[2]}")

    # sbas belegart distintos con query simple (sin GROUP BY)
    log("\nsbas belegart values (separate queries):")
    for bg in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]:
        for r in run(cur, f"sbas bg={bg}", f"""
            SELECT COUNT(*) cnt FROM sbas WHERE firma = {FIRMA} AND belegart = {bg}
        """):
            if r[0] > 0:
                log(f"  belegart={bg}  filas={r[0]}")

    # ============================================================
    # 2. kund — COLUMNAS COMPLETAS
    # ============================================================
    log("\n=== kund COLUMNAS COMPLETAS ===")
    for r in run(cur, "kund cols", """
        SELECT c.colno, c.colname, c.coltype
        FROM syscolumns c, systables t
        WHERE c.tabid = t.tabid AND t.tabname = 'kund'
        ORDER BY c.colno
    """):
        log(f"  [{r[0]}] {r[1]}  type={r[2]}")

    # ============================================================
    # 3. kund — CAMPOS DE CRÉDITO/SALDO
    # ============================================================
    log("\n=== kund CAMPOS CRÉDITO (sample valores) ===")

    # kredlim range
    for r in run(cur, "kund kredlim range", f"""
        SELECT MIN(kredlim) mn, MAX(kredlim) mx, COUNT(*) cnt
        FROM kund WHERE firma = {FIRMA}
    """):
        log(f"  kredlim: min={r[0]}  max={r[1]}  cnt={r[2]}")

    # debsaldo si existe
    for r in run(cur, "kund debsaldo", f"""
        SELECT MIN(debsaldo) mn, MAX(debsaldo) mx, COUNT(*) cnt
        FROM kund WHERE firma = {FIRMA}
    """):
        log(f"  debsaldo: min={r[0]}  max={r[1]}  cnt={r[2]}")

    # saldo si existe
    for r in run(cur, "kund saldo", f"""
        SELECT MIN(saldo) mn, MAX(saldo) mx, COUNT(*) cnt
        FROM kund WHERE firma = {FIRMA}
    """):
        log(f"  saldo: min={r[0]}  max={r[1]}  cnt={r[2]}")

    # kzsperr si existe
    for r in run(cur, "kund kzsperr", f"""
        SELECT kzsperr, COUNT(*) cnt FROM kund
        WHERE firma = {FIRMA} GROUP BY kzsperr ORDER BY kzsperr
    """):
        log(f"  kzsperr={r[0]}  cnt={r[1]}")

    # ============================================================
    # 4. BLOQUEADOS vs BACKORDERS — split por kund credito
    # ============================================================
    log("\n=== SPLIT BLOQUEADOS vs BACKORDERS por kund.kredlim ===")

    # Ordenes aufkstat=0 donde credito del cliente excedido
    # Hipotesis: kund.saldo > kund.kredlim = bloqueado
    for r in run(cur, "bloqueados kund saldo>kredlim", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p, kund k
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA} AND k.firma = {FIRMA}
          AND h.auftrag = p.auftrag AND h.kdnr = k.kdnr
          AND h.aufkstat = 0
          AND p.posstat = 0 AND p.kzerl = '0'
          AND k.saldo > k.kredlim
    """):
        log(f"  bloqueados (saldo>kredlim): ords={r[0]}  pos={r[1]}  val={r[2]}")

    for r in run(cur, "backorders kund saldo<=kredlim", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p, kund k
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA} AND k.firma = {FIRMA}
          AND h.auftrag = p.auftrag AND h.kdnr = k.kdnr
          AND h.aufkstat = 0
          AND p.posstat = 0 AND p.kzerl = '0'
          AND k.saldo <= k.kredlim
    """):
        log(f"  backorders (saldo<=kredlim): ords={r[0]}  pos={r[1]}  val={r[2]}")

    # Usando debsaldo si saldo no existe
    for r in run(cur, "bloqueados debsaldo>kredlim", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p, kund k
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA} AND k.firma = {FIRMA}
          AND h.auftrag = p.auftrag AND h.kdnr = k.kdnr
          AND h.aufkstat = 0
          AND p.posstat = 0 AND p.kzerl = '0'
          AND k.debsaldo > k.kredlim
    """):
        log(f"  bloqueados (debsaldo>kredlim): ords={r[0]}  pos={r[1]}  val={r[2]}")

    for r in run(cur, "backorders debsaldo<=kredlim", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p, kund k
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA} AND k.firma = {FIRMA}
          AND h.auftrag = p.auftrag AND h.kdnr = k.kdnr
          AND h.aufkstat = 0
          AND p.posstat = 0 AND p.kzerl = '0'
          AND k.debsaldo <= k.kredlim
    """):
        log(f"  backorders (debsaldo<=kredlim): ords={r[0]}  pos={r[1]}  val={r[2]}")

    # ============================================================
    # 5. aufkstat=8 — POSSTAT BREAKDOWN (remitos emitidos)
    # ============================================================
    log("\n=== aufkstat=8 POSSTAT BREAKDOWN ===")
    for r in run(cur, "aufkstat8 posstat", f"""
        SELECT p.posstat, COUNT(DISTINCT h.auftrag) ords,
               COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND h.aufkstat = 8
          AND p.kzerl = '0'
        GROUP BY p.posstat ORDER BY p.posstat
    """):
        log(f"  posstat={r[0]}  ords={r[1]}  pos={r[2]}  val={r[3]}")

    # aufkstat=8 con posstat=0 solamente
    for r in run(cur, "aufkstat8 posstat0", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND h.aufkstat = 8
          AND p.posstat = 0 AND p.kzerl = '0'
    """):
        log(f"  aufkstat=8 posstat=0: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # ============================================================
    # 6. sb104 con liefdat (columna correcta, no lsdat)
    # ============================================================
    log("\n=== sb104 con liefdat (columna correcta) ===")

    for r in run(cur, "sb104 liefdat range", f"""
        SELECT MIN(liefdat) mn, MAX(liefdat) mx, COUNT(*) cnt
        FROM sb104 WHERE firma = {FIRMA}
    """):
        log(f"  sb104 liefdat: min={r[0]}  max={r[1]}  cnt={r[2]}")

    for r in run(cur, "sb104 2026 count", f"""
        SELECT COUNT(DISTINCT liefnr) liefers, COUNT(DISTINCT auftrag) ords, SUM(liefwe) val
        FROM sb104
        WHERE firma = {FIRMA} AND liefdat >= '01/01/2026'
    """):
        log(f"  sb104 2026: liefers={r[0]}  ords={r[1]}  val={r[2]}")

    for r in run(cur, "sb104 hoy", f"""
        SELECT COUNT(DISTINCT liefnr) liefers, COUNT(DISTINCT auftrag) ords, SUM(liefwe) val
        FROM sb104
        WHERE firma = {FIRMA} AND liefdat = TODAY
    """):
        log(f"  sb104 hoy: liefers={r[0]}  ords={r[1]}  val={r[2]}")

    # ============================================================
    # 7. SNAPSHOT — todas las categorías al mismo tiempo
    # ============================================================
    log("\n=== SNAPSHOT SIMULTÁNEO ===")

    for r in run(cur, "snap backorders p.termin", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND p.termin < TODAY
          AND h.aufkstat = 0
          AND p.posstat = 0 AND p.kzerl = '0'
    """):
        log(f"  [BO p.termin<HOY] ords={r[0]}  pos={r[1]}  val={r[2]}")

    for r in run(cur, "snap produccion", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND h.aufkstat = 2
          AND p.posstat = 2 AND p.kzerl = '0'
    """):
        log(f"  [PRODUCCION] ords={r[0]}  pos={r[1]}  val={r[2]}")

    for r in run(cur, "snap aufkstat8", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND h.aufkstat = 8
          AND p.kzerl = '0'
    """):
        log(f"  [AUFKSTAT=8] ords={r[0]}  pos={r[1]}  val={r[2]}")

    for r in run(cur, "snap remitos sbas8", f"""
        SELECT COUNT(DISTINCT renr) docs, COUNT(*) pos, SUM(netwert) val
        FROM sbas
        WHERE firma = {FIRMA} AND redat = TODAY AND belegart = 8
    """):
        log(f"  [REMITOS belegart=8] docs={r[0]}  pos={r[1]}  val={r[2]}")

    for r in run(cur, "snap venta sbas11", f"""
        SELECT COUNT(DISTINCT renr) docs, COUNT(*) pos, SUM(netwert) val
        FROM sbas
        WHERE firma = {FIRMA} AND redat = TODAY AND belegart = 11
    """):
        log(f"  [VENTA belegart=11] docs={r[0]}  pos={r[1]}  val={r[2]}")

    conn.close()

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\nListo → {OUTPUT_FILE}")


if __name__ == "__main__":
    main()

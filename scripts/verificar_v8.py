"""
TagInfo v8 — aufkstat=2 x termin, abterm, posstat=2, sb104 fix.
SOLO LECTURA.
"""

import pyodbc
from datetime import date, datetime

DSN = "MSPA"
OUTPUT_FILE = "taginfo_v8.txt"
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

    log(f"TagInfo v8 — {datetime.now()}")
    log(f"DSN: {DSN}  |  Fecha: {today}  |  SOLO LECTURA")
    log("=" * 70)

    conn = get_conn()
    cur = conn.cursor()
    log("Conexión OK\n")

    # ============================================================
    # 1. aufkstat=2 desglose por termin — hipótesis crédito bloqueado
    # ============================================================
    log("=== aufkstat=2 DESGLOSE POR TERMIN ===")
    log("  Hipótesis: aufkstat=2 + termin<HOY = 'Bloqueados por credito'")

    for r in run(cur, "aufkstat2 termin<hoy", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND h.aufkstat = 2
          AND p.termin < TODAY
          AND p.posstat = 0 AND p.kzerl = '0'
    """):
        log(f"  aufkstat=2 + termin<HOY: ords={r[0]}  pos={r[1]}  val={r[2]}")

    for r in run(cur, "aufkstat2 termin>=hoy", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND h.aufkstat = 2
          AND p.termin >= TODAY
          AND p.posstat = 0 AND p.kzerl = '0'
    """):
        log(f"  aufkstat=2 + termin>=HOY: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # aufkstat=2 incluyendo posstat=2
    for r in run(cur, "aufkstat2 posstat IN(0,2)", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND h.aufkstat = 2
          AND p.posstat IN (0, 2)
          AND p.kzerl = '0'
    """):
        log(f"  aufkstat=2 posstat IN(0,2): ords={r[0]}  pos={r[1]}  val={r[2]}")

    # ============================================================
    # 2. Backorders con ABTERM en lugar de TERMIN
    # ============================================================
    log("\n=== BACKORDERS USANDO abterm ===")
    for r in run(cur, "abterm<hoy", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND p.abterm < TODAY
          AND h.aufkstat = 0
          AND p.posstat = 0 AND p.kzerl = '0'
    """):
        log(f"  abterm<HOY: ords={r[0]}  pos={r[1]}  val={r[2]}")

    for r in run(cur, "termin+abterm<hoy", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND h.aufkstat = 0
          AND p.posstat = 0 AND p.kzerl = '0'
          AND (p.abterm IS NOT NULL AND p.abterm < TODAY)
    """):
        log(f"  abterm NOT NULL + <HOY: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # ============================================================
    # 3. posstat=2 — qué significa?
    # ============================================================
    log("\n=== posstat=2 — ANÁLISIS ===")
    for r in run(cur, "posstat2 por aufkstat", f"""
        SELECT h.aufkstat, COUNT(DISTINCT h.auftrag) ords,
               COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND p.posstat = 2
          AND p.kzerl = '0'
        GROUP BY h.aufkstat ORDER BY h.aufkstat
    """):
        log(f"  aufkstat={r[0]}  ords={r[1]}  pos={r[2]}  val={r[3]}")

    # posstat=2 + termin breakdown
    for r in run(cur, "posstat2 termin<hoy", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND p.posstat = 2
          AND p.termin < TODAY
          AND p.kzerl = '0'
    """):
        log(f"  posstat=2 termin<HOY: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # ============================================================
    # 4. RESUMEN COMPLETO — todas las combinaciones
    # ============================================================
    log("\n=== RESUMEN TODAS COMBINACIONES aufkstat x posstat ===")
    for r in run(cur, "full cross", f"""
        SELECT h.aufkstat, p.posstat,
               COUNT(DISTINCT h.auftrag) ords,
               COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND p.kzerl = '0'
          AND h.aufkstat IN (-2, 0, 2, 4)
          AND p.posstat IN (0, 2, 3, 8)
        GROUP BY h.aufkstat, p.posstat
        ORDER BY h.aufkstat, p.posstat
    """):
        log(f"  aufkstat={r[0]}  posstat={r[1]}  ords={r[2]}  pos={r[3]}  val={r[4]}")

    # ============================================================
    # 5. sb104 — query directa con columnas explícitas
    # ============================================================
    log("\n=== sb104 LIEFSTAT + VALORES ===")
    for r in run(cur, "sb104 liefstat valores", f"""
        SELECT liefstat, COUNT(*) cnt
        FROM sb104 WHERE firma = {FIRMA}
        GROUP BY liefstat ORDER BY liefstat
    """):
        log(f"  liefstat={r[0]}  cnt={r[1]}")

    # sb104 reciente (último año) sin filtro liefstat
    for r in run(cur, "sb104 reciente tot", f"""
        SELECT COUNT(DISTINCT liefnr) liefers,
               COUNT(DISTINCT auftrag) ords,
               SUM(liefwe) val
        FROM sb104
        WHERE firma = {FIRMA}
          AND liefdat >= '01/01/2026'
    """):
        log(f"  sb104 desde 2026: liefers={r[0]}  ords={r[1]}  val={r[2]}")

    # sb104 hoy
    for r in run(cur, "sb104 hoy", f"""
        SELECT COUNT(DISTINCT liefnr) liefers,
               COUNT(DISTINCT auftrag) ords,
               SUM(liefwe) val
        FROM sb104
        WHERE firma = {FIRMA} AND liefdat = TODAY
    """):
        log(f"  sb104 hoy: liefers={r[0]}  ords={r[1]}  val={r[2]}")

    # ============================================================
    # 6. REMITOS ABIERTOS — sbas con lsdat + sin redat
    # ============================================================
    log("\n=== REMITOS/FACTURAS ABIERTAS — múltiples enfoques ===")

    # sbas donde renr existe pero redat es futura o nula
    for r in run(cur, "sbas lsdat no redat", f"""
        SELECT COUNT(DISTINCT lsnr) liefers,
               COUNT(DISTINCT auftrag) ords,
               COUNT(*) pos,
               SUM(netwert) val
        FROM sbas
        WHERE firma = {FIRMA}
          AND lsdat > '01/01/1990'
          AND (redat IS NULL OR redat > TODAY)
    """):
        log(f"  sbas lsdat+sin redat: liefers={r[0]}  ords={r[1]}  pos={r[2]}  val={r[3]}")

    # sbas belegart=8 (posible remito) último mes
    for r in run(cur, "sbas belegart8 reciente", f"""
        SELECT COUNT(DISTINCT renr) docs,
               COUNT(DISTINCT auftrag) ords,
               COUNT(*) pos,
               SUM(netwert) val
        FROM sbas
        WHERE firma = {FIRMA}
          AND belegart = 8
          AND redat >= '01/01/2026'
    """):
        log(f"  sbas belegart=8 2026: docs={r[0]}  ords={r[1]}  pos={r[2]}  val={r[3]}")

    # sbas belegart=15 (otro tipo posible)
    for r in run(cur, "sbas belegart15 2026", f"""
        SELECT COUNT(DISTINCT renr) docs, COUNT(DISTINCT auftrag) ords,
               COUNT(*) pos, SUM(netwert) val
        FROM sbas
        WHERE firma = {FIRMA} AND belegart = 15
          AND redat >= '01/01/2026'
    """):
        log(f"  sbas belegart=15 2026: docs={r[0]}  ords={r[1]}  pos={r[2]}  val={r[3]}")

    # ============================================================
    # 7. VENTA DIARIA — probar belegart más probable
    # ============================================================
    log("\n=== VENTA DIARIA — todos los belegart hoy ===")
    for r in run(cur, "sbas hoy all belegart", f"""
        SELECT belegart, COUNT(DISTINCT renr) docs,
               COUNT(*) pos, SUM(netwert) net
        FROM sbas
        WHERE firma = {FIRMA} AND redat = TODAY
        GROUP BY belegart ORDER BY belegart
    """):
        log(f"  belegart={r[0]}  docs={r[1]}  pos={r[2]}  net={r[3]}")

    conn.close()

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\nListo → {OUTPUT_FILE}")


if __name__ == "__main__":
    main()

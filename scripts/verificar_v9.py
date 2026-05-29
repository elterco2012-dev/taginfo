"""
TagInfo v9 — backorders con liefdat f090, bloqueados full posstat, remitos pauf/f314.
SOLO LECTURA.
"""

import pyodbc
from datetime import date, datetime

DSN = "MSPA"
OUTPUT_FILE = "taginfo_v9.txt"
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

    log(f"TagInfo v9 — {datetime.now()}")
    log(f"DSN: {DSN}  |  Fecha: {today}  |  SOLO LECTURA")
    log("=" * 70)

    conn = get_conn()
    cur = conn.cursor()
    log("Conexión OK\n")

    # ============================================================
    # 1. f090 columnas — buscar campo de fecha de entrega en cabecera
    # ============================================================
    log("=== f090 COLUMNAS ===")
    for r in run(cur, "f090 cols", """
        SELECT c.colno, c.colname, c.coltype
        FROM syscolumns c, systables t
        WHERE c.tabid = t.tabid AND t.tabname = 'f090'
        ORDER BY c.colno
    """):
        log(f"  [{r[0]}] {r[1]}  type={r[2]}")

    # ============================================================
    # 2. BACKORDERS — probar con liefdat de f090 (cabecera)
    # ============================================================
    log("\n=== BACKORDERS — f090.liefdat vs f092.termin ===")

    # Con f090.liefdat
    for r in run(cur, "backorders f090.liefdat", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND h.liefdat < TODAY
          AND h.aufkstat = 0
          AND p.posstat = 0 AND p.kzerl = '0'
    """):
        log(f"  f090.liefdat<HOY: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # Con f092.termin (referencia - ya conocido)
    for r in run(cur, "backorders f092.termin", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND p.termin < TODAY
          AND h.aufkstat = 0
          AND p.posstat = 0 AND p.kzerl = '0'
    """):
        log(f"  f092.termin<HOY: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # Desglose por f090.liefdat para ver distribución
    log("\nDistribución f090.liefdat (aufkstat=0, posstat=0):")
    for r in run(cur, "liefdat dist", f"""
        SELECT
          CASE WHEN h.liefdat < TODAY THEN 'PASADO'
               WHEN h.liefdat = TODAY THEN 'HOY'
               ELSE 'FUTURO' END estado,
          COUNT(DISTINCT h.auftrag) ords,
          COUNT(*) pos,
          SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND h.aufkstat = 0
          AND p.posstat = 0 AND p.kzerl = '0'
        GROUP BY 1 ORDER BY 1
    """):
        log(f"  liefdat={r[0]}  ords={r[1]}  pos={r[2]}  val={r[3]}")

    # Combinación: AMBOS vencidos (liefdat Y termin)
    for r in run(cur, "backorders liefdat AND termin", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND h.liefdat < TODAY
          AND p.termin < TODAY
          AND h.aufkstat = 0
          AND p.posstat = 0 AND p.kzerl = '0'
    """):
        log(f"  liefdat<HOY AND termin<HOY: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # Solo liefdat < TODAY con besch=0
    for r in run(cur, "backorders liefdat+besch0", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND h.liefdat < TODAY
          AND h.aufkstat = 0
          AND p.posstat = 0 AND p.kzerl = '0'
          AND p.besch = 0
    """):
        log(f"  liefdat<HOY + besch=0: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # ============================================================
    # 3. BLOQUEADOS CRÉDITO — aufkstat=2, TODOS los posstat
    # ============================================================
    log("\n=== BLOQUEADOS CRÉDITO — aufkstat=2 todos posstat ===")

    # Total sin filtro posstat
    for r in run(cur, "aufkstat2 total sin posstat", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND h.aufkstat = 2
          AND p.kzerl = '0'
    """):
        log(f"  aufkstat=2 (todos posstat): ords={r[0]}  pos={r[1]}  val={r[2]}")

    # Desglose completo por posstat (sin filtro posstat)
    log("\naufkstat=2 desglose por posstat (sin filtro):")
    for r in run(cur, "aufkstat2 x posstat full", f"""
        SELECT p.posstat,
               COUNT(DISTINCT h.auftrag) ords,
               COUNT(*) pos,
               SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND h.aufkstat = 2
          AND p.kzerl = '0'
        GROUP BY p.posstat ORDER BY p.posstat
    """):
        log(f"  posstat={r[0]}  ords={r[1]}  pos={r[2]}  val={r[3]}")

    # aufkstat=2 excluyendo posstat=2 (producción) = bloqueados puros?
    for r in run(cur, "aufkstat2 excl posstat2", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND h.aufkstat = 2
          AND p.posstat <> 2
          AND p.kzerl = '0'
    """):
        log(f"  aufkstat=2 posstat<>2: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # aufkstat=2 sin filtro kzerl (incluye completadas)
    for r in run(cur, "aufkstat2 sin kzerl", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND h.aufkstat = 2
    """):
        log(f"  aufkstat=2 (sin kzerl): ords={r[0]}  pos={r[1]}  val={r[2]}")

    # aufkstat IN (2, 4) — quizás aufkstat=4 también es bloqueado
    for r in run(cur, "aufkstat IN(2,4)", f"""
        SELECT h.aufkstat,
               COUNT(DISTINCT h.auftrag) ords,
               COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND h.aufkstat IN (2, 4)
          AND p.kzerl = '0'
        GROUP BY h.aufkstat ORDER BY h.aufkstat
    """):
        log(f"  aufkstat={r[0]}  ords={r[1]}  pos={r[2]}  val={r[3]}")

    # ============================================================
    # 4. REMITOS ABIERTOS — pauf columnas y datos
    # ============================================================
    log("\n=== pauf — COLUMNAS Y ANÁLISIS ===")
    for r in run(cur, "pauf cols", """
        SELECT c.colno, c.colname, c.coltype
        FROM syscolumns c, systables t
        WHERE c.tabid = t.tabid AND t.tabname = 'pauf'
        ORDER BY c.colno
    """):
        log(f"  [{r[0]}] {r[1]}  type={r[2]}")

    # pauf sin va_kz='10000...' — los que tienen estado diferente
    for r in run(cur, "pauf va_kz 00001", f"""
        SELECT COUNT(DISTINCT liefnr) liefers,
               COUNT(DISTINCT auftrag) ords,
               COUNT(*) pos,
               SUM(liefwe) val
        FROM pauf
        WHERE firma = {FIRMA} AND va_kz LIKE '0%'
    """):
        log(f"  pauf va_kz LIKE '0%': liefers={r[0]}  ords={r[1]}  pos={r[2]}  val={r[3]}")

    # pauf con liefwe > 0 (tiene valor de entrega)
    for r in run(cur, "pauf liefwe>0", f"""
        SELECT COUNT(DISTINCT liefnr) liefers,
               COUNT(DISTINCT auftrag) ords,
               COUNT(*) pos,
               SUM(liefwe) val
        FROM pauf
        WHERE firma = {FIRMA} AND liefwe > 0
    """):
        log(f"  pauf liefwe>0: liefers={r[0]}  ords={r[1]}  pos={r[2]}  val={r[3]}")

    # pauf reciente (liefdat 2026) con liefwe
    for r in run(cur, "pauf 2026 liefwe>0", f"""
        SELECT COUNT(DISTINCT liefnr) liefers,
               COUNT(DISTINCT auftrag) ords,
               COUNT(*) pos,
               SUM(liefwe) val
        FROM pauf
        WHERE firma = {FIRMA} AND liefwe > 0
          AND liefdat >= '01/01/2026'
    """):
        log(f"  pauf 2026 liefwe>0: liefers={r[0]}  ords={r[1]}  pos={r[2]}  val={r[3]}")

    # ============================================================
    # 5. f314 — columnas y datos (56K filas)
    # ============================================================
    log("\n=== f314 — COLUMNAS Y ANÁLISIS ===")
    for r in run(cur, "f314 cols", """
        SELECT c.colno, c.colname, c.coltype
        FROM syscolumns c, systables t
        WHERE c.tabid = t.tabid AND t.tabname = 'f314'
        ORDER BY c.colno
    """):
        log(f"  [{r[0]}] {r[1]}  type={r[2]}")

    for r in run(cur, "f314 count", f"SELECT COUNT(*) FROM f314 WHERE firma = {FIRMA}"):
        log(f"  FILAS: {r[0]}")

    # ============================================================
    # 6. sbas — entender por qué lsdat/redat queries fallaron
    # ============================================================
    log("\n=== sbas — DIAGNÓSTICO redat/lsdat ===")

    # Verificar columnas de sbas
    for r in run(cur, "sbas cols", """
        SELECT c.colno, c.colname, c.coltype
        FROM syscolumns c, systables t
        WHERE c.tabid = t.tabid AND t.tabname = 'sbas'
        ORDER BY c.colno
    """):
        log(f"  [{r[0]}] {r[1]}  type={r[2]}")

    # sbas: distribución de belegart con lsnr>0 (tiene remito)
    log("\nsbas belegart donde lsnr>0:")
    for r in run(cur, "sbas lsnr>0 belegart", f"""
        SELECT belegart, COUNT(DISTINCT lsnr) lsnrs,
               COUNT(DISTINCT renr) renrs,
               COUNT(*) pos, SUM(netwert) val
        FROM sbas
        WHERE firma = {FIRMA} AND lsnr > 0
        GROUP BY belegart ORDER BY belegart
    """):
        log(f"  belegart={r[0]}  lsnrs={r[1]}  renrs={r[2]}  pos={r[3]}  val={r[4]}")

    # sbas: cuántos tienen renr nulo/0 (remito sin factura)
    for r in run(cur, "sbas renr NULL", f"""
        SELECT COUNT(DISTINCT lsnr) lsnrs,
               COUNT(DISTINCT auftrag) ords,
               COUNT(*) pos, SUM(netwert) val
        FROM sbas
        WHERE firma = {FIRMA} AND lsnr > 0 AND renr IS NULL
    """):
        log(f"  sbas renr IS NULL: lsnrs={r[0]}  ords={r[1]}  pos={r[2]}  val={r[3]}")

    # sbas redat nulo (no tiene fecha de factura)
    for r in run(cur, "sbas redat NULL", f"""
        SELECT COUNT(DISTINCT lsnr) lsnrs,
               COUNT(DISTINCT auftrag) ords,
               COUNT(*) pos, SUM(netwert) val
        FROM sbas
        WHERE firma = {FIRMA} AND redat IS NULL
    """):
        log(f"  sbas redat IS NULL: lsnrs={r[0]}  ords={r[1]}  pos={r[2]}  val={r[3]}")

    # sbas lsdat range — ver si existe y tiene valores recientes
    for r in run(cur, "sbas lsdat range", f"""
        SELECT MIN(lsdat) mn, MAX(lsdat) mx, COUNT(*) cnt
        FROM sbas WHERE firma = {FIRMA}
    """):
        log(f"  sbas lsdat: min={r[0]}  max={r[1]}  cnt={r[2]}")

    # ============================================================
    # 7. TOTAL GENERAL — resumen de todas las categorías conocidas
    # ============================================================
    log("\n=== RESUMEN CATEGORÍAS CONFIRMADAS ===")

    # Backorders (best guess — probar las dos variantes)
    for r in run(cur, "cat backorders liefdat", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND h.liefdat < TODAY
          AND h.aufkstat = 0
          AND p.posstat = 0 AND p.kzerl = '0'
    """):
        log(f"  [BACKORDERS-liefdat] ords={r[0]}  pos={r[1]}  val={r[2]}")

    # Produccion (CONFIRMADO)
    for r in run(cur, "cat produccion", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND h.aufkstat = 2
          AND p.posstat = 2 AND p.kzerl = '0'
    """):
        log(f"  [PRODUCCION-confirmado] ords={r[0]}  pos={r[1]}  val={r[2]}")

    # Venta diaria (CONFIRMADO belegart IN 8,11)
    for r in run(cur, "cat venta diaria", f"""
        SELECT COUNT(DISTINCT renr) docs, COUNT(*) pos, SUM(netwert) val
        FROM sbas
        WHERE firma = {FIRMA} AND redat = TODAY AND belegart IN (8, 11)
    """):
        log(f"  [VENTA-DIARIA] docs={r[0]}  pos={r[1]}  val={r[2]}")

    conn.close()

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\nListo → {OUTPUT_FILE}")


if __name__ == "__main__":
    main()

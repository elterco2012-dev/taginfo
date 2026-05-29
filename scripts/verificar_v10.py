"""
TagInfo v10 — backorders f090.termin, bloqueados via f116/kz, remitos sb104/posstat8.
SOLO LECTURA.
"""

import pyodbc
from datetime import date, datetime

DSN = "MSPA"
OUTPUT_FILE = "taginfo_v10.txt"
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

    log(f"TagInfo v10 — {datetime.now()}")
    log(f"DSN: {DSN}  |  Fecha: {today}  |  SOLO LECTURA")
    log("=" * 70)

    conn = get_conn()
    cur = conn.cursor()
    log("Conexión OK\n")

    # ============================================================
    # 1. BACKORDERS — usar f090.termin (existe en col 51)
    # ============================================================
    log("=== BACKORDERS — f090.termin (cabecera) ===")

    for r in run(cur, "backorders h.termin<hoy", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND h.termin < TODAY
          AND h.aufkstat = 0
          AND p.posstat = 0 AND p.kzerl = '0'
    """):
        log(f"  h.termin<HOY: ords={r[0]}  pos={r[1]}  val={r[2]}")

    for r in run(cur, "backorders h.termin>=hoy", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND h.termin >= TODAY
          AND h.aufkstat = 0
          AND p.posstat = 0 AND p.kzerl = '0'
    """):
        log(f"  h.termin>=HOY: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # Desglose termin por mes (f090)
    log("\nDistribución h.termin (aufkstat=0, posstat=0, kzerl='0'):")
    for r in run(cur, "h.termin por mes", f"""
        SELECT YEAR(h.termin) yy, MONTH(h.termin) mm,
               COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND h.aufkstat = 0
          AND p.posstat = 0 AND p.kzerl = '0'
        GROUP BY 1, 2 ORDER BY 1, 2
    """):
        log(f"  {r[0]}-{r[1]:02d}  ords={r[2]}  pos={r[3]}  val={r[4]}")

    # ============================================================
    # 2. BLOQUEADOS CRÉDITO — investigar f116
    # ============================================================
    log("\n=== f116 — DISTRIBUCIÓN inkasso / va / lb / zb ===")

    for r in run(cur, "f116 count", f"SELECT COUNT(*) FROM f116 WHERE firma = {FIRMA}"):
        log(f"  f116 FILAS: {r[0]}")

    for r in run(cur, "f116 inkasso dist", f"""
        SELECT inkasso, COUNT(*) cnt, COUNT(DISTINCT auftrag) ords
        FROM f116 WHERE firma = {FIRMA}
        GROUP BY inkasso ORDER BY inkasso
    """):
        log(f"  inkasso={r[0]}  cnt={r[1]}  ords={r[2]}")

    for r in run(cur, "f116 va dist", f"""
        SELECT va, lb, zb, COUNT(*) cnt, COUNT(DISTINCT auftrag) ords
        FROM f116 WHERE firma = {FIRMA}
        GROUP BY va, lb, zb ORDER BY va, lb, zb
    """):
        log(f"  va={r[0]}  lb={r[1]}  zb={r[2]}  cnt={r[3]}  ords={r[4]}")

    # f116 ordenes con posiciones abiertas en f092
    for r in run(cur, "f116 join f092 open", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p, f116 c
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA} AND c.firma = {FIRMA}
          AND h.auftrag = p.auftrag AND h.auftrag = c.auftrag
          AND p.kzerl = '0'
    """):
        log(f"  f116 join f092 open: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # ============================================================
    # 3. BLOQUEADOS — f090.kzloesp y kzaeb (flags de bloqueo)
    # ============================================================
    log("\n=== f090 FLAGS DE BLOQUEO ===")

    for r in run(cur, "kzloesp dist", f"""
        SELECT kzloesp, COUNT(*) cnt, COUNT(DISTINCT auftrag) ords
        FROM f090 WHERE firma = {FIRMA}
        GROUP BY kzloesp ORDER BY kzloesp
    """):
        log(f"  kzloesp={r[0]}  cnt={r[1]}  ords={r[2]}")

    for r in run(cur, "kzaeb dist", f"""
        SELECT kzaeb, COUNT(*) cnt, COUNT(DISTINCT auftrag) ords
        FROM f090 WHERE firma = {FIRMA}
        GROUP BY kzaeb ORDER BY kzaeb
    """):
        log(f"  kzaeb={r[0]}  cnt={r[1]}  ords={r[2]}")

    # kzloesp=1 con posiciones abiertas
    for r in run(cur, "kzloesp=1 open", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND h.kzloesp = 1
          AND p.kzerl = '0'
    """):
        log(f"  kzloesp=1: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # ============================================================
    # 4. BLOQUEADOS — aufkstat distribución completa (TODOS los valores)
    # ============================================================
    log("\n=== AUFKSTAT DISTRIBUCIÓN COMPLETA ===")
    for r in run(cur, "aufkstat all values", f"""
        SELECT h.aufkstat, COUNT(DISTINCT h.auftrag) ords,
               COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND p.kzerl = '0'
        GROUP BY h.aufkstat ORDER BY h.aufkstat
    """):
        log(f"  aufkstat={r[0]}  ords={r[1]}  pos={r[2]}  val={r[3]}")

    # ============================================================
    # 5. REMITOS — sb104 esquema y datos recientes
    # ============================================================
    log("\n=== sb104 COLUMNAS ===")
    for r in run(cur, "sb104 cols", """
        SELECT c.colno, c.colname, c.coltype
        FROM syscolumns c, systables t
        WHERE c.tabid = t.tabid AND t.tabname = 'sb104'
        ORDER BY c.colno
    """):
        log(f"  [{r[0]}] {r[1]}  type={r[2]}")

    for r in run(cur, "sb104 lsdat range", f"""
        SELECT MIN(lsdat) mn, MAX(lsdat) mx, COUNT(*) cnt
        FROM sb104 WHERE firma = {FIRMA}
    """):
        log(f"  sb104 lsdat: min={r[0]}  max={r[1]}  cnt={r[2]}")

    # sb104 reciente (2026) con datos
    for r in run(cur, "sb104 2026 liefstat0", f"""
        SELECT liefstat, COUNT(DISTINCT liefnr) liefers,
               COUNT(DISTINCT auftrag) ords,
               SUM(liefwe) val
        FROM sb104
        WHERE firma = {FIRMA} AND lsdat >= '01/01/2026'
        GROUP BY liefstat ORDER BY liefstat
    """):
        log(f"  liefstat={r[0]}  liefers={r[1]}  ords={r[2]}  val={r[3]}")

    # sb104 HOY
    for r in run(cur, "sb104 hoy", f"""
        SELECT liefstat, COUNT(DISTINCT liefnr) liefers,
               COUNT(DISTINCT auftrag) ords,
               SUM(liefwe) val
        FROM sb104
        WHERE firma = {FIRMA} AND lsdat = TODAY
        GROUP BY liefstat ORDER BY liefstat
    """):
        log(f"  sb104 hoy liefstat={r[0]}  liefers={r[1]}  ords={r[2]}  val={r[3]}")

    # ============================================================
    # 6. REMITOS — f092 posstat=8 (shipped/dispatched)
    # ============================================================
    log("\n=== f092 posstat=8 (enviado sin factura?) ===")
    for r in run(cur, "posstat8 open", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND p.posstat = 8
          AND p.kzerl = '0'
    """):
        log(f"  posstat=8 kzerl='0': ords={r[0]}  pos={r[1]}  val={r[2]}")

    for r in run(cur, "posstat8 all kzerl", f"""
        SELECT p.kzerl, COUNT(DISTINCT h.auftrag) ords,
               COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND p.posstat = 8
        GROUP BY p.kzerl ORDER BY p.kzerl
    """):
        log(f"  posstat=8 kzerl={r[0]}  ords={r[1]}  pos={r[2]}  val={r[3]}")

    # ============================================================
    # 7. REMITOS — sbas belegart distribución (todos los tipos)
    # ============================================================
    log("\n=== sbas BELEGART DISTRIBUCIÓN (todos) ===")
    for r in run(cur, "sbas belegart all", f"""
        SELECT belegart, COUNT(DISTINCT renr) renrs,
               COUNT(DISTINCT lsnr) lsnrs,
               COUNT(*) pos, SUM(netwert) val
        FROM sbas
        WHERE firma = {FIRMA}
        GROUP BY belegart ORDER BY belegart
    """):
        log(f"  belegart={r[0]}  renrs={r[1]}  lsnrs={r[2]}  pos={r[3]}  val={r[4]}")

    # sbas belegart dist solo 2026
    log("\nsbas belegart 2026:")
    for r in run(cur, "sbas belegart 2026", f"""
        SELECT belegart, COUNT(DISTINCT renr) renrs,
               COUNT(DISTINCT lsnr) lsnrs,
               COUNT(*) pos, SUM(netwert) val
        FROM sbas
        WHERE firma = {FIRMA} AND redat >= '01/01/2026'
        GROUP BY belegart ORDER BY belegart
    """):
        log(f"  belegart={r[0]}  renrs={r[1]}  lsnrs={r[2]}  pos={r[3]}  val={r[4]}")

    # ============================================================
    # 8. PEDIDOS FUTUROS = 0 — por qué?
    # ============================================================
    log("\n=== PEDIDOS FUTUROS — diagnóstico ===")
    for r in run(cur, "futuros h.termin>=hoy", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND h.termin >= TODAY
          AND h.aufkstat = 0
          AND p.posstat = 0 AND p.kzerl = '0'
    """):
        log(f"  h.termin>=HOY (aufkstat=0): ords={r[0]}  pos={r[1]}  val={r[2]}")

    # Rango de h.termin para orders activas
    for r in run(cur, "h.termin range activas", f"""
        SELECT MIN(h.termin) mn, MAX(h.termin) mx, COUNT(DISTINCT h.auftrag) ords
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND h.aufkstat = 0
          AND p.posstat = 0 AND p.kzerl = '0'
    """):
        log(f"  h.termin range: min={r[0]}  max={r[1]}  ords={r[2]}")

    # ============================================================
    # 9. RESUMEN SNAPSHOT — todas las categorías candidatas
    # ============================================================
    log("\n=== SNAPSHOT CATEGORÍAS ===")

    for r in run(cur, "snap backorders", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND h.termin < TODAY
          AND h.aufkstat = 0
          AND p.posstat = 0 AND p.kzerl = '0'
    """):
        log(f"  [BACKORDERS h.termin] ords={r[0]}  pos={r[1]}  val={r[2]}")

    for r in run(cur, "snap produccion", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND h.aufkstat = 2
          AND p.posstat = 2 AND p.kzerl = '0'
    """):
        log(f"  [PRODUCCION] ords={r[0]}  pos={r[1]}  val={r[2]}")

    for r in run(cur, "snap venta", f"""
        SELECT COUNT(DISTINCT renr) docs, COUNT(*) pos, SUM(netwert) val
        FROM sbas
        WHERE firma = {FIRMA} AND redat = TODAY AND belegart IN (8, 11)
    """):
        log(f"  [VENTA DIARIA] docs={r[0]}  pos={r[1]}  val={r[2]}")

    conn.close()

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\nListo → {OUTPUT_FILE}")


if __name__ == "__main__":
    main()

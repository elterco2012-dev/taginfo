"""
TagInfo v5 — fix kund join, sbas remitos abiertos, operf, tablas con datos.
SOLO LECTURA.
"""

import pyodbc
from datetime import date, datetime

DSN = "MSPA"
OUTPUT_FILE = "taginfo_v5.txt"
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

    log(f"TagInfo v5 — {datetime.now()}")
    log(f"DSN: {DSN}  |  Fecha: {today}  |  SOLO LECTURA")
    log("=" * 70)

    conn = get_conn()
    cur = conn.cursor()
    log("Conexión OK\n")

    # ============================================================
    # 1. Diagnóstico kund — por qué el join da 0
    # ============================================================
    log("=== DIAGNÓSTICO KUND JOIN ===")

    for r in run(cur, "kund firmas", """
        SELECT firma, COUNT(*) cnt FROM kund GROUP BY firma ORDER BY firma
    """):
        log(f"  kund firma={r[0]}  count={r[1]}")

    for r in run(cur, "f090 kdnr en kund (sin filtro firma)", f"""
        SELECT COUNT(DISTINCT h.kdnr) en_f090,
               COUNT(DISTINCT k.kdnr) en_kund
        FROM f090 h, kund k
        WHERE h.firma = {FIRMA}
    """):
        log(f"  f090 kdnr count={r[0]}  kund kdnr count={r[1]}")

    # Join sin filtro firma en kund
    for r in run(cur, "backorders SIN filtro firma en kund", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p, kund k
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND h.kdnr = k.kdnr
          AND p.termin < TODAY
          AND h.aufkstat = 0
          AND p.posstat = 0 AND p.kzerl = '0'
    """):
        log(f"  backorders (sin firma en kund): ords={r[0]} pos={r[1]} val={r[2]}")

    # kund firma para los kdnr de f090
    for r in run(cur, "kund firma de clientes de f090", f"""
        SELECT k.firma, COUNT(DISTINCT k.kdnr) clientes
        FROM kund k
        WHERE k.kdnr IN (SELECT DISTINCT kdnr FROM f090 WHERE firma = {FIRMA})
        GROUP BY k.firma
        ORDER BY k.firma
    """):
        log(f"  kund.firma={r[0]}  clientes_en_f090={r[1]}")

    # ============================================================
    # 2. aufkstat=2 — sin join kund
    # ============================================================
    log("\n=== aufkstat=2 SIN join kund ===")
    for r in run(cur, "aufkstat=2 direct", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND h.aufkstat = 2
          AND p.posstat = 0 AND p.kzerl = '0'
    """):
        log(f"  aufkstat=2: ords={r[0]} pos={r[1]} val={r[2]}")

    for aufkstat in [-2, -1, 0, 2, 4]:
        for r in run(cur, f"aufkstat={aufkstat}", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p
            WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
              AND h.auftrag = p.auftrag
              AND h.aufkstat = {aufkstat}
              AND p.posstat = 0 AND p.kzerl = '0'
        """):
            if r[0] and r[0] > 0:
                log(f"  aufkstat={aufkstat}: ords={r[0]} pos={r[1]} val={r[2]}")

    # ============================================================
    # 3. SBAS — remitos abiertos (entregado pero no facturado)
    # ============================================================
    log("\n=== SBAS — REMITOS ABIERTOS (lsnr>0, renr=0) ===")
    for r in run(cur, "sbas remitos sin factura", f"""
        SELECT COUNT(DISTINCT lsnr) remitos,
               COUNT(DISTINCT auftrag) ordenes,
               COUNT(*) posiciones,
               SUM(netwert) valor
        FROM sbas
        WHERE firma = {FIRMA}
          AND lsnr > 0
          AND renr = 0
    """):
        log(f"  remitos={r[0]} ordenes={r[1]} pos={r[2]} val={r[3]}")

    # sbas con lsdat reciente (abiertos últimos 90 días)
    for r in run(cur, "sbas lsdat reciente + renr=0", f"""
        SELECT COUNT(DISTINCT lsnr) remitos,
               COUNT(DISTINCT auftrag) ordenes,
               COUNT(*) posiciones,
               SUM(netwert) valor
        FROM sbas
        WHERE firma = {FIRMA}
          AND lsnr > 0
          AND renr = 0
          AND lsdat > TODAY - 90
    """):
        log(f"  remitos recientes (90d): remitos={r[0]} ordenes={r[1]} pos={r[2]} val={r[3]}")

    # belegart en sbas para entender tipos
    log("\nDistribución belegart en sbas (total, no solo hoy):")
    for r in run(cur, "sbas belegart dist", f"""
        SELECT belegart, COUNT(DISTINCT renr) docs, SUM(netwert) net
        FROM sbas WHERE firma = {FIRMA}
        GROUP BY belegart ORDER BY belegart
    """):
        log(f"  belegart={r[0]}  docs={r[1]}  netwert={r[2]}")

    # ============================================================
    # 4. operf — tabla de operaciones/producción
    # ============================================================
    log("\n=== operf — TABLA OPERACIONES ===")
    for r in run(cur, "operf cols", """
        SELECT c.colno, c.colname
        FROM syscolumns c, systables t
        WHERE c.tabid = t.tabid AND t.tabname = 'operf'
        ORDER BY c.colno
    """):
        log(f"  [{r[0]}] {r[1]}")

    for r in run(cur, "operf count", f"SELECT COUNT(*) FROM operf WHERE firma = {FIRMA}"):
        log(f"  FILAS: {r[0]}")

    # ============================================================
    # 5. f116 — explorar con nombres de columnas explícitos
    # ============================================================
    log("\n=== f116 — MUESTRA (columnas explícitas) ===")
    for r in run(cur, "f116 sample", f"""
        SELECT FIRST 5 firma, kdnr, auftrag, aufwert, va, lb, zb, inkasso
        FROM f116 WHERE firma = {FIRMA}
    """):
        log(f"  {list(r)}")

    # Total f116
    for r in run(cur, "f116 totales", f"""
        SELECT COUNT(DISTINCT kdnr) clientes,
               COUNT(DISTINCT auftrag) ordenes,
               COUNT(*) filas,
               SUM(aufwert) valor_total
        FROM f116 WHERE firma = {FIRMA}
    """):
        log(f"  clientes={r[0]} ordenes={r[1]} filas={r[2]} valor={r[3]}")

    # ============================================================
    # 6. TABLAS CON DATOS QUE NO HEMOS EXPLORADO
    # ============================================================
    log("\n=== TABLAS CON MAS DE 50 FILAS NO EXPLORADAS ===")
    for r in run(cur, "tablas con datos", """
        SELECT t.tabname
        FROM systables t
        WHERE t.tabid > 99 AND t.tabtype = 'T'
          AND t.tabname NOT LIKE 'f0%'
          AND t.tabname NOT LIKE 'f1%'
          AND t.tabname NOT LIKE 'op%'
          AND t.tabname NOT LIKE 'vk%'
          AND t.tabname NOT IN ('sbas','sbaset','kund','f040')
        ORDER BY t.tabname
    """):
        tname = r[0]
        cnt = run(cur, f"count {tname}", f"SELECT COUNT(*) FROM {tname}")
        if cnt and cnt[0][0] > 100:
            log(f"  {tname}: {cnt[0][0]} filas")

    # ============================================================
    # 7. VENTA DIARIA — confirmar belegart correcto
    # ============================================================
    log("\n=== VENTA DIARIA — muestra sbas hoy ===")
    for r in run(cur, "sbas hoy belegart11 sample", f"""
        SELECT FIRST 3 renr, lsnr, auftrag, redat, netwert, brtwert
        FROM sbas
        WHERE firma = {FIRMA} AND redat = TODAY AND belegart = 11
    """):
        log(f"  renr={r[0]} lsnr={r[1]} auftrag={r[2]} redat={r[3]} net={r[4]} brt={r[5]}")

    conn.close()

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\nListo → {OUTPUT_FILE}")


if __name__ == "__main__":
    main()

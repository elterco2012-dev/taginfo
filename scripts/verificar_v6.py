"""
TagInfo v6 — fix sperrgrund CHAR, investigar pauf/sbli/f314/vplan, kredlim.
SOLO LECTURA.
"""

import pyodbc
from datetime import date, datetime

DSN = "MSPA"
OUTPUT_FILE = "taginfo_v6.txt"
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


def cols(cursor, tname):
    return run(cursor, f"{tname} cols", f"""
        SELECT c.colno, c.colname
        FROM syscolumns c, systables t
        WHERE c.tabid = t.tabid AND t.tabname = '{tname}'
        ORDER BY c.colno
    """)


def main():
    lines = []
    log = lines.append
    today = date.today()

    log(f"TagInfo v6 — {datetime.now()}")
    log(f"DSN: {DSN}  |  Fecha: {today}  |  SOLO LECTURA")
    log("=" * 70)

    conn = get_conn()
    cur = conn.cursor()
    log("Conexión OK\n")

    # ============================================================
    # 1. BACKORDERS — fix correcto con kund.firma=1 sin sperrgrund
    # ============================================================
    log("=== BACKORDERS CORREGIDOS (kund.firma=1, sin filtro sperrgrund) ===")
    for r in run(cur, "backorders fix", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords,
               COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p, kund k
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA} AND k.firma = {FIRMA}
          AND h.auftrag = p.auftrag AND h.kdnr = k.kdnr
          AND p.termin < TODAY
          AND h.aufkstat = 0
          AND p.posstat = 0 AND p.kzerl = '0'
    """):
        log(f"  ords={r[0]}  pos={r[1]}  val={r[2]}")

    log("\n  (sin kund join - total):")
    for r in run(cur, "backorders sin kund", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords,
               COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND p.termin < TODAY
          AND h.aufkstat = 0
          AND p.posstat = 0 AND p.kzerl = '0'
    """):
        log(f"  ords={r[0]}  pos={r[1]}  val={r[2]}")

    # ============================================================
    # 2. CREDITO BLOQUEADO — usando kredlim
    # ============================================================
    log("\n=== CRÉDITO BLOQUEADO — kund.kredlim ===")
    for r in run(cur, "kredlim dist", f"""
        SELECT kredlim, COUNT(*) cnt
        FROM kund WHERE firma = {FIRMA}
        GROUP BY kredlim ORDER BY kredlim
    """):
        log(f"  kredlim={r[0]}  count={r[1]}")

    # Ordenes de clientes con kredlim = 0 (sin límite otorgado = bloqueado?)
    log("\nOrdenes de clientes con kredlim = 0:")
    for r in run(cur, "kredlim=0 orders", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords,
               COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p, kund k
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA} AND k.firma = {FIRMA}
          AND h.auftrag = p.auftrag AND h.kdnr = k.kdnr
          AND k.kredlim = 0
          AND h.aufkstat = 0
          AND p.posstat = 0 AND p.kzerl = '0'
    """):
        log(f"  ords={r[0]}  pos={r[1]}  val={r[2]}")

    # Ordenes de clientes sin entry en kund (not exists)
    log("\nOrdenes de clientes SIN entrada en kund (orphan):")
    for r in run(cur, "orphan orders", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords,
               COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND h.aufkstat = 0
          AND p.posstat = 0 AND p.kzerl = '0'
          AND NOT EXISTS (
              SELECT 1 FROM kund k
              WHERE k.kdnr = h.kdnr AND k.firma = {FIRMA}
          )
    """):
        log(f"  ords={r[0]}  pos={r[1]}  val={r[2]}")

    # ============================================================
    # 3. pauf — posibles órdenes de producción
    # ============================================================
    log("\n=== pauf — TABLA (posibles órdenes producción) ===")
    for c in cols(cur, "pauf"):
        log(f"  [{c[0]}] {c[1]}")

    for r in run(cur, "pauf count", f"SELECT COUNT(*) FROM pauf WHERE firma = {FIRMA}"):
        log(f"  FILAS firma={FIRMA}: {r[0]}")

    # Muestra primeras columnas clave
    for r in run(cur, "pauf status dist", f"""
        SELECT kopfstat, COUNT(*) cnt
        FROM pauf WHERE firma = {FIRMA}
        GROUP BY kopfstat ORDER BY kopfstat
    """):
        log(f"  pauf.kopfstat={r[0]}  count={r[1]}")

    # ============================================================
    # 4. panz — relacionada con pauf?
    # ============================================================
    log("\n=== panz — TABLA ===")
    for c in cols(cur, "panz"):
        log(f"  [{c[0]}] {c[1]}")

    for r in run(cur, "panz count", f"SELECT COUNT(*) FROM panz WHERE firma = {FIRMA}"):
        log(f"  FILAS firma={FIRMA}: {r[0]}")

    # ============================================================
    # 5. sbli — posibles remitos abiertos
    # ============================================================
    log("\n=== sbli — TABLA (posibles remitos) ===")
    for c in cols(cur, "sbli"):
        log(f"  [{c[0]}] {c[1]}")

    for r in run(cur, "sbli count", f"SELECT COUNT(*) FROM sbli WHERE firma = {FIRMA}"):
        log(f"  FILAS firma={FIRMA}: {r[0]}")

    # ============================================================
    # 6. f314 — tabla con 56K filas
    # ============================================================
    log("\n=== f314 — TABLA (56K filas) ===")
    for c in cols(cur, "f314"):
        log(f"  [{c[0]}] {c[1]}")

    for r in run(cur, "f314 count", f"SELECT COUNT(*) FROM f314 WHERE firma = {FIRMA}"):
        log(f"  FILAS firma={FIRMA}: {r[0]}")

    # ============================================================
    # 7. vplan — delivery planning (59K filas)
    # ============================================================
    log("\n=== vplan — TABLA ===")
    for c in cols(cur, "vplan"):
        log(f"  [{c[0]}] {c[1]}")

    for r in run(cur, "vplan count", f"SELECT COUNT(*) FROM vplan WHERE firma = {FIRMA}"):
        log(f"  FILAS firma={FIRMA}: {r[0]}")

    # ============================================================
    # 8. f313 — tabla con 5K filas (posible remito-factura)
    # ============================================================
    log("\n=== f313 — TABLA ===")
    for c in cols(cur, "f313"):
        log(f"  [{c[0]}] {c[1]}")

    for r in run(cur, "f313 count", f"SELECT COUNT(*) FROM f313 WHERE firma = {FIRMA}"):
        log(f"  FILAS firma={FIRMA}: {r[0]}")

    # ============================================================
    # 9. sb104 — tabla con 610K filas (sbas related?)
    # ============================================================
    log("\n=== sb104 — TABLA ===")
    for c in cols(cur, "sb104"):
        log(f"  [{c[0]}] {c[1]}")

    for r in run(cur, "sb104 count", f"SELECT COUNT(*) FROM sb104 WHERE firma = {FIRMA}"):
        log(f"  FILAS firma={FIRMA}: {r[0]}")

    # ============================================================
    # 10. sbli — muestra de datos si tiene filas
    # ============================================================
    log("\n=== sbli MUESTRA ===")
    sbli_cols = cols(cur, "sbli")
    if sbli_cols:
        colnames = [c[1] for c in sbli_cols[:8]]
        col_str = ", ".join(colnames)
        for r in run(cur, "sbli sample", f"""
            SELECT {col_str} FROM sbli WHERE firma = {FIRMA} AND rowid IN (
                SELECT MIN(rowid) FROM sbli WHERE firma = {FIRMA}
                UNION ALL SELECT MIN(rowid)+1 FROM sbli WHERE firma = {FIRMA}
                UNION ALL SELECT MIN(rowid)+2 FROM sbli WHERE firma = {FIRMA}
            )
        """):
            log(f"  {list(r)}")

    # ============================================================
    # 11. venta diaria — sbas con columnas explícitas (fix FIRST)
    # ============================================================
    log("\n=== VENTA DIARIA sbas hoy ===")
    for r in run(cur, "sbas hoy belegart11", f"""
        SELECT COUNT(DISTINCT renr) docs, COUNT(*) pos, SUM(netwert) net
        FROM sbas
        WHERE firma = {FIRMA} AND redat = TODAY AND belegart = 11
    """):
        log(f"  belegart=11: docs={r[0]}  pos={r[1]}  net={r[2]}")

    for r in run(cur, "sbas hoy belegart8", f"""
        SELECT COUNT(DISTINCT renr) docs, COUNT(*) pos, SUM(netwert) net
        FROM sbas
        WHERE firma = {FIRMA} AND redat = TODAY AND belegart = 8
    """):
        log(f"  belegart=8:  docs={r[0]}  pos={r[1]}  net={r[2]}")

    conn.close()

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\nListo → {OUTPUT_FILE}")


if __name__ == "__main__":
    main()

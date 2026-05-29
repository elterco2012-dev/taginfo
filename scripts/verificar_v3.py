"""
TagInfo v3 — investigación profunda de filtros y credit block.
SOLO LECTURA.
"""

import pyodbc
from datetime import date, datetime

DSN = "MSPA"
OUTPUT_FILE = "taginfo_v3.txt"


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

    log(f"TagInfo v3 — {datetime.now()}")
    log(f"DSN: {DSN}  |  Fecha: {today}  |  SOLO LECTURA")
    log("=" * 70)

    conn = get_conn()
    cur = conn.cursor()
    log("Conexión OK\n")

    # 1) Distribución por FIRMA
    log("=== DISTRIBUCIÓN POR FIRMA en f090 ===")
    for r in run(cur, "firmas f090", """
        SELECT firma, aufkstat, COUNT(*) cnt
        FROM f090
        GROUP BY firma, aufkstat
        ORDER BY firma, aufkstat
    """):
        log(f"  firma={r[0]}  aufkstat={r[1]}  count={r[2]}")

    # 2) Todas las columnas de la tabla kund
    log("\n=== TODAS LAS COLUMNAS DE kund ===")
    for r in run(cur, "kund cols", """
        SELECT c.colno, c.colname, c.coltype, c.collength
        FROM syscolumns c, systables t
        WHERE c.tabid = t.tabid AND t.tabname = 'kund'
        ORDER BY c.colno
    """):
        log(f"  [{r[0]}] {r[1]}")

    # 3) Valores de las últimas columnas de kund (las menos obvias, probables flags)
    log("\n=== VALORES COLUMNAS CLAVE DE kund ===")
    for col in ["kzsperre", "kzsperr", "sperrart", "kzbonitaet", "bonkz",
                "kzkreditsp", "kreditsp", "kzkrsperr", "kzblock",
                "kzlimit", "kzloesp", "kzges"]:
        rows = run(cur, f"kund.{col}", f"""
            SELECT {col}, COUNT(*) cnt FROM kund GROUP BY {col} ORDER BY {col}
        """)
        if rows:
            log(f"\n  kund.{col}:")
            for r in rows:
                log(f"    {col}={r[0]}  count={r[1]}")

    # 4) Buscar en kund columnas con 'kz' (indicadores/flags)
    log("\n=== COLUMNAS kund CON 'kz' (flags) ===")
    for r in run(cur, "kund kz cols", """
        SELECT c.colname
        FROM syscolumns c, systables t
        WHERE c.tabid = t.tabid AND t.tabname = 'kund'
          AND c.colname LIKE 'kz%'
        ORDER BY c.colno
    """):
        log(f"  {r[0]}")

    # 5) kzlock en f090 — intentar interpretarlo como bitmask
    log("\n=== kzlock en f090 — interpretación bitmask ===")
    log("  (valores no-cero):")
    for r in run(cur, "kzlock nonzero", """
        SELECT firma, kzlock, aufkstat, aufart,
               COUNT(*) cnt
        FROM f090
        WHERE kzlock <> 0
        GROUP BY firma, kzlock, aufkstat, aufart
        ORDER BY firma, kzlock
    """):
        log(f"  firma={r[0]}  kzlock={r[1]}  aufkstat={r[2]}  aufart={r[3]}  count={r[4]}")

    # bit 1 (valor 1) de kzlock = crédito?
    log("\n  Prueba kzlock bit 0 (kzlock MOD 2 = 1):")
    for r in run(cur, "kzlock bit0", """
        SELECT firma, COUNT(DISTINCT auftrag) ords
        FROM f090
        WHERE MOD(kzlock, 2) = 1
        GROUP BY firma
    """):
        log(f"  firma={r[0]}  orders_con_bit0={r[1]}")

    # 6) Termin en f092 — versión sin CASE (Informix no siempre soporta CASE en GROUP BY)
    log("\n=== TERMIN vs HOY en f092 (posstat=0, kzerl='0') ===")
    for firma in [1, 2]:
        log(f"\n  FIRMA={firma}:")
        # vencidos
        for r in run(cur, f"vencidos firma={firma}", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p
            WHERE h.firma = {firma} AND p.firma = {firma}
              AND h.auftrag = p.auftrag
              AND p.posstat = 0 AND p.kzerl = '0'
              AND h.aufkstat = 0
              AND p.termin < TODAY
        """):
            log(f"    vencidos (termin<hoy): ords={r[0]} pos={r[1]} val={r[2]}")

        for r in run(cur, f"futuros firma={firma}", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p
            WHERE h.firma = {firma} AND p.firma = {firma}
              AND h.auftrag = p.auftrag
              AND p.posstat = 0 AND p.kzerl = '0'
              AND h.aufkstat = 0
              AND p.termin >= TODAY
        """):
            log(f"    futuros  (termin>=hoy): ords={r[0]} pos={r[1]} val={r[2]}")

    # 7) Ordenes de produccion — buscar en otras tablas
    log("\n=== BUSCAR ÓRDENES DE PRODUCCIÓN ===")
    # Tablas con 'fertig', 'prod', 'hers', 'fabr', 'werk'
    for r in run(cur, "tablas produccion", """
        SELECT tabname FROM systables
        WHERE tabid > 99 AND tabtype = 'T'
          AND (tabname LIKE '%fertig%' OR tabname LIKE '%prod%'
               OR tabname LIKE '%hers%' OR tabname LIKE '%fabr%'
               OR tabname LIKE '%werk%' OR tabname LIKE '%manu%'
               OR tabname LIKE '%fert%')
        ORDER BY tabname
    """):
        log(f"  {r[0]}")

    # f092 con posstat diferente — posstat=3 podria ser en produccion
    log("\n  f092 posstat=3 (posible en producción):")
    for firma in [1, 2]:
        for r in run(cur, f"posstat3 firma={firma}", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p
            WHERE h.firma = {firma} AND p.firma = {firma}
              AND h.auftrag = p.auftrag
              AND p.posstat = 3
              AND p.kzerl = '0'
        """):
            log(f"    firma={firma}: ords={r[0]} pos={r[1]} val={r[2]}")

    # 8) Remitos f116 — desglose más detallado
    log("\n=== REMITOS f116 DESGLOSE ===")
    log("  Columnas de f116:")
    for r in run(cur, "f116 cols", """
        SELECT c.colname, c.coltype
        FROM syscolumns c, systables t
        WHERE c.tabid = t.tabid AND t.tabname = 'f116'
        ORDER BY c.colno
    """):
        log(f"  {r[0]}")

    for firma in [1, 2]:
        log(f"\n  f116 firma={firma} — muestra 5 filas:")
        for r in run(cur, f"f116 sample {firma}", f"""
            SELECT FIRST 5 * FROM f116 WHERE firma = {firma}
        """):
            log(f"  {list(r)}")

    # 9) Venta diaria — verificar firma
    log("\n=== VENTA DIARIA POR FIRMA ===")
    for r in run(cur, "sbas hoy por firma", """
        SELECT firma, belegart, COUNT(DISTINCT renr) docs,
               COUNT(*) pos, SUM(netwert) net
        FROM sbas
        WHERE redat = TODAY
        GROUP BY firma, belegart
        ORDER BY firma, belegart
    """):
        log(f"  firma={r[0]}  belegart={r[1]}  docs={r[2]}  pos={r[3]}  net={r[4]}")

    conn.close()

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\nListo → {OUTPUT_FILE}")


if __name__ == "__main__":
    main()

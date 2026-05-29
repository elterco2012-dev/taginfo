"""
Script enfocado en la tabla f090 y familia f0xx para TagInfo.
Solo lectura — ninguna modificación a la base de datos.
"""

import pyodbc
from datetime import date, datetime

DSN = "MSPA"
OUTPUT_FILE = "f090_estructura.txt"

# Tablas a inspeccionar
TARGET_TABLES = [
    "f010", "f020", "f030", "f040", "f050",
    "f060", "f070", "f080", "f090", "f100",
    "f110", "f120",
    # también variantes con sufijos
    "f090a", "f090b", "f090p", "f090i",
    # y las de órdenes de producción comunes en sistemas alemanes
    "op", "opkopf", "oppos", "fertkopf", "fertpos",
    "aufkopf", "aufpos", "aukopf", "aupos",
    # pedidos / ventas
    "vkkopf", "vkpos", "vekopf", "vepos",
    "opos", "okopf",
    "sbas", "sbaset",
]


def get_conn():
    return pyodbc.connect(f"DSN={DSN};", autocommit=True)


def coltype_name(coltype):
    types = {
        0: "CHAR", 1: "SMALLINT", 2: "INTEGER", 3: "FLOAT",
        4: "SMALLFLOAT", 5: "DECIMAL", 6: "SERIAL", 7: "DATE",
        8: "MONEY", 10: "DATETIME", 11: "BYTE", 12: "TEXT",
        13: "VARCHAR", 14: "INTERVAL", 15: "NCHAR", 16: "NVARCHAR",
        17: "INT8", 18: "SERIAL8", 40: "LVARCHAR",
    }
    base = coltype & 0xFF
    return types.get(base, f"TYPE({base})")


def table_exists(cursor, tabname):
    cursor.execute(
        f"SELECT COUNT(*) FROM systables WHERE tabname = '{tabname}' AND tabid > 99"
    )
    return cursor.fetchone()[0] > 0


def get_columns(cursor, tabname):
    cursor.execute(
        "SELECT c.colno, c.colname, c.coltype, c.collength "
        "FROM syscolumns c, systables t "
        "WHERE c.tabid = t.tabid "
        f"AND t.tabname = '{tabname}' "
        "ORDER BY c.colno"
    )
    return cursor.fetchall()


def table_count(cursor, tabname):
    try:
        cursor.execute(f"SELECT COUNT(*) FROM {tabname}")
        return cursor.fetchone()[0]
    except Exception:
        return -1


def sample_rows(cursor, tabname, limit=5):
    try:
        cursor.execute(f"SELECT FIRST {limit} * FROM {tabname}")
        return cursor.fetchall(), [d[0] for d in cursor.description]
    except Exception as e:
        return [], []


def all_f_tables(cursor):
    """Lista todas las tablas que empiezan con f0 o f1."""
    cursor.execute(
        "SELECT tabname FROM systables "
        "WHERE tabid > 99 AND tabtype = 'T' "
        "AND (tabname LIKE 'f0%' OR tabname LIKE 'f1%' OR tabname LIKE 'op%' "
        "     OR tabname LIKE 'auf%' OR tabname LIKE 'vk%' OR tabname LIKE 'ok%') "
        "ORDER BY tabname"
    )
    return [r[0] for r in cursor.fetchall()]


def main():
    lines = []
    log = lines.append

    log(f"f090 / TagInfo Explorer — {datetime.now()}")
    log(f"DSN: {DSN}  |  SOLO LECTURA")
    log("=" * 70)

    conn = get_conn()
    cur = conn.cursor()
    log("Conexión OK\n")

    # 1) Mostrar todas las tablas f0x, f1x, op*, auf*, vk*
    all_f = all_f_tables(cur)
    log(f"Tablas f0x/f1x/op*/auf*/vk* encontradas ({len(all_f)}):")
    for t in all_f:
        log(f"  {t}")
    log("")

    # 2) Inspeccionar cada tabla objetivo
    to_inspect = list(dict.fromkeys(TARGET_TABLES + all_f))  # sin duplicados

    for tname in to_inspect:
        if not table_exists(cur, tname):
            continue

        cols = get_columns(cur, tname)
        cnt = table_count(cur, tname)
        rows, headers = sample_rows(cur, tname)

        log(f"\n{'='*60}")
        log(f"TABLA: {tname}  ({cnt} filas)")
        log("COLUMNAS:")
        for c in cols:
            log(f"  {c[1]:<30} {coltype_name(c[2]):<12} len={c[3]}")

        if headers and rows:
            log(f"\nCABECERAS: {headers}")
            log(f"MUESTRA ({len(rows)} filas):")
            for r in rows:
                log(f"  {list(r)}")

    # 3) Buscar tablas con columna 'status' que tenga valores negativos
    log("\n\n--- TABLAS CON COLUMNA 'status' (candidatas a bloqueados) ---")
    cur.execute(
        "SELECT DISTINCT t.tabname "
        "FROM systables t, syscolumns c "
        "WHERE c.tabid = t.tabid "
        "AND t.tabtype = 'T' AND t.tabid > 99 "
        "AND c.colname = 'status' "
        "ORDER BY t.tabname"
    )
    status_tables = [r[0] for r in cur.fetchall()]
    log(f"Tablas con columna 'status': {status_tables}")

    # 4) Buscar tablas con columna de fecha de vencimiento
    log("\n--- TABLAS CON COLUMNA DE VENCIMIENTO/PLAZO ---")
    cur.execute(
        "SELECT DISTINCT t.tabname, c.colname "
        "FROM systables t, syscolumns c "
        "WHERE c.tabid = t.tabid "
        "AND t.tabtype = 'T' AND t.tabid > 99 "
        "AND (c.colname LIKE '%venc%' OR c.colname LIKE '%plazo%' "
        "     OR c.colname LIKE '%liefdat%' OR c.colname LIKE '%wtermin%' "
        "     OR c.colname LIKE '%termin%' OR c.colname LIKE '%fdat%') "
        "ORDER BY t.tabname"
    )
    for r in cur.fetchall():
        log(f"  {r[0]:<30} col: {r[1]}")

    # 5) Buscar tablas con columna de valor/monto
    log("\n--- TABLAS CON COLUMNA DE VALOR/MONTO ---")
    cur.execute(
        "SELECT DISTINCT t.tabname, c.colname "
        "FROM systables t, syscolumns c "
        "WHERE c.tabid = t.tabid "
        "AND t.tabtype = 'T' AND t.tabid > 99 "
        "AND (c.colname LIKE '%wert%' OR c.colname LIKE '%betrag%' "
        "     OR c.colname LIKE '%menge%' OR c.colname LIKE '%preis%' "
        "     OR c.colname LIKE '%valor%' OR c.colname LIKE '%saldo%') "
        "ORDER BY t.tabname"
    )
    for r in cur.fetchall():
        log(f"  {r[0]:<30} col: {r[1]}")

    cur.close()
    conn.close()

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"Listo. Resultado en: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()

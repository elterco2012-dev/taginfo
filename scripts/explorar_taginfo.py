"""
Script de exploración de Informix para la pantalla TagInfo (Daily Info 2 Sales).

Busca las tablas y columnas relacionadas con:
  - Backorders (pedidos vencidos)
  - Bloqueados por límite de crédito
  - Bloqueados por status < -1
  - Pedidos abiertos futuros
  - Órdenes de producción abiertas
  - Remitos/Facturas abiertas
  - Venta diaria

Salida: taginfo_estructura.txt
"""

import pyodbc
import traceback
from datetime import date, datetime

DSN = "MSPA"   # <-- cambiá si tu DSN tiene otro nombre

OUTPUT_FILE = "taginfo_estructura.txt"

CANDIDATE_TABLES = [
    # pedidos / orders
    "orders", "pedidos", "ped", "p010", "p020", "p030",
    # posiciones de pedidos
    "ordpos", "pedpos", "ppos", "p011", "p021",
    # órdenes de producción
    "prodord", "prod", "op", "workor", "worder",
    # remitos / facturas
    "remito", "factura", "invoice", "fac", "rem",
    "f010", "f020", "f030", "f040", "f050",
    # delivery / despacho
    "deliv", "dispatch", "shipm",
    # cliente / crédito
    "kund", "client", "cred",
    # ventas
    "sales", "venta", "vtas",
    # genéricas comunes en Informix MSPA
    "sbas", "vplan", "adrchr",
]

KEYWORDS = [
    "status", "stato", "estado",
    "fecha", "date", "fdate", "ddate",
    "plazo", "due", "venc",
    "valor", "value", "amount", "importe", "monto",
    "orden", "order", "pedido",
    "cliente", "kunden", "cust",
    "bloqueo", "block", "cred",
    "prod", "fabr",
    "remit", "factur", "invoic",
]


def get_conn():
    return pyodbc.connect(f"DSN={DSN};", autocommit=True)


def list_all_tables(cursor):
    cursor.execute("""
        SELECT tabname, tabtype
        FROM systables
        WHERE tabtype IN ('T', 'V')
          AND tabid > 99
        ORDER BY tabname
    """)
    return cursor.fetchall()


def get_columns(cursor, tabname):
    cursor.execute("""
        SELECT c.colname, c.coltype, c.collength
        FROM syscolumns c
        JOIN systables t ON t.tabid = c.tabid
        WHERE t.tabname = ?
        ORDER BY c.colno
    """, tabname)
    return cursor.fetchall()


def sample_rows(cursor, tabname, limit=3):
    try:
        cursor.execute(f"SELECT FIRST {limit} * FROM {tabname}")
        return cursor.fetchall()
    except Exception:
        return []


def table_count(cursor, tabname):
    try:
        cursor.execute(f"SELECT COUNT(*) FROM {tabname}")
        row = cursor.fetchone()
        return row[0] if row else 0
    except Exception:
        return -1


def coltype_name(coltype):
    types = {
        0: "CHAR", 1: "SMALLINT", 2: "INTEGER", 3: "FLOAT",
        4: "SMALLFLOAT", 5: "DECIMAL", 6: "SERIAL", 7: "DATE",
        8: "MONEY", 10: "DATETIME", 11: "BYTE", 12: "TEXT",
        13: "VARCHAR", 14: "INTERVAL", 15: "NCHAR", 16: "NVARCHAR",
        17: "INT8", 18: "SERIAL8", 40: "LVARCHAR",
    }
    base = coltype & 0xFF
    nullable = " NULL" if coltype > 255 else " NOT NULL"
    return types.get(base, f"TYPE({base})") + nullable


def matches_keywords(tabname, colnames):
    combined = (tabname + " " + " ".join(colnames)).lower()
    return any(kw in combined for kw in KEYWORDS)


def main():
    lines = []
    log = lines.append

    log(f"TagInfo Explorer — {datetime.now()}")
    log(f"DSN: {DSN}")
    log("=" * 70)

    try:
        conn = get_conn()
        cur = conn.cursor()
        log("Conexión OK\n")
    except Exception as e:
        log(f"ERROR DE CONEXIÓN: {e}")
        save(lines)
        return

    # 1) Listar todas las tablas
    all_tables = list_all_tables(cur)
    log(f"Total tablas/vistas en systables: {len(all_tables)}\n")

    # 2) Tablas candidatas por nombre
    log("--- TABLAS CANDIDATAS POR NOMBRE ---")
    found_candidates = []
    for row in all_tables:
        tname = row[0].lower()
        for cand in CANDIDATE_TABLES:
            if cand in tname:
                found_candidates.append(row[0])
                break

    log(f"Encontradas {len(found_candidates)} tablas candidatas por nombre:")
    for t in found_candidates:
        log(f"  {t}")
    log("")

    # 3) Para cada candidata, mostrar columnas, conteo y muestra
    interesting = []

    for tname in found_candidates:
        cols = get_columns(cur, tname)
        colnames = [c[0] for c in cols]
        cnt = table_count(cur, tname)

        if not matches_keywords(tname, colnames):
            continue

        interesting.append(tname)
        log(f"\n{'='*60}")
        log(f"TABLA: {tname}  ({cnt} filas)")
        log(f"COLUMNAS:")
        for c in cols:
            log(f"  {c[0]:<30} {coltype_name(c[1]):<20} len={c[2]}")

        if cnt > 0:
            rows = sample_rows(cur, tname)
            log(f"MUESTRA ({len(rows)} filas):")
            for r in rows:
                log(f"  {list(r)}")

    # 4) Búsqueda ampliada: tablas NO candidatas pero con columnas clave
    log("\n\n--- BÚSQUEDA AMPLIADA (tablas con columnas clave) ---")
    extra = []
    for row in all_tables:
        tname = row[0]
        if tname in found_candidates:
            continue
        try:
            cols = get_columns(cur, tname)
            colnames = [c[0].lower() for c in cols]
            # buscar columnas que sugieran pedidos/órdenes
            hits = [c for c in colnames if any(kw in c for kw in
                    ["status", "stato", "venc", "due_date", "plazo",
                     "order", "pedido", "prod_ord", "remit", "factur"])]
            if len(hits) >= 2:
                extra.append((tname, hits, cols))
        except Exception:
            pass

    log(f"Tablas adicionales con columnas clave: {len(extra)}")
    for tname, hits, cols in extra:
        cnt = table_count(cur, tname)
        log(f"\n{'='*60}")
        log(f"TABLA: {tname}  ({cnt} filas)  hits={hits}")
        log("COLUMNAS:")
        for c in cols:
            log(f"  {c[0]:<30} {coltype_name(c[1]):<20} len={c[2]}")

    # 5) Intentar queries directas similares a TagInfo
    log("\n\n--- PRUEBAS DE QUERIES TAGINFO ---")
    today = date.today()
    test_queries = [
        ("Todas las tablas con 'status' y 'fecha'", """
            SELECT t.tabname
            FROM systables t
            JOIN syscolumns c1 ON c1.tabid = t.tabid AND c1.colname LIKE '%status%'
            JOIN syscolumns c2 ON c2.tabid = t.tabid AND c2.colname LIKE '%fecha%'
            WHERE t.tabtype = 'T' AND t.tabid > 99
        """),
        ("Todas las tablas con 'valor' o 'amount' o 'importe'", """
            SELECT DISTINCT t.tabname
            FROM systables t
            JOIN syscolumns c ON c.tabid = t.tabid
            WHERE t.tabtype = 'T' AND t.tabid > 99
              AND (c.colname LIKE '%valor%' OR c.colname LIKE '%amount%' OR c.colname LIKE '%importe%')
        """),
    ]

    for desc, q in test_queries:
        log(f"\n{desc}:")
        try:
            cur.execute(q)
            rows = cur.fetchall()
            for r in rows:
                log(f"  {r[0]}")
        except Exception as e:
            log(f"  ERROR: {e}")

    cur.close()
    conn.close()

    save(lines)
    print(f"Listo. Resultado en: {OUTPUT_FILE}")


def save(lines):
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    main()

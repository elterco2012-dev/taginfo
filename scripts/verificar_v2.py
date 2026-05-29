"""
TagInfo Query Verification v2 — queries corregidas.
SOLO LECTURA.
"""

import pyodbc
from datetime import date, datetime

DSN = "MSPA"
OUTPUT_FILE = "taginfo_v2.txt"
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

    log(f"TagInfo v2 — {datetime.now()}")
    log(f"DSN: {DSN}  |  Fecha: {today}  |  SOLO LECTURA")
    log("=" * 70)

    conn = get_conn()
    cur = conn.cursor()
    log("Conexión OK\n")

    # ============================================================
    # DIAGNÓSTICO PREVIO
    # ============================================================

    log("=== DIAGNÓSTICO f090.aufart (tipo de orden) ===")
    for r in run(cur, "aufart", f"""
        SELECT aufart, aufkstat, COUNT(*) cnt
        FROM f090 WHERE firma = {FIRMA}
        GROUP BY aufart, aufkstat
        ORDER BY aufart, aufkstat
    """):
        log(f"  aufart='{r[0]}'  aufkstat={r[1]}  count={r[2]}")

    log("\n=== POSICIONES ABIERTAS (posstat=0, kzerl='0') ===")
    for r in run(cur, "pos abiertas por aufart", f"""
        SELECT h.aufart, COUNT(DISTINCT h.auftrag) ordenes,
               COUNT(*) posiciones, SUM(p.poswert) valor
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND p.posstat = 0
          AND p.kzerl = '0'
        GROUP BY h.aufart
        ORDER BY h.aufart
    """):
        log(f"  aufart='{r[0]}'  ordenes={r[1]}  pos={r[2]}  valor={r[3]}")

    log("\n=== POSICIONES ABIERTAS por termin vs hoy ===")
    for r in run(cur, "abiertas termin dist", f"""
        SELECT CASE WHEN p.termin < TODAY THEN 'VENCIDO'
                    WHEN p.termin = TODAY THEN 'HOY'
                    ELSE 'FUTURO' END as tipo,
               COUNT(DISTINCT h.auftrag) ordenes,
               COUNT(*) posiciones, SUM(p.poswert) valor
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND p.posstat = 0
          AND p.kzerl = '0'
          AND h.aufkstat >= 0
        GROUP BY 1
        ORDER BY 1
    """):
        log(f"  tipo={r[0]}  ordenes={r[1]}  pos={r[2]}  valor={r[3]}")

    # ============================================================
    # BLOQUEO POR CRÉDITO — buscar en tabla kund
    # ============================================================
    log("\n=== BÚSQUEDA DE BLOQUEO POR CRÉDITO EN kund ===")
    for r in run(cur, "kund columnas con 'sperr' o 'limit' o 'kred'", """
        SELECT c.colname
        FROM syscolumns c, systables t
        WHERE c.tabid = t.tabid AND t.tabname = 'kund'
          AND (c.colname LIKE '%sperr%' OR c.colname LIKE '%limit%'
               OR c.colname LIKE '%kred%' OR c.colname LIKE '%block%'
               OR c.colname LIKE '%lock%')
        ORDER BY c.colno
    """):
        log(f"  kund.{r[0]}")

    log("\nValores de columnas de bloqueo en kund:")
    # intentar kzsperre
    for r in run(cur, "kund.kzsperre", f"""
        SELECT kzsperre, COUNT(*) cnt
        FROM kund WHERE firma = {FIRMA}
        GROUP BY kzsperre ORDER BY kzsperre
    """):
        log(f"  kzsperre={r[0]}  count={r[1]}")

    # Pedidos de clientes con kzsperre > 0
    log("\nPedidos de clientes con kzsperre > 0 (crédito):")
    for r in run(cur, "pedidos kund bloqueados", f"""
        SELECT COUNT(DISTINCT h.auftrag) ordenes,
               COUNT(*) posiciones, SUM(p.poswert) valor
        FROM f090 h, f092 p, kund k
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA} AND k.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND h.kdnr = k.kdnr
          AND k.kzsperre > 0
          AND p.posstat = 0
          AND p.kzerl = '0'
    """):
        log(f"  ordenes={r[0]}  pos={r[1]}  valor={r[2]}")

    # Alternativa: aufkstat especifico para bloqueo credito
    log("\naufkstat candidatos para bloqueo credito (aufkstat=2 o negativo):")
    for r in run(cur, "aufkstat bloq", f"""
        SELECT COUNT(DISTINCT h.auftrag) ordenes,
               COUNT(*) posiciones, SUM(p.poswert) valor
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND h.aufkstat = 2
          AND p.posstat = 0
          AND p.kzerl = '0'
    """):
        log(f"  aufkstat=2: ordenes={r[0]}  pos={r[1]}  valor={r[2]}")

    # ============================================================
    # QUERIES TAGINFO CORREGIDAS
    # ============================================================
    log("\n\n=== QUERIES TAGINFO CORREGIDAS ===\n")
    log(f"Fecha: {today}  |  Filtros: posstat=0, kzerl='0'\n")

    # 1. BACKORDERS
    log("--- 1. Backorders (Plazos viejos) ---")
    for r in run(cur, "backorders v2", f"""
        SELECT COUNT(DISTINCT h.auftrag) ordenes,
               COUNT(*) posiciones, SUM(p.poswert) valor
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND p.termin < TODAY
          AND p.posstat = 0
          AND p.kzerl = '0'
          AND h.aufkstat = 0
    """):
        log(f"  (aufkstat=0) ordenes={r[0]}  pos={r[1]}  valor={r[2]}")

    # 2. BLOQUEADOS POR CRÉDITO — probar varias combinaciones
    log("\n--- 2. Bloqueados por Límite de crédito ---")
    for r in run(cur, "bloq aufkstat<0", f"""
        SELECT COUNT(DISTINCT h.auftrag) ordenes,
               COUNT(*) posiciones, SUM(p.poswert) valor
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND h.aufkstat < 0
          AND p.posstat = 0
          AND p.kzerl = '0'
    """):
        log(f"  aufkstat<0: ordenes={r[0]}  pos={r[1]}  valor={r[2]}")

    # 3. BLOQUEADO STATUS < -1
    log("\n--- 3. Bloqueado (Status < -1) ---")
    for r in run(cur, "bloq <-1", f"""
        SELECT COUNT(DISTINCT h.auftrag) ordenes,
               COUNT(*) posiciones, SUM(p.poswert) valor
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND h.aufkstat < -1
          AND p.posstat = 0
          AND p.kzerl = '0'
    """):
        log(f"  ordenes={r[0]}  pos={r[1]}  valor={r[2]}")

    # 4. PEDIDOS ABIERTOS FUTUROS
    log("\n--- 4. Pedidos Abiertos (Plazos futuros) ---")
    for r in run(cur, "futuros v2", f"""
        SELECT COUNT(DISTINCT h.auftrag) ordenes,
               COUNT(*) posiciones, SUM(p.poswert) valor
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND p.termin >= TODAY
          AND p.posstat = 0
          AND p.kzerl = '0'
          AND h.aufkstat = 0
    """):
        log(f"  (aufkstat=0) ordenes={r[0]}  pos={r[1]}  valor={r[2]}")

    # 5. ÓRDENES DE PRODUCCIÓN — buscar en f090 por aufart
    log("\n--- 5. Ordenes de produccion (f090 por aufart) ---")
    for aufart in ["F", "P", "M", "A", "B", "C", "D", "E", "G", "H", "I", "J", "K"]:
        rows = run(cur, f"aufart={aufart}", f"""
            SELECT COUNT(DISTINCT h.auftrag) ordenes,
                   COUNT(*) posiciones, SUM(p.poswert) valor
            FROM f090 h, f092 p
            WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
              AND h.auftrag = p.auftrag
              AND h.aufart = '{aufart}'
              AND p.posstat = 0
              AND p.kzerl = '0'
        """)
        for r in rows:
            if r[0] and r[0] > 0:
                log(f"  aufart='{aufart}': ordenes={r[0]}  pos={r[1]}  valor={r[2]}")

    # 6. REMITOS/FACTURAS ABIERTAS
    log("\n--- 6. Remitos/Facturas abiertas ---")

    # f116 breakdown
    log("  f116 (remitos/facturas abiertas):")
    for r in run(cur, "f116 detalle", f"""
        SELECT COUNT(DISTINCT auftrag) ordenes,
               COUNT(*) posiciones, SUM(aufwert) valor
        FROM f116
        WHERE firma = {FIRMA}
    """):
        log(f"  f116: ordenes={r[0]}  pos={r[1]}  valor={r[2]}")

    # f104 + f106 con distintos liefstat
    for liefstat in range(0, 5):
        rows = run(cur, f"f106 liefstat={liefstat}", f"""
            SELECT COUNT(DISTINCT liefnr) liefs,
                   COUNT(DISTINCT auftrag) ordenes,
                   SUM(liefwe) valor
            FROM f106
            WHERE firma = {FIRMA} AND liefstat = {liefstat}
        """)
        for r in rows:
            if r[0] and r[0] > 0:
                log(f"  f106 liefstat={liefstat}: liefs={r[0]}  ordenes={r[1]}  valor={r[2]}")

    # 7. VENTA DIARIA
    log("\n--- 7. Venta diaria ---")
    log("  sbas por belegart hoy (TODOS):")
    for r in run(cur, "sbas hoy todo", f"""
        SELECT belegart, COUNT(DISTINCT renr) docs,
               COUNT(*) pos, SUM(netwert) netwert, SUM(brtwert) brtwert
        FROM sbas
        WHERE firma = {FIRMA} AND redat = TODAY
        GROUP BY belegart ORDER BY belegart
    """):
        log(f"  belegart={r[0]}  docs={r[1]}  pos={r[2]}  net={r[3]}  brt={r[4]}")

    # belegart=11
    log("  Venta diaria belegart=11:")
    for r in run(cur, "venta belegart=11", f"""
        SELECT COUNT(DISTINCT renr) docs, COUNT(*) pos, SUM(netwert) netwert
        FROM sbas
        WHERE firma = {FIRMA} AND redat = TODAY AND belegart = 11
    """):
        log(f"  docs={r[0]}  pos={r[1]}  netwert={r[2]}")

    conn.close()

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\nListo → {OUTPUT_FILE}")


if __name__ == "__main__":
    main()

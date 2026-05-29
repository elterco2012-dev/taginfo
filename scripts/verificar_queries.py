"""
Verificación de queries TagInfo vs pantalla real.
SOLO LECTURA — sin modificaciones.

Corre cada query y muestra los resultados para comparar con la pantalla.
"""

import pyodbc
from datetime import date, datetime

DSN = "MSPA"
OUTPUT_FILE = "taginfo_queries.txt"

# Ajustá FIRMA si tu empresa tiene otro número (probamos 1)
FIRMA = 1


def get_conn():
    return pyodbc.connect(f"DSN={DSN};", autocommit=True)


def run(cursor, label, sql, params=None):
    print(f"  {label}...")
    try:
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
        rows = cursor.fetchall()
        return rows if rows else []
    except Exception as e:
        print(f"    SQL ERROR: {e}")
        return []


def first(rows, default=(None, None, None)):
    return rows[0] if rows else default


def main():
    lines = []
    log = lines.append

    today = date.today()
    log(f"TagInfo Query Verification — {datetime.now()}")
    log(f"DSN: {DSN}  |  Fecha: {today}  |  SOLO LECTURA")
    log("=" * 70)

    conn = get_conn()
    cur = conn.cursor()
    log("Conexión OK\n")

    # --- Primero, valores únicos de aufkstat y kzlock para entender los rangos ---
    log("=== DIAGNÓSTICO: valores de aufkstat y kzlock en f090 ===\n")

    rows = run(cur, "aufkstat valores", f"""
        SELECT aufkstat, COUNT(*) cnt
        FROM f090
        WHERE firma = {FIRMA}
        GROUP BY aufkstat
        ORDER BY aufkstat
    """)
    log("f090.aufkstat  (status de cabecera de pedido):")
    for r in rows:
        log(f"  aufkstat={r[0]}  count={r[1]}")

    rows = run(cur, "kzlock valores", f"""
        SELECT kzlock, COUNT(*) cnt
        FROM f090
        WHERE firma = {FIRMA}
        GROUP BY kzlock
        ORDER BY kzlock
    """)
    log("\nf090.kzlock  (indicador de bloqueo):")
    for r in rows:
        log(f"  kzlock={r[0]}  count={r[1]}")

    rows = run(cur, "posstat valores", f"""
        SELECT posstat, COUNT(*) cnt
        FROM f092
        WHERE firma = {FIRMA}
        GROUP BY posstat
        ORDER BY posstat
    """)
    log("\nf092.posstat  (status de posición):")
    for r in rows:
        log(f"  posstat={r[0]}  count={r[1]}")

    rows = run(cur, "kzerl valores", f"""
        SELECT kzerl, COUNT(*) cnt
        FROM f092
        WHERE firma = {FIRMA}
        GROUP BY kzerl
        ORDER BY kzerl
    """)
    log("\nf092.kzerl  (completado):")
    for r in rows:
        log(f"  kzerl='{r[0]}'  count={r[1]}")

    # --- QUERIES TAGINFO ---
    log("\n\n=== QUERIES TAGINFO ===\n")
    log(f"Fecha de corte: {today}\n")

    # 1. BACKORDERS (Plazos viejos) — pedidos vencidos no entregados
    log("--- 1. Backorders (Plazos viejos) ---")
    log("    Pedidos con termin < hoy, no completados, sin bloqueo")
    rows = run(cur, "backorders", f"""
        SELECT COUNT(DISTINCT h.auftrag) nro_ordenes,
               COUNT(*) nro_pos,
               SUM(p.poswert) valor
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA}
          AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND p.termin < TODAY
          AND p.kzerl <> 'J'
          AND h.aufkstat >= 0
          AND h.kzlock = 0
    """)
    for r in rows:
        log(f"  Ordenes={r[0]}  Posiciones={r[1]}  Valor={r[2]}")

    # 2. BLOQUEADOS POR LÍMITE DE CRÉDITO
    log("\n--- 2. Bloqueados por Límite de crédito ---")
    log("    Pedidos con kzlock > 0, posiciones abiertas")
    rows = run(cur, "bloq credito", f"""
        SELECT COUNT(DISTINCT h.auftrag) nro_ordenes,
               COUNT(*) nro_pos,
               SUM(p.poswert) valor
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA}
          AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND h.kzlock > 0
          AND p.kzerl <> 'J'
    """)
    for r in rows:
        log(f"  Ordenes={r[0]}  Posiciones={r[1]}  Valor={r[2]}")

    # Alternativa: kzlock con bitmask (a veces es bitmask)
    rows = run(cur, "bloq credito alt (kzlock & 1)", f"""
        SELECT COUNT(DISTINCT h.auftrag) nro_ordenes,
               COUNT(*) nro_pos,
               SUM(p.poswert) valor
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA}
          AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND (h.kzlock > 0 OR h.aufkstat < 0)
          AND p.kzerl <> 'J'
    """)
    r = first(rows)
    log(f"  ALT (kzlock>0 OR aufkstat<0): Ordenes={r[0]}  Pos={r[1]}  Valor={r[2]}")

    # 3. BLOQUEADO (Status < -1)
    log("\n--- 3. Bloqueado (Status < -1) ---")
    rows = run(cur, "bloq status", f"""
        SELECT COUNT(DISTINCT h.auftrag) nro_ordenes,
               COUNT(*) nro_pos,
               SUM(p.poswert) valor
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA}
          AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND h.aufkstat < -1
          AND p.kzerl <> 'J'
    """)
    for r in rows:
        log(f"  Ordenes={r[0]}  Posiciones={r[1]}  Valor={r[2]}")

    # 4. PEDIDOS ABIERTOS (Plazos futuros)
    log("\n--- 4. Pedidos Abiertos (Plazos futuros) ---")
    log("    Pedidos con termin >= hoy, no completados, sin bloqueo")
    rows = run(cur, "pedidos futuros", f"""
        SELECT COUNT(DISTINCT h.auftrag) nro_ordenes,
               COUNT(*) nro_pos,
               SUM(p.poswert) valor
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA}
          AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND p.termin >= TODAY
          AND p.kzerl <> 'J'
          AND h.aufkstat >= 0
          AND h.kzlock = 0
    """)
    for r in rows:
        log(f"  Ordenes={r[0]}  Posiciones={r[1]}  Valor={r[2]}")

    # 5. ÓRDENES DE PRODUCCIÓN ABIERTAS (f096)
    log("\n--- 5. Ordenes de produccion abiertas (f096) ---")
    rows = run(cur, "op abiertas - posstat", f"""
        SELECT posstat, COUNT(*) cnt
        FROM f096
        WHERE firma = {FIRMA}
        GROUP BY posstat
        ORDER BY posstat
    """)
    log("  f096 posstat valores:")
    for r in rows:
        log(f"    posstat={r[0]}  count={r[1]}")

    rows = run(cur, "op sperrkz", f"""
        SELECT sperrkz, COUNT(*) cnt
        FROM f096
        WHERE firma = {FIRMA}
        GROUP BY sperrkz
    """)
    log("  f096 sperrkz valores:")
    for r in rows:
        log(f"    sperrkz={r[0]}  count={r[1]}")

    # intento total OP abiertas
    rows = run(cur, "op total abiertas", f"""
        SELECT COUNT(DISTINCT modinr) nro_ordenes,
               COUNT(*) nro_pos,
               SUM(dek) valor
        FROM f096
        WHERE firma = {FIRMA}
          AND posstat >= 0
          AND sperrkz = 0
    """)
    for r in rows:
        log(f"  OP abiertas: Ordenes={r[0]}  Posiciones={r[1]}  Valor={r[2]}")

    # 6. REMITOS / FACTURAS ABIERTAS
    log("\n--- 6. Remitos/Facturas abiertas ---")

    # f104 = lieferschein VK tipo 1
    rows = run(cur, "f104 liefstat", f"""
        SELECT liefstat, COUNT(*) cnt
        FROM f104
        WHERE firma = {FIRMA}
        GROUP BY liefstat
    """)
    log("  f104.liefstat:")
    for r in rows:
        log(f"    liefstat={r[0]}  count={r[1]}")

    # f106 = lieferschein VK tipo 2 (con sperrkz, belegart)
    rows = run(cur, "f106 liefstat", f"""
        SELECT liefstat, COUNT(*) cnt
        FROM f106
        WHERE firma = {FIRMA}
        GROUP BY liefstat
    """)
    log("  f106.liefstat:")
    for r in rows:
        log(f"    liefstat={r[0]}  count={r[1]}")

    # total remitos abiertos (f104 + f106 con liefstat < 9 o similar)
    rows = run(cur, "remitos f104 abiertos", f"""
        SELECT COUNT(DISTINCT liefnr) nro_ordenes,
               COUNT(DISTINCT auftrag) nro_auftr,
               SUM(liefwe) valor
        FROM f104
        WHERE firma = {FIRMA}
          AND liefstat < 9
    """)
    for r in rows:
        log(f"  f104 abiertos: liefnr={r[0]}  auftrag={r[1]}  Valor={r[2]}")

    rows = run(cur, "remitos f106 abiertos", f"""
        SELECT COUNT(DISTINCT liefnr) nro_ordenes,
               COUNT(DISTINCT auftrag) nro_auftr,
               SUM(liefwe) valor
        FROM f106
        WHERE firma = {FIRMA}
          AND liefstat < 9
    """)
    for r in rows:
        log(f"  f106 abiertos: liefnr={r[0]}  auftrag={r[1]}  Valor={r[2]}")

    # f116 = otro tipo (sin liefnr, tiene kdnr + auftrag)
    rows = run(cur, "f116 total", f"""
        SELECT COUNT(DISTINCT auftrag) nro_ordenes,
               COUNT(*) nro_pos,
               SUM(aufwert) valor
        FROM f116
        WHERE firma = {FIRMA}
    """)
    for r in rows:
        log(f"  f116 total: Ordenes={r[0]}  Posiciones={r[1]}  Valor={r[2]}")

    # 7. VENTA DIARIA
    log("\n--- 7. Venta diaria ---")
    log(f"  Buscando ventas de hoy ({today})")

    rows = run(cur, "sbas hoy belegart", f"""
        SELECT belegart, COUNT(DISTINCT renr) cnt_doc, SUM(netwert) netwert
        FROM sbas
        WHERE firma = {FIRMA}
          AND redat = TODAY
        GROUP BY belegart
        ORDER BY belegart
    """)
    log("  sbas hoy por belegart (1=factura normalmente):")
    for r in rows:
        log(f"    belegart={r[0]}  docs={r[1]}  netwert={r[2]}")

    # Total venta diaria (belegart=1 suele ser factura)
    rows = run(cur, "venta diaria", f"""
        SELECT COUNT(DISTINCT renr) nro_facturas,
               COUNT(*) nro_pos,
               SUM(netwert) valor
        FROM sbas
        WHERE firma = {FIRMA}
          AND redat = TODAY
          AND belegart = 1
    """)
    for r in rows:
        log(f"  Venta hoy: Facturas={r[0]}  Posiciones={r[1]}  Valor={r[2]}")

    cur.close()
    conn.close()

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"\nListo. Resultado en: {OUTPUT_FILE}")
    print("Comparalo con la pantalla TagInfo para validar los números.")


if __name__ == "__main__":
    main()

"""
TagInfo v4 — sperrgrund, produccion, categorias mutuamente exclusivas.
SOLO LECTURA.
"""

import pyodbc
from datetime import date, datetime

DSN = "MSPA"
OUTPUT_FILE = "taginfo_v4.txt"
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

    log(f"TagInfo v4 — {datetime.now()}")
    log(f"DSN: {DSN}  |  Fecha: {today}  |  SOLO LECTURA")
    log("=" * 70)

    conn = get_conn()
    cur = conn.cursor()
    log("Conexión OK\n")

    # ============================================================
    # 1. kund.sperrgrund — bloqueo de crédito
    # ============================================================
    log("=== kund.sperrgrund (motivo bloqueo) ===")
    for r in run(cur, "sperrgrund vals", f"""
        SELECT sperrgrund, COUNT(*) cnt
        FROM kund WHERE firma = {FIRMA}
        GROUP BY sperrgrund ORDER BY sperrgrund
    """):
        log(f"  sperrgrund={r[0]}  count={r[1]}")

    log("\nPedidos de clientes con sperrgrund > 0 (crédito bloqueado):")
    for r in run(cur, "bloq credito sperrgrund", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords,
               COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p, kund k
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA} AND k.firma = {FIRMA}
          AND h.auftrag = p.auftrag AND h.kdnr = k.kdnr
          AND k.sperrgrund > 0
          AND p.posstat = 0 AND p.kzerl = '0'
    """):
        log(f"  ords={r[0]}  pos={r[1]}  val={r[2]}")

    log("\nDesglose sperrgrund por valor (distintos motivos):")
    for r in run(cur, "sperrgrund breakdown", f"""
        SELECT k.sperrgrund,
               COUNT(DISTINCT h.auftrag) ords,
               COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p, kund k
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA} AND k.firma = {FIRMA}
          AND h.auftrag = p.auftrag AND h.kdnr = k.kdnr
          AND k.sperrgrund > 0
          AND p.posstat = 0 AND p.kzerl = '0'
        GROUP BY k.sperrgrund
        ORDER BY k.sperrgrund
    """):
        log(f"  sperrgrund={r[0]}  ords={r[1]}  pos={r[2]}  val={r[3]}")

    # ============================================================
    # 2. CATEGORIAS MUTUAMENTE EXCLUSIVAS (como la pantalla)
    # ============================================================
    log("\n\n=== QUERIES MUTUAMENTE EXCLUSIVAS ===\n")

    # A. Bloqueado Status < -1  (prioridad 1)
    log("--- A. Bloqueado (Status < -1) ---")
    for r in run(cur, "bloq status", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords,
               COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND h.aufkstat < -1
          AND p.posstat = 0 AND p.kzerl = '0'
    """):
        log(f"  ords={r[0]}  pos={r[1]}  val={r[2]}")

    # B. Bloqueado por crédito (sperrgrund > 0, no status<-1)
    log("\n--- B. Bloqueados por Limite credito (sperrgrund>0, aufkstat>=-1) ---")
    for r in run(cur, "bloq credito excl", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords,
               COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p, kund k
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA} AND k.firma = {FIRMA}
          AND h.auftrag = p.auftrag AND h.kdnr = k.kdnr
          AND k.sperrgrund > 0
          AND h.aufkstat >= -1
          AND p.posstat = 0 AND p.kzerl = '0'
    """):
        log(f"  ords={r[0]}  pos={r[1]}  val={r[2]}")

    # C. Backorders (termin<hoy, sin bloqueos, aufkstat=0)
    log("\n--- C. Backorders (vencidos, sin bloqueo, aufkstat=0) ---")
    for r in run(cur, "backorders excl", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords,
               COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p, kund k
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA} AND k.firma = {FIRMA}
          AND h.auftrag = p.auftrag AND h.kdnr = k.kdnr
          AND p.termin < TODAY
          AND h.aufkstat = 0
          AND k.sperrgrund = 0
          AND p.posstat = 0 AND p.kzerl = '0'
    """):
        log(f"  ords={r[0]}  pos={r[1]}  val={r[2]}")

    # D. Pedidos futuros (termin>=hoy, sin bloqueos, aufkstat=0)
    log("\n--- D. Pedidos futuros (termin>=hoy, sin bloqueo, aufkstat=0) ---")
    for r in run(cur, "futuros excl", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords,
               COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p, kund k
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA} AND k.firma = {FIRMA}
          AND h.auftrag = p.auftrag AND h.kdnr = k.kdnr
          AND p.termin >= TODAY
          AND h.aufkstat = 0
          AND k.sperrgrund = 0
          AND p.posstat = 0 AND p.kzerl = '0'
    """):
        log(f"  ords={r[0]}  pos={r[1]}  val={r[2]}")

    # ============================================================
    # 3. TABLAS DE PRODUCCION
    # ============================================================
    log("\n\n=== TABLAS DE PRODUCCION ===")

    prod_tables = ["aklmanuk", "aklmanup", "aksmanuk", "aksmanup", "hmsmanuk", "hmsmanup"]

    for tname in prod_tables:
        log(f"\n--- {tname} ---")
        cols = run(cur, f"{tname} cols", f"""
            SELECT c.colno, c.colname, c.coltype, c.collength
            FROM syscolumns c, systables t
            WHERE c.tabid = t.tabid AND t.tabname = '{tname}'
            ORDER BY c.colno
        """)
        for c in cols:
            log(f"  [{c[0]}] {c[1]}")

        cnt = run(cur, f"{tname} count", f"SELECT COUNT(*) FROM {tname}")
        if cnt:
            log(f"  FILAS: {cnt[0][0]}")

        # muestra si tiene filas
        if cnt and cnt[0][0] > 0:
            sample = run(cur, f"{tname} sample", f"""
                SELECT t.colname
                FROM syscolumns t, systables s
                WHERE t.tabid = s.tabid AND s.tabname = '{tname}'
                ORDER BY t.colno
            """)
            colnames = [r[0] for r in sample]
            log(f"  Columnas: {colnames}")

    # ============================================================
    # 4. REMITOS: explorar f116 directamente
    # ============================================================
    log("\n\n=== f116 — EXPLORACIÓN DIRECTA ===")
    cols = run(cur, "f116 cols directo", """
        SELECT c.colno, c.colname
        FROM syscolumns c, systables t
        WHERE c.tabid = t.tabid AND t.tabname = 'f116'
        ORDER BY c.colno
    """)
    for c in cols:
        log(f"  [{c[0]}] {c[1]}")

    cnt = run(cur, "f116 count", f"SELECT COUNT(*) FROM f116 WHERE firma = {FIRMA}")
    if cnt:
        log(f"  FILAS firma={FIRMA}: {cnt[0][0]}")

    # Muestra columnas y primeras filas (sin SELECT *)
    if cols and cnt and cnt[0][0] > 0:
        col_list = ", ".join([c[1] for c in cols[:10]])  # primeras 10 cols
        for r in run(cur, "f116 sample cols", f"""
            SELECT FIRST 3 {col_list} FROM f116 WHERE firma = {FIRMA}
        """):
            log(f"  {list(r)}")

    # ============================================================
    # 5. aufkstat=2 — ¿qué significa?
    # ============================================================
    log("\n\n=== aufkstat=2 — diagnóstico ===")
    log("Ordenes con aufkstat=2 y su sperrgrund en kund:")
    for r in run(cur, "aufkstat2 sperrgrund", f"""
        SELECT k.sperrgrund, COUNT(DISTINCT h.auftrag) ords
        FROM f090 h, kund k
        WHERE h.firma = {FIRMA} AND k.firma = {FIRMA}
          AND h.kdnr = k.kdnr
          AND h.aufkstat = 2
        GROUP BY k.sperrgrund
        ORDER BY k.sperrgrund
    """):
        log(f"  sperrgrund={r[0]}  ords={r[1]}")

    conn.close()

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\nListo → {OUTPUT_FILE}")


if __name__ == "__main__":
    main()

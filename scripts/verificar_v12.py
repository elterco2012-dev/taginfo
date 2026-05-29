"""
TagInfo v12 — kund.sperrgrund bloqueados, sb104 sin invoice = remitos, pauf exacto.
SOLO LECTURA.
"""

import pyodbc
from datetime import date, datetime

DSN = "MSPA"
OUTPUT_FILE = "taginfo_v12.txt"
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

    log(f"TagInfo v12 — {datetime.now()}")
    log(f"DSN: {DSN}  |  Fecha: {today}  |  SOLO LECTURA")
    log("=" * 70)

    conn = get_conn()
    cur = conn.cursor()
    log("Conexión OK\n")

    # ============================================================
    # 1. kund.sperrgrund — distribución (CHAR field)
    # ============================================================
    log("=== kund SPERRGRUND DISTRIBUCIÓN ===")
    # Count nulls
    for r in run(cur, "kund sperrgrund null", f"""
        SELECT COUNT(*) cnt FROM kund
        WHERE firma = {FIRMA} AND sperrgrund IS NULL
    """):
        log(f"  sperrgrund IS NULL: {r[0]}")

    # Count empty/spaces
    for r in run(cur, "kund sperrgrund vacio", f"""
        SELECT COUNT(*) cnt FROM kund
        WHERE firma = {FIRMA} AND TRIM(sperrgrund) = ''
    """):
        log(f"  sperrgrund TRIM='': {r[0]}")

    # Count non-empty (blocked)
    for r in run(cur, "kund sperrgrund nonempty", f"""
        SELECT COUNT(*) cnt FROM kund
        WHERE firma = {FIRMA} AND sperrgrund IS NOT NULL AND TRIM(sperrgrund) <> ''
    """):
        log(f"  sperrgrund non-empty (bloqueados): {r[0]}")

    # Distinct values non-empty
    for r in run(cur, "kund sperrgrund values", f"""
        SELECT TRIM(sperrgrund) sg, COUNT(*) cnt FROM kund
        WHERE firma = {FIRMA} AND sperrgrund IS NOT NULL AND TRIM(sperrgrund) <> ''
        GROUP BY TRIM(sperrgrund) ORDER BY cnt DESC
    """):
        log(f"  sperrgrund='{r[0]}'  cnt={r[1]}")

    # ============================================================
    # 2. BLOQUEADOS — ordenes de clientes con sperrgrund
    # ============================================================
    log("\n=== BLOQUEADOS via kund.sperrgrund ===")

    # Bloqueados = aufkstat=0 + cliente con sperrgrund
    for r in run(cur, "bloq sperrgrund orders", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p, kund k
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA} AND k.firma = {FIRMA}
          AND h.auftrag = p.auftrag AND h.kdnr = k.kdnr
          AND h.aufkstat = 0
          AND p.posstat = 0 AND p.kzerl = '0'
          AND k.sperrgrund IS NOT NULL AND TRIM(k.sperrgrund) <> ''
    """):
        log(f"  bloqueados (sperrgrund): ords={r[0]}  pos={r[1]}  val={r[2]}")

    # Backorders = aufkstat=0 + cliente SIN sperrgrund
    for r in run(cur, "back sin sperrgrund orders", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p, kund k
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA} AND k.firma = {FIRMA}
          AND h.auftrag = p.auftrag AND h.kdnr = k.kdnr
          AND h.aufkstat = 0
          AND p.posstat = 0 AND p.kzerl = '0'
          AND (k.sperrgrund IS NULL OR TRIM(k.sperrgrund) = '')
    """):
        log(f"  backorders (sin sperrgrund): ords={r[0]}  pos={r[1]}  val={r[2]}")

    # Bloqueados SIN filtro aufkstat (incluyendo aufkstat=2 etc.)
    for r in run(cur, "bloq sperrgrund all aufkstat", f"""
        SELECT h.aufkstat, COUNT(DISTINCT h.auftrag) ords,
               COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p, kund k
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA} AND k.firma = {FIRMA}
          AND h.auftrag = p.auftrag AND h.kdnr = k.kdnr
          AND p.posstat = 0 AND p.kzerl = '0'
          AND k.sperrgrund IS NOT NULL AND TRIM(k.sperrgrund) <> ''
        GROUP BY h.aufkstat ORDER BY h.aufkstat
    """):
        log(f"  aufkstat={r[0]}  ords={r[1]}  pos={r[2]}  val={r[3]}")

    # ============================================================
    # 3. REMITOS — sb104 sin invoice en sbas (delivery note no facturada)
    # ============================================================
    log("\n=== REMITOS — sb104 HOY sin sbas.lsnr ===")

    # sb104 hoy (usando liefdat=TODAY)
    for r in run(cur, "sb104 today liefdat", f"""
        SELECT COUNT(DISTINCT liefnr) liefers, COUNT(DISTINCT auftrag) ords,
               SUM(liefwe) val
        FROM sb104
        WHERE firma = {FIRMA} AND liefdat = TODAY
    """):
        log(f"  sb104 hoy total: liefers={r[0]}  ords={r[1]}  val={r[2]}")

    # sb104 hoy sin factura (liefnr no aparece en sbas como lsnr)
    for r in run(cur, "sb104 hoy sin sbas", f"""
        SELECT COUNT(DISTINCT s.liefnr) liefers, COUNT(DISTINCT s.auftrag) ords,
               SUM(s.liefwe) val
        FROM sb104 s
        WHERE s.firma = {FIRMA} AND s.liefdat = TODAY
          AND NOT EXISTS (
              SELECT 1 FROM sbas b
              WHERE b.firma = {FIRMA} AND b.lsnr = s.liefnr
          )
    """):
        log(f"  sb104 hoy SIN sbas: liefers={r[0]}  ords={r[1]}  val={r[2]}")

    # sb104 todos con liefnr sin sbas correspondiente
    for r in run(cur, "sb104 all sin sbas", f"""
        SELECT COUNT(DISTINCT s.liefnr) liefers, COUNT(DISTINCT s.auftrag) ords,
               SUM(s.liefwe) val
        FROM sb104 s
        WHERE s.firma = {FIRMA}
          AND NOT EXISTS (
              SELECT 1 FROM sbas b
              WHERE b.firma = {FIRMA} AND b.lsnr = s.liefnr
          )
    """):
        log(f"  sb104 ALL sin sbas: liefers={r[0]}  ords={r[1]}  val={r[2]}")

    # sb104 versdat IS NULL (no enviado aún?)
    for r in run(cur, "sb104 versdat null", f"""
        SELECT COUNT(DISTINCT liefnr) liefers, COUNT(DISTINCT auftrag) ords,
               SUM(liefwe) val
        FROM sb104
        WHERE firma = {FIRMA} AND versdat IS NULL
    """):
        log(f"  sb104 versdat NULL: liefers={r[0]}  ords={r[1]}  val={r[2]}")

    # sb104 versdat=TODAY
    for r in run(cur, "sb104 versdat hoy", f"""
        SELECT COUNT(DISTINCT liefnr) liefers, COUNT(DISTINCT auftrag) ords,
               SUM(liefwe) val
        FROM sb104
        WHERE firma = {FIRMA} AND versdat = TODAY
    """):
        log(f"  sb104 versdat=HOY: liefers={r[0]}  ords={r[1]}  val={r[2]}")

    # ============================================================
    # 4. pauf — query exacta (no LIKE, no liefdat)
    # ============================================================
    log("\n=== pauf — QUERIES SIMPLES ===")

    for r in run(cur, "pauf total count", f"""
        SELECT COUNT(*) cnt FROM pauf WHERE firma = {FIRMA}
    """):
        log(f"  pauf total: {r[0]}")

    for r in run(cur, "pauf va_kz exacto 00001", f"""
        SELECT COUNT(*) cnt, COUNT(DISTINCT auftrag) ords
        FROM pauf WHERE firma = {FIRMA}
          AND va_kz = '00001000000000000000'
    """):
        log(f"  va_kz='00001...': cnt={r[0]}  ords={r[1]}")

    for r in run(cur, "pauf va_kz exacto 10000", f"""
        SELECT COUNT(*) cnt, COUNT(DISTINCT auftrag) ords
        FROM pauf WHERE firma = {FIRMA}
          AND va_kz = '10000000000000000000'
    """):
        log(f"  va_kz='10000...': cnt={r[0]}  ords={r[1]}")

    # pauf versdat=TODAY (despachos de hoy)
    for r in run(cur, "pauf versdat hoy", f"""
        SELECT COUNT(DISTINCT liefnr) liefers, COUNT(DISTINCT auftrag) ords,
               SUM(liefwe) val
        FROM pauf WHERE firma = {FIRMA} AND versdat = TODAY
    """):
        log(f"  pauf versdat=HOY: liefers={r[0]}  ords={r[1]}  val={r[2]}")

    # ============================================================
    # 5. SNAPSHOT SIMULTÁNEO COMPLETO
    # ============================================================
    log("\n=== SNAPSHOT COMPLETO ===")
    ts = datetime.now()

    for r in run(cur, "A bloqueados", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p, kund k
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA} AND k.firma = {FIRMA}
          AND h.auftrag = p.auftrag AND h.kdnr = k.kdnr
          AND h.aufkstat = 0
          AND p.posstat = 0 AND p.kzerl = '0'
          AND k.sperrgrund IS NOT NULL AND TRIM(k.sperrgrund) <> ''
    """):
        log(f"  [BLOQUEADOS] ords={r[0]}  pos={r[1]}  val={r[2]}")

    for r in run(cur, "B backorders", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p, kund k
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA} AND k.firma = {FIRMA}
          AND h.auftrag = p.auftrag AND h.kdnr = k.kdnr
          AND h.aufkstat = 0
          AND p.posstat = 0 AND p.kzerl = '0'
          AND (k.sperrgrund IS NULL OR TRIM(k.sperrgrund) = '')
    """):
        log(f"  [BACKORDERS] ords={r[0]}  pos={r[1]}  val={r[2]}")

    for r in run(cur, "C produccion", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND h.aufkstat = 2 AND p.posstat = 2 AND p.kzerl = '0'
    """):
        log(f"  [PRODUCCION] ords={r[0]}  pos={r[1]}  val={r[2]}")

    for r in run(cur, "D remitos sb104", f"""
        SELECT COUNT(DISTINCT s.liefnr) liefers, COUNT(DISTINCT s.auftrag) ords,
               SUM(s.liefwe) val
        FROM sb104 s
        WHERE s.firma = {FIRMA} AND s.liefdat = TODAY
          AND NOT EXISTS (
              SELECT 1 FROM sbas b
              WHERE b.firma = {FIRMA} AND b.lsnr = s.liefnr
          )
    """):
        log(f"  [REMITOS sb104-sin-sbas hoy] liefers={r[0]}  ords={r[1]}  val={r[2]}")

    for r in run(cur, "E venta", f"""
        SELECT COUNT(DISTINCT renr) docs, COUNT(*) pos, SUM(netwert) val
        FROM sbas
        WHERE firma = {FIRMA} AND redat = TODAY AND belegart IN (8, 11)
    """):
        log(f"  [VENTA bel8+11] docs={r[0]}  pos={r[1]}  val={r[2]}")

    for r in run(cur, "F status<-1", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND h.aufkstat < -1
          AND p.kzerl = '0'
    """):
        log(f"  [STATUS<-1] ords={r[0]}  pos={r[1]}  val={r[2]}")

    log(f"\n  Snapshot timestamp: {ts}")

    conn.close()

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\nListo → {OUTPUT_FILE}")


if __name__ == "__main__":
    main()

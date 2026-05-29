"""
TagInfo v7 — sbli remitos, sb104, f092.besch, pauf, backorders fix.
SOLO LECTURA.
"""

import pyodbc
from datetime import date, datetime

DSN = "MSPA"
OUTPUT_FILE = "taginfo_v7.txt"
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

    log(f"TagInfo v7 — {datetime.now()}")
    log(f"DSN: {DSN}  |  Fecha: {today}  |  SOLO LECTURA")
    log("=" * 70)

    conn = get_conn()
    cur = conn.cursor()
    log("Conexión OK\n")

    # ============================================================
    # 1. sbli — remitos abiertos (netwert_ofakt > 0)
    # ============================================================
    log("=== sbli — REMITOS ABIERTOS (netwert_ofakt > 0) ===")
    for r in run(cur, "sbli ofakt total", f"""
        SELECT COUNT(*) liefers, SUM(netwert_ofakt) val_ofakt,
               SUM(netwert) val_total
        FROM sbli
        WHERE firma = {FIRMA} AND netwert_ofakt > 0
    """):
        log(f"  liefers={r[0]}  val_ofakt={r[1]}  val_total={r[2]}")

    # sbli muestra directa
    log("\nsbli muestra (5 filas):")
    for r in run(cur, "sbli muestra", f"""
        SELECT liefer, bujahr, bumonat, netwert, netwert_ofakt, hwnetwert_ofakt
        FROM sbli
        WHERE firma = {FIRMA}
        ORDER BY liefer
    """):
        # solo primeras 5
        log(f"  liefer={r[0]}  año={r[1]}  mes={r[2]}  netwert={r[3]}  ofakt={r[4]}  hw={r[5]}")
        break  # solo la primera para diagnóstico

    # sbli via sbas: los lsnr que tienen netwert pero renr=0
    log("\nsbas: liefs sin facturar (lsnr>0, renr=0):")
    for r in run(cur, "sbas lsnr sin renr", f"""
        SELECT COUNT(DISTINCT lsnr) liefers,
               COUNT(DISTINCT auftrag) ordenes,
               COUNT(*) posiciones,
               SUM(netwert) val
        FROM sbas
        WHERE firma = {FIRMA} AND lsnr > 0 AND (renr = 0 OR renr IS NULL)
    """):
        log(f"  liefers={r[0]}  ordenes={r[1]}  pos={r[2]}  val={r[3]}")

    # sbas: verificar si renr puede ser 0
    log("\nsbas renr=0 filas (sample):")
    for r in run(cur, "sbas renr0 count", f"""
        SELECT COUNT(*) cnt FROM sbas WHERE firma = {FIRMA} AND renr = 0
    """):
        log(f"  rows con renr=0: {r[0]}")

    # ============================================================
    # 2. sb104 — remitos con liefstat
    # ============================================================
    log("\n=== sb104 — LIEFSTAT VALUES ===")
    for r in run(cur, "sb104 liefstat", f"""
        SELECT liefstat, COUNT(*) cnt, COUNT(DISTINCT liefnr) liefers
        FROM sb104
        WHERE firma = {FIRMA}
        GROUP BY liefstat ORDER BY liefstat
    """):
        log(f"  liefstat={r[0]}  filas={r[1]}  liefers={r[2]}")

    log("\nsb104 open (liefstat=0):")
    for r in run(cur, "sb104 open", f"""
        SELECT COUNT(DISTINCT liefnr) liefers,
               COUNT(DISTINCT auftrag) ordenes,
               SUM(liefwe) val
        FROM sb104
        WHERE firma = {FIRMA} AND liefstat = 0
    """):
        log(f"  liefers={r[0]}  ordenes={r[1]}  val={r[2]}")

    # sb104 con liefstat reciente
    log("\nsb104 open + reciente (liefdat > TODAY-60):")
    for r in run(cur, "sb104 open recent", f"""
        SELECT COUNT(DISTINCT liefnr) liefers,
               COUNT(DISTINCT auftrag) ordenes,
               SUM(liefwe) val
        FROM sb104
        WHERE firma = {FIRMA} AND liefstat = 0
          AND liefdat > TODAY - 60
    """):
        log(f"  liefers={r[0]}  ordenes={r[1]}  val={r[2]}")

    # ============================================================
    # 3. f092.besch — indicador de producción
    # ============================================================
    log("\n=== f092.besch — POSIBLES ÓRDENES EN PRODUCCIÓN ===")
    for r in run(cur, "besch dist", f"""
        SELECT besch, COUNT(*) cnt, COUNT(DISTINCT auftrag) ords
        FROM f092
        WHERE firma = {FIRMA}
        GROUP BY besch ORDER BY besch
    """):
        log(f"  besch={r[0]}  filas={r[1]}  ordenes={r[2]}")

    # besch > 0 = en producción?
    log("\nf092 besch>0 abiertos:")
    for r in run(cur, "besch>0 open", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords,
               COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND p.besch > 0
          AND p.posstat = 0 AND p.kzerl = '0'
    """):
        log(f"  besch>0: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # f092.besch por posstat
    log("\nf092 besch X posstat (posiciones abiertas kzerl='0'):")
    for r in run(cur, "besch posstat", f"""
        SELECT p.besch, p.posstat, COUNT(*) cnt, COUNT(DISTINCT p.auftrag) ords
        FROM f092 p
        WHERE p.firma = {FIRMA} AND p.kzerl = '0'
        GROUP BY p.besch, p.posstat
        ORDER BY p.besch, p.posstat
    """):
        log(f"  besch={r[0]}  posstat={r[1]}  cnt={r[2]}  ords={r[3]}")

    # ============================================================
    # 4. pauf — open dispatch orders (versdat reciente)
    # ============================================================
    log("\n=== pauf — VERSANDAUFTRÄGE ABIERTOS ===")
    for r in run(cur, "pauf liefstat? va_kz dist", f"""
        SELECT va_kz, COUNT(*) cnt, COUNT(DISTINCT auftrag) ords
        FROM pauf
        WHERE firma = {FIRMA}
        GROUP BY va_kz ORDER BY va_kz
    """):
        log(f"  va_kz={r[0]}  cnt={r[1]}  ords={r[2]}")

    for r in run(cur, "pauf totales", f"""
        SELECT COUNT(DISTINCT liefnr) liefers,
               COUNT(DISTINCT auftrag) ordenes,
               SUM(liefwe) val
        FROM pauf WHERE firma = {FIRMA}
    """):
        log(f"  liefers={r[0]}  ordenes={r[1]}  val={r[2]}")

    # ============================================================
    # 5. BACKORDERS — intentar con posstat IN (0,3,5,8)
    # ============================================================
    log("\n=== BACKORDERS todos posstat abiertos ===")
    for r in run(cur, "backorders posstat IN", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords,
               COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND p.termin < TODAY
          AND h.aufkstat = 0
          AND p.posstat IN (0, 3, 5, 8)
          AND p.kzerl = '0'
    """):
        log(f"  posstat IN(0,3,5,8): ords={r[0]}  pos={r[1]}  val={r[2]}")

    for r in run(cur, "backorders aufkstat IN 0,4", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords,
               COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND p.termin < TODAY
          AND h.aufkstat IN (0, 4)
          AND p.posstat = 0
          AND p.kzerl = '0'
    """):
        log(f"  aufkstat IN(0,4): ords={r[0]}  pos={r[1]}  val={r[2]}")

    # ============================================================
    # 6. BLOQUEADO POR CRÉDITO — via aufkstat=2 o kzlock
    # ============================================================
    log("\n=== BLOQUEADO CRÉDITO — aufkstat=2 + kzlock ===")
    for r in run(cur, "aufkstat IN (-2,-1,2) abiertos", f"""
        SELECT h.aufkstat,
               COUNT(DISTINCT h.auftrag) ords,
               COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND h.aufkstat IN (-2, -1, 2)
          AND p.kzerl = '0'
        GROUP BY h.aufkstat
    """):
        log(f"  aufkstat={r[0]}  ords={r[1]}  pos={r[2]}  val={r[3]}")

    # kzlock != 0 con posiciones abiertas
    for r in run(cur, "kzlock!=0 abiertos", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords,
               COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND h.kzlock <> 0
          AND h.aufkstat = 0
          AND p.posstat = 0 AND p.kzerl = '0'
    """):
        log(f"  kzlock!=0: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # TOTAL posiciones abiertas (posstat=0, kzerl='0', aufkstat=0)
    log("\n=== TOTAL posiciones activas en f092 ===")
    for r in run(cur, "total activas", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords,
               COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p
        WHERE h.firma = {FIRMA} AND p.firma = {FIRMA}
          AND h.auftrag = p.auftrag
          AND h.aufkstat = 0
          AND p.posstat = 0 AND p.kzerl = '0'
    """):
        log(f"  TOTAL ords={r[0]}  pos={r[1]}  val={r[2]}")

    conn.close()

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\nListo → {OUTPUT_FILE}")


if __name__ == "__main__":
    main()

"""
TagInfo v43 - QUERIES EXACTAS del codigo fuente taginfo2.4gl
Traduccion directa de las queries 4GL a SQL/Python.

CAMPOS NUEVOS vs versiones anteriores:
  f092.termin <= today    (backorders = plazos vencidos)
  f092.kzentns = '0'      (sin ES/remito creado)
  f092.gliefme            (cantidad ya entregada)
  f092.auftme - f092.gliefme > 0   (cantidad aun abierta)
  f090.liefspkz           (traba levantada = '1')
  f090.aufart             (tipo orden: excluir storno/gutschrift/angebot)
  kund.liefsp = '2' o '9' (bloqueo credito/entrega)
  aufkstat = -9           (bloqueado por kredlim)
  formula: poswert/auftme * (auftme - gliefme)  (valor abierto)

SOLO LECTURA.
"""

import pyodbc
from datetime import date, datetime

DSN = "MSPA"
OUTPUT_FILE = "taginfo_v43.txt"
FIRMA = 1


def get_conn():
    return pyodbc.connect(f"DSN={DSN};", autocommit=True)


def run(cursor, label, sql):
    print(f"  {label}...")
    try:
        cursor.execute(sql)
        return cursor.fetchall()
    except Exception as e:
        print(f"    SQL ERROR [{label}]: {e}")
        return []


def main():
    lines = []
    log = lines.append
    today = date.today()

    log(f"TagInfo v43 - QUERIES EXACTAS 4GL - {datetime.now()}")
    log(f"DSN: {DSN}  |  Fecha: {today}  |  SOLO LECTURA")
    log("=" * 70)

    conn = get_conn()
    cur = conn.cursor()
    log("Conexion OK\n")

    # ============================================================
    # 0. VERIFICAR COLUMNAS NUEVAS
    # ============================================================
    log("=== VERIFICAR COLUMNAS NUEVAS ===")
    new_cols = [
        ("f092.kzentns", f"SELECT FIRST 1 kzentns FROM f092 WHERE firma={FIRMA}"),
        ("f092.gliefme", f"SELECT FIRST 1 gliefme FROM f092 WHERE firma={FIRMA}"),
        ("f092.jjtermin", f"SELECT FIRST 1 jjtermin FROM f092 WHERE firma={FIRMA}"),
        ("f092.kwtermin", f"SELECT FIRST 1 kwtermin FROM f092 WHERE firma={FIRMA}"),
        ("f090.liefspkz", f"SELECT FIRST 1 liefspkz FROM f090 WHERE firma={FIRMA}"),
        ("f090.aufart",   f"SELECT FIRST 1 aufart FROM f090 WHERE firma={FIRMA}"),
        ("f103.kzdfue",   f"SELECT FIRST 1 kzdfue FROM f103 WHERE firma={FIRMA}"),
        ("f103.sollme",   f"SELECT FIRST 1 sollme FROM f103 WHERE firma={FIRMA}"),
        ("f103.istme",    f"SELECT FIRST 1 istme FROM f103 WHERE firma={FIRMA}"),
        ("f103.posstat",  f"SELECT FIRST 1 posstat FROM f103 WHERE firma={FIRMA}"),
        ("f104.liefstat", f"SELECT FIRST 1 liefstat FROM f104 WHERE firma={FIRMA}"),
        ("f105.liefme",   f"SELECT FIRST 1 liefme FROM f105 WHERE firma={FIRMA}"),
        ("f105.liefnr",   f"SELECT FIRST 1 liefnr FROM f105 WHERE firma={FIRMA}"),
        ("f107.faktme",   f"SELECT FIRST 1 faktme FROM f107 WHERE firma={FIRMA}"),
        ("f107.liefnr",   f"SELECT FIRST 1 liefnr FROM f107 WHERE firma={FIRMA}"),
        ("f107.lieflfdnr",f"SELECT FIRST 1 lieflfdnr FROM f107 WHERE firma={FIRMA}"),
        ("f106.liefnr",   f"SELECT FIRST 1 liefnr FROM f106 WHERE firma={FIRMA}"),
        ("f106.periode",  f"SELECT FIRST 1 periode FROM f106 WHERE firma={FIRMA}"),
        ("kund.liefspkz", f"SELECT FIRST 1 liefspkz FROM kund WHERE firma={FIRMA}"),
    ]
    ok_cols = []
    for name, sql in new_cols:
        rows = run(cur, f"col {name}", sql)
        if rows:
            ok_cols.append(name)
            log(f"  OK: {name} = {rows[0][0]}")
        else:
            log(f"  NO: {name}")

    # ============================================================
    # 1. DISTRIBUCION DE CAMPOS NUEVOS
    # ============================================================
    log("\n=== DIST kzentns en f092 ===")
    for r in run(cur, "kzentns dist", f"SELECT kzentns, COUNT(*) FROM f092 WHERE firma={FIRMA} GROUP BY kzentns ORDER BY kzentns"):
        log(f"  kzentns={r[0]}  cnt={r[1]}")

    log("\n=== DIST aufart en f090 bel(6,7,11) ===")
    for r in run(cur, "aufart dist", f"""
        SELECT aufart, COUNT(*) FROM f090 WHERE firma={FIRMA}
          AND belegart IN (6,7,11)
        GROUP BY aufart ORDER BY aufart
    """):
        log(f"  aufart={r[0]}  cnt={r[1]}")

    log("\n=== DIST liefspkz en f090 bel(6,7,11) aufkstat=0 ===")
    for r in run(cur, "liefspkz dist", f"""
        SELECT liefspkz, COUNT(*) FROM f090 WHERE firma={FIRMA}
          AND belegart IN (6,7,11) AND aufkstat=0
        GROUP BY liefspkz ORDER BY liefspkz
    """):
        log(f"  liefspkz={r[0]}  cnt={r[1]}")

    log("\n=== DIST liefsp en kund (aufkstat=0 orders) ===")
    for r in run(cur, "liefsp dist kund aufkstat=0", f"""
        SELECT k.liefsp, COUNT(DISTINCT h.auftrag) ords
        FROM f090 h, kund k
        WHERE h.firma={FIRMA} AND k.firma={FIRMA}
          AND h.kdnr=k.kdnr AND h.aufkstat=0 AND h.belegart IN (6,7,11)
        GROUP BY k.liefsp ORDER BY k.liefsp
    """):
        log(f"  liefsp={r[0]}  ords={r[1]}")

    # ============================================================
    # 2. BACKORDERS (selrueck) - TRADUCCION EXACTA DEL 4GL
    # Formula: poswert/auftme * (auftme - gliefme)
    # Filtros clave:
    #   f092.termin <= TODAY
    #   f092.kzentns = '0'  (sin ES creado)
    #   f090.aufkstat >= 0
    #   f090.aufart IN (0,2,4,6,7,8)
    #   (auftme - gliefme) > 0
    #   f092.kzerl = '0'
    #   f092.auftme <> 0
    #   (liefsp <> '2' AND liefsp <> '9') OR liefspkz = '1'
    # ============================================================
    log("\n=== BACKORDERS (selrueck) - QUERY EXACTA ===")
    log("  TARGET: 14 ords / 16 pos / 1,070,283 val")

    for r in run(cur, "BACK selrueck exacto", f"""
        SELECT COUNT(DISTINCT f092.auftrag) ords,
               COUNT(*) pos,
               SUM(f092.poswert/f092.auftme * (f092.auftme - f092.gliefme)) val
          FROM f090, f092, kund
         WHERE f092.firma = {FIRMA}
           AND f090.firma = f092.firma
           AND kund.firma = f090.firma
           AND f090.auftrag  = f092.auftrag
           AND kund.kdnr     = f090.kdnr
           AND f092.termin  <= TODAY
           AND f092.kzentns  = '0'
           AND f090.aufkstat >= 0
           AND f090.aufart IN ('0','2','4','6','7','8')
           AND (f092.auftme - f092.gliefme) > 0
           AND f092.kzerl   = '0'
           AND f092.auftme <> 0
           AND ( (kund.liefsp <> '2' AND kund.liefsp <> '9')
               OR f090.liefspkz = '1')
    """):
        log(f"  BACK selrueck: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # Sin kzentns (por si no existe)
    for r in run(cur, "BACK sin kzentns", f"""
        SELECT COUNT(DISTINCT f092.auftrag) ords,
               COUNT(*) pos,
               SUM(f092.poswert/f092.auftme * (f092.auftme - f092.gliefme)) val
          FROM f090, f092, kund
         WHERE f092.firma = {FIRMA}
           AND f090.firma = f092.firma
           AND kund.firma = f090.firma
           AND f090.auftrag  = f092.auftrag
           AND kund.kdnr     = f090.kdnr
           AND f092.termin  <= TODAY
           AND f090.aufkstat >= 0
           AND f090.aufart IN ('0','2','4','6','7','8')
           AND (f092.auftme - f092.gliefme) > 0
           AND f092.kzerl   = '0'
           AND f092.auftme <> 0
           AND ( (kund.liefsp <> '2' AND kund.liefsp <> '9')
               OR f090.liefspkz = '1')
    """):
        log(f"  BACK sin kzentns: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # Sin aufart filter
    for r in run(cur, "BACK sin aufart", f"""
        SELECT COUNT(DISTINCT f092.auftrag) ords,
               COUNT(*) pos,
               SUM(f092.poswert/f092.auftme * (f092.auftme - f092.gliefme)) val
          FROM f090, f092, kund
         WHERE f092.firma = {FIRMA}
           AND f090.firma = f092.firma
           AND kund.firma = f090.firma
           AND f090.auftrag  = f092.auftrag
           AND kund.kdnr     = f090.kdnr
           AND f092.termin  <= TODAY
           AND f092.kzentns  = '0'
           AND f090.aufkstat >= 0
           AND (f092.auftme - f092.gliefme) > 0
           AND f092.kzerl   = '0'
           AND f092.auftme <> 0
           AND ( (kund.liefsp <> '2' AND kund.liefsp <> '9')
               OR f090.liefspkz = '1')
    """):
        log(f"  BACK sin aufart: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # Sin liefsp filter
    for r in run(cur, "BACK sin liefsp", f"""
        SELECT COUNT(DISTINCT f092.auftrag) ords,
               COUNT(*) pos,
               SUM(f092.poswert/f092.auftme * (f092.auftme - f092.gliefme)) val
          FROM f090, f092
         WHERE f092.firma = {FIRMA}
           AND f090.firma = f092.firma
           AND f090.auftrag  = f092.auftrag
           AND f092.termin  <= TODAY
           AND f092.kzentns  = '0'
           AND f090.aufkstat >= 0
           AND f090.aufart IN ('0','2','4','6','7','8')
           AND (f092.auftme - f092.gliefme) > 0
           AND f092.kzerl   = '0'
           AND f092.auftme <> 0
    """):
        log(f"  BACK sin liefsp/liefspkz: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # ============================================================
    # 3. BLOQUEADOS (selkredlim) - QUERY EXACTA
    # Filtros clave:
    #   f092.posstat < 9
    #   (aufkstat >= 0 OR aufkstat = -9)
    #   aufart IN (0,2,4,6,7,8)
    #   (auftme - gliefme) > 0
    #   (kund.liefsp = '2' OR '9') AND liefspkz <> '1'
    # ============================================================
    log("\n=== BLOQUEADOS (selkredlim) - QUERY EXACTA ===")
    log("  TARGET: 0 / 0 / 0 (hoy, fin de mes)")

    for r in run(cur, "BLOQ selkredlim exacto", f"""
        SELECT COUNT(DISTINCT f092.auftrag) ords,
               COUNT(*) pos,
               SUM(f092.poswert/f092.auftme * (f092.auftme - f092.gliefme)) val
          FROM f090, f092, kund
         WHERE f092.firma = {FIRMA}
           AND f090.firma = f092.firma
           AND kund.firma = f090.firma
           AND f090.auftrag  = f092.auftrag
           AND kund.kdnr     = f090.kdnr
           AND f092.posstat  < 9
           AND (f090.aufkstat >= 0 OR f090.aufkstat = -9)
           AND f090.aufart IN ('0','2','4','6','7','8')
           AND (f092.auftme - f092.gliefme) > 0
           AND f092.kzerl   = '0'
           AND f092.auftme <> 0
           AND ( (kund.liefsp = '2' OR kund.liefsp = '9')
               AND f090.liefspkz <> '1')
    """):
        log(f"  BLOQ selkredlim: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # ============================================================
    # 4. STATUS < -1 (selneg) - QUERY EXACTA
    # ============================================================
    log("\n=== STATUS<-1 (selneg) - QUERY EXACTA ===")

    for r in run(cur, "NEG selneg exacto", f"""
        SELECT COUNT(DISTINCT f092.auftrag) ords,
               COUNT(*) pos,
               SUM(f092.poswert/f092.auftme * (f092.auftme - f092.gliefme)) val
          FROM f090, f092, kund
         WHERE f092.firma = {FIRMA}
           AND f090.firma = f092.firma
           AND kund.firma = f090.firma
           AND f090.auftrag  = f092.auftrag
           AND kund.kdnr     = f090.kdnr
           AND f092.posstat  < 9
           AND f090.aufkstat < -1
           AND f090.aufart IN ('0','2','4','6','7','8')
           AND (f092.auftme - f092.gliefme) > 0
           AND f092.kzerl   = '0'
           AND f092.auftme <> 0
           AND ( (kund.liefsp <> '2' AND kund.liefsp <> '9')
               OR f090.liefspkz = '1')
    """):
        log(f"  NEG selneg: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # ============================================================
    # 5. PEDIDOS ABIERTOS (seloffen) - QUERY EXACTA
    # ============================================================
    log("\n=== PEDIDOS ABIERTOS (seloffen) - QUERY EXACTA ===")

    for r in run(cur, "OFFEN seloffen exacto", f"""
        SELECT COUNT(DISTINCT f092.auftrag) ords,
               COUNT(*) pos,
               SUM(f092.poswert/f092.auftme * (f092.auftme - f092.gliefme)) val
          FROM f090, f092, kund
         WHERE f092.firma = {FIRMA}
           AND f090.firma = f092.firma
           AND kund.firma = f090.firma
           AND f090.auftrag  = f092.auftrag
           AND kund.kdnr     = f090.kdnr
           AND f092.termin  > TODAY
           AND f090.aufkstat >= 0
           AND f090.aufart IN ('0','2','4','6','7','8')
           AND (f092.auftme - f092.gliefme) > 0
           AND f092.kzerl   = '0'
           AND f092.auftme <> 0
           AND ( (kund.liefsp <> '2' AND kund.liefsp <> '9')
               OR f090.liefspkz = '1')
    """):
        log(f"  OFFEN seloffen: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # ============================================================
    # 6. PRODUCCION (selentns via f103) - QUERY EXACTA
    # ============================================================
    log("\n=== PRODUCCION (selentns via f103) - QUERY EXACTA ===")

    for r in run(cur, "ENTNS selentns exacto", f"""
        SELECT COUNT(DISTINCT f103.auftrag) ords,
               COUNT(*) pos,
               SUM(f092.poswert/f092.auftme * f103.sollme) val
          FROM f103, f090, f092
         WHERE f103.firma = {FIRMA}
           AND f090.firma = f103.firma
           AND f092.firma = f103.firma
           AND f103.auftrag = f090.auftrag
           AND f103.auftrag = f092.auftrag
           AND f103.posnr   = f092.posnr
           AND f092.auftme <> 0
           AND (f103.kzdfue = 0 OR f103.kzdfue IS NULL)
    """):
        log(f"  ENTNS selentns: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # ============================================================
    # 7. REMITOS (self105 = Lieferscheine) - QUERY EXACTA
    # ============================================================
    log("\n=== REMITOS (self105 Lieferscheine) - QUERY EXACTA ===")

    for r in run(cur, "LS self105 exacto", f"""
        SELECT COUNT(DISTINCT f105.auftrag) ords,
               COUNT(*) pos,
               SUM(f092.poswert/f092.auftme * f105.liefme) val
          FROM f105, f090, f092
         WHERE f105.firma = {FIRMA}
           AND f090.firma = f105.firma
           AND f092.firma = f105.firma
           AND f105.auftrag = f090.auftrag
           AND f105.auftrag = f092.auftrag
           AND f105.posnr   = f092.posnr
           AND f092.auftme <> 0
           AND f105.liefnr IN (SELECT liefnr FROM f104
                                WHERE f104.firma = {FIRMA}
                                  AND f104.liefstat < 9)
    """):
        log(f"  LS self105: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # ============================================================
    # 8. FACTURAS (self107) - QUERY EXACTA
    # ============================================================
    log("\n=== FACTURAS (self107 Rechnungen) - QUERY EXACTA ===")

    for r in run(cur, "RE self107 exacto", f"""
        SELECT COUNT(DISTINCT f107.auftrag) ords,
               COUNT(*) pos,
               SUM(f092.poswert/f092.auftme * f107.faktme) val
          FROM f107, f090, f092, f106
         WHERE f107.firma = {FIRMA}
           AND f107.firma = f106.firma
           AND f107.liefnr = f106.liefnr
           AND f090.firma = f107.firma
           AND f092.firma = f107.firma
           AND f107.auftrag = f090.auftrag
           AND f107.auftrag = f092.auftrag
           AND f107.posnr   = f092.posnr
           AND f107.lieflfdnr = 0
           AND f092.auftme <> 0
           AND f090.aufart IN ('0','2','4','6','7','8')
           AND (f106.periode = '0' OR f106.periode = ' ' OR f106.periode IS NULL)
    """):
        log(f"  RE self107: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # ============================================================
    # 9. VENTA DIARIA (sbascur) - QUERY EXACTA
    # sbas.redat = today, group by auftrag,auftpos, sum(netwert)
    # ============================================================
    log("\n=== VENTA DIARIA (sbascur) - QUERY EXACTA ===")

    for r in run(cur, "VENTA sbascur exacto", f"""
        SELECT COUNT(DISTINCT auftrag) ords,
               COUNT(*) pos,
               SUM(netwert) val
          FROM sbas
         WHERE firma = {FIRMA}
           AND redat = TODAY
    """):
        log(f"  VENTA sbascur: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # ============================================================
    # 10. SNAPSHOT SIMULTANEO
    # ============================================================
    print("\n*** TOMAR SCREENSHOT DE PANTALLA AHORA ***\n")
    log("\n=== SNAPSHOT SIMULTANEO ===")
    ts = datetime.now()
    log(f"  Timestamp: {ts}")
    log("  TARGETS: BACK=14/16/1070283  BLOQ=0/0/0  NEG=?  OFFEN=?  PROD=?  LS/RE=?  VENTA=?")

    snap_queries = [
        ("BACK selrueck", f"""
            SELECT COUNT(DISTINCT f092.auftrag) ords, COUNT(*) pos,
                   SUM(f092.poswert/f092.auftme * (f092.auftme - f092.gliefme)) val
              FROM f090, f092, kund
             WHERE f092.firma={FIRMA} AND f090.firma=f092.firma AND kund.firma=f090.firma
               AND f090.auftrag=f092.auftrag AND kund.kdnr=f090.kdnr
               AND f092.termin <= TODAY AND f092.kzentns='0' AND f090.aufkstat >= 0
               AND f090.aufart IN ('0','2','4','6','7','8')
               AND (f092.auftme - f092.gliefme) > 0 AND f092.kzerl='0' AND f092.auftme <> 0
               AND ((kund.liefsp <> '2' AND kund.liefsp <> '9') OR f090.liefspkz = '1')
        """),
        ("BLOQ selkredlim", f"""
            SELECT COUNT(DISTINCT f092.auftrag) ords, COUNT(*) pos,
                   SUM(f092.poswert/f092.auftme * (f092.auftme - f092.gliefme)) val
              FROM f090, f092, kund
             WHERE f092.firma={FIRMA} AND f090.firma=f092.firma AND kund.firma=f090.firma
               AND f090.auftrag=f092.auftrag AND kund.kdnr=f090.kdnr
               AND f092.posstat < 9
               AND (f090.aufkstat >= 0 OR f090.aufkstat = -9)
               AND f090.aufart IN ('0','2','4','6','7','8')
               AND (f092.auftme - f092.gliefme) > 0 AND f092.kzerl='0' AND f092.auftme <> 0
               AND ((kund.liefsp = '2' OR kund.liefsp = '9') AND f090.liefspkz <> '1')
        """),
        ("NEG selneg", f"""
            SELECT COUNT(DISTINCT f092.auftrag) ords, COUNT(*) pos,
                   SUM(f092.poswert/f092.auftme * (f092.auftme - f092.gliefme)) val
              FROM f090, f092, kund
             WHERE f092.firma={FIRMA} AND f090.firma=f092.firma AND kund.firma=f090.firma
               AND f090.auftrag=f092.auftrag AND kund.kdnr=f090.kdnr
               AND f092.posstat < 9 AND f090.aufkstat < -1
               AND f090.aufart IN ('0','2','4','6','7','8')
               AND (f092.auftme - f092.gliefme) > 0 AND f092.kzerl='0' AND f092.auftme <> 0
               AND ((kund.liefsp <> '2' AND kund.liefsp <> '9') OR f090.liefspkz = '1')
        """),
        ("OFFEN seloffen", f"""
            SELECT COUNT(DISTINCT f092.auftrag) ords, COUNT(*) pos,
                   SUM(f092.poswert/f092.auftme * (f092.auftme - f092.gliefme)) val
              FROM f090, f092, kund
             WHERE f092.firma={FIRMA} AND f090.firma=f092.firma AND kund.firma=f090.firma
               AND f090.auftrag=f092.auftrag AND kund.kdnr=f090.kdnr
               AND f092.termin > TODAY AND f090.aufkstat >= 0
               AND f090.aufart IN ('0','2','4','6','7','8')
               AND (f092.auftme - f092.gliefme) > 0 AND f092.kzerl='0' AND f092.auftme <> 0
               AND ((kund.liefsp <> '2' AND kund.liefsp <> '9') OR f090.liefspkz = '1')
        """),
        ("PRODUCCION selentns", f"""
            SELECT COUNT(DISTINCT f103.auftrag) ords, COUNT(*) pos,
                   SUM(f092.poswert/f092.auftme * f103.sollme) val
              FROM f103, f090, f092
             WHERE f103.firma={FIRMA} AND f090.firma=f103.firma AND f092.firma=f103.firma
               AND f103.auftrag=f090.auftrag AND f103.auftrag=f092.auftrag
               AND f103.posnr=f092.posnr AND f092.auftme <> 0
               AND (f103.kzdfue = 0 OR f103.kzdfue IS NULL)
        """),
        ("REMITOS self105", f"""
            SELECT COUNT(DISTINCT f105.auftrag) ords, COUNT(*) pos,
                   SUM(f092.poswert/f092.auftme * f105.liefme) val
              FROM f105, f090, f092
             WHERE f105.firma={FIRMA} AND f090.firma=f105.firma AND f092.firma=f105.firma
               AND f105.auftrag=f090.auftrag AND f105.auftrag=f092.auftrag
               AND f105.posnr=f092.posnr AND f092.auftme <> 0
               AND f105.liefnr IN (SELECT liefnr FROM f104
                                    WHERE f104.firma={FIRMA} AND f104.liefstat < 9)
        """),
        ("FACTURAS self107", f"""
            SELECT COUNT(DISTINCT f107.auftrag) ords, COUNT(*) pos,
                   SUM(f092.poswert/f092.auftme * f107.faktme) val
              FROM f107, f090, f092, f106
             WHERE f107.firma={FIRMA} AND f107.firma=f106.firma AND f107.liefnr=f106.liefnr
               AND f090.firma=f107.firma AND f092.firma=f107.firma
               AND f107.auftrag=f090.auftrag AND f107.auftrag=f092.auftrag
               AND f107.posnr=f092.posnr AND f107.lieflfdnr=0 AND f092.auftme <> 0
               AND f090.aufart IN ('0','2','4','6','7','8')
               AND (f106.periode='0' OR f106.periode=' ' OR f106.periode IS NULL)
        """),
        ("VENTA sbas", f"""
            SELECT COUNT(DISTINCT auftrag) ords, COUNT(*) pos, SUM(netwert) val
              FROM sbas WHERE firma={FIRMA} AND redat=TODAY
        """),
    ]

    for label, sql in snap_queries:
        for r in run(cur, f"snap {label}", sql):
            log(f"  [{label}] ords={r[0]}  pos={r[1]}  val={r[2]}")

    log(f"  End Timestamp: {datetime.now()}")

    conn.close()

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\nListo -> {OUTPUT_FILE}")


if __name__ == "__main__":
    main()

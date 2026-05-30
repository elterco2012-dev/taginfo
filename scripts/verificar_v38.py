"""
TagInfo v38 - DETALLE POSICIONES de los 14 ordenes bel=7+11 NOT OVER
+ hipotesis valor alternativo (netwert, menge*preis)
+ kund fields para credit block flag
+ hipotesis pos query SEPARADA de ord query
SOLO LECTURA.
"""

import pyodbc
from datetime import date, datetime

DSN = "MSPA"
OUTPUT_FILE = "taginfo_v38.txt"
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

    log(f"TagInfo v38 - DETALLE POSICIONES - {datetime.now()}")
    log(f"DSN: {DSN}  |  Fecha: {today}  |  SOLO LECTURA")
    log("=" * 70)

    conn = get_conn()
    cur = conn.cursor()
    log("Conexion OK\n")

    kredlim_rows = run(cur, "kredlim", f"SELECT kdnr, kredlim FROM kund WHERE firma={FIRMA} AND kredlim > 0")
    kredlim_map = {r[0]: r[1] for r in kredlim_rows}

    def fmt_in(lst): return ",".join(str(k) for k in lst)

    # Standard credit base bel(6,7,11)
    totals_6711 = run(cur, "per-kdnr bel(6,7,11)", f"""
        SELECT h.kdnr, SUM(p.poswert)
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.kzerl='0'
          AND h.aufkstat<>8 AND h.belegart IN (6,7,11)
        GROUP BY h.kdnr
    """)
    over_6711 = [r[0] for r in totals_6711 if kredlim_map.get(r[0],0)>0 and r[1] and r[1]>kredlim_map.get(r[0],0)]

    # bel=7+11 NOT OVER orders (the 14)
    orders_b711_under = run(cur, "orders bel=7+11 NOT OVER", f"""
        SELECT DISTINCT h.auftrag
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.kzerl='0'
          AND h.aufkstat=0 AND h.belegart IN (7,11)
          AND h.kdnr NOT IN ({fmt_in(over_6711)})
    """)
    aut_711_under = [r[0] for r in orders_b711_under]
    log(f"  bel=7+11 NOT OVER orders: {len(aut_711_under)}\n")

    # ============================================================
    # 1. DETALLE COMPLETO de posiciones de los 14 ordenes bel=7+11
    # Mostrar todos los campos de f092 para entender que filtra la pantalla
    # ============================================================
    log("=== POSICIONES COMPLETAS de bel=7+11 NOT OVER (los 14 ordenes) ===")
    log("  auftrag  pospos  posstat  kzerl  liefme  menge  poswert  termin")

    if aut_711_under:
        pos_detail = run(cur, "pos detail bel=7+11", f"""
            SELECT h.auftrag, h.belegart, h.kdnr,
                   p.pospos, p.posstat, p.kzerl, p.liefme,
                   p.menge, p.poswert, p.termin
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag
              AND h.auftrag IN ({fmt_in(aut_711_under)})
            ORDER BY h.auftrag, p.pospos
        """)
        total_poswert = 0
        orders_seen = {}
        for r in pos_detail:
            auftrag, bel, kdnr, pospos, posstat, kzerl, liefme, menge, poswert, termin = r
            if auftrag not in orders_seen:
                orders_seen[auftrag] = 0
            orders_seen[auftrag] += 1
            v = float(poswert) if poswert else 0.0
            total_poswert += v
            log(f"  {auftrag} bel={bel} kdnr={kdnr} | pos={pospos} pstat={posstat} kzerl={kzerl} liefme={liefme} menge={menge} val={poswert} termin={termin}")
        log(f"\n  TOTAL pos rows: {len(pos_detail)}  (kzerl='0' only)")
        log(f"  TOTAL poswert sum: {total_poswert:.2f}")
        log(f"  Pos per order distribution: {sorted(orders_seen.values())}")

    # ============================================================
    # 2. POSICIONES con kzerl='0' vs TODAS (sin filtro kzerl)
    # Quizas la pantalla cuenta TODAS las posiciones (no solo kzerl='0')
    # ============================================================
    log("\n=== bel=7+11 NOT OVER: con vs sin filtro kzerl ===")

    if aut_711_under:
        for r in run(cur, "bel=7+11 NOT OVER kzerl=0", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.auftrag IN ({fmt_in(aut_711_under)})
        """):
            log(f"  kzerl='0': ords={r[0]}  pos={r[1]}  val={r[2]}")

        for r in run(cur, "bel=7+11 NOT OVER ALL kzerl", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag
              AND h.auftrag IN ({fmt_in(aut_711_under)})
        """):
            log(f"  ALL kzerl: ords={r[0]}  pos={r[1]}  val={r[2]}")

        for r in run(cur, "bel=7+11 NOT OVER kzerl<>0", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl<>'0'
              AND h.auftrag IN ({fmt_in(aut_711_under)})
        """):
            log(f"  kzerl<>'0': ords={r[0]}  pos={r[1]}  val={r[2]}")

    # kzerl distribution in bel=7+11
    log("\n  kzerl values in bel=7+11 aufkstat=0:")
    for r in run(cur, "kzerl dist bel=7+11", f"""
        SELECT p.kzerl, COUNT(*) cnt
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND h.aufkstat=0 AND h.belegart IN (7,11)
        GROUP BY p.kzerl ORDER BY p.kzerl
    """):
        log(f"    kzerl={r[0]}  cnt={r[1]}")

    # ============================================================
    # 3. VALOR ALTERNATIVO: netwert o menge*preis
    # ============================================================
    log("\n=== VALOR ALTERNATIVO en bel=7+11 NOT OVER ===")

    if aut_711_under:
        # Try netwert field
        for r in run(cur, "netwert bel=7+11 NOT OVER", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.netwert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.auftrag IN ({fmt_in(aut_711_under)})
        """):
            log(f"  netwert kzerl='0': ords={r[0]}  pos={r[1]}  val={r[2]}")

        # Try without kzerl for netwert
        for r in run(cur, "netwert bel=7+11 NOT OVER all kzerl", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.netwert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag
              AND h.auftrag IN ({fmt_in(aut_711_under)})
        """):
            log(f"  netwert ALL kzerl: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # ============================================================
    # 4. HIPOTESIS: pos count desde f090 (no f092)
    # Y ordenes desde f090 con count(pospos) propio campo
    # ============================================================
    log("\n=== f090 TIENE CAMPO posanz (Positionsanzahl)? ===")

    if aut_711_under:
        # See if f090 has a posanz or similar column
        for r in run(cur, "f090 fields for bel=7+11", f"""
            SELECT h.auftrag, h.belegart, h.kdnr, h.aufkstat, h.termin
            FROM f090 h WHERE h.firma={FIRMA}
              AND h.auftrag IN ({fmt_in(aut_711_under)})
            ORDER BY h.auftrag
        """):
            log(f"  auftrag={r[0]} bel={r[1]} kdnr={r[2]} aufkstat={r[3]} termin={r[4]}")

    # ============================================================
    # 5. HIPOTESIS: BACK query usa bel=6 para posiciones, bel=7+11 para ordenes
    # Screen might show: ords from bel=7+11, pos from bel=6 (separate queries)
    # ============================================================
    log("\n=== HIPOTESIS SEPARADA: ords bel=7+11 / pos bel=6 excl val=0 ===")

    # bel=6 NOT OVER excluding poswert=0 positions
    for r in run(cur, "bel=6 NOT OVER poswert>0", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.kzerl='0'
          AND h.aufkstat=0 AND h.belegart=6
          AND p.poswert > 0
          AND h.kdnr NOT IN ({fmt_in(over_6711)})
    """):
        log(f"  bel=6 NOT OVER poswert>0: ords={r[0]}  pos={r[1]}  val={r[2]}")

    for r in run(cur, "bel=6 NOT OVER poswert<>0", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.kzerl='0'
          AND h.aufkstat=0 AND h.belegart=6
          AND p.poswert <> 0
          AND h.kdnr NOT IN ({fmt_in(over_6711)})
    """):
        log(f"  bel=6 NOT OVER poswert<>0: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # All bel=6 NOT OVER positions
    for r in run(cur, "bel=6 NOT OVER all pos", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.kzerl='0'
          AND h.aufkstat=0 AND h.belegart=6
          AND h.kdnr NOT IN ({fmt_in(over_6711)})
    """):
        log(f"  bel=6 NOT OVER all pos: ords={r[0]}  pos={r[1]}  val={r[2]}")

    # ============================================================
    # 6. KUND FIELDS - buscar campo de bloqueo de credito
    # ============================================================
    log("\n=== KUND fields: buscar campo bloqueo credito ===")

    # Try common field names for credit block flag
    kund_fields = [
        ("sperre",   f"SELECT kdnr, sperre FROM kund WHERE firma={FIRMA} AND kdnr IN (107038,122427,128447,134670,157944) ORDER BY kdnr"),
        ("sperrkz",  f"SELECT kdnr, sperrkz FROM kund WHERE firma={FIRMA} AND kdnr IN (107038,122427,128447,134670,157944) ORDER BY kdnr"),
        ("kredsp",   f"SELECT kdnr, kredsp FROM kund WHERE firma={FIRMA} AND kdnr IN (107038,122427,128447,134670,157944) ORDER BY kdnr"),
        ("kreditsp", f"SELECT kdnr, kreditsp FROM kund WHERE firma={FIRMA} AND kdnr IN (107038,122427,128447,134670,157944) ORDER BY kdnr"),
        ("autosperre",f"SELECT kdnr, autosperre FROM kund WHERE firma={FIRMA} AND kdnr IN (107038,122427,128447,134670,157944) ORDER BY kdnr"),
        ("kreditsperre",f"SELECT kdnr, kreditsperre FROM kund WHERE firma={FIRMA} AND kdnr IN (107038,122427,128447,134670,157944) ORDER BY kdnr"),
        ("mahnsperre",f"SELECT kdnr, mahnsperre FROM kund WHERE firma={FIRMA} AND kdnr IN (107038,122427,128447,134670,157944) ORDER BY kdnr"),
        ("liefsp",   f"SELECT kdnr, liefsp FROM kund WHERE firma={FIRMA} AND kdnr IN (107038,122427,128447,134670,157944) ORDER BY kdnr"),
    ]
    for field_name, sql in kund_fields:
        rows = run(cur, f"kund.{field_name}", sql)
        if rows:
            log(f"  kund.{field_name} EXISTS: {[(r[0],r[1]) for r in rows]}")

    # Also try f090 for a block flag field
    f090_fields = [
        ("sperre",  f"SELECT auftrag, sperre FROM f090 WHERE firma={FIRMA} AND auftrag IN ({fmt_in(aut_711_under[:5] if aut_711_under else [0])})"),
        ("sperr",   f"SELECT auftrag, sperr FROM f090 WHERE firma={FIRMA} AND auftrag IN ({fmt_in(aut_711_under[:5] if aut_711_under else [0])})"),
        ("kreditsp",f"SELECT auftrag, kreditsp FROM f090 WHERE firma={FIRMA} AND auftrag IN ({fmt_in(aut_711_under[:5] if aut_711_under else [0])})"),
    ]
    for field_name, sql in f090_fields:
        rows = run(cur, f"f090.{field_name}", sql)
        if rows:
            log(f"  f090.{field_name} EXISTS: {rows[:5]}")

    # ============================================================
    # 7. SNAPSHOT SIMULTANEO
    # ============================================================
    print("\n*** TOMAR SCREENSHOT DE PANTALLA AHORA ***\n")
    log("\n=== SNAPSHOT SIMULTANEO ===")
    ts = datetime.now()
    log(f"  Timestamp: {ts}")

    # The 14 orders hypothesis: bel=7+11 NOT OVER (ords=14)
    # but positions could come from bel=6+7+11 or just bel=6
    # Let's try all combos

    # BACK: ords from bel=7+11, pos from bel=7+11 (28 pos)
    if aut_711_under:
        for r in run(cur, "snap BACK bel=7+11 NOT OVER kzerl=0", f"""
            SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
            FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
              AND h.auftrag=p.auftrag AND p.kzerl='0'
              AND h.aufkstat=0 AND h.belegart IN (7,11)
              AND h.kdnr NOT IN ({fmt_in(over_6711)})
        """):
            log(f"  [BACK bel=7+11 NOT OVER kzerl=0] ords={r[0]}  pos={r[1]}  val={r[2]}")

    # BACK: all bel(6,7,11) NOT OVER kzerl=0 (= 22 ords before)
    for r in run(cur, "snap BACK bel(6,7,11) NOT OVER kzerl=0", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.kzerl='0'
          AND h.aufkstat=0 AND h.belegart IN (6,7,11)
          AND h.kdnr NOT IN ({fmt_in(over_6711)})
    """):
        log(f"  [BACK bel(6,7,11) NOT OVER kzerl=0] ords={r[0]}  pos={r[1]}  val={r[2]}")

    # BLOQ: aufkstat=0 bel(6,7,11) IN over
    for r in run(cur, "snap BLOQ bel(6,7,11) IN over", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND p.kzerl='0'
          AND h.aufkstat=0 AND h.belegart IN (6,7,11)
          AND h.kdnr IN ({fmt_in(over_6711)})
    """):
        log(f"  [BLOQ bel(6,7,11) IN over] ords={r[0]}  pos={r[1]}  val={r[2]}")

    # REMITOS, PRODUCCION, VENTA
    for r in run(cur, "REMITOS", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND h.belegart=11 AND h.aufkstat=4
    """):
        log(f"  [REMITOS] ords={r[0]}  pos={r[1]}  val={r[2]}")

    for r in run(cur, "PRODUCCION", f"""
        SELECT COUNT(DISTINCT h.auftrag) ords, COUNT(*) pos, SUM(p.poswert) val
        FROM f090 h, f092 p WHERE h.firma={FIRMA} AND p.firma={FIRMA}
          AND h.auftrag=p.auftrag AND h.aufkstat=2 AND p.posstat=2 AND p.kzerl='0'
    """):
        log(f"  [PRODUCCION] ords={r[0]}  pos={r[1]}  val={r[2]}")

    for r in run(cur, "VENTA", f"""
        SELECT COUNT(DISTINCT renr) docs, COUNT(*) pos, SUM(netwert) val
        FROM sbas WHERE firma={FIRMA} AND redat=TODAY AND belegart IN (8,11)
    """):
        log(f"  [VENTA] docs={r[0]}  pos={r[1]}  val={r[2]}")

    log(f"  End Timestamp: {datetime.now()}")

    conn.close()

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\nListo -> {OUTPUT_FILE}")


if __name__ == "__main__":
    main()

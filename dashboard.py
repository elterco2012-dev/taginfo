"""
Würth Operations Dashboard - Reactor (MySQL) + MSPA (Informix)
SOLO LECTURA — no INSERT/UPDATE/DELETE/DDL.

Uso: python.exe dashboard.py
Abrir: http://localhost:8765
"""

import json
import decimal
import pyodbc
import threading
import base64
import os
import calendar
from datetime import date, datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer


class _Enc(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            return float(o)
        if isinstance(o, (datetime, date)):
            return str(o)
        return super().default(o)


DSN_MSPA    = "MSPA"
DSN_REACTOR = "Wurth Reactor Produccion"
FIRMA       = 1
PORT        = 8765
MSPA_TTL    = 60
REACTOR_TTL = 600

_lock           = threading.Lock()
_cache_mspa     = None
_cache_mspa_ts  = None
_cache_reactor  = None
_cache_react_ts = None


def get_mspa():
    return pyodbc.connect(f"DSN={DSN_MSPA};", autocommit=True)

def get_reactor():
    return pyodbc.connect(f"DSN={DSN_REACTOR};", autocommit=True)

def run(cur, sql, params=None):
    try:
        cur.execute(sql, params) if params else cur.execute(sql)
        return cur.fetchall()
    except Exception as e:
        print(f"  SQL ERROR: {e}")
        return []


def _load_logo():
    here = os.path.dirname(os.path.abspath(__file__))
    for name in ["og-image.png", "wurth_logo.png", "logo.png", "wurth.png",
                 "wurth_logo.jpg", "logo.jpg", "wurth_logo.svg", "logo.svg"]:
        path = os.path.join(here, name)
        if os.path.exists(path):
            ext  = name.rsplit(".", 1)[-1]
            mime = "image/svg+xml" if ext == "svg" else f"image/{ext}"
            with open(path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            return f'<img src="data:{mime};base64,{b64}" style="height:36px;width:auto" alt="Würth">'
    return '<div class="logo-text-fallback"><span class="lw">W</span><span class="ln">WÜRTH</span></div>'

LOGO_HTML = _load_logo()


# ─────────────────────────────────────────────────────────────────────────────
# REACTOR fetch
# ─────────────────────────────────────────────────────────────────────────────
def fetch_reactor(target_date=None):
    conn = get_reactor()
    cur  = conn.cursor()

    if target_date:
        target_str = target_date
        target_dt  = date.fromisoformat(target_date)
    else:
        # Most recent order_date with significant activity
        rows = run(cur, """
            SELECT DATE(order_date) d FROM order_placed
            GROUP BY DATE(order_date) HAVING COUNT(*) >= 50
            ORDER BY d DESC LIMIT 1
        """)
        target     = rows[0][0] if rows else (date.today() - timedelta(days=1))
        target_str = str(target)
        target_dt  = target if isinstance(target, date) else date.fromisoformat(target_str)

    # KPIs — sin JOIN a order_detail para evitar multiplicar el total por cada línea
    rows = run(cur, """
        SELECT COUNT(DISTINCT id) pedidos,
               COUNT(DISTINCT id_user) vendedores,
               SUM(total) valor
        FROM order_placed
        WHERE DATE(order_date) = ?
    """, (target_str,))
    pedidos, vendedores, valor = rows[0] if rows else (0, 0, 0)
    pedidos    = pedidos    or 0
    vendedores = vendedores or 0
    valor      = float(valor or 0)

    # Líneas — query separada para no multiplicar el total
    lineas_rows = run(cur, """
        SELECT COUNT(od.id) lineas
        FROM order_placed op
        JOIN order_detail od ON od.id_order_placed = op.id
        WHERE DATE(op.order_date) = ?
    """, (target_str,))
    lineas = lineas_rows[0][0] if lineas_rows else 0
    lineas = lineas or 0

    # By status
    status_rows = run(cur, """
        SELECT op.id_order_status, os.name, COUNT(*) cnt, SUM(op.total) val
        FROM order_placed op
        JOIN order_status os ON os.id = op.id_order_status
        WHERE DATE(op.order_date) = ?
        GROUP BY op.id_order_status, os.name ORDER BY op.id_order_status
    """, (target_str,))
    by_status = {}
    for r in status_rows:
        by_status[int(r[0])] = {"name": r[1], "cnt": r[2], "val": float(r[3] or 0)}

    # Monthly trend — 12 COMPLETE months (fix: start from 1st of month 11 months ago)
    trend_rows = run(cur, """
        SELECT DATE_FORMAT(order_date, '%Y-%m') mes,
               COUNT(DISTINCT id) pedidos,
               SUM(total) valor
        FROM order_placed
        WHERE order_date >= DATE_FORMAT(DATE_SUB(CURDATE(), INTERVAL 11 MONTH), '%Y-%m-01')
          AND DATE(order_date) <= CURDATE()
        GROUP BY DATE_FORMAT(order_date, '%Y-%m')
        ORDER BY mes
    """)

    # Work days per month
    wd_rows = run(cur, """
        SELECT CONCAT(year, '-', LPAD(month, 2, '0')) mes, days
        FROM work_days
        WHERE year >= YEAR(CURDATE()) - 1
        ORDER BY year, month
    """)
    wd_map = {r[0]: r[1] for r in wd_rows} if wd_rows else {}

    # Exact business day per calendar date from work_days_log
    # real_date = date, working_day = business day number within month
    wdl_rows = run(cur, """
        SELECT DATE_FORMAT(real_date, '%Y-%m-%d'), working_day
        FROM work_days_log
        WHERE real_date >= DATE_FORMAT(DATE_SUB(CURDATE(), INTERVAL 13 MONTH), '%Y-%m-01')
    """)
    wd_log = {str(r[0]): int(r[1]) for r in (wdl_rows or []) if r[0] and r[1]}

    trend = []
    for r in trend_rows:
        mes    = r[0]
        peds   = r[1] or 0
        val    = float(r[2] or 0)
        dias   = wd_map.get(mes, 0)
        avg_pd = round(peds / dias, 1) if dias else None
        trend.append({"mes": mes, "pedidos": peds, "valor": val,
                       "dias_hab": dias, "avg_dia": avg_pd})

    # Inverse wd_log: (year, month, wd_num) -> date_str
    wd_inverse = {}
    for ds, wn in wd_log.items():
        try:
            y2, m2, _ = ds.split('-')
            wd_inverse[(int(y2), int(m2), wn)] = ds
        except Exception:
            pass

    # Comparison: mismo día hábil del mes anterior (no mismo día calendario)
    comp = None
    try:
        target_wd_num = wd_log.get(target_str)  # ej: 19
        if target_wd_num:
            prev_m = target_dt.month - 1 if target_dt.month > 1 else 12
            prev_y = target_dt.year if target_dt.month > 1 else target_dt.year - 1
            # Si el mes anterior tuvo menos días hábiles, usar el último disponible
            max_wd_prev = max((wn for (y2, m2, wn) in wd_inverse if y2 == prev_y and m2 == prev_m),
                              default=None)
            eff_wd = min(target_wd_num, max_wd_prev) if max_wd_prev else None
            prev_date_str = wd_inverse.get((prev_y, prev_m, eff_wd)) if eff_wd else None
            if prev_date_str:
                prev_dt = date.fromisoformat(prev_date_str)
            else:
                # Fallback: mismo día calendario si no hay wd_log para ese mes
                if target_dt.month == 1:
                    prev_dt = target_dt.replace(year=target_dt.year - 1, month=12)
                else:
                    last_day_prev = calendar.monthrange(target_dt.year, target_dt.month - 1)[1]
                    prev_dt = target_dt.replace(month=target_dt.month - 1,
                                                day=min(target_dt.day, last_day_prev))
        else:
            # target no está en wd_log (fin de semana/feriado): fallback calendario
            if target_dt.month == 1:
                prev_dt = target_dt.replace(year=target_dt.year - 1, month=12)
            else:
                last_day_prev = calendar.monthrange(target_dt.year, target_dt.month - 1)[1]
                prev_dt = target_dt.replace(month=target_dt.month - 1,
                                            day=min(target_dt.day, last_day_prev))
        comp_rows = run(cur, """
            SELECT COUNT(DISTINCT id) pedidos, COUNT(DISTINCT id_user) vendedores, SUM(total) valor
            FROM order_placed WHERE DATE(order_date) = ?
        """, (str(prev_dt),))
        comp_lin = run(cur, """
            SELECT COUNT(od.id) FROM order_placed op
            JOIN order_detail od ON od.id_order_placed = op.id
            WHERE DATE(op.order_date) = ?
        """, (str(prev_dt),))
        if comp_rows and comp_rows[0][0]:
            cp = comp_rows[0]
            c_ped  = cp[0] or 0
            c_vend = cp[1] or 0
            c_lin  = comp_lin[0][0] if comp_lin else 0
            comp = {"pedidos":      c_ped,
                    "vendedores":   c_vend,
                    "valor":        float(cp[2] or 0),
                    "avg_lineas":   round(c_lin / c_ped, 1) if c_ped else 0,
                    "avg_ped_vend": round(c_ped / c_vend, 1) if c_vend else 0,
                    "date":         str(prev_dt),
                    "wd_num":       eff_wd if target_wd_num else None}
    except Exception as e:
        print(f"  comp error: {e}")
        comp = None

    # Monthly meta
    curr_month = target_dt.strftime("%Y-%m")
    last_month = ((target_dt.replace(day=1) - timedelta(days=1))).strftime("%Y-%m")
    meta_rows  = run(cur, """
        SELECT DATE_FORMAT(order_date, '%Y-%m') mes,
               COUNT(DISTINCT id) pedidos, SUM(total) valor
        FROM order_placed
        WHERE DATE_FORMAT(order_date, '%Y-%m') IN (?, ?)
        GROUP BY DATE_FORMAT(order_date, '%Y-%m')
    """, (curr_month, last_month))
    meta_by = {r[0]: {"pedidos": r[1] or 0, "valor": float(r[2] or 0)} for r in meta_rows}

    days_in_month = calendar.monthrange(target_dt.year, target_dt.month)[1]
    curr_wd       = wd_map.get(curr_month, 0)
    last_wd       = wd_map.get(last_month, 0)
    # Usar lookup exacto de work_days_log si está disponible
    dias_elapsed  = wd_log.get(target_str,
                        round(curr_wd * target_dt.day / days_in_month) if curr_wd else target_dt.day)
    meta = {
        "curr_month":    curr_month,
        "last_month":    last_month,
        "curr_pedidos":  meta_by.get(curr_month, {}).get("pedidos", 0),
        "curr_valor":    meta_by.get(curr_month, {}).get("valor", 0),
        "last_pedidos":  meta_by.get(last_month, {}).get("pedidos", 0),
        "last_valor":    meta_by.get(last_month, {}).get("valor", 0),
        "curr_wd":       curr_wd,
        "last_wd":       last_wd,
        "dias_elapsed":  dias_elapsed,
        "day_of_month":  target_dt.day,
        "days_in_month": days_in_month,
    }

    # Sellers with most RETENIDOS today (status 15)
    # Try to get user names from users table
    user_names = {}
    supervisor_map = {}
    for name_col in ["name", "username", "full_name", "nombre", "first_name",
                     "apellido", "display_name", "lastname", "email"]:
        nr = run(cur, f"SELECT id, {name_col} FROM users LIMIT 1")
        if nr:
            all_u = run(cur, f"SELECT id, {name_col} FROM users")
            user_names = {r[0]: str(r[1]) for r in (all_u or []) if r[1]}
            break
    # Try to find supervisor field
    for sup_col in ["supervisor_id", "manager_id", "reports_to", "jefe_id", "parent_id"]:
        sr = run(cur, f"SELECT id, {sup_col} FROM users LIMIT 1")
        if sr:
            sup_rows = run(cur, f"SELECT id, {sup_col} FROM users")
            supervisor_map = {r[0]: r[1] for r in (sup_rows or []) if r[1]}
            break

    def seller_name(uid):
        n = user_names.get(uid, "")
        code = f"({uid})"
        sup_id = supervisor_map.get(uid)
        sup_n  = user_names.get(sup_id, "") if sup_id else ""
        if n:
            return f"{n} {code}" + (f" — {sup_n}" if sup_n else "")
        return f"Vend. {uid}"

    ret_rows = run(cur, """
        SELECT id_user, COUNT(*) cnt, SUM(total) val
        FROM order_placed
        WHERE DATE(order_date) = ? AND id_order_status = 15
        GROUP BY id_user ORDER BY cnt DESC LIMIT 15
    """, (target_str,))
    sellers_ret = [{"id": r[0], "nombre": seller_name(r[0]),
                    "cnt": int(r[1] or 0), "val": float(r[2] or 0)} for r in ret_rows]

    an_rows = run(cur, """
        SELECT id_user, COUNT(*) cnt, SUM(total) val
        FROM order_placed
        WHERE DATE(order_date) = ? AND id_order_status = 14
        GROUP BY id_user ORDER BY cnt DESC LIMIT 15
    """, (target_str,))
    sellers_an = [{"id": r[0], "nombre": seller_name(r[0]),
                   "cnt": int(r[1] or 0), "val": float(r[2] or 0)} for r in an_rows]

    # Sparklines — últimos 14 días hábiles (reusa wd_log ya consultado)
    sparklines = {"pedidos": [], "ventas": [], "ped_vend": [], "avg_lin": []}
    try:
        if wd_log:
            spark_dates = sorted(d for d in wd_log if d <= target_str)[-14:]
            if len(spark_dates) >= 2:
                ph = ",".join(["?"] * len(spark_dates))
                sp_rows = run(cur, f"""
                    SELECT DATE(order_date) fecha,
                           COUNT(DISTINCT id) pedidos,
                           COUNT(DISTINCT id_user) vendedores,
                           SUM(total) valor
                    FROM order_placed
                    WHERE DATE(order_date) IN ({ph})
                    GROUP BY DATE(order_date)
                    ORDER BY fecha
                """, tuple(spark_dates))
                sp_lin = run(cur, f"""
                    SELECT DATE(op.order_date) fecha,
                           COUNT(od.id) lineas,
                           COUNT(DISTINCT op.id) pedidos
                    FROM order_placed op
                    JOIN order_detail od ON od.id_order_placed = op.id
                    WHERE DATE(op.order_date) IN ({ph})
                    GROUP BY DATE(op.order_date)
                    ORDER BY fecha
                """, tuple(spark_dates))
                lin_by_date = {str(r[0]): (r[1] or 0, r[2] or 0) for r in (sp_lin or [])}
                for row in (sp_rows or []):
                    fd   = str(row[0])
                    ped  = int(row[1] or 0)
                    vend = int(row[2] or 0)
                    val  = float(row[3] or 0)
                    lin, lped = lin_by_date.get(fd, (0, 0))
                    sparklines["pedidos"].append(ped)
                    sparklines["ventas"].append(round(val / 1e6, 3))
                    sparklines["ped_vend"].append(round(ped / vend, 2) if vend else 0)
                    sparklines["avg_lin"].append(round(lin / lped, 2) if lped else 0)
    except Exception as e:
        print(f"  sparklines error: {e}")

    conn.close()

    return {
        "target_date":         target_str,
        "target_date_display": target_dt.strftime("%d/%m/%Y"),
        "pedidos":      pedidos,
        "vendedores":   vendedores,
        "valor":        valor,
        "lineas":       lineas,
        "avg_lineas":   round(lineas / pedidos, 1) if pedidos else 0,
        "avg_ped_vend": round(pedidos / vendedores, 1) if vendedores else 0,
        "by_status":    by_status,
        "trend":        trend,
        "has_workdays": bool(wd_map),
        "wd_map":       wd_map,
        "wd_log":       wd_log,
        "comp":         comp,
        "meta":         meta,
        "sellers_ret":  sellers_ret,
        "sellers_an":   sellers_an,
        "sparklines":   sparklines,
    }


# ─────────────────────────────────────────────────────────────────────────────
# MSPA fetch
# ─────────────────────────────────────────────────────────────────────────────
def fetch_mspa(target_date=None):
    conn = get_mspa()
    cur  = conn.cursor()

    # Fecha objetivo — para queries sbas y vplan
    if target_date:
        td      = date.fromisoformat(target_date)
        tday    = f"MDY({td.month},{td.day},{td.year})"
        t_year  = td.year
        t_month = td.month
    else:
        tday    = "TODAY"
        _today  = date.today()
        t_year  = _today.year
        t_month = _today.month

    def q(sql):
        rows = run(cur, sql)
        if rows:
            return {"ords": rows[0][0] or 0, "pos": rows[0][1] or 0,
                    "val": float(rows[0][2]) if rows[0][2] else 0.0}
        return {"ords": 0, "pos": 0, "val": 0.0}

    backorders = q(f"""
        SELECT COUNT(DISTINCT f092.auftrag), COUNT(*),
               SUM(f092.poswert/f092.auftme * (f092.auftme - f092.gliefme))
          FROM f090, f092, kund
         WHERE f092.firma={FIRMA} AND f090.firma=f092.firma AND kund.firma=f090.firma
           AND f090.auftrag=f092.auftrag AND kund.kdnr=f090.kdnr
           AND f092.termin <= TODAY AND f092.kzentns='0' AND f090.aufkstat >= 0
           AND f090.aufart IN ('0','2','4','6','7','8')
           AND (f092.auftme - f092.gliefme) > 0 AND f092.kzerl='0' AND f092.auftme <> 0
           AND ((kund.liefsp <> '2' AND kund.liefsp <> '9') OR f090.liefspkz = '1')
    """)
    bloqueados = q(f"""
        SELECT COUNT(DISTINCT f092.auftrag), COUNT(*),
               SUM(f092.poswert/f092.auftme * (f092.auftme - f092.gliefme))
          FROM f090, f092, kund
         WHERE f092.firma={FIRMA} AND f090.firma=f092.firma AND kund.firma=f090.firma
           AND f090.auftrag=f092.auftrag AND kund.kdnr=f090.kdnr
           AND f092.posstat < 9 AND (f090.aufkstat >= 0 OR f090.aufkstat = -9)
           AND f090.aufart IN ('0','2','4','6','7','8')
           AND (f092.auftme - f092.gliefme) > 0 AND f092.kzerl='0' AND f092.auftme <> 0
           AND ((kund.liefsp = '2' OR kund.liefsp = '9') AND f090.liefspkz <> '1')
    """)
    neg_status = q(f"""
        SELECT COUNT(DISTINCT f092.auftrag), COUNT(*),
               SUM(f092.poswert/f092.auftme * (f092.auftme - f092.gliefme))
          FROM f090, f092, kund
         WHERE f092.firma={FIRMA} AND f090.firma=f092.firma AND kund.firma=f090.firma
           AND f090.auftrag=f092.auftrag AND kund.kdnr=f090.kdnr
           AND f092.posstat < 9 AND f090.aufkstat < -1
           AND f090.aufart IN ('0','2','4','6','7','8')
           AND (f092.auftme - f092.gliefme) > 0 AND f092.kzerl='0' AND f092.auftme <> 0
           AND ((kund.liefsp <> '2' AND kund.liefsp <> '9') OR f090.liefspkz = '1')
    """)
    futuros = q(f"""
        SELECT COUNT(DISTINCT f092.auftrag), COUNT(*),
               SUM(f092.poswert/f092.auftme * (f092.auftme - f092.gliefme))
          FROM f090, f092, kund
         WHERE f092.firma={FIRMA} AND f090.firma=f092.firma AND kund.firma=f090.firma
           AND f090.auftrag=f092.auftrag AND kund.kdnr=f090.kdnr
           AND f092.termin > TODAY AND f090.aufkstat >= 0
           AND f090.aufart IN ('0','2','4','6','7','8')
           AND (f092.auftme - f092.gliefme) > 0 AND f092.kzerl='0' AND f092.auftme <> 0
           AND ((kund.liefsp <> '2' AND kund.liefsp <> '9') OR f090.liefspkz = '1')
    """)
    produccion = q(f"""
        SELECT COUNT(DISTINCT f103.auftrag), COUNT(*),
               SUM(f092.poswert/f092.auftme * f103.sollme)
          FROM f103, f090, f092
         WHERE f103.firma={FIRMA} AND f090.firma=f103.firma AND f092.firma=f103.firma
           AND f103.auftrag=f090.auftrag AND f103.auftrag=f092.auftrag
           AND f103.posnr=f092.posnr AND f092.auftme <> 0
           AND (f103.kzdfue = 0 OR f103.kzdfue IS NULL)
    """)
    ls = q(f"""
        SELECT COUNT(DISTINCT f105.auftrag), COUNT(*),
               SUM(f092.poswert/f092.auftme * f105.liefme)
          FROM f105, f090, f092
         WHERE f105.firma={FIRMA} AND f090.firma=f105.firma AND f092.firma=f105.firma
           AND f105.auftrag=f090.auftrag AND f105.auftrag=f092.auftrag
           AND f105.posnr=f092.posnr AND f092.auftme <> 0
           AND f105.liefnr IN (SELECT liefnr FROM f104 WHERE f104.firma={FIRMA} AND f104.liefstat < 9)
    """)
    re = q(f"""
        SELECT COUNT(DISTINCT f107.auftrag), COUNT(*),
               SUM(f092.poswert/f092.auftme * f107.faktme)
          FROM f107, f090, f092, f106
         WHERE f107.firma={FIRMA} AND f107.firma=f106.firma AND f107.liefnr=f106.liefnr
           AND f090.firma=f107.firma AND f092.firma=f107.firma
           AND f107.auftrag=f090.auftrag AND f107.auftrag=f092.auftrag
           AND f107.posnr=f092.posnr AND f107.lieflfdnr=0 AND f092.auftme <> 0
           AND f090.aufart IN ('0','2','4','6','7','8')
           AND (f106.periode='0' OR f106.periode=' ' OR f106.periode IS NULL)
    """)
    remitos = {"ords": ls["ords"]+re["ords"], "pos": ls["pos"]+re["pos"], "val": ls["val"]+re["val"]}
    venta = q(f"""
        SELECT COUNT(DISTINCT auftrag), COUNT(*), SUM(netwert)
          FROM sbas WHERE firma={FIRMA} AND redat={tday}
    """)

    # ── Top 5 facturación del día — sbas JOIN f040 para nombres reales ────────
    fact_rows = run(cur, f"""
        SELECT s.vertr1, f.name1, COUNT(DISTINCT s.auftrag) ped, SUM(s.netwert) val
          FROM sbas s, f040 f
         WHERE s.firma={FIRMA} AND f.firma=s.firma AND f.vertr=s.vertr1
           AND s.redat={tday} AND s.netwert > 0
         GROUP BY s.vertr1, f.name1 ORDER BY val DESC
    """)
    if not fact_rows:
        fact_rows_raw = run(cur, f"""
            SELECT vertr1, COUNT(DISTINCT auftrag) ped, SUM(netwert) val
              FROM sbas WHERE firma={FIRMA} AND redat={tday} AND netwert > 0
             GROUP BY vertr1 ORDER BY val DESC
        """)
        fact_rows = [(r[0], f"Vend. {r[0]}", r[1], r[2]) for r in fact_rows_raw]

    sellers_fact_top5 = [
        {"vertr":  str(r[0] or '').strip(),
         "nombre": f"{str(r[1] or '').strip()} ({str(r[0] or '').strip()})",
         "ped":    int(r[2] or 0),
         "val":    float(r[3] or 0)}
        for r in fact_rows[:5]
    ]

    # ── Plan de ventas mensual — vplan JOIN f040 JOIN sbas ─────────────────
    # vplan cols: firma, vertr, bujahr, bumonat, planums, plannutz, planumsk, aktivkd, ...
    plan_rows = run(cur, f"""
        SELECT v.vertr, f.name1, v.planums,
               SUM(s.netwert) fact_acum
          FROM vplan v, f040 f, sbas s
         WHERE v.firma={FIRMA} AND f.firma=v.firma AND f.vertr=v.vertr
           AND s.firma=v.firma AND s.vertr1=v.vertr
           AND v.bujahr={t_year} AND v.bumonat={t_month}
           AND s.bujahr={t_year} AND s.bumonat={t_month}
           AND s.redat <= {tday}
         GROUP BY v.vertr, f.name1, v.planums
         ORDER BY v.planums DESC
    """)
    # Fallback: totales sin desglose por vendedor si el JOIN falla
    if not plan_rows:
        plan_tot = run(cur, f"""
            SELECT SUM(planums) FROM vplan
             WHERE firma={FIRMA} AND bujahr={t_year} AND bumonat={t_month}
        """)
        fact_tot = run(cur, f"""
            SELECT SUM(netwert) FROM sbas
             WHERE firma={FIRMA} AND bujahr={t_year} AND bumonat={t_month}
             AND redat <= {tday}
        """)
        plan_total = float(plan_tot[0][0] or 0) if plan_tot else 0
        fact_acum  = float(fact_tot[0][0] or 0) if fact_tot else 0
        sellers_plan = []
    else:
        plan_total = sum(float(r[2] or 0) for r in plan_rows)
        fact_acum  = sum(float(r[3] or 0) for r in plan_rows)
        sellers_plan = [
            {"vertr": str(r[0] or '').strip(), "nombre": str(r[1] or '').strip(),
             "plan": float(r[2] or 0), "fact": float(r[3] or 0),
             "pct": round(float(r[3] or 0) / float(r[2]) * 100, 1) if r[2] else 0}
            for r in plan_rows
        ]

    # Mapa de vendedores activos: deben tener sbas en el mes objetivo o el anterior
    # Filtra vendedores que dejaron de trabajar (sin actividad reciente)
    if t_month > 1:
        act_q = f"""SELECT DISTINCT vertr1 FROM sbas WHERE firma={FIRMA}
                    AND bujahr={t_year} AND bumonat IN ({t_month},{t_month-1})"""
    else:
        act_q = f"""SELECT DISTINCT vertr1 FROM sbas WHERE firma={FIRMA}
                    AND ((bujahr={t_year} AND bumonat=1)
                      OR (bujahr={t_year-1} AND bumonat=12))"""
    act_rows     = run(cur, act_q)
    active_vertrs = {str(r[0]).strip() for r in (act_rows or []) if r[0]}
    all_names    = run(cur, f"SELECT vertr, name1 FROM f040 WHERE firma={FIRMA} AND name1 IS NOT NULL")
    vertr_names  = {str(r[0]).strip(): str(r[1]).strip()
                    for r in (all_names or []) if r[1] and str(r[0]).strip() in active_vertrs}

    plan_ventas = {
        "plan_total": plan_total,
        "fact_acum":  fact_acum,
        "pct_plan":   round(fact_acum / plan_total * 100, 1) if plan_total else 0,
        "sellers":    sellers_plan,
    }

    conn.close()
    return {
        "backorders":       backorders,
        "bloqueados":       bloqueados,
        "neg_status":       neg_status,
        "futuros":          futuros,
        "produccion":       produccion,
        "remitos":          remitos,
        "venta":            venta,
        "sellers_fact_top": sellers_fact_top5,
        "plan_ventas":      plan_ventas,
        "vertr_names":      vertr_names,
    }


# ─────────────────────────────────────────────────────────────────────────────
def _get_cached(ttl, fetcher, name):
    global _cache_mspa, _cache_mspa_ts, _cache_reactor, _cache_react_ts
    now  = datetime.now()
    ts   = _cache_mspa_ts if name == "mspa" else _cache_react_ts
    data = _cache_mspa    if name == "mspa" else _cache_reactor
    if data is None or ts is None or (now - ts).total_seconds() >= ttl:
        print(f"  [{now.strftime('%H:%M:%S')}] Refresh {name}...")
        try:
            data = fetcher()
            if name == "mspa":
                _cache_mspa, _cache_mspa_ts = data, now
            else:
                _cache_reactor, _cache_react_ts = data, now
            print(f"  [{now.strftime('%H:%M:%S')}] {name} OK")
        except Exception as e:
            print(f"  [{now.strftime('%H:%M:%S')}] {name} ERROR: {e}")
            if data is None:
                data = {"error": str(e)}
    return data


def get_cached_data(override_date=None):
    now = datetime.now()
    if override_date:
        # Fecha manual: fetch directo sin cache — todos los datos para esa fecha
        try:
            reactor = fetch_reactor(target_date=override_date)
        except Exception as e:
            reactor = {"error": str(e)}
        try:
            mspa = fetch_mspa(target_date=override_date)
        except Exception as e:
            mspa = {"error": str(e)}
        r_age, m_age = 0, 0
    else:
        with _lock:
            reactor = _get_cached(REACTOR_TTL, fetch_reactor, "reactor")
            mspa    = _get_cached(MSPA_TTL,    fetch_mspa,    "mspa")
        r_age = int((now - _cache_react_ts).total_seconds()) if _cache_react_ts else 0
        m_age = int((now - _cache_mspa_ts).total_seconds())  if _cache_mspa_ts  else 0

    r_err = reactor.pop("error", None) if isinstance(reactor, dict) else None
    m_err = mspa.pop("error", None)    if isinstance(mspa, dict)    else None

    # Enriquecer sellers de Reactor con nombres de f040 de MSPA
    # Solo mostrar vendedores que matchean en f040 (vertr = id_user)
    # Los que no matchean son IDs de otro sistema, no "inactivos"
    if isinstance(reactor, dict) and isinstance(mspa, dict):
        vnames = mspa.get("vertr_names", {})
        for lst in ("sellers_ret", "sellers_an"):
            enriched = []
            for s in reactor.get(lst, []):
                uid = str(s.get("id", "")).strip()
                if uid in vnames:
                    s["nombre"]   = f"{vnames[uid]} ({uid})"
                    s["inactive"] = False
                    enriched.append(s)
            reactor[lst] = enriched

    return {
        "timestamp":      now.strftime("%d/%m/%Y %H:%M:%S"),
        "reactor":        reactor or {},
        "mspa":           mspa    or {},
        "reactor_error":  r_err,
        "mspa_error":     m_err,
        "reactor_age":    r_age,
        "mspa_age":       m_age,
        "reactor_next":   max(0, REACTOR_TTL - r_age),
        "mspa_next":      max(0, MSPA_TTL    - m_age),
    }


# ─────────────────────────────────────────────────────────────────────────────
# HTML
# ─────────────────────────────────────────────────────────────────────────────
HTML_PAGE = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Würth — Operations Dashboard</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;600;700&display=swap">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
/* ── TOKENS v3 ── */
:root{
  --wurth-red:#cc0000; --wurth-red-hover:#b00000;
  --bg:#f0f2f5; --surface:#ffffff; --surface-2:#f8fafc;
  --border:#e2e8f0; --border-2:#cbd5e1;
  --text:#0f172a; --text-2:#475569; --text-3:#94a3b8;
  --blue:#2563eb; --green:#059669; --amber:#d97706; --red:#dc2626;
  --amber-bg:#fffbeb; --red-bg:#fef2f2; --green-bg:#f0fdf4;
  --pos-bg:#dcfce7; --pos-fg:#15803d; --neg-bg:#fee2e2; --neg-fg:#b91c1c;
  --r-card:10px;
  --shadow-pop:0 8px 24px rgba(0,0,0,.15);
  --font-sans:'IBM Plex Sans',-apple-system,BlinkMacSystemFont,'Segoe UI',system-ui,sans-serif;
  /* aliases para compatibilidad con inline styles */
  --surface2:var(--surface-2); --border2:var(--border-2);
  --text2:var(--text-2); --text3:var(--text-3);
}
body.dark{
  --bg:#0f172a; --surface:#1e293b; --surface-2:#0f1a30;
  --border:#334155; --border-2:#475569;
  --text:#f1f5f9; --text-2:#cbd5e1; --text-3:#64748b;
  --amber-bg:#3b2800; --red-bg:#3b0d0d; --green-bg:#052e16;
  --pos-bg:#052e16; --neg-bg:#3b0d0d;
  --shadow-pop:0 8px 24px rgba(0,0,0,.5);
}
*{margin:0;padding:0;box-sizing:border-box}
body{background:var(--bg);color:var(--text);font-family:var(--font-sans);font-size:13px;transition:background .25s,color .25s}
.num{font-variant-numeric:tabular-nums;font-feature-settings:"tnum"}
.ico{width:15px;height:15px;stroke-width:1.75;vertical-align:-2px;flex-shrink:0}
.ico-sm{width:13px;height:13px;stroke-width:1.75;vertical-align:-2px}

/* ── HIST BANNER ── */
.hist-banner{display:none;background:#7c2d12;color:#fed7aa;text-align:center;padding:8px 24px;font-size:13px;font-weight:700;letter-spacing:.5px;border-bottom:2px solid #ea580c}

/* ── ALERTAS POR EXCEPCIÓN ── */
.alerts{display:flex;flex-direction:column;gap:8px;margin-bottom:4px}
.alert{display:flex;align-items:center;gap:10px;padding:11px 16px;border-radius:var(--r-card);border:1px solid;font-size:13px}
.alert .ico{width:17px;height:17px;flex-shrink:0}
.alert b{font-weight:700}
.alert .a-act{margin-left:auto;font-size:11px;font-weight:600;text-decoration:none;white-space:nowrap;opacity:.8;color:inherit}
.alert.warn{background:var(--amber-bg);border-color:var(--amber);color:var(--amber)}
.alert.danger{background:var(--red-bg);border-color:var(--red);color:var(--neg-fg)}
.alert.danger .ico{color:var(--red)}

/* ── HEADER ── */
.hdr{position:sticky;top:0;z-index:50;background:var(--surface);border-bottom:1px solid var(--border);padding:0 28px;height:58px;display:flex;align-items:center;justify-content:space-between}
.hdr::before{content:'';position:absolute;left:0;top:0;bottom:0;width:3px;background:var(--wurth-red)}
.hdr-left{display:flex;align-items:center;gap:14px}
.logo-text-fallback{display:flex;align-items:center;gap:6px}
.lw{background:var(--wurth-red);color:#fff;font-weight:900;font-size:16px;padding:5px 9px;border-radius:3px;line-height:1}
.ln{font-size:20px;font-weight:900;letter-spacing:3px;color:var(--wurth-red)}
.div-v{width:1px;height:26px;background:var(--border-2)}
.hdr-title{font-size:13px;font-weight:700;color:var(--text);white-space:nowrap;letter-spacing:-.1px}
.hdr-sub{font-size:10px;color:var(--text-3);margin-top:1px;letter-spacing:.3px}
.hdr-right{display:flex;align-items:center;gap:12px;flex-shrink:0}
/* conexión */
.conn{display:flex;flex-direction:column;gap:3px;font-size:10px;color:var(--text-3);text-align:right;line-height:1.3}
.conn-row{display:flex;align-items:center;gap:5px;justify-content:flex-end}
.conn-dot{width:7px;height:7px;border-radius:50%;flex-shrink:0}
.conn-dot.ok{background:var(--green);animation:ring 2.4s ease-out infinite}
.conn-dot.slow{background:var(--amber)}
.conn-dot.down{background:var(--red)}
.conn b{color:var(--text-2);font-variant-numeric:tabular-nums}
@keyframes ring{0%{box-shadow:0 0 0 0 rgba(5,150,105,.4)}70%,100%{box-shadow:0 0 0 5px rgba(5,150,105,0)}}
/* date badge */
.date-badge{display:flex;align-items:center;gap:6px;background:transparent;border:1px solid var(--border-2);border-radius:6px;padding:5px 12px;font-size:12px;color:var(--text);font-weight:600;white-space:nowrap;cursor:pointer;user-select:none;position:relative;transition:background .15s}
.date-badge:hover{background:var(--surface-2)}
.date-badge .ico{color:var(--text-3)}
.date-pop{position:absolute;top:calc(100% + 8px);right:0;z-index:999;background:var(--surface);border:1px solid var(--border-2);border-radius:10px;box-shadow:var(--shadow-pop);padding:14px;min-width:230px;text-align:left;display:none}
.date-pop.open{display:block}
.date-pop h4{font-size:11px;font-weight:700;margin-bottom:8px;color:var(--text)}
.date-pop input{border:1px solid var(--border-2);border-radius:6px;padding:7px 10px;font-size:13px;color:var(--text);background:var(--surface-2);width:100%}
body.dark .date-pop input{color-scheme:dark}
.date-pop .hint{font-size:10px;color:var(--text-3);margin-top:8px;line-height:1.4}
.date-pop .go{margin-top:10px;width:100%;background:var(--wurth-red);color:#fff;border:none;border-radius:6px;padding:7px;font-size:12px;font-weight:700;cursor:pointer}
.date-pop .clr{margin-top:5px;width:100%;background:transparent;color:var(--text-3);border:1px solid var(--border);border-radius:6px;padding:6px;font-size:11px;cursor:pointer}
/* icon buttons */
.icon-btn{display:flex;align-items:center;justify-content:center;cursor:pointer;border:1px solid var(--border-2);border-radius:6px;width:32px;height:30px;background:transparent;color:var(--text-2);transition:all .15s}
.icon-btn:hover{background:var(--surface-2);color:var(--text)}
.icon-btn.on{background:var(--wurth-red);border-color:var(--wurth-red);color:#fff}
.icon-btn .ico{width:16px;height:16px}
.tooltip-info{display:inline-block;color:var(--text-3);font-size:10px;cursor:help;position:relative}
.tooltip-info .tt{display:none;position:absolute;left:50%;transform:translateX(-50%);bottom:calc(100%+4px);background:#1e293b;color:#f1f5f9;padding:6px 10px;border-radius:6px;font-size:10px;white-space:nowrap;z-index:100;line-height:1.5}
.tooltip-info:hover .tt{display:block}

/* ── LAYOUT ── */
.main{padding:20px 28px 40px;display:flex;flex-direction:column;gap:20px;max-width:1440px;margin:0 auto}
.sec{display:flex;flex-direction:column;gap:10px}
.sec-lbl{display:flex;align-items:center;gap:6px;font-size:10px;font-weight:700;letter-spacing:1.4px;text-transform:uppercase;color:var(--text-3);white-space:nowrap}
.sec-lbl .ico{width:13px;height:13px;color:var(--text-3)}
.err{color:var(--red);font-size:11px;margin-top:4px}

/* ── HERO ── */
.hero{display:grid;grid-template-columns:1.5fr 1fr;gap:1px;background:var(--border);border:1px solid var(--border);border-radius:var(--r-card);overflow:hidden}
.hero-main{background:var(--surface);padding:22px 26px}
.hero-side{background:var(--surface);padding:22px 26px;display:flex;flex-direction:column;justify-content:center;gap:18px}
.hero-eyebrow{display:flex;align-items:center;gap:6px;font-size:10px;font-weight:700;letter-spacing:1.4px;text-transform:uppercase;color:var(--text-3);margin-bottom:14px;white-space:nowrap}
.hero-eyebrow .ico{width:13px;height:13px;color:var(--wurth-red)}
.hero-figs{display:flex;align-items:baseline;gap:10px;margin-bottom:4px}
.hero-curr{font-size:46px;font-weight:700;color:var(--text);line-height:1;letter-spacing:-1px;font-variant-numeric:tabular-nums}
.hero-total{font-size:18px;color:var(--text-3);font-weight:600;font-variant-numeric:tabular-nums}
.hero-pct-line{display:flex;align-items:center;gap:10px;margin:14px 0 8px}
.hero-pct{font-size:14px;font-weight:700;font-variant-numeric:tabular-nums;white-space:nowrap}
.plan-bar-bg{background:var(--border);border-radius:6px;height:12px;position:relative;overflow:hidden;flex:1}
.plan-bar-fill{height:100%;border-radius:6px;transition:width .8s ease}
.plan-bar-pace{position:absolute;top:-3px;bottom:-3px;width:2px;background:var(--text);z-index:2}
.plan-bar-pace::after{content:'';position:absolute;top:-3px;left:-2px;border-left:3px solid transparent;border-right:3px solid transparent;border-top:4px solid var(--text)}
.hero-foot{display:flex;justify-content:space-between;font-size:11px;color:var(--text-3);margin-top:4px;font-variant-numeric:tabular-nums}
.hero-proy{display:none;margin-top:14px;padding-top:12px;border-top:1px solid var(--border);font-size:12px;color:var(--text-2);font-variant-numeric:tabular-nums}
.state-tag{display:inline-flex;align-items:center;gap:4px;font-size:11px;padding:3px 9px;border-radius:6px;font-weight:600;white-space:nowrap;flex-shrink:0}
.state-ok{background:var(--pos-bg);color:var(--pos-fg)}
.state-warn{background:var(--amber-bg);color:var(--amber)}
.state-danger{background:var(--neg-bg);color:var(--neg-fg)}
.state-neutral{background:#f1f5f9;color:var(--text-3)}
body.dark .state-neutral{background:#334155;color:var(--text-3)}
.hero-stat .l{font-size:10px;color:var(--text-3);text-transform:uppercase;letter-spacing:.5px;margin-bottom:4px;font-weight:600}
.hero-stat .v{font-size:28px;font-weight:700;color:var(--text);line-height:1;font-variant-numeric:tabular-nums}
.hero-stat .d{margin-top:6px;display:flex;align-items:center;gap:8px}
.hero-stat.alert-warn{background:var(--amber-bg);border-radius:8px;padding:10px 12px}
.hero-stat.alert-danger{background:var(--neg-bg);border-radius:8px;padding:10px 12px}
.hsep{height:1px;background:var(--border)}

/* ── KPI STRIP ── */
.kpi-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:1px;background:var(--border);border:1px solid var(--border);border-radius:var(--r-card);overflow:hidden;min-width:0}
.kpi{background:var(--surface);padding:15px 18px;display:flex;flex-direction:column}
.kpi-lbl{font-size:10px;color:var(--text-3);margin-bottom:7px;font-weight:600;text-transform:uppercase;letter-spacing:.4px}
.kpi-top{display:flex;align-items:flex-end;justify-content:space-between;gap:10px}
.kpi-val{font-size:25px;font-weight:700;line-height:1;color:var(--text);font-variant-numeric:tabular-nums}
.spark{width:74px;height:30px;flex-shrink:0;opacity:.9}
.kpi-foot{display:flex;align-items:center;gap:8px;margin-top:9px;flex-wrap:wrap}
.delta{display:inline-flex;align-items:center;gap:2px;font-size:11px;font-weight:700;font-variant-numeric:tabular-nums}
.delta .ico{width:13px;height:13px}
.delta.up{color:var(--pos-fg)}.delta.down{color:var(--neg-fg)}.delta.flat{color:var(--text-3)}
.meta-chip{display:inline-flex;align-items:center;gap:4px;font-size:10px;color:var(--text-3);font-variant-numeric:tabular-nums}
.meta-chip .dot{width:6px;height:6px;border-radius:50%}
.meta-chip .dot.ok{background:var(--green)}.meta-chip .dot.warn{background:var(--amber)}
.kpi-sub{font-size:10px;color:var(--text-3);margin-top:6px;font-variant-numeric:tabular-nums}

/* ── FLOW BAR ── */
.flow-bar{display:flex;align-items:stretch;background:var(--surface);border:1px solid var(--border);border-radius:var(--r-card);overflow:hidden}
.flow-cell{flex:1;padding:15px 20px;display:flex;flex-direction:column;gap:5px;min-width:0;border-left:1px solid var(--border);position:relative}
.flow-cell:first-child{border-left:none}
.flow-dot{display:flex;align-items:center;gap:7px}
.flow-tick{width:8px;height:8px;border-radius:2px;flex-shrink:0}
.tk-blue{background:var(--blue)}.tk-amber{background:var(--amber)}.tk-red{background:var(--red)}.tk-green{background:var(--green)}
.flow-label{font-size:10px;font-weight:700;letter-spacing:.6px;text-transform:uppercase;color:var(--text-2)}
.flow-val{font-size:24px;font-weight:700;line-height:1;color:var(--text);font-variant-numeric:tabular-nums}
.flow-sub{font-size:11px;color:var(--text-3);font-variant-numeric:tabular-nums}
.alert-icon{position:absolute;top:8px;right:10px;display:flex;align-items:center}
.alert-icon .ico{width:14px;height:14px;color:var(--amber)}
.flow-cell.pulse-warn{background:var(--amber-bg);animation:bgpulse 3s ease-in-out infinite}
.flow-cell.pulse-danger{background:var(--neg-bg);animation:bgpulse 1.8s ease-in-out infinite}
@keyframes bgpulse{0%,100%{opacity:1}50%{opacity:.65}}

/* ── META MENSUAL ── */
.meta-card{background:var(--surface);border:1px solid var(--border);border-radius:var(--r-card);padding:14px 20px}
.meta-row{display:flex;align-items:center;gap:16px;flex-wrap:wrap}
.meta-nums{display:flex;align-items:baseline;gap:6px}
.meta-curr{font-size:22px;font-weight:700;color:var(--blue);font-variant-numeric:tabular-nums}
.meta-sep{color:var(--text-3);font-size:13px}
.meta-last{font-size:15px;font-weight:600;color:var(--text-3);font-variant-numeric:tabular-nums}
.meta-bar-wrap{flex:1;min-width:200px}
.meta-bar-bg{background:var(--border);border-radius:6px;height:10px;position:relative;overflow:hidden}
.meta-bar-fill{height:100%;border-radius:6px;transition:width .8s}
.meta-bar-pace{position:absolute;top:0;bottom:0;width:2px;background:var(--amber)}
.meta-bar-labels{font-size:10px;color:var(--text-3);margin-top:3px;font-variant-numeric:tabular-nums}
.meta-tags{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.meta-tag{font-size:10px;padding:2px 8px;border-radius:12px;font-weight:600}
.tag-ok{background:var(--pos-bg);color:var(--pos-fg)}.tag-warn{background:var(--amber-bg);color:var(--amber)}
.tag-danger{background:var(--neg-bg);color:var(--neg-fg)}.tag-neutral{background:#f1f5f9;color:var(--text-3)}
body.dark .tag-neutral{background:#334155}

/* ── BOTTOM GRID ── */
.bottom{display:grid;grid-template-columns:1fr 380px;gap:18px}
.card{background:var(--surface);border:1px solid var(--border);border-radius:var(--r-card);padding:18px 20px}
.card-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:14px}
.card-head .stamp{font-size:10px;color:var(--text-3);font-variant-numeric:tabular-nums}
.chart-wrap{height:248px;position:relative}

/* ── MSPA ── */
.mspa-row{display:flex;align-items:center;justify-content:space-between;padding:10px 0;border-bottom:1px solid var(--border)}
.mspa-row:last-child{border-bottom:none}
.mspa-l{display:flex;align-items:center;gap:9px}
.mspa-sem{width:7px;height:7px;border-radius:50%;background:var(--green);flex-shrink:0}
.mspa-sem.warn{background:var(--amber)}.mspa-sem.danger{background:var(--red)}
.mspa-lbl{font-size:12px;color:var(--text-2)}
.mspa-val{font-size:14px;font-weight:700;color:var(--text);text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums}
.mspa-sub-txt{font-size:10px;color:var(--text-3);font-weight:400;display:block;text-align:right;margin-top:1px;font-variant-numeric:tabular-nums}
.mspa-row.venta{border-top:1px solid var(--border);margin-top:2px;padding-top:13px}
.mspa-row.venta .mspa-lbl{color:var(--text);font-weight:700}
.mspa-row.venta .mspa-val{color:var(--green);font-size:18px}
.mspa-row.venta .mspa-sem{background:var(--green)}

/* ── SELLERS ── */
.sellers-wrap{display:grid;grid-template-columns:repeat(3,1fr);gap:18px;align-items:start}
.head-ico{display:flex;align-items:center;gap:6px}
.head-ico .ico{width:14px;height:14px}
.ic-fact{color:var(--green)}.ic-ret{color:var(--amber)}.ic-an{color:var(--red)}
.seller-tbl{width:100%;border-collapse:collapse;font-size:12px}
.seller-tbl th{font-size:9px;font-weight:700;letter-spacing:.8px;text-transform:uppercase;color:var(--text-3);padding:0 8px 8px;border-bottom:1px solid var(--border);text-align:left}
.seller-tbl td{padding:9px 8px;border-bottom:1px solid var(--border);font-variant-numeric:tabular-nums}
.seller-tbl tr:last-child td{border-bottom:none}
.seller-tbl tr:hover td{background:var(--surface-2)}
.s-rank{font-weight:700;color:var(--text-3);width:20px;font-size:12px;text-align:center;font-variant-numeric:tabular-nums}
.s-name{font-weight:600;color:var(--text)}
.s-sub{font-size:10px;color:var(--text-3);font-weight:400;font-variant-numeric:tabular-nums}
.s-val{font-weight:700;text-align:right;white-space:nowrap;color:var(--text);font-variant-numeric:tabular-nums}
.fact-val{color:var(--green)}.ret-val{color:var(--amber)}.an-val{color:var(--red)}
.s-pill{display:inline-block;padding:1px 6px;border-radius:10px;font-size:10px;font-weight:700}
.pill-ret{background:var(--amber-bg);color:var(--amber)}.pill-an{background:var(--neg-bg);color:var(--neg-fg)}

/* ── SKELETON (carga inicial) ── */
@keyframes shimmer{0%{background-position:-260px 0}100%{background-position:260px 0}}
.main.is-loading .hero,
.main.is-loading .kpi-grid,
.main.is-loading .flow-bar,
.main.is-loading .meta-card,
.main.is-loading .card{position:relative;overflow:hidden}
.main.is-loading .hero::after,
.main.is-loading .kpi-grid::after,
.main.is-loading .flow-bar::after,
.main.is-loading .meta-card::after,
.main.is-loading .card::after{content:'';position:absolute;inset:0;z-index:5;background:#e2e8f0;background-image:linear-gradient(90deg,#e2e8f0 0px,#f1f5f9 80px,#e2e8f0 160px);background-size:260px 100%;animation:shimmer 1.2s infinite linear}
body.dark .main.is-loading .hero::after,
body.dark .main.is-loading .kpi-grid::after,
body.dark .main.is-loading .flow-bar::after,
body.dark .main.is-loading .meta-card::after,
body.dark .main.is-loading .card::after{background:#1e293b;background-image:linear-gradient(90deg,#1e293b 0px,#283548 80px,#1e293b 160px)}
.main.is-loading .alerts{display:none!important}

/* ── TV MODE ── */
body.tv{font-size:15px}
body.tv .main{max-width:100%;gap:26px;padding:26px 40px}
body.tv .hero-curr{font-size:64px}
body.tv .hero-stat .v{font-size:40px}
body.tv .kpi-val{font-size:34px}
body.tv .flow-val{font-size:32px}
body.tv .spark{width:96px;height:38px}
body.tv .mspa-lbl{font-size:14px}
body.tv .mspa-val{font-size:17px}
body.tv .seller-tbl{font-size:14px}
body.tv .meta-curr{font-size:28px}

@media print{
  .hdr-right .icon-btn,.date-badge{display:none}
  body{background:#fff}
  .card,.hero,.flow-bar,.kpi-grid{break-inside:avoid}
}
/* ── RESPONSIVE ── */
@media(max-width:1080px){.hero{grid-template-columns:1fr}.bottom{grid-template-columns:1fr}.sellers-wrap{grid-template-columns:1fr}.kpi-grid{grid-template-columns:repeat(2,1fr)}}
</style>
</head>
<body>

<div class="hdr">
  <div class="hdr-left">
    @@LOGO@@
    <div class="div-v"></div>
    <div>
      <div class="hdr-title">Operations Dashboard</div>
      <div class="hdr-sub">Reactor · MSPA · Tiempo Real</div>
    </div>
  </div>
  <div class="hdr-right">
    <div class="conn" id="conn-block">
      <span class="conn-row"><span class="conn-dot ok" id="conn-mspa-dot"></span><span id="conn-mspa-txt">MSPA · <b id="last-update">—</b></span></span>
      <span class="conn-row"><span class="conn-dot ok" id="conn-r-dot"></span><span id="conn-r-txt">Reactor · <b id="next-r">—</b></span></span>
    </div>
    <div class="date-badge" id="date-badge" onclick="toggleDatePicker(event)">
      <svg class="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><rect width="18" height="18" x="3" y="4" rx="2"/><path d="M3 10h18M8 2v4M16 2v4"/></svg>
      <span id="date-badge-txt">Cargando...</span>
      <div class="date-pop" id="date-picker" onclick="event.stopPropagation()">
        <h4>Seleccionar fecha</h4>
        <input type="date" id="dp-input" onkeydown="if(event.key==='Enter')gotoDate()" onchange="updateDpHint(this.value)">
        <div class="hint" id="dp-hint-txt">Ingresá la fecha a consultar.</div>
        <button class="go" onclick="gotoDate()">Ver fecha</button>
        <button class="clr" onclick="gotoDate(true)">Volver al día actual</button>
      </div>
    </div>
    <button class="icon-btn" onclick="window.print()" title="Exportar / Imprimir">
      <svg class="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="M7 10l5 5 5-5M12 15V3"/></svg>
    </button>
    <button class="icon-btn" onclick="toggleTV()" id="tv-btn" title="Modo TV">
      <svg class="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><rect width="20" height="15" x="2" y="3" rx="2"/><path d="M7 21h10M12 18v3"/></svg>
    </button>
    <button class="icon-btn" onclick="toggleDark()" id="mode-btn" title="Modo oscuro">
      <svg class="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" id="mode-ico"><path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/></svg>
    </button>
  </div>
</div>
<div class="hist-banner" id="hist-banner">⚠ MODO HISTÓRICO — Datos del <span id="hist-date"></span> · No son datos de hoy</div>

<div class="main">

  <!-- Banda de alertas por excepción -->
  <div id="alerts-band" style="display:none"></div>

  <!-- HERO: Plan de Ventas + Venta del Día + Pedidos -->
  <div class="hero">
    <div class="hero-main">
      <div class="hero-eyebrow">
        <svg class="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/></svg>
        Plan de Ventas · Facturación acumulada del mes
      </div>
      <div class="hero-figs">
        <span class="hero-curr num" id="hero-fact">—</span>
        <span class="hero-total num" id="hero-plan"></span>
      </div>
      <div class="hero-pct-line">
        <span class="hero-pct num" id="hero-pct-val">—</span>
        <div class="plan-bar-bg">
          <div class="plan-bar-fill" id="hero-bar" style="width:0%"></div>
          <div class="plan-bar-pace" id="hero-pace" style="left:0%"></div>
        </div>
        <span class="state-tag state-neutral" id="hero-tag">—</span>
      </div>
      <div class="hero-foot">
        <span id="hero-foot-l"></span>
        <span id="hero-foot-r"></span>
      </div>
      <div class="hero-proy" id="hero-proy"></div>
    </div>
    <div class="hero-side">
      <div class="hero-stat" id="hero-venta-stat">
        <div class="l">Venta del Día · MSPA</div>
        <div style="display:flex;align-items:flex-end;justify-content:space-between;gap:8px">
          <div class="v num" id="hero-venta-val">—</div>
          <div id="spark-ventas"></div>
        </div>
        <div id="hero-venta-sub" style="font-size:10px;color:var(--text3);margin-top:4px;font-variant-numeric:tabular-nums"></div>
      </div>
      <div class="hsep"></div>
      <div class="hero-stat">
        <div class="l">Pedidos Informados</div>
        <div style="display:flex;align-items:flex-end;justify-content:space-between;gap:8px">
          <div class="v num" id="hero-ped-val">—</div>
          <div id="spark-ped"></div>
        </div>
        <div id="hero-ped-delta"></div>
      </div>
    </div>
  </div>

  <!-- KPI strip secundario -->
  <div class="sec">
    <div class="sec-lbl" id="sec-reactor">Indicadores del día · —</div>
    <div id="err-r" class="err"></div>
    <div class="kpi-grid" style="grid-template-columns:repeat(2,1fr)">
      <div class="kpi">
        <div class="kpi-lbl">Pedidos / Vendedor</div>
        <div class="kpi-top">
          <div class="kpi-val num" id="k-vend">—</div>
          <div id="spark-vend"></div>
        </div>
        <div class="kpi-foot" id="d-vend"></div>
      </div>
      <div class="kpi">
        <div class="kpi-lbl">Promedio Líneas / Pedido</div>
        <div class="kpi-top">
          <div class="kpi-val num" id="k-avg">—</div>
          <div id="spark-avg"></div>
        </div>
        <div class="kpi-foot" id="d-avg"></div>
      </div>
    </div>
  </div>

  <!-- Flujo del día -->
  <div class="sec">
    <div class="sec-lbl">Flujo del Día — Pedidos Informados → Facturación</div>
    <div class="flow-bar">
      <div class="flow-cell">
        <div class="flow-dot"><span class="flow-tick tk-blue"></span><span class="flow-label">Informado</span></div>
        <div class="flow-val num" id="fl-inf-val">—</div>
        <div class="flow-sub num" id="fl-inf-ped">—</div>
      </div>
      <div class="flow-cell" id="fc-ret">
        <div class="flow-dot"><span class="flow-tick tk-amber"></span><span class="flow-label">Retenido</span></div>
        <div class="flow-val num" id="fl-ret-val">—</div>
        <div class="flow-sub num" id="fl-ret-ped">—</div>
        <span class="alert-icon" id="ai-ret"></span>
      </div>
      <div class="flow-cell" id="fc-an">
        <div class="flow-dot"><span class="flow-tick tk-red"></span><span class="flow-label">Anulado</span></div>
        <div class="flow-val num" id="fl-an-val">—</div>
        <div class="flow-sub num" id="fl-an-ped">—</div>
        <span class="alert-icon" id="ai-an"></span>
      </div>
      <div class="flow-cell">
        <div class="flow-dot"><span class="flow-tick tk-green"></span>
          <span class="flow-label">Facturado <span class="tooltip-info">ⓘ<span class="tt">Pedidos de este día que pasaron a<br>estado Facturado (Reactor status 13/18).<br>La Venta del Día suma todo lo facturado<br>en MSPA ese día, incluye días anteriores.</span></span></span>
        </div>
        <div class="flow-val num" id="fl-fact-val">—</div>
        <div class="flow-sub num" id="fl-fact-ped">—</div>
        <div class="flow-sub num" id="fl-fact-mspa" style="font-size:9px;opacity:.7;margin-top:2px"></div>
      </div>
    </div>
  </div>

  <!-- Ritmo mensual -->
  <div class="meta-card">
    <div class="sec-lbl">Ritmo Mensual — Pedidos vs. Mes Anterior</div>
    <div class="meta-row" id="meta-row">
      <span style="color:var(--text3);font-size:11px">Cargando...</span>
    </div>
  </div>

  <!-- Gráfico + MSPA -->
  <div class="bottom">
    <div class="card">
      <div class="card-head">
        <div class="sec-lbl">
          <svg class="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M16 7h6v6"/><path d="m22 7-8.5 8.5-5-5L2 17"/></svg>
          Tendencia mensual
        </div>
        <span class="stamp" id="stamp-reactor"></span>
      </div>
      <div class="chart-wrap"><canvas id="trend"></canvas></div>
    </div>
    <div class="card">
      <div class="card-head">
        <div class="sec-lbl">
          <svg class="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="m12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83l8.58 3.91a2 2 0 0 0 1.66 0l8.58-3.9a1 1 0 0 0 0-1.83Z"/><path d="m22 17.65-9.17 4.16a2 2 0 0 1-1.66 0L2 17.65M22 12.65l-9.17 4.16a2 2 0 0 1-1.66 0L2 12.65"/></svg>
          MSPA · Estado actual
        </div>
        <span class="stamp" id="stamp-mspa"></span>
      </div>
      <div id="err-m" class="err"></div>
      <div id="mspa-body"></div>
    </div>
  </div>

  <!-- Ranking vendedores -->
  <div class="sec">
    <div class="sec-lbl">Ranking de vendedores</div>
    <div class="sellers-wrap">
      <div class="card">
        <div class="card-head">
          <div class="head-ico">
            <svg class="ico ic-fact" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6M18 9h1.5a2.5 2.5 0 0 0 0-5H18M4 22h16M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22M18 2H6v7a6 6 0 0 0 12 0V2Z"/></svg>
            <span class="sec-lbl">Top facturación</span>
          </div>
        </div>
        <div id="sell-fact-top"></div>
      </div>
      <div class="card">
        <div class="card-head">
          <div class="head-ico">
            <svg class="ico ic-ret" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M10 15V9M14 15V9"/></svg>
            <span class="sec-lbl">Más retenidos</span>
          </div>
        </div>
        <div id="sell-ret"></div>
      </div>
      <div class="card">
        <div class="card-head">
          <div class="head-ico">
            <svg class="ico ic-an" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="m4.9 4.9 14.2 14.2"/></svg>
            <span class="sec-lbl">Más anulados</span>
          </div>
        </div>
        <div id="sell-an"></div>
      </div>
    </div>
  </div>

</div>

<script>
let _mspaNext=60, _reactNext=600;
let chartObj=null;
let _lastMspaTs=null, _lastReactTs=null;

const THR_RET_WARN=20,THR_RET_DNG=35;
const THR_AN_WARN=10,THR_AN_DNG=20;

const ICO={
  arrowUp:'<svg class="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="m5 12 7-7 7 7M12 19V5"/></svg>',
  arrowDown:'<svg class="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M12 5v14M5 12l7 7 7-7"/></svg>',
  checkCircle:'<svg class="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><path d="m9 11 3 3L22 4"/></svg>',
  trendingDown:'<svg class="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M16 17h6v-6"/><path d="m22 17-8.5-8.5-5 5L2 7"/></svg>',
  pauseCircle:'<svg class="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M10 15V9M14 15V9"/></svg>',
  clock:'<svg class="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>',
  creditCard:'<svg class="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><rect width="20" height="14" x="2" y="5" rx="2"/><path d="M2 10h20"/></svg>',
  lock:'<svg class="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><rect width="18" height="11" x="3" y="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>',
  fileText:'<svg class="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4M10 9H8M16 13H8M16 17H8"/></svg>',
  factory:'<svg class="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M2 20a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V8l-7 5V8l-7 5V4a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2Z"/><path d="M17 18h1M12 18h1M7 18h1"/></svg>',
  truck:'<svg class="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M14 18V6a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2v11a1 1 0 0 0 1 1h2"/><path d="M15 18H9M19 18h2a1 1 0 0 0 1-1v-3.65a1 1 0 0 0-.22-.62l-3.48-4.35A1 1 0 0 0 17.52 8H14"/><circle cx="17" cy="18" r="2"/><circle cx="7" cy="18" r="2"/></svg>',
  banknote:'<svg class="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><rect width="20" height="12" x="2" y="6" rx="2"/><circle cx="12" cy="12" r="2"/><path d="M6 12h.01M18 12h.01"/></svg>',
};

const MSPA_DEF=[
  {k:'backorders', l:'Backorders (Plazos viejos)',    cls:'',      ico:'clock'},
  {k:'bloqueados', l:'Bloqueados por Límite Crédito', cls:'',      ico:'creditCard'},
  {k:'neg_status', l:'Bloqueados (Status < -1)',       cls:'',      ico:'lock'},
  {k:'futuros',    l:'Pedidos Abiertos (Futuros)',     cls:'',      ico:'fileText'},
  {k:'produccion', l:'Producción Abierta',             cls:'',      ico:'factory'},
  {k:'remitos',    l:'Remitos / Facturas Abiertas',    cls:'',      ico:'truck'},
  {k:'venta',      l:'Venta del Día',                  cls:'venta', ico:'banknote'},
];

function fmtN(n,d=0){return Number(n||0).toLocaleString('es-AR',{minimumFractionDigits:d,maximumFractionDigits:d})}
function fmtK(n){
  n=Number(n)||0;
  const fmt1=v=>v.toLocaleString('es-AR',{minimumFractionDigits:1,maximumFractionDigits:1});
  if(n>=1e9)return '$'+fmt1(n/1e9)+'B';
  if(n>=1e6)return '$'+fmt1(n/1e6)+'M';
  if(n>=1e3)return '$'+Math.round(n/1e3).toLocaleString('es-AR')+'K';
  return '$'+fmtN(n,0);
}
function pct(a,b){return b?fmtN((a/b)*100,1)+'%':'—'}
function pctNum(a,b){return b?(a/b)*100:0}

function nextFmt(secs){
  if(secs<=0)return '<span style="color:var(--amber)">actualizando…</span>';
  if(secs<60)return `<span style="color:var(--green)">${secs}s</span>`;
  const m=Math.ceil(secs/60);
  return `<span style="color:var(--green)">${m}min</span>`;
}

function semaforo(v,w,d){return v>=d?'danger':v>=w?'warn':'ok'}

function sparkSvg(data,w=74,h=30){
  if(!data||data.length<2)return '';
  const mn=Math.min(...data),mx=Math.max(...data),rng=(mx-mn)||1;
  const pad=2,step=(w-pad*2)/(data.length-1);
  const pts=data.map((v,i)=>[pad+i*step, h-pad-((v-mn)/rng)*(h-pad*2)]);
  const d=pts.map(([x,y],i)=>`${i?'L':'M'}${x.toFixed(1)} ${y.toFixed(1)}`).join(' ');
  const area=`${d} L${pts[pts.length-1][0].toFixed(1)} ${h} L${pts[0][0].toFixed(1)} ${h} Z`;
  const up=data[data.length-1]>=data[0];
  const c=up?'var(--green)':'var(--red)';
  const gid='sg'+Math.abs(data.slice(0,3).reduce((a,v,i)=>a^(v*1000+i*7),0)).toString(36);
  const [lx,ly]=pts[pts.length-1];
  return `<svg class="spark" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none">
  <defs><linearGradient id="${gid}" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="${c}" stop-opacity=".18"/><stop offset="100%" stop-color="${c}" stop-opacity="0"/>
  </linearGradient></defs>
  <path d="${area}" fill="url(#${gid})"/>
  <path d="${d}" fill="none" stroke="${c}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
  <circle cx="${lx.toFixed(1)}" cy="${ly.toFixed(1)}" r="2.2" fill="${c}"/>
</svg>`;
}

function deltaHtml(curr,prev,compLbl){
  if(!prev||!curr)return '';
  const p=(curr-prev)/prev*100;
  const ico=p>0?ICO.arrowUp:ICO.arrowDown;
  const cls=p>0?'up':'down';
  const lbl=compLbl?`<span style="font-size:9px;color:var(--text3);display:block;margin-top:2px">${compLbl}</span>`:'';
  return `<span class="delta ${cls}">${ico} ${fmtN(Math.abs(p),1)}%</span>${lbl}`;
}

function renderPlan(pv, diasElapsed, diasHab){
  const noData=()=>{
    document.getElementById('hero-fact').textContent='—';
    document.getElementById('hero-plan').textContent='';
    document.getElementById('hero-pct-val').textContent='—';
    document.getElementById('hero-tag').textContent='Sin datos';
    document.getElementById('hero-proy').style.display='none';
  };
  if(!pv||!pv.plan_total){noData();return;}
  const plan=pv.plan_total, fact=pv.fact_acum, pctVal=pv.pct_plan||0;
  const fill=Math.min(pctVal,100);
  const pacePos=diasHab>0?Math.min((diasElapsed/diasHab)*100,100):0;
  const paceTarget=plan*(pacePos/100);
  const onTrack=fact>=paceTarget;
  const barColor=pctVal>=100?'var(--green)':onTrack?'var(--wurth-red)':'var(--amber)';

  document.getElementById('hero-fact').textContent=fmtK(fact);
  document.getElementById('hero-plan').textContent='/ '+fmtK(plan);
  document.getElementById('hero-pct-val').textContent=fmtN(pctVal,1)+'%';
  document.getElementById('hero-pct-val').style.color=barColor;
  document.getElementById('hero-bar').style.width=fill+'%';
  document.getElementById('hero-bar').style.background=barColor;
  document.getElementById('hero-pace').style.left=pacePos.toFixed(1)+'%';
  document.getElementById('hero-foot-l').textContent=diasHab>0?`Día hábil ${diasElapsed} de ${diasHab}`:'';
  document.getElementById('hero-foot-r').textContent=plan>0?`Restante: ${fmtK(plan-fact)}`:'';

  const tag=document.getElementById('hero-tag');
  if(pctVal>=100){
    tag.className='state-tag state-ok';
    tag.innerHTML=ICO.checkCircle+' Plan cumplido';
  } else if(onTrack){
    tag.className='state-tag state-ok';
    tag.innerHTML=ICO.checkCircle+` En ritmo · ${fmtN(pctVal,1)}%`;
  } else {
    const pctBehind=((paceTarget-fact)/plan*100);
    const cls=pctBehind>15?'state-danger':'state-warn';
    tag.className='state-tag '+cls;
    tag.innerHTML=ICO.trendingDown+` ${fmtN(pctBehind,1)}% por debajo del ritmo`;
  }

  const proyEl=document.getElementById('hero-proy');
  if(diasElapsed>0&&diasHab>0&&fact>0){
    const proy=fact/diasElapsed*diasHab;
    const proyPct=plan>0?(proy/plan*100):0;
    const proyColor=proyPct>=100?'var(--green)':proyPct>=90?'var(--amber)':'var(--red)';
    proyEl.style.display='block';
    proyEl.innerHTML=`Proyección de cierre: <b style="color:${proyColor}">${fmtK(proy)}</b>`
      +(plan>0?` · <b style="color:${proyColor}">${fmtN(proyPct,1)}% del plan</b>`:'');
  } else {
    proyEl.style.display='none';
  }
}

function renderMeta(meta){
  if(!meta){document.getElementById('meta-row').innerHTML='<span style="color:var(--text3);font-size:11px">Sin datos</span>';return;}
  const curr=meta.curr_pedidos,last=meta.last_pedidos;
  const pctProg=last>0?Math.min((curr/last)*100,120):0;
  const pacePos=meta.curr_wd>0
    ?(meta.dias_elapsed/meta.curr_wd)*100
    :meta.days_in_month>0?(meta.day_of_month/meta.days_in_month)*100:0;
  const paceTarget=last>0?(Math.min(pacePos,100)/100)*last:0;
  const onTrack=curr>=paceTarget;
  const fill=Math.min(pctProg,100);
  let tagCls='tag-neutral',tagTxt='Sin referencia';
  if(last>0){
    const diff=curr-paceTarget;
    if(onTrack){tagCls='tag-ok';tagTxt=`+${fmtN(Math.round(diff))} sobre ritmo`;}
    else{const bh=Math.round(paceTarget-curr);tagCls=bh>last*0.1?'tag-danger':'tag-warn';tagTxt=`${fmtN(bh)} pedidos por debajo del ritmo`;}
  }
  document.getElementById('meta-row').innerHTML=`
    <div style="font-size:11px;color:var(--text2);white-space:nowrap">${meta.curr_month} vs ${meta.last_month||'—'}</div>
    <div class="meta-nums"><span class="meta-curr num">${fmtN(curr,0)}</span><span class="meta-sep">de</span><span class="meta-last num">${fmtN(last,0)} pedidos</span></div>
    <div class="meta-bar-wrap">
      <div class="meta-bar-bg">
        <div class="meta-bar-fill" style="width:${fill}%;background:${pctProg>100?'var(--green)':onTrack?'var(--blue)':'var(--amber)'}"></div>
        <div class="meta-bar-pace" style="left:${Math.min(pacePos,100).toFixed(1)}%"></div>
      </div>
      <div class="meta-bar-labels"><span class="num">${fmtN(pctProg,0)}% del mes anterior</span></div>
    </div>
    <div class="meta-tags"><span class="meta-tag ${tagCls}">${tagTxt}</span></div>`;
}

function renderChart(trend){
  if(!trend||!trend.labels||!trend.labels.length)return;
  const ctx=document.getElementById('trend');
  if(!ctx)return;
  const isDark=document.body.classList.contains('dark');
  const gridColor=isDark?'rgba(255,255,255,.06)':'rgba(0,0,0,.06)';
  const txtColor=isDark?'#94a3b8':'#64748b';
  if(chartObj){chartObj.destroy();chartObj=null;}
  chartObj=new Chart(ctx,{
    data:{
      labels:trend.labels,
      datasets:[
        {type:'bar',label:'Pedidos / día hábil',data:trend.pedidos,backgroundColor:'rgba(203,213,225,.8)',borderColor:'#cbd5e1',yAxisID:'y1',borderRadius:3},
        {type:'line',label:'M$ / día hábil',data:trend.ventas,borderColor:'#cc0000',backgroundColor:'rgba(204,0,0,.06)',tension:.35,yAxisID:'y2',fill:true,pointRadius:3,pointBackgroundColor:'#cc0000'},
      ]
    },
    options:{
      responsive:true,maintainAspectRatio:false,
      plugins:{legend:{position:'bottom',labels:{boxWidth:12,padding:16,color:txtColor,font:{size:11}}}},
      scales:{
        x:{grid:{display:false},ticks:{color:txtColor,font:{size:10}}},
        y1:{position:'left',title:{display:true,text:'pedidos/día',color:txtColor,font:{size:10}},ticks:{color:txtColor,font:{size:10}},grid:{color:gridColor}},
        y2:{position:'right',title:{display:true,text:'M$/día',color:txtColor,font:{size:10}},ticks:{color:txtColor,font:{size:10},callback:v=>fmtN(v,1)},grid:{drawOnChartArea:false}},
      }
    }
  });
}

function buildSellerTable(sellers, valClass, valLabel, valueKey, showPed){
  if(!sellers||!sellers.length)
    return '<p style="color:var(--text3);font-size:11px;padding:4px 0;font-style:italic">— Sin movimiento</p>';
  const pedCol=showPed?`<th style="text-align:right;color:var(--text3)">Ped.</th>`:'';
  let h=`<table class="seller-tbl"><tr><th></th><th>Vendedor</th>${pedCol}<th style="text-align:right">${valLabel}</th></tr>`;
  sellers.slice(0,5).forEach((s,i)=>{
    const nameRaw=s.nombre||'';
    const nameHtml=nameRaw.includes('(')?
      nameRaw.replace(/^(.+?)(\(.+\))(.*)$/,'<div class="s-name">$1</div><div class="s-sub">$2$3</div>'):
      `<div class="s-name">${nameRaw}</div>`;
    const valHtml=valueKey==='val'
      ?`<span class="${valClass}">${fmtK(s.val||s.val_valido||0)}</span>`
      :`<span class="s-pill ${valClass==='ret-val'?'pill-ret':'pill-an'}">${s.cnt} ped.</span>`;
    const pedCell=showPed?`<td class="s-val" style="color:var(--text3);font-size:11px">${s.ped||s.cnt||''}</td>`:'';
    h+=`<tr><td class="s-rank">${i+1}</td><td>${nameHtml}</td>${pedCell}<td class="s-val">${valHtml}</td></tr>`;
  });
  return h+'</table>';
}

function connSev(secsAgo){
  if(secsAgo===null||secsAgo===undefined)return 'down';
  if(secsAgo>600)return 'down';
  if(secsAgo>120)return 'slow';
  return 'ok';
}
function connLabel(sev){
  return sev==='ok'?'OK':sev==='slow'?'lento':'sin conexión';
}

function renderAlerts(r,m){
  const total=r.pedidos||0;
  const bs=r.by_status||{};
  const ret=(bs[15]?.cnt||0);
  const retPct=total>0?(ret/total)*100:0;
  const pv=m.plan_ventas||null;
  const alerts=[];

  if(retPct>=THR_RET_WARN){
    const sev=retPct>=THR_RET_DNG?'danger':'warn';
    alerts.push(`<div class="alert ${sev}">${ICO.pauseCircle}<span><b>Retenidos en ${fmtN(retPct,1)}%</b> — por encima del objetivo de ${THR_RET_WARN}% (${fmtN(ret)} pedidos)</span><a class="a-act" href="#">Ver retenidos →</a></div>`);
  }
  if(pv&&pv.plan_total&&r.meta){
    const diasEl=r.meta.dias_elapsed||0, diasHab=r.meta.curr_wd||0;
    const pacePos=diasHab>0?Math.min((diasEl/diasHab)*100,100):0;
    const pctVal=pv.pct_plan||0;
    if(pacePos>0&&pctVal<pacePos){
      const gap=pacePos-pctVal;
      alerts.push(`<div class="alert warn">${ICO.trendingDown}<span>Plan de ventas <b>${fmtN(gap,1)} pts por debajo del ritmo</b> (${fmtN(pctVal,1)}% vs ${fmtN(pacePos,1)}% esperado)</span><a class="a-act" href="#">Ver plan →</a></div>`);
    }
  }

  const band=document.getElementById('alerts-band');
  if(alerts.length){
    band.innerHTML=`<div class="alerts">${alerts.join('')}</div>`;
    band.style.display='';
  } else {
    band.style.display='none';
    band.innerHTML='';
  }
}

function render(data){
  const now=new Date();
  const nowStr=now.toLocaleTimeString('es-AR',{hour:'2-digit',minute:'2-digit',second:'2-digit'});
  document.getElementById('err-r').textContent=data.reactor_error?'⚠ Reactor: '+data.reactor_error:'';
  document.getElementById('err-m').textContent=data.mspa_error?'⚠ MSPA: '+data.mspa_error:'';
  if(data.reactor&&data.reactor.wd_map){_wdMap=data.reactor.wd_map;}
  if(data.reactor&&data.reactor.wd_log){_wdLog=data.reactor.wd_log;}

  _mspaNext  = data.mspa_next  || 60;
  _reactNext = data.reactor_next || 600;
  _lastMspaTs  = now;
  _lastReactTs = now;

  // Conexión: actualizar conn-dots y stamps
  const mspaSegs = data.mspa_error ? 9999 : 0;
  const reactSegs = data.reactor_error ? 9999 : 0;
  const mSev=connSev(mspaSegs), rSev=connSev(reactSegs);
  document.getElementById('conn-mspa-dot').className=`conn-dot ${mSev}`;
  document.getElementById('conn-r-dot').className=`conn-dot ${rSev}`;
  document.getElementById('conn-mspa-txt').innerHTML=`MSPA ${connLabel(mSev)} · <b>${nowStr}</b>`;
  document.getElementById('conn-r-txt').innerHTML=`Reactor ${connLabel(rSev)} · <b>${nowStr}</b>`;
  const stampEl=document.getElementById('stamp-mspa');
  if(stampEl)stampEl.textContent='datos al '+nowStr;
  const stampR=document.getElementById('stamp-reactor');
  if(stampR)stampR.textContent='datos al '+nowStr;

  const r=data.reactor||{};
  const m=data.mspa||{};
  const dp=r.target_date_display||'—';
  document.getElementById('date-badge-txt').textContent='Pedidos del '+dp+(_isHistoric?' (manual)':'');
  document.getElementById('sec-reactor').textContent='Indicadores del día · '+dp+(_isHistoric?' (fecha manual)':'');
  const histBanner=document.getElementById('hist-banner');
  if(_isHistoric){
    document.getElementById('hist-date').textContent=dp;
    histBanner.style.display='block';
  } else {
    histBanner.style.display='none';
  }

  const c=r.comp||null;
  const compLbl='vs. mismo día hábil mes anterior';

  // Hero: Venta del día
  const venta=m.venta||{ords:0,val:0};
  document.getElementById('hero-venta-val').textContent=fmtK(venta.val);
  document.getElementById('hero-venta-val').style.color=venta.val>0?'':'var(--text3)';
  document.getElementById('hero-venta-sub').textContent=fmtN(venta.ords,0)+' pedidos facturados';

  // Hero: Pedidos informados
  document.getElementById('hero-ped-val').textContent=fmtN(r.pedidos,0);
  document.getElementById('hero-ped-delta').innerHTML=c?deltaHtml(r.pedidos,c.pedidos,compLbl):'';

  // Semáforo anulados en hero-venta-stat
  const total=r.pedidos||0;
  const bs=r.by_status||{};
  const an=(bs[14]?.cnt||0), ret=(bs[15]?.cnt||0);
  const anPct=pctNum(an,total), retPct=pctNum(ret,total);
  const heroVenta=document.getElementById('hero-venta-stat');
  heroVenta.classList.remove('alert-warn','alert-danger');
  const sAn=semaforo(anPct,THR_AN_WARN,THR_AN_DNG);
  if(sAn==='danger')heroVenta.classList.add('alert-danger');
  else if(sAn==='warn')heroVenta.classList.add('alert-warn');

  // KPI strip
  const apv=r.avg_ped_vend||0;
  document.getElementById('k-vend').textContent=fmtN(apv,1);
  document.getElementById('d-vend').innerHTML=c&&c.avg_ped_vend?deltaHtml(apv,c.avg_ped_vend,compLbl):'';
  document.getElementById('k-avg').textContent=r.avg_lineas||'—';
  document.getElementById('d-avg').innerHTML=c&&c.avg_lineas?deltaHtml(r.avg_lineas,c.avg_lineas,compLbl):'';

  // Sparklines
  const sp=r.sparklines||{};
  document.getElementById('spark-ped').innerHTML=sparkSvg(sp.pedidos);
  document.getElementById('spark-ventas').innerHTML=sparkSvg(sp.ventas);
  document.getElementById('spark-vend').innerHTML=sparkSvg(sp.ped_vend);
  document.getElementById('spark-avg').innerHTML=sparkSvg(sp.avg_lin);

  // Flow bar
  const fact_cnt=(bs[13]?.cnt||0)+(bs[18]?.cnt||0);
  const fact_val=(bs[13]?.val||0)+(bs[18]?.val||0);
  document.getElementById('fl-inf-val').textContent=fmtK(r.valor||0);
  document.getElementById('fl-inf-ped').textContent=fmtN(total,0)+' pedidos';
  document.getElementById('fl-ret-val').textContent=fmtK(bs[15]?.val||0);
  document.getElementById('fl-ret-ped').textContent=fmtN(ret,0)+' ped · '+pct(ret,total);
  document.getElementById('fl-an-val').textContent=fmtK(bs[14]?.val||0);
  document.getElementById('fl-an-ped').textContent=fmtN(an,0)+' ped · '+pct(an,total);
  document.getElementById('fl-fact-val').textContent=fmtK(fact_val);
  document.getElementById('fl-fact-ped').textContent=fmtN(fact_cnt,0)+' pedidos';
  const elMspaRef=document.getElementById('fl-fact-mspa');
  if(elMspaRef)elMspaRef.textContent=venta.val>0?'MSPA total día: '+fmtK(venta.val):'';

  // Semáforo flow — ícono estático (la banda de alertas ya notifica activamente)
  const fcRet=document.getElementById('fc-ret'),fcAn=document.getElementById('fc-an');
  const aiRet=document.getElementById('ai-ret'),aiAn=document.getElementById('ai-an');
  fcRet.classList.remove('pulse-warn','pulse-danger');fcAn.classList.remove('pulse-warn','pulse-danger');
  const sRet=semaforo(retPct,THR_RET_WARN,THR_RET_DNG);
  aiRet.innerHTML=sRet!=='ok'?ICO.trendingDown:'';
  aiAn.innerHTML=sAn!=='ok'?ICO.trendingDown:'';

  // Plan de ventas → hero
  const pv=m.plan_ventas||null;
  const diasEl=r.meta?.dias_elapsed||0;
  const diasHab=r.meta?.curr_wd||0;
  renderPlan(pv, diasEl, diasHab);

  renderMeta(r.meta||null);

  // Alertas por excepción
  renderAlerts(r,m);

  // Gráfico tendencia
  if(r.trend)renderChart(r.trend);

  // MSPA con semáforos
  let mhtml='';
  MSPA_DEF.forEach(row=>{
    const d=m[row.k]||{ords:0,pos:0,val:0};
    // semáforo: bloqueados y backorders con valor > 0 → warn; sin datos o venta → ok
    let sem='';
    if(row.cls!=='venta'){
      const sev=d.val>0?'warn':'';
      sem=`<span class="mspa-sem${sev?' '+sev:''}"></span>`;
    } else {
      sem=`<span class="mspa-sem"></span>`;
    }
    mhtml+=`<div class="mspa-row ${row.cls}">
      <span class="mspa-l">${sem}<span class="mspa-lbl">${row.l}</span></span>
      <span class="mspa-val">${fmtK(d.val)}<span class="mspa-sub-txt">${fmtN(d.ords)} ord · ${fmtN(d.pos)} pos</span></span>
    </div>`;
  });
  document.getElementById('mspa-body').innerHTML=mhtml;

  // Sellers
  document.getElementById('sell-fact-top').innerHTML=buildSellerTable(m.sellers_fact_top||[],'fact-val','Facturado','val',true);
  document.getElementById('sell-ret').innerHTML=buildSellerTable(r.sellers_ret||[],'ret-val','Retenidos','cnt',false);
  document.getElementById('sell-an').innerHTML=buildSellerTable(r.sellers_an||[],'an-val','Anulados','cnt',false);
}

const _customDate=new URLSearchParams(location.search).get('date')||'';
const _todayStr=new Date().toISOString().slice(0,10);
const _isHistoric=_customDate && _customDate!==_todayStr;
let _wdMap={};
let _wdLog={};

async function load(){
  const url='/api/data'+(_customDate?'?date='+_customDate:'');
  try{const res=await fetch(url);const d=await res.json();render(d);}
  catch(e){console.error(e);}
  finally{document.querySelector('.main').classList.remove('is-loading');}
}
document.querySelector('.main').classList.add('is-loading');

function tick(){
  if(_isHistoric){
    document.getElementById('conn-mspa-txt').innerHTML='MSPA · <b>histórico</b>';
    document.getElementById('conn-r-txt').innerHTML='Reactor · <b>histórico</b>';
    return;
  }
  _mspaNext  = Math.max(0,_mspaNext-1);
  _reactNext = Math.max(0,_reactNext-1);
  // actualizar conn-dots según antigüedad
  if(_lastMspaTs){
    const segsM=Math.round((Date.now()-_lastMspaTs.getTime())/1000)+(_mspaNext<=0?0:60-_mspaNext);
    document.getElementById('conn-mspa-dot').className=`conn-dot ${connSev(segsM)}`;
  }
  if(_mspaNext<=0){load();_mspaNext=60;}
}

function calcDiaHabil(dateStr){
  if(!dateStr)return{dh:null,total:null,exact:false};
  if(_wdLog[dateStr]!==undefined){
    const mes=dateStr.slice(0,7);
    return{dh:_wdLog[dateStr],total:_wdMap[mes]||null,exact:true};
  }
  const d=new Date(dateStr+'T12:00:00');
  const mes=dateStr.slice(0,7);
  const diasHab=_wdMap[mes];
  if(!diasHab)return{dh:null,total:null,exact:false};
  const diasMes=new Date(d.getFullYear(),d.getMonth()+1,0).getDate();
  return{dh:Math.max(1,Math.round(diasHab*d.getDate()/diasMes)),total:diasHab,exact:false};
}

function toggleDark(){
  const dark=document.body.classList.toggle('dark');
  const ico=document.getElementById('mode-ico');
  ico.innerHTML=dark
    ?'<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/>'
    :'<path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/>';
  document.getElementById('mode-btn').classList.toggle('on',dark);
  localStorage.setItem('wuerth-dark',dark?'1':'0');
  if(chartObj){const t=chartObj.data.datasets;renderChart({labels:chartObj.data.labels,pedidos:t[0].data,ventas:t[1].data});}
}
function toggleTV(){
  const tv=document.body.classList.toggle('tv');
  document.getElementById('tv-btn').classList.toggle('on',tv);
  localStorage.setItem('wuerth-tv',tv?'1':'0');
}
if(localStorage.getItem('wuerth-tv')==='1'){
  document.body.classList.add('tv');
  document.getElementById('tv-btn').classList.add('on');
}
if(localStorage.getItem('wuerth-dark')==='1'||new URLSearchParams(location.search).get('dark')==='1'){
  document.body.classList.add('dark');
  document.getElementById('mode-btn').classList.add('on');
  document.getElementById('mode-ico').innerHTML='<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/>';
}

function toggleDatePicker(e){
  e.stopPropagation();
  const dp=document.getElementById('date-picker');
  dp.classList.toggle('open');
  if(dp.classList.contains('open')){
    const val=_customDate||new Date().toISOString().slice(0,10);
    document.getElementById('dp-input').value=val;
    updateDpHint(val);
  }
}
document.addEventListener('click',()=>document.getElementById('date-picker').classList.remove('open'));

function updateDpHint(v){
  const hint=document.getElementById('dp-hint-txt');
  if(!v){hint.textContent='Seleccioná una fecha para consultar.';return;}
  const {dh,total,exact}=calcDiaHabil(v);
  if(dh){
    const lbl=exact?`<b>día hábil ${dh}${total?' de '+total:''}</b>`:`aprox. día hábil ${dh}${total?' de '+total:''}`;
    hint.innerHTML=`${lbl} del mes.`;
  } else {
    hint.textContent='Fecha sin datos de días hábiles.';
  }
}

function gotoDate(clear){
  if(clear){window.location.href=window.location.pathname;return;}
  const v=document.getElementById('dp-input').value;
  if(v)window.location.href=window.location.pathname+'?date='+v;
}

load();
setInterval(tick,1000);
</script>
</body>
</html>
""".replace("@@LOGO@@", LOGO_HTML)


# ─────────────────────────────────────────────────────────────────────────────
class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args): pass

    def send_json(self, data):
        body=json.dumps(data,ensure_ascii=False,cls=_Enc).encode()
        self.send_response(200)
        self.send_header("Content-Type","application/json; charset=utf-8")
        self.send_header("Content-Length",len(body))
        self.end_headers()
        self.wfile.write(body)

    def send_html(self, html):
        body=html.encode()
        self.send_response(200)
        self.send_header("Content-Type","text/html; charset=utf-8")
        self.send_header("Content-Length",len(body))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(self.path)
        qs     = parse_qs(parsed.query)
        if parsed.path in ("/", "/index.html"):
            self.send_html(HTML_PAGE)
        elif parsed.path == "/api/data":
            override = qs.get("date", [None])[0]
            self.send_json(get_cached_data(override_date=override))
        else: self.send_response(404); self.end_headers()


def main():
    print("Würth Operations Dashboard")
    print(f"DSN MSPA: {DSN_MSPA}  |  DSN Reactor: {DSN_REACTOR}")
    print(f"MSPA TTL: {MSPA_TTL}s  |  Reactor TTL: {REACTOR_TTL}s")
    print(f"SOLO LECTURA  |  http://localhost:{PORT}  |  Oscuro: ?dark=1")
    print("Ctrl+C para detener\n")
    server=HTTPServer(("0.0.0.0",PORT),Handler)
    try: server.serve_forever()
    except KeyboardInterrupt: print("\nDetenido.")


if __name__=="__main__":
    main()

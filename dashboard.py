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
_cache_today    = None
_cache_today_ts = None


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
        target_str  = target_date
        target_dt   = date.fromisoformat(target_date)
        is_historic = True
    else:
        today     = date.today()
        today_str = str(today)
        # Prev working day from work_days_log
        prev_rows = run(cur, """
            SELECT DATE_FORMAT(real_date, '%Y-%m-%d')
            FROM work_days_log WHERE real_date < ?
            ORDER BY real_date DESC LIMIT 1
        """, (today_str,))
        # Is today the last working day of the month?
        next_wd = run(cur, """
            SELECT COUNT(*) FROM work_days_log
            WHERE real_date > ? AND YEAR(real_date)=YEAR(?) AND MONTH(real_date)=MONTH(?)
        """, (today_str, today_str, today_str))
        is_last_wd = bool(next_wd and next_wd[0][0] == 0)
        if is_last_wd:
            target_str = today_str
            target_dt  = today
        elif prev_rows and prev_rows[0][0]:
            target_str = str(prev_rows[0][0])
            target_dt  = date.fromisoformat(target_str)
        else:
            target_dt  = today - timedelta(days=1)
            target_str = str(target_dt)
        is_historic = False

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

    # Work days per month
    wd_rows = run(cur, """
        SELECT CONCAT(year, '-', LPAD(month, 2, '0')) mes, days
        FROM work_days
        WHERE year >= YEAR(CURDATE()) - 1
        ORDER BY year, month
    """)
    wd_map = {r[0]: r[1] for r in wd_rows} if wd_rows else {}

    # Exact business day per calendar date from work_days_log
    wdl_rows = run(cur, """
        SELECT DATE_FORMAT(real_date, '%Y-%m-%d'), working_day
        FROM work_days_log
        WHERE real_date >= DATE_FORMAT(DATE_SUB(CURDATE(), INTERVAL 13 MONTH), '%Y-%m-01')
    """)
    wd_log = {str(r[0]): int(r[1]) for r in (wdl_rows or []) if r[0] and r[1]}

    # Monthly trend — solo días hábiles (wd_log), todos los estados
    # Así el numerador SUM(total) y el divisor (elapsed_wd / dias_tot) cuentan exactamente los mismos días
    trend_dates = sorted(d for d in wd_log if d <= target_str)
    if trend_dates:
        td_ph = ",".join(["?"] * len(trend_dates))
        trend_rows = run(cur, f"""
            SELECT DATE_FORMAT(order_date, '%Y-%m') mes,
                   COUNT(DISTINCT id) pedidos,
                   SUM(total) valor
            FROM order_placed
            WHERE DATE(order_date) IN ({td_ph})
            GROUP BY DATE_FORMAT(order_date, '%Y-%m')
            ORDER BY mes
        """, tuple(trend_dates))
    else:
        trend_rows = []

    # Días hábiles transcurridos en el mes del target (para el mes en curso)
    cur_mes = target_dt.strftime("%Y-%m")
    elapsed_wd = sum(1 for d in wd_log if d.startswith(cur_mes) and d <= target_str)

    trend = []
    for r in trend_rows:
        mes       = r[0]
        peds      = r[1] or 0
        val       = float(r[2] or 0)
        dias_tot  = wd_map.get(mes, 0)
        is_cur    = (mes == cur_mes)
        # Mes en curso: dividir por días hábiles transcurridos (no el total del mes)
        dias_div  = elapsed_wd if is_cur and elapsed_wd > 0 else dias_tot
        avg_pd    = round(peds / dias_div, 1) if dias_div else None
        trend.append({"mes": mes, "pedidos": peds, "valor": val,
                      "dias_hab": dias_div, "dias_tot": dias_tot,
                      "elapsed": elapsed_wd if is_cur else dias_tot,
                      "is_partial": is_cur, "avg_dia": avg_pd})

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

    # Sellers: keyed by username (= número de vendedor), name + surname concatenados
    user_names = {}
    rows_u = run(cur, "SELECT username, name, surname FROM `user`")
    if rows_u:
        for r in rows_u:
            uname = str(r[0]).strip() if r[0] else None
            name  = str(r[1]).strip() if r[1] else ""
            surn  = str(r[2]).strip() if r[2] else ""
            full  = (name + " " + surn).strip()
            if uname and full:
                user_names[uname] = full
        print(f"  user names loaded: {len(user_names)} rows")

    def seller_name(uid):
        key = str(uid).strip()
        n   = user_names.get(key, "")
        if n:
            return f"{n} ({key})"
        return f"Vend. {key}"

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
    sparklines = {"pedidos": [], "ventas": [], "ped_vend": [], "avg_lin": [], "ticket": [], "dates": []}
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
                      AND id_order_status <> 14
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
                      AND op.id_order_status <> 14
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
                    sparklines["ticket"].append(round(val / ped) if ped else 0)
                    # fecha legible dd/mm para tooltip
                    try:
                        from datetime import date as _date
                        parts = fd.split("-")
                        sparklines["dates"].append(f"{parts[2]}/{parts[1]}")
                    except Exception:
                        sparklines["dates"].append(fd)
    except Exception as e:
        print(f"  sparklines error: {e}")

    conn.close()

    return {
        "target_date":         target_str,
        "target_date_display": target_dt.strftime("%d/%m/%Y"),
        "is_historic":         is_historic,
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
# HOY SUMMARY — pedidos informados hoy (panel informativo)
# ─────────────────────────────────────────────────────────────────────────────
def fetch_today_summary():
    today_str = str(date.today())
    conn = get_reactor()
    cur  = conn.cursor()
    try:
        rows = run(cur, """
            SELECT COUNT(DISTINCT id) pedidos,
                   COUNT(DISTINCT id_user) vendedores,
                   SUM(total) valor
            FROM order_placed WHERE DATE(order_date) = ?
        """, (today_str,))
        pedidos, vendedores, valor = rows[0] if rows else (0, 0, 0)
        pedidos    = int(pedidos    or 0)
        vendedores = int(vendedores or 0)
        valor      = float(valor    or 0)
        lineas_row = run(cur, """
            SELECT COUNT(od.id)
            FROM order_placed op
            JOIN order_detail od ON od.id_order_placed = op.id
            WHERE DATE(op.order_date) = ?
        """, (today_str,))
        lineas = int(lineas_row[0][0] or 0) if lineas_row else 0
        return {
            "date":         today_str,
            "pedidos":      pedidos,
            "vendedores":   vendedores,
            "valor":        valor,
            "lineas":       lineas,
            "avg_lineas":   round(lineas / pedidos, 1)  if pedidos    else 0,
            "avg_ped_vend": round(pedidos / vendedores, 1) if vendedores else 0,
            "ticket":       round(valor / pedidos)       if pedidos    else 0,
        }
    except Exception as e:
        print(f"  fetch_today_summary error: {e}")
        return {"date": today_str, "pedidos": 0, "vendedores": 0, "valor": 0,
                "lineas": 0, "avg_lineas": 0, "avg_ped_vend": 0, "ticket": 0}
    finally:
        conn.close()


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
    global _cache_today, _cache_today_ts
    now = datetime.now()
    today_summary = None
    if override_date:
        # Fecha manual: fetch directo sin cache — datos exactos para esa fecha
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
            # Today summary se refresca con el mismo TTL que MSPA
            if (_cache_today is None or _cache_today_ts is None
                    or (now - _cache_today_ts).total_seconds() >= MSPA_TTL
                    or _cache_today.get("date") != str(date.today())):
                try:
                    _cache_today    = fetch_today_summary()
                    _cache_today_ts = now
                except Exception as e:
                    print(f"  today_summary error: {e}")
            today_summary = _cache_today
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
            for s in reactor.get(lst, []):
                uid = str(s.get("id", "")).strip()
                if uid in vnames:
                    s["nombre"] = f"{vnames[uid]} ({uid})"

    return {
        "timestamp":      now.strftime("%d/%m/%Y %H:%M:%S"),
        "reactor":        reactor or {},
        "mspa":           mspa    or {},
        "today_summary":  today_summary,
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
.hero-proy{display:none;margin-top:14px;padding-top:12px;border-top:1px solid var(--border);font-size:14px;color:var(--text-2);font-variant-numeric:tabular-nums}
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
.kpi-top{display:flex;align-items:flex-end;justify-content:space-between;gap:10px;height:44px}
.kpi-val{font-size:25px;font-weight:700;line-height:1;color:var(--text);font-variant-numeric:tabular-nums}
.kpi-foot{display:flex;align-items:center;gap:8px;margin-top:9px;flex-wrap:wrap}
.spark{width:74px;height:30px;flex-shrink:0;opacity:.9}
.delta{display:inline-flex;align-items:center;gap:2px;font-size:13px;font-weight:700;font-variant-numeric:tabular-nums}
.delta .ico{width:13px;height:13px}
.delta.up{color:var(--pos-fg)}.delta.down{color:var(--neg-fg)}.delta.flat{color:var(--text-3)}
.meta-chip{display:inline-flex;align-items:center;gap:4px;font-size:10px;color:var(--text-3);font-variant-numeric:tabular-nums}
.meta-chip .dot{width:6px;height:6px;border-radius:50%}
.meta-chip .dot.ok{background:var(--green)}.meta-chip .dot.warn{background:var(--amber)}
.kpi-sub{font-size:10px;color:var(--text-3);margin-top:6px;font-variant-numeric:tabular-nums}

/* ── FLOW BAR ── */
.flow-bar{display:flex;align-items:stretch;background:var(--surface);border:1px solid var(--border);border-radius:var(--r-card);overflow:hidden}
.hoy-bar{display:flex;align-items:stretch;background:var(--surface-2);border:1px solid var(--border);border-radius:var(--r-card);overflow:hidden;margin-top:0}
.hoy-bar.hidden{display:none}
.hoy-cell{flex:1;padding:12px 18px;display:flex;flex-direction:column;gap:3px;min-width:0;border-left:1px solid var(--border)}
.hoy-cell:first-child{border-left:none}
.hoy-lbl{font-size:9px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;color:var(--text-3)}
.hoy-val{font-size:18px;font-weight:700;line-height:1.15;color:var(--text);font-variant-numeric:tabular-nums}
.hoy-sub{font-size:10px;color:var(--text-3);font-variant-numeric:tabular-nums}
.flow-cell{flex:1;padding:15px 20px;display:flex;flex-direction:column;gap:5px;min-width:0;border-left:1px solid var(--border);position:relative}
.flow-cell:first-child{border-left:none}
.flow-dot{display:flex;align-items:center;gap:7px}
.flow-tick{width:8px;height:8px;border-radius:2px;flex-shrink:0}
.tk-blue{background:var(--blue)}.tk-amber{background:var(--amber)}.tk-red{background:var(--red)}.tk-green{background:var(--green)}
.flow-label{font-size:10px;font-weight:700;letter-spacing:.6px;text-transform:uppercase;color:var(--text-2)}
.flow-val{font-size:24px;font-weight:700;line-height:1;color:var(--text);font-variant-numeric:tabular-nums}
.flow-sub{font-size:13px;color:var(--text-3);font-variant-numeric:tabular-nums}
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
.meta-tag{font-size:13px;padding:3px 10px;border-radius:12px;font-weight:700}
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
@keyframes shimmer{0%{background-position:-200px 0}100%{background-position:200px 0}}
.sk{height:12px;border-radius:4px;background:#e2e8f0;background-image:linear-gradient(90deg,#e2e8f0 0,#f1f5f9 60px,#e2e8f0 120px);background-size:200px 100%;animation:shimmer 1.2s infinite linear;flex-shrink:0}
body.dark .sk{background:#334155;background-image:linear-gradient(90deg,#334155 0,#3e4f66 60px,#334155 120px)}
.sk-overlay{display:none;position:absolute;inset:0;z-index:6;background:var(--surface);border-radius:inherit;overflow:hidden;padding:16px 20px;flex-direction:column;gap:10px}
.hero .sk-overlay,.flow-bar .sk-overlay,.kpi-grid .sk-overlay{border-radius:0}
.main.is-loading .hero,.main.is-loading .kpi-grid,.main.is-loading .flow-bar,
.main.is-loading .meta-card,.main.is-loading .card{position:relative;overflow:hidden}
.main.is-loading .sk-overlay{display:flex}
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
/* ── Chip días hábiles restantes ── */
.rest-chip{display:inline-block;background:var(--bg2,#f1f5f9);color:var(--text3,#64748b);font-size:10px;font-weight:600;padding:2px 7px;border-radius:10px;margin-left:6px;vertical-align:middle;border:1px solid var(--border)}
.rest-chip.urgent{background:#fef3c7;color:#92400e;border-color:#fde68a}
</style>
</head>
<body>

<div class="hdr">
  <div class="hdr-left">
    @@LOGO@@
    <div class="div-v"></div>
    <div>
      <div class="hdr-title">Operaciones · Tiempo Real</div>
      <div class="hdr-sub">Reactor · MSPA · Actualización automática</div>
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
    <button class="icon-btn" onclick="toggleKiosk()" id="kiosk-btn" title="Modo Kiosk (presentación)">
      <svg class="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M8 3H5a2 2 0 0 0-2 2v3M21 8V5a2 2 0 0 0-2-2h-3M3 16v3a2 2 0 0 0 2 2h3M16 21h3a2 2 0 0 0 2-2v-3"/></svg>
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
    <div class="sk-overlay" style="flex-direction:row;gap:16px">
      <div style="flex:1.6;display:flex;flex-direction:column;gap:12px">
        <div class="sk" style="width:45%;height:9px"></div>
        <div class="sk" style="width:75%;height:48px;border-radius:6px"></div>
        <div class="sk" style="width:35%;height:9px"></div>
        <div class="sk" style="width:28%;height:9px;margin-top:4px"></div>
      </div>
      <div style="flex:1;display:flex;flex-direction:column;gap:16px">
        <div style="display:flex;flex-direction:column;gap:8px">
          <div class="sk" style="width:60%;height:9px"></div>
          <div class="sk" style="width:85%;height:22px;border-radius:5px"></div>
        </div>
        <div class="sk" style="width:100%;height:1px;opacity:.4"></div>
        <div style="display:flex;flex-direction:column;gap:8px">
          <div class="sk" style="width:55%;height:9px"></div>
          <div class="sk" style="width:85%;height:22px;border-radius:5px"></div>
        </div>
      </div>
    </div>
  </div>

  <!-- KPI strip secundario -->
  <div class="sec">
    <div class="sec-lbl" id="sec-reactor">Indicadores del día · —</div>
    <div id="err-r" class="err"></div>
    <div class="kpi-grid" style="grid-template-columns:repeat(4,1fr)">
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
      <div class="kpi">
        <div class="kpi-lbl">Pedido Promedio</div>
        <div class="kpi-top">
          <div class="kpi-val num" id="k-ticket">—</div>
          <div id="spark-ticket"></div>
        </div>
        <div class="kpi-foot" id="d-ticket"></div>
      </div>
      <div class="kpi">
        <div class="kpi-lbl">% Facturado del Día</div>
        <div class="kpi-top">
          <div class="kpi-val num" id="k-factpct">—</div>
          <div style="width:74px;height:30px;flex-shrink:0"></div>
        </div>
        <div class="kpi-foot" id="d-factpct"></div>
      </div>
    <div class="sk-overlay" style="flex-direction:row;gap:12px;padding:12px 16px">
      <div style="flex:1;display:flex;flex-direction:column;gap:8px">
        <div class="sk" style="width:65%;height:9px"></div>
        <div class="sk" style="width:50%;height:26px;border-radius:5px"></div>
        <div class="sk" style="width:55%;height:9px"></div>
      </div>
      <div style="flex:1;display:flex;flex-direction:column;gap:8px">
        <div class="sk" style="width:65%;height:9px"></div>
        <div class="sk" style="width:50%;height:26px;border-radius:5px"></div>
        <div class="sk" style="width:55%;height:9px"></div>
      </div>
      <div style="flex:1;display:flex;flex-direction:column;gap:8px">
        <div class="sk" style="width:65%;height:9px"></div>
        <div class="sk" style="width:50%;height:26px;border-radius:5px"></div>
        <div class="sk" style="width:55%;height:9px"></div>
      </div>
      <div style="flex:1;display:flex;flex-direction:column;gap:8px">
        <div class="sk" style="width:65%;height:9px"></div>
        <div class="sk" style="width:50%;height:26px;border-radius:5px"></div>
        <div class="sk" style="width:55%;height:9px"></div>
      </div>
    </div>
    </div>
  </div>

  <!-- Flujo del día -->
  <div class="sec">
    <div class="sec-lbl" data-flow="1">Flujo del Día — Pedidos Informados → Facturación</div>
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
        <div class="flow-sub num" id="fl-fact-mspa" style="font-size:12px;opacity:.7;margin-top:2px"></div>
      </div>
    <div class="sk-overlay" style="flex-direction:row;gap:8px;padding:12px 16px">
      <div style="flex:1;display:flex;flex-direction:column;gap:7px">
        <div class="sk" style="width:55%;height:9px"></div>
        <div class="sk" style="width:70%;height:20px;border-radius:4px"></div>
        <div class="sk" style="width:45%;height:9px"></div>
      </div>
      <div style="flex:1;display:flex;flex-direction:column;gap:7px">
        <div class="sk" style="width:55%;height:9px"></div>
        <div class="sk" style="width:70%;height:20px;border-radius:4px"></div>
        <div class="sk" style="width:45%;height:9px"></div>
      </div>
      <div style="flex:1;display:flex;flex-direction:column;gap:7px">
        <div class="sk" style="width:55%;height:9px"></div>
        <div class="sk" style="width:70%;height:20px;border-radius:4px"></div>
        <div class="sk" style="width:45%;height:9px"></div>
      </div>
      <div style="flex:1;display:flex;flex-direction:column;gap:7px">
        <div class="sk" style="width:55%;height:9px"></div>
        <div class="sk" style="width:70%;height:20px;border-radius:4px"></div>
        <div class="sk" style="width:45%;height:9px"></div>
      </div>
    </div>
    </div>
  </div>

  <!-- Pedidos de hoy — panel informativo (oculto en modo histórico) -->
  <div class="sec" id="hoy-sec">
    <div class="sec-lbl" id="hoy-lbl">Hoy — Pedidos informados hoy (en tiempo real)</div>
    <div class="hoy-bar" id="hoy-bar">
      <div class="hoy-cell">
        <div class="hoy-lbl">Pedidos</div>
        <div class="hoy-val num" id="hoy-pedidos">—</div>
        <div class="hoy-sub" id="hoy-vend">—</div>
      </div>
      <div class="hoy-cell">
        <div class="hoy-lbl">Monto Informado</div>
        <div class="hoy-val num" id="hoy-valor">—</div>
      </div>
      <div class="hoy-cell">
        <div class="hoy-lbl">Pedido Promedio</div>
        <div class="hoy-val num" id="hoy-ticket">—</div>
      </div>
      <div class="hoy-cell">
        <div class="hoy-lbl">Ped / Vendedor</div>
        <div class="hoy-val num" id="hoy-pedvend">—</div>
      </div>
      <div class="hoy-cell">
        <div class="hoy-lbl">Líneas / Pedido</div>
        <div class="hoy-val num" id="hoy-lineas">—</div>
      </div>
    </div>
  </div>

  <!-- Ritmo mensual — ancla para kiosk página 2 -->
  <div class="meta-card" id="kiosk-p2">
    <div class="sec-lbl">Ritmo Mensual — Pedidos vs. Mes Anterior</div>
    <div class="meta-row" id="meta-row">
      <span style="color:var(--text3);font-size:11px">Cargando...</span>
    </div>
    <div class="sk-overlay" style="gap:12px">
      <div class="sk" style="width:45%;height:9px"></div>
      <div style="display:flex;gap:10px;flex:1">
        <div class="sk" style="flex:1;border-radius:6px"></div>
        <div class="sk" style="flex:1;border-radius:6px"></div>
        <div class="sk" style="flex:1;border-radius:6px"></div>
        <div class="sk" style="flex:1;border-radius:6px"></div>
        <div class="sk" style="flex:1;border-radius:6px"></div>
      </div>
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
      <div id="chart-partial-note" style="font-size:10px;color:var(--text-3);padding:4px 4px 0;font-style:italic"></div>
      <div class="sk-overlay" style="gap:10px">
        <div class="sk" style="width:40%;height:9px"></div>
        <div class="sk" style="width:100%;flex:1;border-radius:6px;min-height:80px"></div>
      </div>
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
      <div class="sk-overlay" style="gap:8px">
        <div class="sk" style="width:40%;height:9px"></div>
        <div class="sk" style="width:100%;height:34px;border-radius:4px"></div>
        <div class="sk" style="width:100%;height:34px;border-radius:4px"></div>
        <div class="sk" style="width:100%;height:34px;border-radius:4px"></div>
        <div class="sk" style="width:75%;height:34px;border-radius:4px"></div>
      </div>
    </div>
  <!-- Ranking vendedores — oculto por pedido de Daniel -->
  <div class="sec" style="display:none">
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
        <div class="sk-overlay" style="gap:7px;padding:14px 16px">
          <div class="sk" style="width:50%;height:9px"></div>
          <div class="sk" style="width:100%;height:26px;border-radius:4px"></div>
          <div class="sk" style="width:100%;height:26px;border-radius:4px"></div>
          <div class="sk" style="width:100%;height:26px;border-radius:4px"></div>
          <div class="sk" style="width:85%;height:26px;border-radius:4px"></div>
          <div class="sk" style="width:70%;height:26px;border-radius:4px"></div>
        </div>
      </div>
      <div class="card">
        <div class="card-head">
          <div class="head-ico">
            <svg class="ico ic-ret" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M10 15V9M14 15V9"/></svg>
            <span class="sec-lbl">Más retenidos</span>
          </div>
        </div>
        <div id="sell-ret"></div>
        <div class="sk-overlay" style="gap:7px;padding:14px 16px">
          <div class="sk" style="width:50%;height:9px"></div>
          <div class="sk" style="width:100%;height:26px;border-radius:4px"></div>
          <div class="sk" style="width:100%;height:26px;border-radius:4px"></div>
          <div class="sk" style="width:100%;height:26px;border-radius:4px"></div>
          <div class="sk" style="width:85%;height:26px;border-radius:4px"></div>
          <div class="sk" style="width:70%;height:26px;border-radius:4px"></div>
        </div>
      </div>
      <div class="card">
        <div class="card-head">
          <div class="head-ico">
            <svg class="ico ic-an" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="m4.9 4.9 14.2 14.2"/></svg>
            <span class="sec-lbl">Más anulados</span>
          </div>
        </div>
        <div id="sell-an"></div>
        <div class="sk-overlay" style="gap:7px;padding:14px 16px">
          <div class="sk" style="width:50%;height:9px"></div>
          <div class="sk" style="width:100%;height:26px;border-radius:4px"></div>
          <div class="sk" style="width:100%;height:26px;border-radius:4px"></div>
          <div class="sk" style="width:100%;height:26px;border-radius:4px"></div>
          <div class="sk" style="width:85%;height:26px;border-radius:4px"></div>
          <div class="sk" style="width:70%;height:26px;border-radius:4px"></div>
        </div>
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

function sparkSvg(data,w=74,h=30,dates,fmtFn){
  if(!data||data.length<2)return '';
  const mn=Math.min(...data),mx=Math.max(...data),rng=(mx-mn)||1;
  const pad=2,step=(w-pad*2)/(data.length-1);
  const pts=data.map((v,i)=>[pad+i*step, h-pad-((v-mn)/rng)*(h-pad*2)]);
  const d=pts.map(([x,y],i)=>`${i?'L':'M'}${x.toFixed(1)} ${y.toFixed(1)}`).join(' ');
  const area=`${d} L${pts[pts.length-1][0].toFixed(1)} ${h} L${pts[0][0].toFixed(1)} ${h} Z`;
  const c='var(--text-3)';
  const gid='sg'+Math.abs(data.slice(0,3).reduce((a,v,i)=>a^(v*1000+i*7),0)).toString(36);
  const [lx,ly]=pts[pts.length-1];
  // hit areas para tooltip
  const hits=pts.map(([x,y],i)=>{
    const lbl=dates&&dates[i]?dates[i]:'';
    const val=fmtFn?fmtFn(data[i]):fmtN(data[i],1);
    return `<rect x="${(x-step/2).toFixed(1)}" y="0" width="${step.toFixed(1)}" height="${h}" fill="transparent"><title>${lbl}: ${val}</title></rect>`;
  }).join('');
  return `<svg class="spark" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none" style="overflow:visible">
  <defs><linearGradient id="${gid}" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="${c}" stop-opacity=".18"/><stop offset="100%" stop-color="${c}" stop-opacity="0"/>
  </linearGradient></defs>
  <path d="${area}" fill="url(#${gid})"/>
  <path d="${d}" fill="none" stroke="${c}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
  <circle cx="${lx.toFixed(1)}" cy="${ly.toFixed(1)}" r="2.2" fill="${c}"/>
  ${hits}
</svg>`;
}

function sparkWithAvg(data,dates,fmtFn){
  if(!data||data.length<2)return '';
  const avg=data.reduce((a,v)=>a+v,0)/data.length;
  const avgStr=fmtFn?fmtFn(avg):fmtN(avg,1);
  return `<div style="display:flex;flex-direction:column;align-items:flex-end;gap:2px">
    ${sparkSvg(data,74,30,dates,fmtFn)}
    <span style="font-size:11px;color:var(--text-3);font-variant-numeric:tabular-nums" title="Promedio 14 días hábiles">prom. ${avgStr}</span>
  </div>`;
}

function deltaHtml(curr,prev,compLbl){
  if(!prev||!curr)return '';
  const p=(curr-prev)/prev*100;
  const ico=p>0?ICO.arrowUp:ICO.arrowDown;
  const cls=p>0?'up':'down';
  const lbl=compLbl?`<span style="font-size:11px;color:var(--text-3);display:block;margin-top:2px">${compLbl}</span>`:'';
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
  if(diasHab>0){
    const restDias=diasHab-diasElapsed;
    const urgente=restDias<=3;
    const chip=`<span class="rest-chip${urgente?' urgent':''}">${restDias} día${restDias!==1?'s':''} hábil${restDias!==1?'es':''} restante${restDias!==1?'s':''}</span>`;
    document.getElementById('hero-foot-l').innerHTML=`Día hábil ${diasElapsed} de ${diasHab}${chip}`;
  } else {
    document.getElementById('hero-foot-l').textContent='';
  }
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

let _lastTrend=null;
function renderChart(trend){
  if(!trend||!trend.length)return;
  const ctx=document.getElementById('trend');
  if(!ctx||!window.Chart)return;
  const MESES=['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic'];
  const labels=trend.map(t=>{
    const[y,m]=t.mes.split('-');
    const base=MESES[+m-1]+' '+y.slice(2);
    return t.is_partial?base+' *':base;
  });
  const barData=trend.map(t=>t.dias_hab?+((t.pedidos/t.dias_hab).toFixed(1)):0);
  const lineData=trend.map(t=>t.dias_hab?+(((t.valor/1e6)/t.dias_hab).toFixed(2)):0);
  const dark=document.body.classList.contains('dark');
  const gridColor=dark?'rgba(255,255,255,.06)':'rgba(0,0,0,.06)';
  const txtColor=dark?'#94a3b8':'#64748b';
  const barBg=trend.map(t=>t.is_partial
    ?(dark?'rgba(148,163,184,.18)':'rgba(203,213,225,.45)')
    :(dark?'rgba(148,163,184,.35)':'rgba(203,213,225,.8)'));
  const barBorder=trend.map(t=>t.is_partial
    ?(dark?'#334155':'#e2e8f0')
    :(dark?'#475569':'#cbd5e1'));
  chartObj=new Chart(ctx,{
    plugins:[{
      id:'dash-labels',
      afterDatasetsDraw(chart){
        const ctx2=chart.ctx;
        chart.data.datasets.forEach((ds,di)=>{
          const meta=chart.getDatasetMeta(di);
          if(meta.hidden)return;
          meta.data.forEach((el,i)=>{
            const t=trend[i];
            if(!t)return;
            const isBars=(ds.type==='bar'||ds.yAxisID==='y1');
            const lbl=isBars
              ? Math.round(t.pedidos/(t.dias_hab||1)).toLocaleString('es-AR')
              : '$'+Math.round((t.valor/1e6)/(t.dias_hab||1));
            ctx2.save();
            ctx2.font=isBars?'600 13px system-ui':'700 13px system-ui';
            ctx2.fillStyle=isBars?txtColor:'#cc0000';
            ctx2.textAlign='center';
            ctx2.textBaseline='bottom';
            ctx2.fillText(lbl, el.x, isBars?el.y-2:el.y-6);
            ctx2.restore();
          });
        });
      }
    }],
    data:{labels,datasets:[
      {type:'bar',label:'Pedidos / día',data:barData,backgroundColor:barBg,borderColor:barBorder,borderWidth:1,yAxisID:'y1',borderRadius:3,order:2},
      {type:'line',label:'Venta M$ / día',data:lineData,borderColor:'#cc0000',backgroundColor:'rgba(204,0,0,.06)',borderWidth:2.5,tension:.35,yAxisID:'y2',fill:true,pointRadius:2.5,pointBackgroundColor:'#cc0000',order:1},
    ]},
    options:{responsive:true,maintainAspectRatio:false,
      layout:{padding:{top:24}},
      interaction:{mode:'index',intersect:false},
      plugins:{
        legend:{position:'bottom',labels:{boxWidth:12,padding:16,color:txtColor,font:{size:11},usePointStyle:true}},
        tooltip:{callbacks:{
          title(items){
            const i=items[0].dataIndex;
            const t=trend[i];
            if(t&&t.is_partial)return items[0].label.replace(' *','')+' (parcial — '+t.dias_hab+' días hábiles transcurridos de '+t.dias_tot+')';
            return items[0].label;
          }
        }}
      },
      scales:{
        x:{grid:{display:false},ticks:{color:txtColor,font:{size:10}}},
        y1:{position:'left',title:{display:true,text:'pedidos/día',color:txtColor,font:{size:10}},ticks:{color:txtColor,font:{size:10}},grid:{color:gridColor}},
        y2:{position:'right',title:{display:true,text:'M$/día',color:txtColor,font:{size:10}},ticks:{color:'#cc0000',font:{size:10},callback:v=>fmtN(v,1)},grid:{drawOnChartArea:false}},
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
      alerts.push(`<div class="alert warn">${ICO.trendingDown}<span>Plan de ventas <b>${fmtN(gap,1)} pts por debajo del ritmo</b> (${fmtN(pctVal,1)}% vs ${fmtN(pacePos,1)}% esperado)</span></div>`);
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

function renderTodaySummary(ts){
  const sec=document.getElementById('hoy-sec');
  if(!ts||!ts.pedidos){if(sec)sec.style.display='none';return;}
  if(sec)sec.style.display='';
  const dp=ts.date?ts.date.split('-').reverse().join('/'):new Date().toLocaleDateString('es-AR');
  document.getElementById('hoy-lbl').textContent='Hoy '+dp+' — Pedidos informados hoy (en tiempo real)';
  document.getElementById('hoy-pedidos').textContent=fmtN(ts.pedidos,0);
  document.getElementById('hoy-vend').textContent=fmtN(ts.vendedores,0)+' vendedores con pedidos hoy';
  document.getElementById('hoy-valor').textContent=fmtK(ts.valor||0);
  document.getElementById('hoy-ticket').textContent=fmtK(ts.ticket||0);
  document.getElementById('hoy-pedvend').textContent=fmtN(ts.avg_ped_vend,1);
  document.getElementById('hoy-lineas').textContent=fmtN(ts.avg_lineas,1);
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
  document.getElementById('sec-reactor').textContent='Indicadores del día · '+dp+(_isHistoric?' (fecha manual)':' (día anterior)');
  const flowLblEl=document.querySelector('.sec-lbl[data-flow]');
  if(flowLblEl)flowLblEl.textContent='Flujo del Día '+dp+' — Pedidos Informados → Facturación';
  const histBanner=document.getElementById('hist-banner');
  if(_isHistoric){
    document.getElementById('hist-date').textContent=dp;
    histBanner.style.display='block';
    const s=document.getElementById('hoy-sec');if(s)s.style.display='none';
  } else {
    histBanner.style.display='none';
    renderTodaySummary(data.today_summary||null);
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
  document.getElementById('k-avg').textContent=fmtN(r.avg_lineas,1);
  document.getElementById('d-avg').innerHTML=c&&c.avg_lineas?deltaHtml(r.avg_lineas,c.avg_lineas,compLbl):'';

  // Sparklines con promedio y tooltip de fecha
  const sp=r.sparklines||{};
  const spd=sp.dates||[];
  document.getElementById('spark-ped').innerHTML=sparkWithAvg(sp.pedidos,spd,v=>fmtN(v,0));
  document.getElementById('spark-ventas').innerHTML=sparkWithAvg(sp.ventas,spd,v=>fmtK(v*1e6));
  document.getElementById('spark-vend').innerHTML=sparkWithAvg(sp.ped_vend,spd,v=>fmtN(v,1));
  document.getElementById('spark-avg').innerHTML=sparkWithAvg(sp.avg_lin,spd,v=>fmtN(v,1));
  document.getElementById('spark-ticket').innerHTML=sparkWithAvg(sp.ticket,spd,v=>fmtK(v));

  // Flow bar
  const fact_cnt=(bs[13]?.cnt||0)+(bs[18]?.cnt||0);
  const fact_val=(bs[13]?.val||0)+(bs[18]?.val||0);
  // KPIs adicionales — ticket promedio y % facturado
  document.getElementById('k-ticket').textContent=total>0?fmtK((r.valor||0)/total):'—';
  document.getElementById('d-ticket').textContent=total>0?fmtN(total,0)+' pedidos informados':'';
  document.getElementById('k-factpct').textContent=total>0?fmtN((fact_cnt/total)*100,1)+'%':'—';
  document.getElementById('d-factpct').textContent=fmtN(fact_cnt,0)+' de '+fmtN(total,0)+' ped.';

  document.getElementById('fl-inf-val').textContent=fmtK(r.valor||0);
  document.getElementById('fl-inf-ped').textContent=fmtN(total,0)+' pedidos';
  document.getElementById('fl-ret-val').textContent=fmtK(bs[15]?.val||0);
  document.getElementById('fl-ret-ped').textContent=fmtN(ret,0)+' ped · '+pct(ret,total);
  document.getElementById('fl-an-val').textContent=fmtK(bs[14]?.val||0);
  document.getElementById('fl-an-ped').textContent=fmtN(an,0)+' ped · '+pct(an,total);
  document.getElementById('fl-fact-val').textContent=fmtK(fact_val);
  document.getElementById('fl-fact-ped').textContent=fmtN(fact_cnt,0)+' pedidos'+(total>0?' · '+pct(fact_cnt,total):'');
  const elMspaRef=document.getElementById('fl-fact-mspa');
  if(elMspaRef)elMspaRef.textContent=venta.val>0?'Cierre Reactor · MSPA día: '+fmtK(venta.val):'';

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
  if(r.trend){
    _lastTrend=r.trend;
    renderChart(r.trend);
    const partial=r.trend.find(t=>t.is_partial);
    const noteEl=document.getElementById('chart-partial-note');
    if(noteEl&&partial)noteEl.textContent='* Mes en curso — promedio sobre '+partial.dias_hab+' días hábiles transcurridos de '+partial.dias_tot+' del mes.';
    else if(noteEl)noteEl.textContent='';
  }

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
      <span class="mspa-val">${fmtK(d.val)}<span class="mspa-sub-txt">${fmtN(d.ords)} ped · ${fmtN(d.pos)} lin</span></span>
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
  if(_lastTrend)renderChart(_lastTrend);
}
function toggleTV(){
  const tv=document.body.classList.toggle('tv');
  document.getElementById('tv-btn').classList.toggle('on',tv);
  localStorage.setItem('wuerth-tv',tv?'1':'0');
  if(_lastTrend)renderChart(_lastTrend);
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

// ── KIOSK — abre el wallboard /kiosk (tablero fijo, rota solo, sin botones) ──
function toggleKiosk(){
  // Pide fullscreen y navega al wallboard
  try{ if(document.documentElement.requestFullscreen) document.documentElement.requestFullscreen(); }catch(e){}
  window.location.href='/kiosk';
}
</script>
</body>
</html>
""".replace("@@LOGO@@", LOGO_HTML)


# ─────────────────────────────────────────────────────────────────────────────
# KIOSK / WALLBOARD — tablero fijo 1920×1080 escalado a la TV, sin scroll,
# sin botones, rota en silencio entre 2 tableros. Consume /api/data (datos reales).
# ─────────────────────────────────────────────────────────────────────────────
KIOSK_PAGE = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Würth — Kiosk / Wallboard</title>
<style>
:root{
  --wurth-red:#cc0000; --wurth-red-hover:#b00000;
  --bg:#eef1f5; --panel:#ffffff; --panel-2:#f6f8fb;
  --border:#e6eaf0; --border-2:#d3dae3;
  --text:#0f172a; --text-2:#475569; --text-3:#8a97a8;
  --blue:#2563eb; --green:#059669; --amber:#d97706; --red:#dc2626;
  --green-bg:#ecfdf3; --amber-bg:#fff8eb; --red-bg:#fef2f2; --blue-bg:#eff5ff;
  --font-sans:'IBM Plex Sans',-apple-system,BlinkMacSystemFont,'Segoe UI',system-ui,sans-serif;
  --shadow:0 1px 3px rgba(15,23,42,.06),0 1px 2px rgba(15,23,42,.04);
}
*{margin:0;padding:0;box-sizing:border-box}
.num{font-variant-numeric:tabular-nums;font-feature-settings:"tnum"}
html,body{height:100%;background:var(--bg);overflow:hidden;font-family:var(--font-sans)}
.viewport{position:fixed;inset:0;background:var(--bg);overflow:hidden}
.stage{width:1920px;height:1080px;background:var(--bg);position:absolute;left:0;top:0;transform-origin:top left;overflow:hidden;color:var(--text)}
.kt-top{height:96px;display:flex;align-items:center;justify-content:space-between;padding:0 44px;border-bottom:3px solid var(--wurth-red);background:var(--panel)}
.kt-brand{display:flex;align-items:center;gap:22px}
.kt-logo{font-size:34px;font-weight:800;color:var(--wurth-red);letter-spacing:-1px}
.kt-brand img{height:54px!important;width:auto!important}
.kt-brand .logo-text-fallback{font-size:34px;font-weight:800;color:var(--wurth-red);letter-spacing:-1px}
.kt-divider{width:2px;height:44px;background:var(--border-2)}
.kt-title{font-size:30px;font-weight:700;letter-spacing:-.3px;line-height:1}
.kt-sub{font-size:16px;color:var(--text-3);margin-top:5px;letter-spacing:.4px}
.kt-right{display:flex;align-items:center;gap:40px}
.kt-conn{display:flex;flex-direction:column;gap:7px;font-size:15px;color:var(--text-2)}
.kt-conn-row{display:flex;align-items:center;gap:9px}
.kt-dot{width:11px;height:11px;border-radius:50%}
.kt-dot.ok{background:var(--green)}
.kt-dot.slow{background:var(--amber)}
.kt-dot.down{background:var(--red)}
.kt-conn b{color:var(--text);font-weight:600}
.kt-clock{text-align:right}
.kt-time{font-size:42px;font-weight:700;line-height:1;letter-spacing:-.5px}
.kt-date{font-size:17px;color:var(--text-3);margin-top:4px;text-transform:capitalize}
.kt-ctxbar{display:flex;align-items:center;gap:16px;height:72px;padding:0 44px;font-size:23px;font-weight:600;border-bottom:1px solid}
.kt-ctxbar .ico{width:30px;height:30px;flex-shrink:0}
.kt-ctxbar b{font-weight:800}
.kt-ctxbar .ctx-sep{color:currentColor;opacity:.4}
.kt-ctxbar .ctx-metric{font-size:20px;font-weight:600;opacity:.92}
.kt-ctxbar .ctx-metric b{margin-left:6px}
.kt-ctxbar .ctx-tag{margin-left:auto;font-size:16px;font-weight:800;padding:5px 14px;border-radius:8px;white-space:nowrap}
.kt-ctxbar.warn{background:var(--amber-bg);color:#b45309;border-color:#fcd9a4}
.kt-ctxbar.warn .ctx-tag{background:#fff;color:#b45309}
.kt-ctxbar.danger{background:var(--red-bg);color:#b91c1c;border-color:#fbcdcd}
.kt-ctxbar.danger .ctx-tag{background:#fff;color:#b91c1c}
.kt-ctxbar.ok{background:var(--green-bg);color:#15803d;border-color:#b7ecca}
.kt-ctxbar.ok .ctx-tag{background:#fff;color:#15803d}
.kt-board{position:absolute;left:0;right:0;bottom:14px;padding:26px 44px 0;display:none}
.kt-board.active{display:block}
.kt-board.top1{top:168px}
.kt-board.top0{top:150px}
.north-tag{margin-left:auto;font-size:15px;font-weight:700;padding:4px 12px;border-radius:8px}
.north-tag.ok{background:var(--green-bg);color:#065f46}
.north-tag.warn{background:#fef3c7;color:#92400e}
.north-tag.danger{background:#fee2e2;color:#991b1b}
.kt-eyebrow{display:flex;align-items:center;gap:9px;font-size:16px;font-weight:700;letter-spacing:1.6px;text-transform:uppercase;color:var(--text-3);margin-bottom:14px}
.kt-eyebrow .ico{width:18px;height:18px}
.b1-grid{display:grid;grid-template-columns:1fr 1fr;grid-template-rows:auto auto auto;gap:20px;height:100%}
.panel{background:var(--panel);border:1px solid var(--border);border-radius:16px;padding:26px 30px;box-shadow:var(--shadow)}
.b1-plan{grid-column:1 / -1;display:flex;align-items:center;gap:54px;padding:30px 36px}
.b1-plan-l{flex:1;min-width:0}
.b1-plan-eyebrow{display:flex;align-items:center;gap:10px;font-size:16px;font-weight:700;letter-spacing:1.6px;text-transform:uppercase;color:var(--text-3);margin-bottom:12px}
.b1-plan-eyebrow .ico{width:18px;height:18px;color:var(--wurth-red)}
.b1-figs{display:flex;align-items:baseline;gap:18px}
.b1-curr{font-size:104px;font-weight:700;line-height:.92;letter-spacing:-3px}
.b1-total{font-size:40px;color:var(--text-3);font-weight:600}
.b1-bar-line{display:flex;align-items:center;gap:22px;margin-top:22px}
.b1-pct{font-size:34px;font-weight:800;min-width:120px}
.b1-bar-bg{flex:1;height:26px;background:var(--border);border-radius:13px;position:relative;overflow:hidden}
.b1-bar-fill{height:100%;border-radius:13px}
.b1-bar-pace{position:absolute;top:-6px;bottom:-6px;width:4px;background:var(--text)}
.b1-plan-foot{display:flex;gap:0;margin-top:20px;font-size:20px;color:var(--text-2)}
.b1-plan-foot b{color:var(--text);font-weight:700}
.b1-plan-foot .pf-item{padding:10px 24px;border-radius:10px;display:inline-flex;align-items:center;gap:6px}
.b1-plan-foot .pf-item .ico{width:14px;height:14px;flex-shrink:0}
.b1-plan-foot .pf-item:first-child{background:var(--blue-bg);color:#1e40af}
.b1-plan-foot .pf-item:first-child b{color:#1d4ed8}
.b1-plan-foot .pf-item:nth-child(2){background:var(--amber-bg);color:#92400e;margin:0 16px}
.b1-plan-foot .pf-item:nth-child(2) b{color:#b45309}
.b1-plan-foot .pf-item:last-child{background:var(--panel-2);color:var(--text-2)}
.b1-plan-r{width:1px;align-self:stretch;background:var(--border)}
.b1-proy{flex-shrink:0;text-align:right;min-width:300px}
.b1-proy .l{font-size:17px;text-transform:uppercase;letter-spacing:1px;color:var(--text-3);margin-bottom:10px}
.b1-proy .v{font-size:58px;font-weight:800;line-height:1;color:var(--wurth-red)}
.b1-proy .s{font-size:24px;color:var(--text-2);margin-top:8px;font-weight:600}
.b1-state{display:inline-flex;align-items:center;gap:8px;margin-top:16px;font-size:19px;font-weight:700;padding:7px 16px;border-radius:10px}
.b1-state.warn{background:#fef3c7;color:#92400e;border:1px solid #f59e0b}
.b1-state.ok{background:#d1fae5;color:#065f46;border:1px solid #059669}
.b1-stat{display:flex;flex-direction:column;justify-content:center}
.b1-stat .l{font-size:18px;text-transform:uppercase;letter-spacing:1px;color:var(--text-3);margin-bottom:12px}
.b1-stat .v{font-size:72px;font-weight:700;line-height:1}
.b1-stat .s{font-size:20px;color:var(--text-2);margin-top:10px}
.b1-delta{display:inline-flex;align-items:center;gap:5px;font-size:22px;font-weight:700;margin-top:10px}
.b1-delta .ico{width:22px;height:22px}
.b1-delta.up{color:var(--green)}.b1-delta.down{color:var(--red)}
.b1-flow{grid-column:1 / -1;display:grid;grid-template-columns:repeat(4,1fr);gap:0;padding:0;overflow:hidden}
.b1-flow-cell{padding:24px 28px;border-left:1px solid var(--border);display:flex;flex-direction:column;gap:9px}
.b1-flow-cell:first-child{border-left:none}
.b1-flow-top{display:flex;align-items:center;gap:11px}
.b1-tick{width:14px;height:14px;border-radius:4px}
.b1-flow-label{font-size:18px;font-weight:700;letter-spacing:.8px;text-transform:uppercase;color:var(--text-2)}
.b1-flow-val{font-size:54px;font-weight:700;line-height:1}
.b1-flow-sub{font-size:18px;color:var(--text-3)}
.tk-blue{background:var(--blue)}.tk-amber{background:var(--amber)}.tk-red{background:var(--red)}.tk-green{background:var(--green)}
.b1-live{grid-column:1 / -1;background:var(--panel-2);border:1px solid var(--border);border-radius:16px;padding:20px 30px;display:flex;align-items:center;gap:0}
.b1-live-head{display:flex;flex-direction:column;gap:8px;padding-right:34px;border-right:1px solid var(--border);margin-right:6px}
.b1-live-badge{display:inline-flex;align-items:center;gap:8px;font-size:15px;font-weight:800;letter-spacing:.8px;color:var(--green);text-transform:uppercase}
.b1-live-badge .pdot{width:10px;height:10px;border-radius:50%;background:var(--green);box-shadow:0 0 10px 1px rgba(34,197,94,.7);animation:pulse-dot 2s ease-in-out infinite}
@keyframes pulse-dot{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.45;transform:scale(.85)}}
.b1-live-ttl{font-size:17px;color:var(--text-3)}
.b1-live-items{flex:1;display:grid;grid-template-columns:repeat(5,1fr);gap:0}
.b1-live-item{padding:0 26px;border-left:1px solid var(--border)}
.b1-live-item:first-child{border-left:none}
.b1-live-item .l{font-size:14px;text-transform:uppercase;letter-spacing:.6px;color:var(--text-3);margin-bottom:7px}
.b1-live-item .v{font-size:34px;font-weight:700;color:var(--text-2);line-height:1}
.b2-grid{display:grid;grid-template-columns:1.4fr 1fr;grid-template-rows:1fr auto;gap:20px;height:100%}
.b2-chart{grid-row:1 / 2}
.b2-mspa{grid-row:1 / 3}
.b2-ritmo{grid-row:2 / 3}
.b2-chart-wrap{position:relative;height:calc(100% - 46px)}
.mspa-row{display:flex;align-items:center;justify-content:space-between;padding:15px 0;border-bottom:1px solid var(--border)}
.mspa-row:last-child{border-bottom:none}
.mspa-l{display:flex;align-items:center;gap:14px}
.mspa-sem{width:12px;height:12px;border-radius:50%;background:var(--green)}
.mspa-sem.warn{background:var(--amber);box-shadow:0 0 10px 1px rgba(245,158,11,.5)}
.mspa-sem.danger{background:var(--red);box-shadow:0 0 10px 1px rgba(239,68,68,.6)}
.mspa-lbl{font-size:22px;color:var(--text-2)}
.mspa-val{font-size:26px;font-weight:700;text-align:right}
.mspa-val .sub{font-size:15px;color:var(--text-3);font-weight:400;margin-top:2px}
.mspa-row.venta{border-top:2px solid var(--border);margin-top:4px;padding-top:18px}
.mspa-row.venta .mspa-lbl{color:var(--text);font-weight:700;font-size:24px}
.mspa-row.venta .mspa-val{color:var(--green);font-size:38px}
.b2-ritmo-row{display:flex;flex-direction:column;gap:16px}
.b2-ritmo-head{display:flex;align-items:center;justify-content:space-between;gap:24px}
.b2-ritmo-fig{font-size:46px;font-weight:800;color:var(--blue);white-space:nowrap}
.b2-ritmo-fig small{font-size:22px;color:var(--text-3);font-weight:600}
.b2-ritmo-bar{width:100%;height:26px;background:var(--border);border-radius:13px;position:relative;overflow:hidden}
.b2-ritmo-fill{height:100%;border-radius:11px;background:var(--blue)}
.b2-ritmo-pace{position:absolute;top:0;bottom:0;width:3px;background:var(--amber)}
.b2-ritmo-tag{font-size:19px;font-weight:700;white-space:nowrap}
.b2-ritmo-tag.ok{color:var(--green)}.b2-ritmo-tag.warn{color:var(--amber)}
.kt-rot{position:absolute;bottom:0;left:0;right:0;height:6px;display:flex;gap:4px;padding:0 44px 0;align-items:flex-end}
.kt-rot-track{flex:1;height:3px;background:var(--border);border-radius:2px;overflow:hidden}
.kt-rot-fill{height:100%;width:0;background:var(--wurth-red);border-radius:2px}
.kt-dots{position:absolute;bottom:16px;left:50%;transform:translateX(-50%);display:flex;gap:11px}
.kt-pg{width:13px;height:13px;border-radius:50%;background:var(--border-2);cursor:pointer;transition:background .25s,transform .25s}
.kt-pg:hover{transform:scale(1.25)}
.kt-pg.on{background:var(--wurth-red)}
/* ── Empty state del strip EN VIVO ── */
.b1-live-empty{flex:1;font-size:24px;color:var(--text-3);font-weight:500;padding-left:8px}
/* ── Barra de CONTROLES (fuera del stage, no escala) ── */
.kt-ctrl{position:fixed;bottom:26px;right:30px;z-index:1000;display:flex;align-items:center;gap:10px;
  background:rgba(255,255,255,.92);backdrop-filter:blur(8px);border:1px solid var(--border-2);
  border-radius:14px;padding:9px 12px;box-shadow:0 10px 30px rgba(15,23,42,.18);
  opacity:0;pointer-events:none;transition:opacity .3s}
.kt-ctrl.show{opacity:1;pointer-events:auto}
.kt-ctrl button{width:42px;height:42px;border:none;border-radius:10px;background:transparent;color:var(--text-2);
  cursor:pointer;display:flex;align-items:center;justify-content:center;transition:background .15s,color .15s}
.kt-ctrl button:hover{background:var(--bg);color:var(--text)}
.kt-ctrl button.exit:hover{background:#fee2e2;color:var(--wurth-red)}
.kt-ctrl button svg{width:22px;height:22px;stroke-width:1.9}
.kt-ctrl .sep{width:1px;height:26px;background:var(--border-2);margin:0 2px}
.kt-ctrl .pgnum{font-size:14px;font-weight:700;color:var(--text-3);padding:0 8px;min-width:46px;text-align:center;font-variant-numeric:tabular-nums}
.kt-hint{position:fixed;bottom:80px;right:30px;z-index:1000;font-size:13px;color:var(--text-3);
  background:rgba(255,255,255,.92);border:1px solid var(--border);border-radius:8px;padding:6px 11px;
  opacity:0;pointer-events:none;transition:opacity .3s}
.kt-hint.show{opacity:1}
</style>
</head>
<body>
<div class="viewport"><div class="stage" id="stage"></div></div>
<script>
function fmtN(n,d=0){return Number(n||0).toLocaleString('es-AR',{minimumFractionDigits:d,maximumFractionDigits:d});}
function fmtK(n){
  n=Number(n)||0;const neg=n<0;n=Math.abs(n);let s;
  if(n>=1e9)s='$'+(n/1e9).toFixed(1).replace('.',',')+'B';
  else if(n>=1e6)s='$'+(n/1e6).toFixed(1).replace('.',',')+'M';
  else if(n>=1e3)s='$'+Math.round(n/1e3)+'K';
  else s='$'+fmtN(n,0);
  return (neg?'−':'')+s;
}
const ICONS={
  target:'<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>',
  trendingDown:'<path d="M16 17h6v-6"/><path d="m22 17-8.5-8.5-5 5L2 7"/>',
  trendingUp:'<path d="M16 7h6v6"/><path d="m22 7-8.5 8.5-5-5L2 17"/>',
  arrowDown:'<path d="M12 5v14M5 12l7 7 7-7"/>',
  arrowUp:'<path d="M12 19V5M5 12l7-7 7 7"/>',
  layers:'<path d="m12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83l8.58 3.91a2 2 0 0 0 1.66 0l8.58-3.9a1 1 0 0 0 0-1.83Z"/><path d="m22 17.65-9.17 4.16a2 2 0 0 1-1.66 0L2 17.65M22 12.65l-9.17 4.16a2 2 0 0 1-1.66 0L2 12.65"/>',
  activity:'<path d="M22 12h-4l-3 9L9 3l-3 9H2"/>',
  calendar:'<rect width="18" height="18" x="3" y="4" rx="2"/><path d="M3 10h18M8 2v4M16 2v4"/>',
  hourglass:'<path d="M5 22h14M5 2h14M17 22v-4.172a2 2 0 0 0-.586-1.414L12 12l-4.414 4.414A2 2 0 0 0 7 17.828V22M7 2v4.172a2 2 0 0 0 .586 1.414L12 12l4.414-4.414A2 2 0 0 0 17 6.172V2"/>',
  wallet:'<path d="M19 7V4a1 1 0 0 0-1-1H5a2 2 0 0 0 0 4h15a1 1 0 0 1 1 1v4h-3a2 2 0 0 0 0 4h3a1 1 0 0 1-1 1v-1a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5"/><path d="M3 5v14a2 2 0 0 0 2 2h15a1 1 0 0 0 1-1v-4"/>',
};
function ico(name,w=18){return `<svg class="ico" style="width:${w}px;height:${w}px" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">${ICONS[name]||''}</svg>`;}

/* ── estado (se llena con /api/data) ── */
const PLAN={fact_acum:0,plan_total:0,pct:0,pace:0,proy:0,proy_pct:0,dia_habil:0,dias_tot:0,dias_rest:0};
const VENTA={val:0,ords:0};
const PEDIDOS={v:0,delta:0};
const FLOW={informado:{v:0,val:0},retenido:{v:0,val:0,pct:0},anulado:{v:0,val:0,pct:0},facturado:{v:0,val:0}};
const HOY={pedidos:0,monto:0,ticket:0,ped_vend:0,lineas:0};
const RITMO={curr:0,last:0,pct:0,pace:0,sobre:0,onTrack:true};
let MSPA=[];
let TREND=[];
const DATOS_AL={mspa:'—',reactor:'—',mspaOk:true,reactorOk:true};
const MESES=['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic'];
const MSPA_DEF=[
  {k:'backorders',l:'Backorders (Plazos viejos)'},
  {k:'bloqueados',l:'Bloqueados por Límite Crédito'},
  {k:'neg_status',l:'Bloqueados (Status < -1)'},
  {k:'futuros',l:'Pedidos Abiertos (Futuros)'},
  {k:'produccion',l:'Producción Abierta'},
  {k:'remitos',l:'Remitos / Facturas Abiertas'},
  {k:'venta',l:'Venta del Día',venta:true},
];

function mapData(d){
  const r=d.reactor||{}, m=d.mspa||{}, ts=d.today_summary||{};
  const pv=m.plan_ventas||{}, meta=r.meta||{}, bs=r.by_status||{};
  // PLAN
  PLAN.fact_acum=pv.fact_acum||0; PLAN.plan_total=pv.plan_total||0; PLAN.pct=pv.pct_plan||0;
  PLAN.dia_habil=meta.dias_elapsed||0; PLAN.dias_tot=meta.curr_wd||0;
  PLAN.dias_rest=Math.max(0,(meta.curr_wd||0)-(meta.dias_elapsed||0));
  PLAN.pace=meta.curr_wd>0?(meta.dias_elapsed/meta.curr_wd*100):0;
  PLAN.proy=PLAN.dia_habil>0?PLAN.fact_acum/PLAN.dia_habil*PLAN.dias_tot:0;
  PLAN.proy_pct=PLAN.plan_total>0?PLAN.proy/PLAN.plan_total*100:0;
  // VENTA
  const v=m.venta||{}; VENTA.val=v.val||0; VENTA.ords=v.ords||0;
  // PEDIDOS
  PEDIDOS.v=r.pedidos||0;
  const comp=r.comp||null;
  PEDIDOS.delta=comp&&comp.pedidos?((r.pedidos-comp.pedidos)/comp.pedidos*100):0;
  // FLOW
  const total=r.pedidos||0;
  const fcnt=(bs[13]?.cnt||0)+(bs[18]?.cnt||0), fval=(bs[13]?.val||0)+(bs[18]?.val||0);
  FLOW.informado={v:total,val:r.valor||0};
  FLOW.retenido={v:bs[15]?.cnt||0,val:bs[15]?.val||0,pct:total?(bs[15]?.cnt||0)/total*100:0};
  FLOW.anulado={v:bs[14]?.cnt||0,val:bs[14]?.val||0,pct:total?(bs[14]?.cnt||0)/total*100:0};
  FLOW.facturado={v:fcnt,val:fval};
  // HOY (parcial en vivo)
  HOY.pedidos=ts.pedidos||0; HOY.monto=ts.valor||0; HOY.ticket=ts.ticket||0;
  HOY.ped_vend=ts.avg_ped_vend||0; HOY.lineas=ts.avg_lineas||0;
  // MSPA
  MSPA=MSPA_DEF.map(row=>{
    const x=m[row.k]||{ords:0,pos:0,val:0};
    return {k:row.l,val:x.val||0,ords:x.ords||0,pos:x.pos||0,venta:!!row.venta,sev:(!row.venta&&(x.val||0)>0)?'warn':'ok'};
  });
  // RITMO
  RITMO.curr=meta.curr_pedidos||0; RITMO.last=meta.last_pedidos||0;
  RITMO.pct=RITMO.last>0?Math.min(RITMO.curr/RITMO.last*100,120):0;
  RITMO.pace=meta.curr_wd>0?(meta.dias_elapsed/meta.curr_wd*100):0;
  const paceTarget=RITMO.last>0?(Math.min(RITMO.pace,100)/100)*RITMO.last:0;
  RITMO.onTrack=RITMO.curr>=paceTarget;
  RITMO.sobre=Math.round(RITMO.curr-paceTarget);
  // TREND (solo meses con datos)
  TREND=(r.trend||[]).map(t=>{
    const[y,mo]=String(t.mes).split('-');
    return [MESES[+mo-1]+' '+String(y).slice(2), t.pedidos||0, (t.valor||0)/1e6, t.dias_hab||1];
  });
  // datos al / conexión
  DATOS_AL.mspaOk=!d.mspa_error; DATOS_AL.reactorOk=!d.reactor_error;
  DATOS_AL.mspa=d.timestamp||'—'; DATOS_AL.reactor=d.timestamp||'—';
}

function topBar(){
  return `<div class="kt-top">
    <div class="kt-brand">
      @@LOGO@@
      <div class="kt-divider"></div>
      <div><div class="kt-title">Operaciones · Tiempo Real</div>
        <div class="kt-sub">Reactor · MSPA · Actualización automática</div></div>
    </div>
    <div class="kt-right">
      <div class="kt-conn">
        <span class="kt-conn-row"><span class="kt-dot ${DATOS_AL.mspaOk?'ok':'down'}"></span>MSPA ${DATOS_AL.mspaOk?'OK':'sin datos'} · <b>${DATOS_AL.mspa}</b></span>
        <span class="kt-conn-row"><span class="kt-dot ${DATOS_AL.reactorOk?'ok':'down'}"></span>Reactor ${DATOS_AL.reactorOk?'OK':'sin datos'} · <b>${DATOS_AL.reactor}</b></span>
      </div>
      <div class="kt-clock"><div class="kt-time num" id="kt-time">--:--:--</div>
        <div class="kt-date" id="kt-date"></div></div>
    </div>
  </div>`;
}
function ctxBar(){
  if(!PLAN.plan_total) return '';
  const onTrack=PLAN.pct>=PLAN.pace;
  const sev=onTrack?'ok':(PLAN.pace-PLAN.pct)>10?'danger':'warn';
  const gap=fmtN(Math.abs(PLAN.pace-PLAN.pct),1);
  const alertTxt=onTrack
    ?`Plan de ventas <b>en ritmo</b> — ${fmtN(PLAN.pct,1)}% vs ${fmtN(PLAN.pace,1)}% esperado a hoy`
    :`Plan de ventas <b>${gap} pts por debajo del ritmo</b> — ${fmtN(PLAN.pct,1)}% vs ${fmtN(PLAN.pace,1)}% esperado a hoy`;
  const tagTxt=onTrack?'En ritmo':null;
  return `<div class="kt-ctxbar ${sev}">
    ${ico(onTrack?'trendingUp':'trendingDown',30)}
    <span class="ctx-alert">${alertTxt}</span>
    <span class="ctx-sep">·</span>
    <span class="ctx-metric">Restante <b class="num">${fmtK(PLAN.plan_total-PLAN.fact_acum)}</b></span>
    <span class="ctx-sep">·</span>
    <span class="ctx-metric">Venta hoy <b class="num">${fmtK(VENTA.val)}</b></span>
    ${tagTxt?`<span class="ctx-tag">${tagTxt}</span>`:''}
  </div>`;
}
function board1(){
  const onTrack=PLAN.pct>=PLAN.pace;
  const fill=onTrack?'var(--green)':'var(--amber)';
  const flowCell=(tick,label,val,sub)=>`<div class="b1-flow-cell"><div class="b1-flow-top"><span class="b1-tick ${tick}"></span><span class="b1-flow-label">${label}</span></div><div class="b1-flow-val num">${val}</div><div class="b1-flow-sub num">${sub}</div></div>`;
  const liveItem=(l,v)=>`<div class="b1-live-item"><div class="l">${l}</div><div class="v num">${v}</div></div>`;
  const up=PEDIDOS.delta>=0;
  return `<div class="kt-board top1 active">
    <div class="b1-grid">
      <div class="b1-plan panel">
        <div class="b1-plan-l">
          <div class="b1-plan-eyebrow">${ico('target')} Plan de ventas · Facturación acumulada del mes</div>
          <div class="b1-figs"><span class="b1-curr num">${fmtK(PLAN.fact_acum)}</span><span class="b1-total num">/ ${fmtK(PLAN.plan_total)}</span></div>
          <div class="b1-bar-line">
            <span class="b1-pct num" style="color:${fill}">${fmtN(PLAN.pct,1)}%</span>
            <div class="b1-bar-bg"><div class="b1-bar-fill" style="width:${Math.min(PLAN.pct,100)}%;background:${fill}"></div><div class="b1-bar-pace" style="left:${Math.min(PLAN.pace,100)}%"></div></div>
          </div>
          <div class="b1-plan-foot">
            <span class="pf-item">${ico('calendar',14)} Día hábil <b class="num">${PLAN.dia_habil} de ${PLAN.dias_tot}</b></span>
            <span class="pf-item">${ico('hourglass',14)} <b class="num">${PLAN.dias_rest}</b> días hábiles restantes</span>
            <span class="pf-item">${ico('wallet',14)} Restante: <b class="num">${fmtK(PLAN.plan_total-PLAN.fact_acum)}</b></span>
          </div>
        </div>
        <div class="b1-plan-r"></div>
        <div class="b1-proy">
          <div class="l">Proyección de cierre</div>
          <div class="v num">${fmtK(PLAN.proy)}</div>
          <div class="s num">${fmtN(PLAN.proy_pct,1)}% del plan</div>
          <div class="b1-state ${onTrack?'ok':'warn'}">${ico(onTrack?'trendingUp':'trendingDown',19)} ${onTrack?'En ritmo':'Por debajo del ritmo'}</div>
        </div>
      </div>
      <div class="b1-stat panel"><div class="l">Venta del Día · MSPA</div><div class="v num">${fmtK(VENTA.val)}</div><div class="s num">${fmtN(VENTA.ords)} pedidos facturados</div></div>
      <div class="b1-stat panel">${(()=>{const up=PEDIDOS.delta>=0;return`<div class="l">Pedidos Informados</div><div class="v num">${fmtN(PEDIDOS.v)}</div><span class="b1-delta ${up?'up':'down'}">${ico(up?'arrowUp':'arrowDown',22)} ${fmtN(Math.abs(PEDIDOS.delta),1)}% <span style="color:var(--text-3);font-weight:400">vs. mismo día hábil mes anterior</span></span>`;})()}</div>
      <div class="b1-flow panel">
        ${flowCell('tk-blue','Informado',fmtK(FLOW.informado.val),fmtN(FLOW.informado.v)+' pedidos')}
        ${flowCell('tk-amber','Retenido',fmtK(FLOW.retenido.val),fmtN(FLOW.retenido.v)+' ped · '+fmtN(FLOW.retenido.pct,1)+'%')}
        ${flowCell('tk-red','Anulado',fmtK(FLOW.anulado.val),fmtN(FLOW.anulado.v)+' ped · '+fmtN(FLOW.anulado.pct,1)+'%')}
        ${flowCell('tk-green','Facturado',fmtK(FLOW.facturado.val),fmtN(FLOW.facturado.v)+' pedidos'+(FLOW.informado.v>0?' · '+fmtN(FLOW.facturado.v/FLOW.informado.v*100,1)+'%':''))}
      </div>
      <div class="b1-live">
        <div class="b1-live-head">
          <span class="b1-live-badge"><span class="pdot"></span>En vivo · parcial</span>
          <span class="b1-live-ttl">Así viene hoy · carga en curso</span>
        </div>
        ${HOY.pedidos===0
          ? `<div class="b1-live-empty">Aún sin movimiento hoy · primeros pedidos en breve</div>`
          : `<div class="b1-live-items">
          ${liveItem('Pedidos',fmtN(HOY.pedidos))}
          ${liveItem('Monto informado',fmtK(HOY.monto))}
          ${liveItem('Pedido promedio',fmtK(HOY.ticket))}
          ${liveItem('Ped / Vendedor',fmtN(HOY.ped_vend,1))}
          ${liveItem('Líneas / Pedido',fmtN(HOY.lineas,1))}
        </div>`}
      </div>
    </div>
  </div>`;
}
function board2(){
  const mspaRow=(r)=>{
    const sem=r.venta?'mspa-sem':'mspa-sem'+(r.sev!=='ok'?' '+r.sev:'');
    return `<div class="mspa-row${r.venta?' venta':''}"><span class="mspa-l"><span class="${sem}"></span><span class="mspa-lbl">${r.k}</span></span><span class="mspa-val num">${fmtK(r.val)}<div class="sub num">${fmtN(r.ords)} ped · ${fmtN(r.pos)} lin</div></span></div>`;
  };
  return `<div class="kt-board top1 active">
    <div class="b2-grid">
      <div class="panel b2-chart">
        <div class="kt-eyebrow">${ico('trendingUp')} Tendencia mensual · pedidos &amp; valor por día hábil</div>
        <div class="b2-chart-wrap"><canvas id="kt-chart"></canvas></div>
      </div>
      <div class="panel b2-mspa">
        <div class="kt-eyebrow">${ico('layers')} MSPA · Estado actual</div>
        ${MSPA.map(mspaRow).join('')}
      </div>
      <div class="panel b2-ritmo">
        <div class="kt-eyebrow">${ico('activity')} Ritmo mensual · pedidos vs. mes anterior</div>
        <div class="b2-ritmo-row">
          <div class="b2-ritmo-head">
            <span class="b2-ritmo-fig num">${fmtN(RITMO.curr)} <small>/ ${fmtN(RITMO.last)} pedidos</small></span>
            <span class="b2-ritmo-tag ${RITMO.onTrack?'ok':'warn'} num">${RITMO.onTrack?'+'+fmtN(RITMO.sobre)+' sobre ritmo':fmtN(Math.abs(RITMO.sobre))+' bajo ritmo'}</span>
          </div>
          <div class="b2-ritmo-bar"><div class="b2-ritmo-fill" style="width:${Math.min(RITMO.pct,100)}%"></div><div class="b2-ritmo-pace" style="left:${Math.min(RITMO.pace,100)}%"></div></div>
        </div>
      </div>
    </div>
  </div>`;
}
let chartInst=null, chartJsLoading=false;
function ensureChartJs(cb){
  if(window.Chart){cb();return;}
  if(chartJsLoading)return;
  chartJsLoading=true;
  const s=document.createElement('script');
  s.src='/static/chart.min.js';
  s.onload=()=>{chartJsLoading=false;cb();};
  s.onerror=()=>{chartJsLoading=false;const w=document.getElementById('kt-chart');if(w&&w.closest('.b2-chart-wrap'))w.closest('.b2-chart-wrap').innerHTML='<div style="display:flex;height:100%;align-items:center;justify-content:center;color:var(--text-3);font-size:18px">No se pudo cargar el gráfico</div>';};
  document.head.appendChild(s);
}
function drawChart(){
  const cv=document.getElementById('kt-chart');
  if(!cv||!TREND.length)return;
  if(!window.Chart){ensureChartJs(drawChart);return;}
  if(chartInst){chartInst.destroy();chartInst=null;}
  // Plugin inline: etiquetas sobre las barras (ped) y sobre los puntos (M$)
  const labelPlugin={
    id:'kiosk-labels',
    afterDatasetsDraw(chart){
      const ctx=chart.ctx;
      chart.data.datasets.forEach((ds,di)=>{
        const meta=chart.getDatasetMeta(di);
        if(meta.hidden)return;
        meta.data.forEach((el,i)=>{
          const v=ds.data[i];
          if(v==null)return;
          const raw=TREND[i];
          let lbl;
          if(ds.type==='bar'||ds.yAxisID==='y1'){
            // Promedio pedidos / día hábil sobre la barra
            lbl=Math.round(raw[1]/raw[3]).toLocaleString('es-AR');
          } else {
            // M$ / día hábil sobre el punto — sin decimales ni "M" (se entiende por contexto)
            lbl='$'+Math.round(raw[2]/raw[3]);
          }
          ctx.save();
          ctx.font=ds.type==='bar'?'600 16px system-ui':'700 15px system-ui';
          ctx.fillStyle=ds.type==='bar'?'#64748b':'#cc0000';
          ctx.textAlign='center';
          ctx.textBaseline=ds.type==='bar'?'bottom':'bottom';
          const x=el.x, y=ds.type==='bar'?el.y-3:el.y-8;
          ctx.fillText(lbl,x,y);
          ctx.restore();
        });
      });
    }
  };
  chartInst=new Chart(cv.getContext('2d'),{
    plugins:[labelPlugin],
    data:{labels:TREND.map(t=>t[0]),datasets:[
      {type:'bar',label:'Pedidos / día',data:TREND.map(t=>+(t[1]/t[3]).toFixed(1)),backgroundColor:'rgba(203,213,225,.30)',borderColor:'rgba(203,213,225,.4)',borderWidth:0,yAxisID:'y1',order:2},
      {type:'line',label:'Venta M$ / día',data:TREND.map(t=>+(t[2]/t[3]).toFixed(2)),borderColor:'#cc0000',backgroundColor:'rgba(204,0,0,.06)',borderWidth:3,pointRadius:4,pointBackgroundColor:'#cc0000',tension:.35,yAxisID:'y2',order:1,fill:true},
    ]},
    options:{responsive:true,maintainAspectRatio:false,animation:false,
      layout:{padding:{top:28}},
      plugins:{legend:{labels:{color:'#475569',font:{size:16},boxWidth:16,padding:22,usePointStyle:true}},
        tooltip:{callbacks:{label:(c)=>c.dataset.label+': '+Number(c.parsed.y).toLocaleString('es-AR',{minimumFractionDigits:1,maximumFractionDigits:1})}}},
      scales:{x:{ticks:{color:'#64748b',font:{size:14}},grid:{display:false}},
        y1:{position:'left',ticks:{color:'#64748b',font:{size:13}},grid:{color:'#eef2f7'}},
        y2:{position:'right',ticks:{color:'#cc0000',font:{size:13},callback:v=>v.toFixed(1).replace('.',',')},grid:{drawOnChartArea:false}}}}
  });
}
function tickClock(){
  const now=new Date();
  const t=document.getElementById('kt-time'),d=document.getElementById('kt-date');
  if(t)t.textContent=now.toLocaleTimeString('es-AR',{hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:false});
  if(d)d.textContent=now.toLocaleDateString('es-AR',{weekday:'long',day:'2-digit',month:'long',year:'numeric'});
}
const ROTATE_MS=30000;
const NBOARDS=2;
let board=0;
let paused=false;
let rotStart=Date.now();
const stage=document.getElementById('stage');
function render(){
  stage.innerHTML=topBar()+ctxBar()+(board===0?board1():board2())+
    `<div class="kt-rot"><div class="kt-rot-track"><div class="kt-rot-fill" id="kt-fill"></div></div></div>
     <div class="kt-dots" id="kt-dots">${Array.from({length:NBOARDS},(_,i)=>
        `<span class="kt-pg${board===i?' on':''}" data-go="${i}"></span>`).join('')}</div>`;
  tickClock();
  if(board===1)drawChart();
}
function fitStage(){
  // Estira a todo el viewport (sin barras). En TV 16:9 la distorsion es imperceptible.
  const sx=window.innerWidth/1920, sy=window.innerHeight/1080;
  stage.style.transform='scale('+sx+','+sy+')';
}
function goTo(n){board=(n+NBOARDS)%NBOARDS;rotStart=Date.now();render();syncCtrl();}
function next(){goTo(board+1);}
function prev(){goTo(board-1);}
function togglePause(){paused=!paused;rotStart=Date.now();syncCtrl();}
function toggleFull(){
  if(document.fullscreenElement)document.exitFullscreen();
  else if(document.documentElement.requestFullscreen)document.documentElement.requestFullscreen();
}
let _exitingKiosk=false;
function exitKiosk(){
  _exitingKiosk=true;
  if(document.fullscreenElement)document.exitFullscreen();
  window.location.href='/';
}
// Cuando Chrome sale del fullscreen con Esc (lo intercepta antes que nuestro JS),
// detectamos el cambio y navegamos al dashboard si no fue el botón salir.
document.addEventListener('fullscreenchange',()=>{
  if(!document.fullscreenElement && !_exitingKiosk){
    // Pequeño delay para que el Esc del overlay no dispare esto prematuramente
    setTimeout(()=>{ if(!document.fullscreenElement) window.location.href='/'; }, 200);
  }
});
async function refrescar(){
  try{
    const res=await fetch('/api/data',{cache:'no-store'});
    const d=await res.json();
    mapData(d);
    render();
  }catch(e){ DATOS_AL.mspaOk=false; DATOS_AL.reactorOk=false; render(); }
}
/* ── barra de controles (fuera del stage → no escala, siempre clickeable) ── */
const CTRL_ICONS={
  prev:'<path d="M15 18l-6-6 6-6"/>', next:'<path d="M9 18l6-6-6-6"/>',
  pause:'<rect x="6" y="5" width="4" height="14" rx="1"/><rect x="14" y="5" width="4" height="14" rx="1"/>',
  play:'<path d="M6 4l14 8-14 8V4z"/>',
  full:'<path d="M8 3H5a2 2 0 0 0-2 2v3M16 3h3a2 2 0 0 1 2 2v3M8 21H5a2 2 0 0 1-2-2v-3M16 21h3a2 2 0 0 0 2-2v-3"/>',
  exit:'<path d="M18 6 6 18M6 6l12 12"/>',
};
function ctrlBtn(action,name,title,cls){
  return `<button class="${cls||''}" data-act="${action}" title="${title}"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round">${CTRL_ICONS[name]}</svg></button>`;
}
const ctrl=document.createElement('div');
ctrl.className='kt-ctrl'; ctrl.id='kt-ctrl';
document.body.appendChild(ctrl);
function syncCtrl(){
  ctrl.innerHTML=
    ctrlBtn('prev','prev','Anterior (←)')+
    ctrlBtn('pause',paused?'play':'pause',paused?'Reanudar (espacio)':'Pausar (espacio)')+
    ctrlBtn('next','next','Siguiente (→)')+
    `<span class="pgnum">${board+1} / ${NBOARDS}</span>`+
    `<span class="sep"></span>`+
    ctrlBtn('full','full','Pantalla completa (F)')+
    ctrlBtn('exit','exit','Salir del modo kiosk (Esc)','exit');
}
ctrl.addEventListener('click',(e)=>{
  const b=e.target.closest('button');if(!b)return;
  ({prev,next,pause:togglePause,full:toggleFull,exit:exitKiosk})[b.dataset.act]?.();
});
stage.addEventListener('click',(e)=>{
  const d=e.target.closest('[data-go]');if(d)goTo(+d.dataset.go);
});
/* mostrar controles al mover el mouse, ocultar tras 3s */
let hideT;
const hint=document.createElement('div');
hint.className='kt-hint'; hint.textContent='← → cambiar · espacio pausar · F pantalla · Esc salir';
document.body.appendChild(hint);
function poke(){
  ctrl.classList.add('show');hint.classList.add('show');
  clearTimeout(hideT);
  hideT=setTimeout(()=>{ctrl.classList.remove('show');hint.classList.remove('show');},3000);
}
window.addEventListener('mousemove',poke);
window.addEventListener('touchstart',poke);
document.addEventListener('keydown',(e)=>{
  if(e.key==='ArrowRight')next();
  else if(e.key==='ArrowLeft')prev();
  else if(e.key===' '){e.preventDefault();togglePause();}
  else if(e.key==='f'||e.key==='F')toggleFull();
  else if(e.key==='Escape')exitKiosk();
  poke();
});
fitStage();
window.addEventListener('resize',fitStage);
// Fullscreen: intento silencioso primero; si Chrome lo bloquea, muestra overlay bloqueante
(function(){
  function showOverlay(){
    const ov=document.createElement('div');
    ov.style.cssText='position:fixed;inset:0;z-index:9999;background:rgba(0,0,0,.55);display:flex;align-items:center;justify-content:center;cursor:pointer;backdrop-filter:blur(3px)';
    ov.innerHTML='<div style="background:#fff;border-radius:16px;padding:32px 48px;text-align:center;font-family:system-ui,sans-serif"><div style="font-size:22px;font-weight:700;color:#0f172a;margin-bottom:8px">Click para entrar en pantalla completa</div><div style="font-size:14px;color:#64748b">o presioná F en cualquier momento</div></div>';
    function enterFs(){ov.remove();if(document.documentElement.requestFullscreen)document.documentElement.requestFullscreen().catch(()=>{});fitStage();}
    ov.addEventListener('click',enterFs);
    document.addEventListener('keydown',function h(e){if(e.key==='f'||e.key==='F'||e.key==='Enter'){document.removeEventListener('keydown',h);enterFs();}},true);
    document.body.appendChild(ov);
  }
  if(document.documentElement.requestFullscreen){
    document.documentElement.requestFullscreen().then(()=>fitStage()).catch(()=>showOverlay());
  } else { showOverlay(); }
})();
render();
syncCtrl();
refrescar();
setInterval(tickClock,1000);
setInterval(refrescar,60000);
setInterval(()=>{
  const fill=document.getElementById('kt-fill');
  const pct=paused?0:Math.min((Date.now()-rotStart)/ROTATE_MS*100,100);
  if(fill)fill.style.width=pct+'%';
},100);
setInterval(()=>{
  if(paused){rotStart=Date.now();return;}
  if(Date.now()-rotStart>=ROTATE_MS)next();
},500);
</script>
</body>
</html>
""".replace("@@LOGO@@", LOGO_HTML)


def get_web_html():
    """Genera el HTML estático del dashboard web (para FTP).
    Idéntico al dashboard local pero lee snapshot.json en vez de /api/data.
    En celular redirige automáticamente a la app móvil.
    """
    # ── Dashboard principal ──────────────────────────────────────────────
    dash = HTML_PAGE.replace(
        "fetch(url)",
        "fetch('snapshot.json?_='+Date.now())"
    ).replace(
        "const url='/api/data'+(_customDate?'?date='+_customDate:'');",
        "const url='snapshot.json?_='+Date.now();"
    ).replace(
        # Auto-refresh cada 60s en la versión estática (reemplaza el tick basado en TTL)
        "if(_mspaNext<=0){load();_mspaNext=60;}",
        "if(_mspaNext<=0){load();_mspaNext=60;} // static: refresca snapshot.json"
    ).replace(
        # Ocultar date picker (requiere servidor)
        'id="date-badge-btn"',
        'id="date-badge-btn" style="display:none"'
    ).replace(
        # Kiosk apunta a kiosk.html
        "window.location.href='/kiosk'",
        "window.location.href='kiosk.html'"
    )
    # ── Kiosk ────────────────────────────────────────────────────────────
    kiosk = KIOSK_PAGE.replace(
        "fetch('/api/data',{cache:'no-store'})",
        "fetch('snapshot.json?_='+Date.now(),{cache:'no-store'})"
    ).replace(
        "s.src='/static/chart.min.js';",
        "s.src='https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js';"
    ).replace(
        "window.location.href='/'",
        "window.location.href='index.html'"
    ).replace(
        "window.location.href='/kiosk'",
        "window.location.href='kiosk.html'"
    )
    return dash, kiosk


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
        elif parsed.path in ("/kiosk", "/kiosk.html"):
            self.send_html(KIOSK_PAGE)
        elif parsed.path == "/api/data":
            override = qs.get("date", [None])[0]
            self.send_json(get_cached_data(override_date=override))
        elif parsed.path == "/static/chart.min.js":
            self.send_static("chart.min.js", "application/javascript; charset=utf-8")
        else: self.send_response(404); self.end_headers()

    def send_static(self, name, ctype):
        import os
        base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
        path = os.path.normpath(os.path.join(base, os.path.basename(name)))
        if not path.startswith(base) or not os.path.isfile(path):
            self.send_response(404); self.end_headers(); return
        with open(path, "rb") as f:
            body = f.read()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", len(body))
        self.send_header("Cache-Control", "public, max-age=86400")
        self.end_headers()
        self.wfile.write(body)


def main():
    print("Würth Operations Dashboard")
    print(f"DSN MSPA: {DSN_MSPA}  |  DSN Reactor: {DSN_REACTOR}")
    print(f"MSPA TTL: {MSPA_TTL}s  |  Reactor TTL: {REACTOR_TTL}s")
    print(f"SOLO LECTURA  |  http://localhost:{PORT}  |  Oscuro: ?dark=1")
    print("Ctrl+C para detener\n")
    try:
        from ftp_snapshot import start_snapshot_job
        start_snapshot_job(get_cached_data, get_web_html)
    except Exception as e:
        print(f"[FTP] No se pudo iniciar el job: {e}")
    server=HTTPServer(("0.0.0.0",PORT),Handler)
    try: server.serve_forever()
    except KeyboardInterrupt: print("\nDetenido.")


if __name__=="__main__":
    main()

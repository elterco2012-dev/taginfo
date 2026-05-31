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
def fetch_reactor():
    conn = get_reactor()
    cur  = conn.cursor()

    # Most recent order_date with significant activity
    rows = run(cur, """
        SELECT DATE(order_date) d FROM order_placed
        GROUP BY DATE(order_date) HAVING COUNT(*) >= 50
        ORDER BY d DESC LIMIT 1
    """)
    target     = rows[0][0] if rows else (date.today() - timedelta(days=1))
    target_str = str(target)
    target_dt  = target if isinstance(target, date) else date.fromisoformat(target_str)

    # KPIs
    rows = run(cur, """
        SELECT COUNT(DISTINCT op.id) pedidos,
               COUNT(DISTINCT op.id_user) vendedores,
               SUM(op.total) valor,
               COUNT(od.id) lineas
        FROM order_placed op
        LEFT JOIN order_detail od ON od.id_order_placed = op.id
        WHERE DATE(op.order_date) = ?
    """, (target_str,))
    pedidos, vendedores, valor, lineas = rows[0] if rows else (0, 0, 0, 0)
    pedidos    = pedidos    or 0
    vendedores = vendedores or 0
    valor      = float(valor or 0)
    lineas     = lineas     or 0

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

    trend = []
    for r in trend_rows:
        mes    = r[0]
        peds   = r[1] or 0
        val    = float(r[2] or 0)
        dias   = wd_map.get(mes, 0)
        avg_pd = round(peds / dias, 1) if dias else None
        trend.append({"mes": mes, "pedidos": peds, "valor": val,
                       "dias_hab": dias, "avg_dia": avg_pd})

    # Comparison: same day-of-month, previous month
    try:
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
        comp = {"pedidos": comp_rows[0][0] or 0,
                "vendedores": comp_rows[0][1] or 0,
                "valor": float(comp_rows[0][2] or 0),
                "date": str(prev_dt)} if comp_rows else None
    except Exception:
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
    dias_elapsed  = round(curr_wd * target_dt.day / days_in_month) if curr_wd else target_dt.day
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
        GROUP BY id_user ORDER BY cnt DESC LIMIT 5
    """, (target_str,))
    sellers_ret = [{"id": r[0], "nombre": seller_name(r[0]),
                    "cnt": int(r[1] or 0), "val": float(r[2] or 0)} for r in ret_rows]

    an_rows = run(cur, """
        SELECT id_user, COUNT(*) cnt, SUM(total) val
        FROM order_placed
        WHERE DATE(order_date) = ? AND id_order_status = 14
        GROUP BY id_user ORDER BY cnt DESC LIMIT 5
    """, (target_str,))
    sellers_an = [{"id": r[0], "nombre": seller_name(r[0]),
                   "cnt": int(r[1] or 0), "val": float(r[2] or 0)} for r in an_rows]

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
        "comp":         comp,
        "meta":         meta,
        "sellers_ret":  sellers_ret,
        "sellers_an":   sellers_an,
    }


# ─────────────────────────────────────────────────────────────────────────────
# MSPA fetch
# ─────────────────────────────────────────────────────────────────────────────
def fetch_mspa():
    conn = get_mspa()
    cur  = conn.cursor()

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
          FROM sbas WHERE firma={FIRMA} AND redat=TODAY
    """)

    # ── Top 5 facturación del día — sbas JOIN f040 para nombres reales ────────
    # f040.vertr = vertr1 en sbas; f040.name1 = nombre del vendedor
    fact_rows = run(cur, f"""
        SELECT s.vertr1, f.name1, COUNT(DISTINCT s.auftrag) ped, SUM(s.netwert) val
          FROM sbas s, f040 f
         WHERE s.firma={FIRMA} AND f.firma=s.firma AND f.vertr=s.vertr1
           AND s.redat=TODAY AND s.netwert > 0
         GROUP BY s.vertr1, f.name1 ORDER BY val DESC
    """)
    # Fallback sin join si no hay datos hoy (ej: facturación ya cerró)
    if not fact_rows:
        fact_rows_raw = run(cur, f"""
            SELECT vertr1, COUNT(DISTINCT auftrag) ped, SUM(netwert) val
              FROM sbas WHERE firma={FIRMA} AND redat=TODAY AND netwert > 0
             GROUP BY vertr1 ORDER BY val DESC
        """)
        fact_rows = [(r[0], f"Vend. {r[0]}", r[1], r[2]) for r in fact_rows_raw]

    sellers_fact_top5 = [
        {"vertr": str(r[0] or '').strip(), "nombre": str(r[1] or '').strip(),
         "ped": int(r[2] or 0), "val": float(r[3] or 0)}
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
           AND v.bujahr=YEAR(TODAY) AND v.bumonat=MONTH(TODAY)
           AND s.bujahr=YEAR(TODAY) AND s.bumonat=MONTH(TODAY)
         GROUP BY v.vertr, f.name1, v.planums
         ORDER BY v.planums DESC
    """)
    # Fallback: totales sin desglose por vendedor si el JOIN falla
    if not plan_rows:
        plan_tot = run(cur, f"""
            SELECT SUM(planums) FROM vplan
             WHERE firma={FIRMA} AND bujahr=YEAR(TODAY) AND bumonat=MONTH(TODAY)
        """)
        fact_tot = run(cur, f"""
            SELECT SUM(netwert) FROM sbas
             WHERE firma={FIRMA} AND bujahr=YEAR(TODAY) AND bumonat=MONTH(TODAY)
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

    # Dias hábiles del mes para calcular el ritmo esperado
    dias_hab_mes = run(cur, f"""
        SELECT days FROM work_days
         WHERE year=YEAR(TODAY) AND month=MONTH(TODAY)
    """) if False else []  # work_days está en Reactor (MySQL), no en MSPA

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
    with _lock:
        reactor = _get_cached(REACTOR_TTL, fetch_reactor, "reactor")
        mspa    = _get_cached(MSPA_TTL,    fetch_mspa,    "mspa")

    r_err = reactor.pop("error", None) if isinstance(reactor, dict) else None
    m_err = mspa.pop("error", None)    if isinstance(mspa, dict)    else None
    now   = datetime.now()
    r_age = int((now - _cache_react_ts).total_seconds()) if _cache_react_ts else 0
    m_age = int((now - _cache_mspa_ts).total_seconds())  if _cache_mspa_ts  else 0

    # "Venta del Día" sincronizada con la fecha objetivo de Reactor
    # sbas.redat = target_date (no TODAY, que puede ser diferente al día mostrado)
    target_date = override_date or (reactor.get("target_date") if isinstance(reactor, dict) else None)
    venta_target = {"ords": 0, "pos": 0, "val": 0.0}
    if target_date:
        try:
            y, m_n, d = target_date.split("-")
            conn = get_mspa()
            cur  = conn.cursor()
            rows = run(cur, f"""
                SELECT COUNT(DISTINCT auftrag), COUNT(*), SUM(netwert)
                  FROM sbas WHERE firma={FIRMA}
                  AND redat = MDY({int(m_n)},{int(d)},{int(y)})
            """)
            if rows:
                venta_target = {"ords": rows[0][0] or 0, "pos": rows[0][1] or 0,
                                "val": float(rows[0][2] or 0)}
            conn.close()
        except Exception as e:
            print(f"  venta_target error: {e}")

    # Inyectar venta_target en mspa (reemplaza la venta "de hoy" con la del día objetivo)
    if isinstance(mspa, dict):
        mspa["venta"] = venta_target

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
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
:root{
  --bg:#f0f2f5; --surface:#fff; --surface2:#f8fafc;
  --border:#e2e8f0; --border2:#cbd5e1;
  --text:#0f172a; --text2:#475569; --text3:#94a3b8;
  --blue:#2563eb; --cyan:#0891b2; --green:#059669;
  --amber:#d97706; --red:#dc2626; --orange:#ea580c; --purple:#7c3aed;
  --red-bg:#fef2f2; --amber-bg:#fffbeb; --green-bg:#f0fdf4; --blue-bg:#eff6ff;
  --würth:#cc0000;
}
*{margin:0;padding:0;box-sizing:border-box}
body{background:var(--bg);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',system-ui,sans-serif;font-size:13px;transition:background .3s,color .3s}

/* ── Dark mode ── */
body.dark{
  --bg:#0f172a;--surface:#1e293b;--surface2:#1e293b;--border:#334155;--border2:#475569;
  --text:#f1f5f9;--text2:#cbd5e1;--text3:#64748b;
  --red-bg:#3b0d0d;--amber-bg:#3b2800;--green-bg:#052e16;--blue-bg:#0d2045;
}
body.dark .hdr{background:#1e293b;border-bottom-color:#cc0000}
body.dark .date-badge{background:#3b0d0d;border-color:var(--würth);color:#fca5a5}
body.dark .flow-cell.fl-ret{background:var(--amber-bg)}
body.dark .flow-cell.fl-an{background:var(--red-bg)}
body.dark .flow-cell.fl-fact{background:var(--green-bg)}

/* ── Header ── */
.hdr{background:#fff;border-bottom:2px solid var(--würth);padding:10px 24px;display:flex;align-items:center;justify-content:space-between;box-shadow:0 1px 4px rgba(0,0,0,.06)}
.hdr-left{display:flex;align-items:center;gap:14px}
.logo-text-fallback{display:flex;align-items:center;gap:6px}
.lw{background:var(--würth);color:#fff;font-weight:900;font-size:16px;padding:5px 9px;border-radius:3px;line-height:1}
.ln{font-size:20px;font-weight:900;letter-spacing:3px;color:var(--würth)}
.div-v{width:1px;height:32px;background:var(--border2);margin:0 4px}
.hdr-title{font-size:14px;font-weight:700;color:var(--text)}
.hdr-sub{font-size:10px;color:var(--text3);margin-top:2px}
.hdr-right{display:flex;align-items:center;gap:14px;flex-shrink:0}
.date-badge{background:#fff7f7;border:1.5px solid var(--würth);border-radius:6px;padding:4px 12px;font-size:12px;color:var(--würth);font-weight:700;white-space:nowrap}
.freshness{font-size:10px;color:var(--text3);text-align:right;line-height:2.2}
.freshness b{color:var(--text2);font-size:11px}
.live{display:flex;align-items:center;gap:5px;font-size:11px;color:var(--text3)}
.dot{width:8px;height:8px;border-radius:50%;background:#16a34a;animation:pulse 2s infinite}
@keyframes pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.4;transform:scale(1.3)}}
.mode-btn{cursor:pointer;border:1px solid var(--border2);border-radius:6px;padding:5px 12px;font-size:11px;background:transparent;color:var(--text2);font-weight:600;transition:all .2s}
.mode-btn:hover{background:var(--border);color:var(--text)}

/* ── Layout ── */
.main{padding:16px 24px;display:flex;flex-direction:column;gap:14px}
.sec-lbl{font-size:9px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:var(--text3);margin-bottom:8px}
.err{color:var(--red);font-size:11px;margin-top:4px}

/* ── KPI (4 cards) ── */
.kpi-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}
.kpi{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:16px;box-shadow:0 1px 3px rgba(0,0,0,.05);position:relative;overflow:hidden;transition:border-color .3s,background .3s}
.kpi::after{content:'';position:absolute;top:0;left:0;right:0;height:3px;border-radius:10px 10px 0 0}
.kpi.c-blue::after{background:var(--blue)}.kpi.c-cyan::after{background:var(--cyan)}
.kpi.c-orange::after{background:var(--orange)}.kpi.c-green::after{background:var(--green)}
.kpi.alert-warn{border-color:var(--amber);background:var(--amber-bg)}.kpi.alert-warn::after{background:var(--amber)}
.kpi.alert-danger{border-color:var(--red);background:var(--red-bg)}.kpi.alert-danger::after{background:var(--red)}
.kpi-lbl{font-size:10px;color:var(--text3);margin-bottom:6px;font-weight:500;text-transform:uppercase;letter-spacing:.5px}
.kpi-val{font-size:32px;font-weight:800;line-height:1}
.c-blue .kpi-val{color:var(--blue)}.c-cyan .kpi-val{color:var(--cyan)}
.c-orange .kpi-val{color:var(--orange)}.c-green .kpi-val{color:var(--green)}
.alert-warn .kpi-val{color:var(--amber)!important}.alert-danger .kpi-val{color:var(--red)!important}
.kpi-sub{font-size:10px;color:var(--text3);margin-top:5px}
.delta{display:inline-flex;align-items:center;gap:2px;font-size:10px;font-weight:700;padding:2px 6px;border-radius:20px;margin-top:5px}
.delta.up{background:#dcfce7;color:#15803d}.delta.down{background:#fee2e2;color:#b91c1c}.delta.flat{background:#f1f5f9;color:var(--text3)}

/* ── Flow bar (4 cells) ── */
.flow-bar{display:grid;grid-template-columns:repeat(4,1fr);gap:1px;background:var(--border);border:1px solid var(--border);border-radius:10px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.05)}
.flow-cell{background:var(--surface);padding:14px 16px;display:flex;flex-direction:column;gap:4px;position:relative;transition:background .3s}
.flow-cell::after{content:'›';position:absolute;right:-8px;top:50%;transform:translateY(-50%);color:var(--text3);font-size:18px;z-index:1;pointer-events:none}
.flow-cell:last-child::after{display:none}
.flow-label{font-size:9px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase}
.flow-val{font-size:22px;font-weight:800;line-height:1.1}
.flow-sub{font-size:10px;color:var(--text3)}
.flow-pct{font-size:11px;font-weight:600;margin-top:2px}
.alert-icon{font-size:14px;position:absolute;top:8px;right:10px}
.fl-inf{border-top:3px solid var(--blue)}.fl-inf .flow-label,.fl-inf .flow-pct,.fl-inf .flow-val{color:var(--blue)}
.fl-ret{border-top:3px solid var(--amber);background:var(--amber-bg)}.fl-ret .flow-label,.fl-ret .flow-pct,.fl-ret .flow-val{color:var(--amber)}
.fl-an{border-top:3px solid var(--red);background:var(--red-bg)}.fl-an .flow-label,.fl-an .flow-pct,.fl-an .flow-val{color:var(--red)}
.fl-fact{border-top:3px solid var(--green);background:var(--green-bg)}.fl-fact .flow-label,.fl-fact .flow-pct,.fl-fact .flow-val{color:var(--green)}
.fl-ret.pulse-warn,.fl-an.pulse-warn{animation:bgpulse 3s ease-in-out infinite}
.fl-ret.pulse-danger,.fl-an.pulse-danger{animation:bgpulse 1.8s ease-in-out infinite}
@keyframes bgpulse{0%,100%{opacity:1}50%{opacity:.65}}

/* ── Meta mensual ── */
.meta-card{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:14px 20px;box-shadow:0 1px 3px rgba(0,0,0,.05)}
.meta-row{display:flex;align-items:center;gap:16px;flex-wrap:wrap}
.meta-nums{display:flex;align-items:baseline;gap:6px}
.meta-curr{font-size:22px;font-weight:800;color:var(--blue)}
.meta-sep{color:var(--text3);font-size:13px}
.meta-last{font-size:15px;font-weight:600;color:var(--text3)}
.meta-bar-wrap{flex:1;min-width:200px}
.meta-bar-bg{background:var(--border);border-radius:6px;height:12px;position:relative;overflow:hidden}
.meta-bar-fill{height:100%;border-radius:6px;background:var(--blue);transition:width .8s}
.meta-bar-pace{position:absolute;top:0;bottom:0;width:2px;background:var(--amber);border-radius:2px}
.meta-bar-labels{display:flex;justify-content:space-between;font-size:10px;color:var(--text3);margin-top:3px}
.meta-tags{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.meta-tag{font-size:10px;padding:2px 8px;border-radius:12px;font-weight:600}
.tag-ok{background:#dcfce7;color:#15803d}.tag-warn{background:#fffbeb;color:#d97706}
.tag-danger{background:#fee2e2;color:#dc2626}.tag-neutral{background:#f1f5f9;color:var(--text3)}

/* ── Bottom ── */
.bottom{display:grid;grid-template-columns:1fr 360px;gap:14px}
.card{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:16px;box-shadow:0 1px 3px rgba(0,0,0,.05)}
.chart-wrap{height:240px;position:relative}

/* ── MSPA ── */
.mspa-row{display:flex;align-items:center;justify-content:space-between;padding:9px 0;border-bottom:1px solid var(--border)}
.mspa-row:last-child{border-bottom:none}
.mspa-lbl{font-size:12px;color:var(--text2);flex:1}
.mspa-val{font-size:14px;font-weight:700;color:var(--text);text-align:right;min-width:80px}
.mspa-sub{font-size:10px;color:var(--text3);text-align:right;margin-top:1px}
.mspa-row.hi .mspa-lbl{color:var(--amber)}.mspa-row.hi .mspa-val{color:var(--amber)}
.mspa-row.venta .mspa-lbl{color:var(--green);font-weight:700}.mspa-row.venta .mspa-val{color:var(--green);font-size:17px}

/* ── Plan de ventas bar ── */
.plan-bar-bg{background:var(--border);border-radius:8px;height:18px;position:relative;overflow:hidden;flex:1;min-width:200px}
.plan-bar-fill{height:100%;border-radius:8px;transition:width .8s;display:flex;align-items:center;padding-left:8px;font-size:10px;font-weight:700;color:#fff;white-space:nowrap;overflow:hidden}
.plan-bar-pace{position:absolute;top:0;bottom:0;width:3px;background:var(--amber);border-radius:2px;z-index:2}
.plan-nums{display:flex;align-items:baseline;gap:8px;flex-shrink:0}
.plan-curr{font-size:26px;font-weight:800;color:var(--würth)}
.plan-total{font-size:14px;color:var(--text3);font-weight:600}
.plan-tags{display:flex;gap:8px;flex-wrap:wrap;flex-shrink:0}

/* ── Sellers 3-panel ── */
.sellers-wrap{display:grid;grid-template-columns:1fr 1fr 1fr;gap:14px}
.seller-tbl{width:100%;border-collapse:collapse;font-size:12px}
.seller-tbl th{font-size:9px;font-weight:700;letter-spacing:1px;text-transform:uppercase;color:var(--text3);padding:4px 8px;border-bottom:2px solid var(--border);text-align:left}
.seller-tbl td{padding:7px 8px;border-bottom:1px solid var(--border)}
.seller-tbl tr:last-child td{border-bottom:none}
.seller-tbl tr:hover td{background:var(--surface2)}
.s-rank{font-weight:800;color:var(--text3);width:22px;font-size:14px}
.med-1{color:#f59e0b}.med-2{color:#94a3b8}.med-3{color:#b45309}
.s-name{font-weight:600;color:var(--text)}
.s-sub{font-size:10px;color:var(--text3);font-weight:400}
.s-val{font-weight:700;text-align:right;white-space:nowrap}
.fact-val{color:var(--green)}.ret-val{color:var(--amber)}.an-val{color:var(--red)}
.lbl-fact{color:var(--green)}.lbl-ret{color:var(--amber)}.lbl-an{color:var(--red)}
.s-pill{display:inline-block;padding:1px 6px;border-radius:10px;font-size:10px;font-weight:700}
.pill-ret{background:#fffbeb;color:#d97706}.pill-an{background:#fee2e2;color:#dc2626}
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
    <div class="date-badge" id="date-badge">Cargando...</div>
    <div class="freshness">
      MSPA actualiza en <b id="next-m">—</b><br>
      Reactor actualiza en <b id="next-r">—</b>
    </div>
    <div class="live"><div class="dot"></div>LIVE</div>
    <button class="mode-btn" onclick="toggleDark()" id="mode-btn">🌙 Oscuro</button>
  </div>
</div>

<div class="main">

  <!-- KPIs (4 cards) -->
  <div>
    <div class="sec-lbl" id="sec-reactor">Pedidos Informados · —</div>
    <div id="err-r" class="err"></div>
    <div class="kpi-grid">
      <div class="kpi c-blue" id="kpi-ped">
        <div class="kpi-lbl">Pedidos Informados</div>
        <div class="kpi-val" id="k-ped">—</div>
        <div id="d-ped"></div>
      </div>
      <div class="kpi c-cyan">
        <div class="kpi-lbl">Vendedores Activos</div>
        <div class="kpi-val" id="k-vend">—</div>
        <div id="d-vend"></div>
      </div>
      <div class="kpi c-orange">
        <div class="kpi-lbl">Promedio Líneas / Pedido</div>
        <div class="kpi-val" id="k-avg">—</div>
        <div class="kpi-sub">líneas por pedido</div>
      </div>
      <div class="kpi c-green">
        <div class="kpi-lbl">Venta del Día</div>
        <div class="kpi-val" id="k-venta">—</div>
        <div class="kpi-sub" id="k-venta-sub">&nbsp;</div>
      </div>
    </div>
  </div>

  <!-- Flow bar (4 cells) -->
  <div>
    <div class="sec-lbl">Flujo del Día — Pedidos Informados → Facturación</div>
    <div class="flow-bar">
      <div class="flow-cell fl-inf">
        <div class="flow-label">Informado</div>
        <div class="flow-val" id="fl-inf-val">—</div>
        <div class="flow-sub" id="fl-inf-ped">—</div>
      </div>
      <div class="flow-cell fl-ret" id="fc-ret">
        <div class="flow-label">Retenido</div>
        <div class="flow-val" id="fl-ret-val">—</div>
        <div class="flow-sub" id="fl-ret-ped">—</div>
        <div class="flow-pct" id="fl-ret-pct">—%</div>
        <span class="alert-icon" id="ai-ret"></span>
      </div>
      <div class="flow-cell fl-an" id="fc-an">
        <div class="flow-label">Anulado</div>
        <div class="flow-val" id="fl-an-val">—</div>
        <div class="flow-sub" id="fl-an-ped">—</div>
        <div class="flow-pct" id="fl-an-pct">—%</div>
        <span class="alert-icon" id="ai-an"></span>
      </div>
      <div class="flow-cell fl-fact">
        <div class="flow-label">Facturado hoy</div>
        <div class="flow-val" id="fl-fact-val">—</div>
        <div class="flow-sub" id="fl-fact-ped">—</div>
        <div class="flow-pct" id="fl-fact-pct">—%</div>
      </div>
    </div>
  </div>

  <!-- Plan de ventas -->
  <div class="meta-card">
    <div class="sec-lbl" style="color:var(--würth)">📊 Plan de Ventas — Facturación Acumulada del Mes vs. Plan</div>
    <div class="meta-row" id="plan-row">
      <span style="color:var(--text3);font-size:11px">Cargando...</span>
    </div>
  </div>

  <!-- Meta mensual pedidos -->
  <div class="meta-card">
    <div class="sec-lbl">Ritmo Mensual — Pedidos vs. Mes Anterior</div>
    <div class="meta-row" id="meta-row">
      <span style="color:var(--text3);font-size:11px">Cargando...</span>
    </div>
  </div>

  <!-- Chart + MSPA -->
  <div class="bottom">
    <div class="card">
      <div class="sec-lbl" id="chart-lbl">Tendencia Mensual</div>
      <div class="chart-wrap"><canvas id="chart"></canvas></div>
    </div>
    <div class="card">
      <div class="sec-lbl">MSPA — Estado Actual <small style="font-size:9px;color:var(--text3)">(refresca cada 60s)</small></div>
      <div id="err-m" class="err"></div>
      <div id="mspa-body"></div>
    </div>
  </div>

  <!-- Sellers 3-panel -->
  <div class="sellers-wrap">
    <!-- Top facturación -->
    <div class="card">
      <div class="sec-lbl lbl-fact">🏆 Top 5 Facturación del Día</div>
      <div id="sell-fact-top"></div>
    </div>
    <!-- Más retenidos -->
    <div class="card">
      <div class="sec-lbl lbl-ret">⏸ Top 5 con Más Retenidos</div>
      <div id="sell-ret"></div>
    </div>
    <!-- Más anulados -->
    <div class="card">
      <div class="sec-lbl lbl-an">✕ Top 5 con Más Anulados</div>
      <div id="sell-an"></div>
    </div>
  </div>

</div>

<script>
let chartObj=null;
let _mspaNext=60, _reactNext=600;

const THR_RET_WARN=20,THR_RET_DNG=35;
const THR_AN_WARN=10,THR_AN_DNG=20;

const MSPA_DEF=[
  {k:'backorders',l:'Backorders (Plazos viejos)',   cls:''},
  {k:'bloqueados',l:'Bloqueados por Límite Crédito',cls:''},
  {k:'neg_status',l:'Bloqueados (Status < -1)',      cls:''},
  {k:'futuros',   l:'Pedidos Abiertos (Futuros)',    cls:''},
  {k:'produccion',l:'Producción Abierta',            cls:''},
  {k:'remitos',   l:'Remitos / Facturas Abiertas',   cls:''},
  {k:'venta',     l:'Venta del Día',                 cls:'venta'},
];

function fmtN(n,d=0){return Number(n||0).toLocaleString('es-AR',{minimumFractionDigits:d,maximumFractionDigits:d})}
function fmtK(n){
  n=Number(n)||0;
  if(n>=1e9)return '$'+(n/1e9).toFixed(1)+'B';
  if(n>=1e6)return '$'+(n/1e6).toFixed(1)+'M';
  if(n>=1e3)return '$'+Math.round(n/1e3)+'K';
  return '$'+fmtN(n,0);
}
function pct(a,b){return b?((a/b)*100).toFixed(1)+'%':'—'}
function pctNum(a,b){return b?(a/b)*100:0}

function nextFmt(secs){
  if(secs<=0)return '<span style="color:var(--amber)">actualizando…</span>';
  if(secs<60)return `<span style="color:var(--green)">${secs}s</span>`;
  const m=Math.ceil(secs/60);
  return `<span style="color:var(--green)">${m}min</span>`;
}

function semaforo(v,w,d){return v>=d?'danger':v>=w?'warn':'ok'}

function deltaHtml(curr,prev){
  if(!prev||!curr)return '';
  const p=(curr-prev)/prev*100;
  const arrow=p>0?'▲':'▼';
  return `<span class="delta ${p>0?'up':'down'}">${arrow} ${Math.abs(p).toFixed(1)}%</span>`;
}

function renderChart(trend,hasWd){
  if(!trend||!trend.length)return;
  const labels=trend.map(t=>{
    const[y,m]=t.mes.split('-');
    return ['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic'][+m-1]+'\n'+y.slice(2);
  });
  const barData  = hasWd ? trend.map(t=>t.avg_dia||t.pedidos) : trend.map(t=>t.pedidos);
  const barLabel = hasWd ? 'Ped/día hábil' : 'Pedidos';
  // Normalizar valor por días hábiles — evita que meses cortos (dic, ago) se vean bajos
  const lineData  = hasWd
    ? trend.map(t => t.dias_hab ? +((t.valor/1e6)/t.dias_hab).toFixed(1) : +(t.valor/1e6).toFixed(1))
    : trend.map(t => +(t.valor/1e6).toFixed(1));
  const lineLabel = hasWd ? 'M$/día hábil' : 'Valor (M$)';

  const ctx=document.getElementById('chart').getContext('2d');
  if(chartObj)chartObj.destroy();
  chartObj=new Chart(ctx,{
    data:{labels,datasets:[
      {type:'bar',label:barLabel,data:barData,backgroundColor:'rgba(37,99,235,.7)',borderColor:'#2563eb',borderWidth:1,yAxisID:'y1',order:2},
      {type:'line',label:lineLabel,data:lineData,
       borderColor:'#059669',backgroundColor:'rgba(5,150,105,.07)',borderWidth:2.5,
       pointRadius:4,pointBackgroundColor:'#059669',tension:.35,yAxisID:'y2',order:1,fill:true},
    ]},
    options:{
      responsive:true,maintainAspectRatio:false,
      interaction:{mode:'index',intersect:false},
      plugins:{
        legend:{labels:{color:'#475569',font:{size:11},boxWidth:12,padding:14}},
        tooltip:{backgroundColor:'#fff',titleColor:'#0f172a',bodyColor:'#475569',borderColor:'#e2e8f0',borderWidth:1,
          callbacks:{
            label:ctx=>' '+ctx.dataset.label+': '+fmtN(ctx.parsed.y,1),
            afterBody:items=>{
              const i=items[0].dataIndex,t=trend[i];
              return t.dias_hab?['  Días hábiles: '+t.dias_hab,'  Total pedidos: '+fmtN(t.pedidos,0),'  Valor total: $'+fmtN(t.valor/1e6,1)+'M']:[];
            }
          }
        }
      },
      scales:{
        x:{ticks:{color:'#94a3b8',font:{size:9}},grid:{color:'#f1f5f9'}},
        y1:{type:'linear',position:'left',ticks:{color:'#2563eb',font:{size:9}},grid:{color:'#f1f5f9'},title:{display:true,text:barLabel,color:'#2563eb',font:{size:9}}},
        y2:{type:'linear',position:'right',ticks:{color:'#059669',font:{size:9},callback:v=>v+'M'},grid:{drawOnChartArea:false},title:{display:true,text:lineLabel,color:'#059669',font:{size:9}}}
      }
    }
  });
}

function renderMeta(meta){
  if(!meta){document.getElementById('meta-row').innerHTML='<span style="color:var(--text3);font-size:11px">Sin datos</span>';return;}
  const curr=meta.curr_pedidos,last=meta.last_pedidos;
  const pctProg=last>0?Math.min((curr/last)*100,120):0;
  const pacePos=meta.days_in_month>0?(meta.day_of_month/meta.days_in_month)*100:0;
  const paceTarget=last>0?(pacePos/100)*last:0;
  const onTrack=curr>=paceTarget;
  const fill=Math.min(pctProg,100);
  const wdInfo=meta.curr_wd>0?`${meta.dias_elapsed}/${meta.curr_wd} días hábiles`:`Día ${meta.day_of_month}/${meta.days_in_month}`;
  let tagCls='tag-neutral',tagTxt='Sin referencia';
  if(last>0){
    const diff=curr-paceTarget;
    if(onTrack){tagCls='tag-ok';tagTxt=`+${Math.round(diff)} sobre ritmo`;}
    else{const bh=Math.round(paceTarget-curr);tagCls=bh>last*0.1?'tag-danger':'tag-warn';tagTxt=`${bh} pedidos por debajo del ritmo`;}
  }
  document.getElementById('meta-row').innerHTML=`
    <div style="font-size:11px;color:var(--text2);white-space:nowrap">${meta.curr_month} vs ${meta.last_month||'—'}</div>
    <div class="meta-nums"><span class="meta-curr">${fmtN(curr,0)}</span><span class="meta-sep">de</span><span class="meta-last">${fmtN(last,0)} pedidos</span></div>
    <div class="meta-bar-wrap">
      <div class="meta-bar-bg">
        <div class="meta-bar-fill" style="width:${fill}%;background:${pctProg>100?'var(--green)':onTrack?'var(--blue)':'var(--amber)'}"></div>
        <div class="meta-bar-pace" style="left:${pacePos.toFixed(1)}%"></div>
      </div>
      <div class="meta-bar-labels"><span>${wdInfo}</span><span>${pctProg.toFixed(0)}% del mes anterior</span></div>
    </div>
    <div class="meta-tags">
      <span class="meta-tag ${tagCls}">${tagTxt}</span>
      ${meta.curr_wd>0?`<span class="meta-tag tag-neutral">${meta.curr_wd} días háb/mes</span>`:''}
    </div>`;
}

function renderPlan(pv, diasElapsed, diasHab){
  const el=document.getElementById('plan-row');
  if(!pv||!pv.plan_total){
    el.innerHTML='<span style="color:var(--text3);font-size:11px">Sin datos de plan para este mes</span>';
    return;
  }
  const plan=pv.plan_total, fact=pv.fact_acum, pct=pv.pct_plan||0;
  const fill=Math.min(pct,100);
  // Pace: qué % del plan debería estar cubierto según días hábiles transcurridos
  const pacePos = diasHab>0 ? Math.min((diasElapsed/diasHab)*100, 100) : 0;
  const paceTarget = plan * (pacePos/100);
  const onTrack = fact >= paceTarget;
  const barColor = pct>=100?'var(--green)':onTrack?'var(--würth)':'var(--amber)';

  let tagCls='tag-neutral', tagTxt='Sin referencia';
  if(plan>0){
    if(pct>=100){tagCls='tag-ok';tagTxt='✓ Plan cumplido';}
    else if(onTrack){tagCls='tag-ok';tagTxt=`Al día · ${pct.toFixed(1)}% del plan`;}
    else{
      const falta=paceTarget-fact;
      const pctBehind=((paceTarget-fact)/plan*100).toFixed(1);
      tagCls=Number(pctBehind)>15?'tag-danger':'tag-warn';
      tagTxt=`${pctBehind}% por debajo del ritmo · Falta ${fmtK(falta)} para estar al día`;
    }
  }
  const wdTxt=diasHab>0?`Día hábil ${diasElapsed} de ${diasHab}`:'';

  el.innerHTML=`
    <div style="font-size:11px;color:var(--text2);white-space:nowrap">Facturado acumulado</div>
    <div class="plan-nums">
      <span class="plan-curr">${fmtK(fact)}</span>
      <span class="plan-total">de ${fmtK(plan)}</span>
    </div>
    <div class="plan-bar-bg">
      <div class="plan-bar-fill" style="width:${fill}%;background:${barColor}">
        ${fill>12?pct.toFixed(1)+'%':''}
      </div>
      <div class="plan-bar-pace" style="left:${pacePos.toFixed(1)}%" title="Ritmo esperado: ${fmtK(paceTarget)}"></div>
    </div>
    <div class="plan-tags">
      <span class="meta-tag ${tagCls}">${tagTxt}</span>
      ${wdTxt?`<span class="meta-tag tag-neutral">${wdTxt}</span>`:''}
    </div>`;
}

function buildSellerTable(sellers, valClass, valLabel, valueKey, cntLabel){
  if(!sellers||!sellers.length)
    return '<p style="color:var(--text3);font-size:11px;padding:8px 0">Sin movimiento hoy</p>';
  const medals=['🥇','🥈','🥉','4°','5°'];
  let h=`<table class="seller-tbl"><tr><th></th><th>Vendedor</th><th style="text-align:right">${valLabel}</th></tr>`;
  sellers.forEach((s,i)=>{
    const nameHtml=s.nombre.includes('(')?
      s.nombre.replace(/^(.+?)(\(.+\))(.*)$/,'<span>$1</span><span class="s-sub">$2$3</span>'):
      `<span>${s.nombre}</span>`;
    const valHtml = valueKey==='val'
      ? `<span class="${valClass}">${fmtK(s.val||s.val_valido||0)}</span>`
      : `<span class="s-pill ${valClass==='ret-val'?'pill-ret':'pill-an'}">${s.cnt} pedidos</span>`;
    h+=`<tr><td class="s-rank ${i<3?'med-'+(i+1):''}">${medals[i]}</td><td class="s-name">${nameHtml}</td><td class="s-val">${valHtml}</td></tr>`;
  });
  return h+'</table>';
}

function render(data){
  document.getElementById('err-r').textContent=data.reactor_error?'⚠ Reactor: '+data.reactor_error:'';
  document.getElementById('err-m').textContent=data.mspa_error?'⚠ MSPA: '+data.mspa_error:'';

  _mspaNext  = data.mspa_next  || 60;
  _reactNext = data.reactor_next || 600;

  const r=data.reactor||{};
  const m=data.mspa||{};
  const dp=r.target_date_display||'—';
  document.getElementById('date-badge').textContent=(_customDate?'📅 ':'')+'Pedidos del '+dp;
  document.getElementById('sec-reactor').textContent='Pedidos Informados · '+dp+(_customDate?' (fecha manual)':'');

  // KPIs
  const c=r.comp||null;
  document.getElementById('k-ped').textContent=fmtN(r.pedidos,0);
  document.getElementById('d-ped').innerHTML=c?deltaHtml(r.pedidos,c.pedidos):'';
  document.getElementById('k-vend').textContent=fmtN(r.vendedores,0);
  document.getElementById('d-vend').innerHTML=c?deltaHtml(r.vendedores,c.vendedores):'';

  // avg_lineas needs lineas/pedidos — compute from by_status or use avg_lineas if available
  const bs=r.by_status||{};
  document.getElementById('k-avg').textContent=r.avg_lineas||'—';

  // Venta del día from MSPA
  const venta=m.venta||{ords:0,val:0};
  document.getElementById('k-venta').textContent=fmtK(venta.val);
  document.getElementById('k-venta-sub').textContent=fmtN(venta.ords,0)+' pedidos facturados';

  // Semáforo on pedidos card (if high anulados %)
  const total=r.pedidos||0;
  const an=(bs[14]?.cnt||0), ret=(bs[15]?.cnt||0);
  const anPct=pctNum(an,total), retPct=pctNum(ret,total);
  const kpiPed=document.getElementById('kpi-ped');
  kpiPed.classList.remove('alert-warn','alert-danger');
  const sAn=semaforo(anPct,THR_AN_WARN,THR_AN_DNG);
  if(sAn==='danger')kpiPed.classList.add('alert-danger');
  else if(sAn==='warn')kpiPed.classList.add('alert-warn');

  // Flow bar (4 cells)
  const fact_cnt=(bs[13]?.cnt||0)+(bs[18]?.cnt||0);
  const fact_val=venta.val;
  document.getElementById('fl-inf-val').textContent=fmtK(r.valor||0);
  document.getElementById('fl-inf-ped').textContent=fmtN(total,0)+' pedidos';

  document.getElementById('fl-ret-val').textContent=fmtK(bs[15]?.val||0);
  document.getElementById('fl-ret-ped').textContent=fmtN(ret,0)+' pedidos';
  document.getElementById('fl-ret-pct').textContent=pct(ret,total);

  document.getElementById('fl-an-val').textContent=fmtK(bs[14]?.val||0);
  document.getElementById('fl-an-ped').textContent=fmtN(an,0)+' pedidos';
  document.getElementById('fl-an-pct').textContent=pct(an,total);

  document.getElementById('fl-fact-val').textContent=fmtK(fact_val);
  document.getElementById('fl-fact-ped').textContent=fmtN(fact_cnt,0)+' pedidos';
  document.getElementById('fl-fact-pct').textContent=pct(fact_cnt,total);

  // Semáforo flow
  const fcRet=document.getElementById('fc-ret'),fcAn=document.getElementById('fc-an');
  const aiRet=document.getElementById('ai-ret'),aiAn=document.getElementById('ai-an');
  fcRet.classList.remove('pulse-warn','pulse-danger');fcAn.classList.remove('pulse-warn','pulse-danger');
  const sRet=semaforo(retPct,THR_RET_WARN,THR_RET_DNG);
  if(sRet==='warn'){fcRet.classList.add('pulse-warn');aiRet.textContent='⚠️';}
  else if(sRet==='danger'){fcRet.classList.add('pulse-danger');aiRet.textContent='🔴';}
  else aiRet.textContent='';
  if(sAn==='warn'){fcAn.classList.add('pulse-warn');aiAn.textContent='⚠️';}
  else if(sAn==='danger'){fcAn.classList.add('pulse-danger');aiAn.textContent='🔴';}
  else aiAn.textContent='';

  // Chart
  if(r.trend&&r.trend.length){
    document.getElementById('chart-lbl').textContent=r.has_workdays
      ?'Tendencia Mensual — Promedio Pedidos por Día Hábil (12 meses)'
      :'Tendencia Mensual — Pedidos Informados (12 meses)';
    renderChart(r.trend,r.has_workdays);
  }

  // Meta
  // Plan de ventas (datos de MSPA + dias hábiles de Reactor)
  const pv=m.plan_ventas||null;
  const diasEl=r.meta?.dias_elapsed||0;
  const diasHab=r.meta?.curr_wd||0;
  renderPlan(pv, diasEl, diasHab);

  renderMeta(r.meta||null);

  // Sellers
  const sf=m.sellers_fact_top||[];
  document.getElementById('sell-fact-top').innerHTML=buildSellerTable(m.sellers_fact_top||[],'fact-val','Facturado hoy','val','pedidos');
  document.getElementById('sell-ret').innerHTML=buildSellerTable(r.sellers_ret||[],'ret-val','Retenidos','cnt','pedidos');
  document.getElementById('sell-an').innerHTML=buildSellerTable(r.sellers_an||[],'an-val','Anulados','cnt','pedidos');

  // MSPA
  let mhtml='';
  MSPA_DEF.forEach(row=>{
    const d=m[row.k]||{ords:0,pos:0,val:0};
    const hi=d.val>0&&row.cls!=='venta'?' hi':'';
    mhtml+=`<div class="mspa-row ${row.cls}${hi}">
      <div class="mspa-lbl">${row.l}</div>
      <div><div class="mspa-val">$${fmtK(d.val).replace('$','')}</div>
      <div class="mspa-sub">${d.ords} pedidos · ${d.pos} líneas</div></div>
    </div>`;
  });
  document.getElementById('mspa-body').innerHTML=mhtml;
}

const _customDate=new URLSearchParams(location.search).get('date')||'';
async function load(){
  const url='/api/data'+(_customDate?'?date='+_customDate:'');
  try{const res=await fetch(url);const d=await res.json();render(d);}
  catch(e){console.error(e);}
}

function tick(){
  _mspaNext  = Math.max(0,_mspaNext-1);
  _reactNext = Math.max(0,_reactNext-1);
  document.getElementById('next-m').innerHTML=nextFmt(_mspaNext);
  document.getElementById('next-r').innerHTML=nextFmt(_reactNext);
  if(_mspaNext<=0){load();_mspaNext=60;}
}

// Dark mode
function toggleDark(){
  const dark=document.body.classList.toggle('dark');
  document.getElementById('mode-btn').textContent=dark?'☀ Claro':'🌙 Oscuro';
  localStorage.setItem('wuerth-dark',dark?'1':'0');
}
if(localStorage.getItem('wuerth-dark')==='1'||new URLSearchParams(location.search).get('dark')==='1'){
  document.body.classList.add('dark');
  document.getElementById('mode-btn').textContent='☀ Claro';
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

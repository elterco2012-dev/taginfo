"""
Würth Operations Dashboard - Reactor (MySQL) + MSPA (Informix)
SOLO LECTURA — no INSERT/UPDATE/DELETE/DDL.

Uso: python.exe dashboard.py
Abrir: http://localhost:8765  |  TV: http://localhost:8765?tv=1
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
                 "wurth_logo.jpg", "logo.jpg",
                 "wurth_logo.svg", "logo.svg"]:
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
# REACTOR fetch  (TTL 10 min)
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
    target    = rows[0][0] if rows else (date.today() - timedelta(days=1))
    target_str = str(target)
    target_dt  = target if isinstance(target, date) else date.fromisoformat(target_str)

    # KPIs — order_placed only
    rows = run(cur, """
        SELECT COUNT(DISTINCT id) pedidos,
               COUNT(DISTINCT id_user) vendedores,
               SUM(total) valor
        FROM order_placed WHERE DATE(order_date) = ?
    """, (target_str,))
    pedidos, vendedores, valor = rows[0] if rows else (0, 0, 0)
    pedidos    = pedidos    or 0
    vendedores = vendedores or 0
    valor      = float(valor or 0)

    # Line count
    rows_lin = run(cur, """
        SELECT COUNT(od.id) FROM order_placed op
        JOIN order_detail od ON od.id_order_placed = op.id
        WHERE DATE(op.order_date) = ?
    """, (target_str,))
    lineas = (rows_lin[0][0] or 0) if rows_lin else 0

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

    # Monthly trend — 12 months, with work_days normalization
    trend_rows = run(cur, """
        SELECT DATE_FORMAT(order_date, '%Y-%m') mes,
               COUNT(DISTINCT id) pedidos,
               SUM(total) valor
        FROM order_placed
        WHERE order_date >= DATE_SUB(CURDATE(), INTERVAL 12 MONTH)
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

    # ── Comparison: same day-of-month, previous month ──────────────────────
    try:
        if target_dt.month == 1:
            prev_dt = target_dt.replace(year=target_dt.year - 1, month=12)
        else:
            last_day_prev = calendar.monthrange(target_dt.year, target_dt.month - 1)[1]
            prev_dt = target_dt.replace(month=target_dt.month - 1,
                                        day=min(target_dt.day, last_day_prev))
        comp_rows = run(cur, """
            SELECT COUNT(DISTINCT id) pedidos,
                   COUNT(DISTINCT id_user) vendedores,
                   SUM(total) valor
            FROM order_placed WHERE DATE(order_date) = ?
        """, (str(prev_dt),))
        comp = {"pedidos": comp_rows[0][0] or 0,
                "vendedores": comp_rows[0][1] or 0,
                "valor": float(comp_rows[0][2] or 0),
                "date": str(prev_dt)} if comp_rows else None
    except Exception:
        comp = None

    # ── Monthly meta (barra de progreso vs mes anterior) ───────────────────
    curr_month = target_dt.strftime("%Y-%m")
    last_month = ((target_dt.replace(day=1) - timedelta(days=1))).strftime("%Y-%m")
    meta_rows  = run(cur, """
        SELECT DATE_FORMAT(order_date, '%Y-%m') mes,
               COUNT(DISTINCT id) pedidos,
               SUM(total) valor
        FROM order_placed
        WHERE DATE_FORMAT(order_date, '%Y-%m') IN (?, ?)
        GROUP BY DATE_FORMAT(order_date, '%Y-%m')
    """, (curr_month, last_month))
    meta_by = {r[0]: {"pedidos": r[1] or 0, "valor": float(r[2] or 0)} for r in meta_rows}

    days_in_month  = calendar.monthrange(target_dt.year, target_dt.month)[1]
    curr_wd        = wd_map.get(curr_month, 0)
    last_wd        = wd_map.get(last_month, 0)
    dias_elapsed   = round(curr_wd * target_dt.day / days_in_month) if curr_wd else target_dt.day
    meta = {
        "curr_month":   curr_month,
        "last_month":   last_month,
        "curr_pedidos": meta_by.get(curr_month, {}).get("pedidos", 0),
        "curr_valor":   meta_by.get(curr_month, {}).get("valor", 0),
        "last_pedidos": meta_by.get(last_month, {}).get("pedidos", 0),
        "last_valor":   meta_by.get(last_month, {}).get("valor", 0),
        "curr_wd":      curr_wd,
        "last_wd":      last_wd,
        "dias_elapsed": dias_elapsed,
        "day_of_month": target_dt.day,
        "days_in_month": days_in_month,
    }

    # ── Sellers ranking ─────────────────────────────────────────────────────
    # Only count valid orders (not anulados = status 14).
    # Sellers who pass fake orders and cancel them drop in the "validos" ranking.
    seller_rows = run(cur, """
        SELECT id_user,
               COUNT(*) total,
               SUM(CASE WHEN id_order_status = 14 THEN 1 ELSE 0 END) anulados,
               COUNT(*) - SUM(CASE WHEN id_order_status = 14 THEN 1 ELSE 0 END) validos,
               SUM(CASE WHEN id_order_status != 14 THEN total ELSE 0 END) valor_valido
        FROM order_placed
        WHERE DATE(order_date) = ?
        GROUP BY id_user
    """, (target_str,))

    # Try to get user names — attempt several column name patterns
    user_names = {}
    for name_col in ["name", "username", "full_name", "first_name", "apellido", "email"]:
        nr = run(cur, f"SELECT id, {name_col} FROM users LIMIT 1")
        if nr:
            all_u = run(cur, f"SELECT id, {name_col} FROM users")
            user_names = {r[0]: str(r[1]) for r in (all_u or []) if r[1]}
            break

    sellers = []
    for r in seller_rows:
        uid     = r[0]
        total   = int(r[1] or 0)
        anulados= int(r[2] or 0)
        validos = int(r[3] or 0)
        v_val   = float(r[4] or 0)
        sellers.append({
            "id":          uid,
            "nombre":      user_names.get(uid, f"Vend. {uid}"),
            "total":       total,
            "anulados":    anulados,
            "validos":     validos,
            "valor_valido": v_val,
            "pct_anulados": round(anulados / total * 100) if total else 0,
        })

    sellers_sorted = sorted(sellers, key=lambda x: (-x["validos"], x["pct_anulados"]))
    sellers_top5   = sellers_sorted[:5]
    sellers_bot5   = sorted(sellers, key=lambda x: (x["validos"], -x["pct_anulados"]))[:5]

    conn.close()

    pending_total = sum(
        by_status.get(s, {}).get("cnt", 0) for s in [10, 11, 12, 17]
    )

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
        "pending":      pending_total,
        "trend":        trend,
        "has_workdays": bool(wd_map),
        "comp":         comp,
        "meta":         meta,
        "sellers_top5": sellers_top5,
        "sellers_bot5": sellers_bot5,
    }


# ─────────────────────────────────────────────────────────────────────────────
# MSPA fetch  (TTL 60s)
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

    conn.close()
    return {
        "backorders": backorders, "bloqueados": bloqueados,
        "neg_status": neg_status, "futuros":    futuros,
        "produccion": produccion, "remitos":    remitos,
        "venta":      venta,
    }


# ─────────────────────────────────────────────────────────────────────────────
def _get_cached(key_data, key_ts, ttl, fetcher, name):
    global _cache_mspa, _cache_mspa_ts, _cache_reactor, _cache_react_ts
    now = datetime.now()
    ts  = _cache_mspa_ts if name == "mspa" else _cache_react_ts
    data= _cache_mspa    if name == "mspa" else _cache_reactor
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


def get_cached_data():
    with _lock:
        reactor = _get_cached(None, None, REACTOR_TTL, fetch_reactor, "reactor")
        mspa    = _get_cached(None, None, MSPA_TTL,    fetch_mspa,    "mspa")

    r_err = reactor.pop("error", None) if isinstance(reactor, dict) else None
    m_err = mspa.pop("error", None)    if isinstance(mspa, dict)    else None

    now = datetime.now()
    return {
        "timestamp":     now.strftime("%d/%m/%Y %H:%M:%S"),
        "reactor":       reactor or {},
        "mspa":          mspa    or {},
        "reactor_error": r_err,
        "mspa_error":    m_err,
        "reactor_age":   int((now - _cache_react_ts).total_seconds()) if _cache_react_ts else 0,
        "mspa_age":      int((now - _cache_mspa_ts).total_seconds())  if _cache_mspa_ts  else 0,
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

/* ── TV Mode ──────────────────────────────────────────────────────────────── */
body.tv{--bg:#0f172a;--surface:#1e293b;--surface2:#1e293b;--border:#334155;--border2:#475569;--text:#f1f5f9;--text2:#cbd5e1;--text3:#64748b;font-size:15px}
body.tv .hdr{background:#1e293b;border-bottom-color:#cc0000}
body.tv .kpi{background:#1e293b}
body.tv .card{background:#1e293b}
body.tv .flow-cell{background:#1e293b}
body.tv .flow-cell.fl-ret{background:#422006}
body.tv .flow-cell.fl-an{background:#450a0a}
body.tv .flow-cell.fl-fact{background:#052e16}
body.tv .kpi-val{font-size:38px}
body.tv .flow-val{font-size:26px}
body.tv .mspa-val{font-size:16px}
body.tv .date-badge{background:#450a0a;border-color:var(--würth);color:#fca5a5}
.tv-btn{cursor:pointer;border:1px solid var(--border2);border-radius:6px;padding:4px 10px;font-size:11px;background:transparent;color:var(--text3);margin-left:8px}
.tv-btn:hover{background:var(--border)}

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
.freshness{font-size:10px;color:var(--text3);text-align:right;line-height:2}
.freshness b{color:var(--text2);font-size:11px}
.live{display:flex;align-items:center;gap:5px;font-size:11px;color:var(--text3)}
.dot{width:8px;height:8px;border-radius:50%;background:#16a34a;animation:pulse 2s infinite}
@keyframes pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.4;transform:scale(1.3)}}

/* ── Layout ── */
.main{padding:16px 24px;display:flex;flex-direction:column;gap:14px}
.sec-lbl{font-size:9px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:var(--text3);margin-bottom:8px}
.err{color:var(--red);font-size:11px;margin-top:4px}

/* ── KPI ── */
.kpi-grid{display:grid;grid-template-columns:repeat(5,1fr);gap:10px}
.kpi{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:16px;box-shadow:0 1px 3px rgba(0,0,0,.05);position:relative;overflow:hidden;transition:border-color .3s,background .3s}
.kpi::after{content:'';position:absolute;top:0;left:0;right:0;height:3px;border-radius:10px 10px 0 0}
.kpi.c-blue::after{background:var(--blue)}.kpi.c-cyan::after{background:var(--cyan)}
.kpi.c-purple::after{background:var(--purple)}.kpi.c-orange::after{background:var(--orange)}
.kpi.c-green::after{background:var(--green)}
/* Semáforo overrides */
.kpi.alert-warn{border-color:var(--amber);background:var(--amber-bg)}.kpi.alert-warn::after{background:var(--amber)}
.kpi.alert-danger{border-color:var(--red);background:var(--red-bg)}.kpi.alert-danger::after{background:var(--red)}

.kpi-lbl{font-size:10px;color:var(--text3);margin-bottom:6px;font-weight:500;text-transform:uppercase;letter-spacing:.5px}
.kpi-val{font-size:32px;font-weight:800;line-height:1}
.c-blue .kpi-val{color:var(--blue)}.c-cyan .kpi-val{color:var(--cyan)}
.c-purple .kpi-val{color:var(--purple)}.c-orange .kpi-val{color:var(--orange)}
.c-green .kpi-val{color:var(--green)}
.alert-warn .kpi-val{color:var(--amber)!important}.alert-danger .kpi-val{color:var(--red)!important}
.kpi-sub{font-size:10px;color:var(--text3);margin-top:5px}
/* Delta badge */
.delta{display:inline-flex;align-items:center;gap:2px;font-size:10px;font-weight:700;padding:2px 6px;border-radius:20px;margin-top:5px}
.delta.up{background:#dcfce7;color:#15803d}.delta.down{background:#fee2e2;color:#b91c1c}.delta.flat{background:#f1f5f9;color:var(--text3)}
.kpi-sub-row{display:flex;align-items:center;gap:6px;margin-top:5px;flex-wrap:wrap}

/* ── Flow bar ── */
.flow-bar{display:grid;grid-template-columns:repeat(5,1fr);gap:1px;background:var(--border);border:1px solid var(--border);border-radius:10px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.05)}
.flow-cell{background:var(--surface);padding:14px 16px;display:flex;flex-direction:column;gap:4px;position:relative;transition:background .3s}
.flow-cell::after{content:'›';position:absolute;right:-8px;top:50%;transform:translateY(-50%);color:var(--text3);font-size:18px;z-index:1;pointer-events:none}
.flow-cell:last-child::after{display:none}
.flow-label{font-size:9px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase}
.flow-val{font-size:20px;font-weight:800;line-height:1.1}
.flow-sub{font-size:10px;color:var(--text3)}
.flow-pct{font-size:11px;font-weight:600;margin-top:2px}
.alert-icon{font-size:14px;position:absolute;top:8px;right:10px}
.fl-inf{border-top:3px solid var(--blue)}
.fl-inf .flow-label,.fl-inf .flow-pct{color:var(--blue)}.fl-inf .flow-val{color:var(--blue)}
.fl-ret{border-top:3px solid var(--amber);background:var(--amber-bg)}
.fl-ret .flow-label,.fl-ret .flow-pct{color:var(--amber)}.fl-ret .flow-val{color:var(--amber)}
.fl-an{border-top:3px solid var(--red);background:var(--red-bg)}
.fl-an .flow-label,.fl-an .flow-pct{color:var(--red)}.fl-an .flow-val{color:var(--red)}
.fl-back{border-top:3px solid var(--orange)}
.fl-back .flow-label,.fl-back .flow-pct{color:var(--orange)}.fl-back .flow-val{color:var(--orange)}
.fl-fact{border-top:3px solid var(--green);background:var(--green-bg)}
.fl-fact .flow-label,.fl-fact .flow-pct{color:var(--green)}.fl-fact .flow-val{color:var(--green)}
/* Semáforo pulse on flow cells */
.fl-ret.pulse-warn,.fl-an.pulse-warn{animation:bgpulse-warn 3s ease-in-out infinite}
.fl-ret.pulse-danger,.fl-an.pulse-danger{animation:bgpulse-danger 2s ease-in-out infinite}
@keyframes bgpulse-warn{0%,100%{opacity:1}50%{opacity:.75}}
@keyframes bgpulse-danger{0%,100%{opacity:1}50%{opacity:.6}}

/* pending strip */
.pending-strip{background:var(--blue-bg);border:1px solid #bfdbfe;border-radius:8px;padding:8px 16px;display:flex;align-items:center;gap:10px;margin-top:8px;font-size:12px;color:var(--blue)}
.pending-strip b{font-size:16px;font-weight:800}
.pending-strip span{color:var(--text3)}

/* ── Meta mensual ── */
.meta-card{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:14px 20px;box-shadow:0 1px 3px rgba(0,0,0,.05)}
.meta-row{display:flex;align-items:center;gap:16px;flex-wrap:wrap}
.meta-label{font-size:11px;color:var(--text2);white-space:nowrap}
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
.tag-ok{background:#dcfce7;color:#15803d}.tag-warn{background:#fffbeb;color:#d97706}.tag-danger{background:#fee2e2;color:#dc2626}
.tag-neutral{background:#f1f5f9;color:var(--text3)}

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

/* ── Sellers ranking ── */
.sellers-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.seller-table{width:100%;border-collapse:collapse;font-size:12px}
.seller-table th{font-size:9px;font-weight:700;letter-spacing:1px;text-transform:uppercase;color:var(--text3);padding:4px 8px;border-bottom:2px solid var(--border);text-align:left}
.seller-table td{padding:7px 8px;border-bottom:1px solid var(--border)}
.seller-table tr:last-child td{border-bottom:none}
.seller-table tr:hover td{background:var(--surface2)}
.s-rank{font-weight:800;color:var(--text3);width:22px}
.s-medal-1{color:#f59e0b}.s-medal-2{color:#94a3b8}.s-medal-3{color:#b45309}
.s-name{font-weight:600;color:var(--text);max-width:130px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.s-val{font-weight:700;text-align:right}
.s-pill{display:inline-block;padding:1px 6px;border-radius:10px;font-size:10px;font-weight:700}
.pill-ok{background:#dcfce7;color:#15803d}
.pill-warn{background:#fffbeb;color:#d97706}
.pill-danger{background:#fee2e2;color:#dc2626}
.seller-top .s-val{color:var(--green)}
.seller-bot .s-val{color:var(--red)}
.top-lbl{color:var(--green)}.bot-lbl{color:var(--red)}
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
      MSPA <b id="fresh-m">—</b><br>
      Reactor <b id="fresh-r">—</b>
    </div>
    <div class="live"><div class="dot"></div>LIVE</div>
    <button class="tv-btn" onclick="toggleTV()" id="tv-btn">📺 TV</button>
  </div>
</div>

<div class="main">

  <!-- KPIs -->
  <div>
    <div class="sec-lbl" id="sec-reactor">Pedidos Informados · —</div>
    <div id="err-r" class="err"></div>
    <div class="kpi-grid">
      <div class="kpi c-blue" id="kpi-ped">
        <div class="kpi-lbl">Pedidos Informados</div>
        <div class="kpi-val" id="k-ped">—</div>
        <div class="kpi-sub-row">
          <span class="kpi-sub" id="k-ped-sub">&nbsp;</span>
          <span class="delta flat" id="d-ped"></span>
        </div>
      </div>
      <div class="kpi c-cyan" id="kpi-vend">
        <div class="kpi-lbl">Vendedores Activos</div>
        <div class="kpi-val" id="k-vend">—</div>
        <div class="kpi-sub-row">
          <span class="kpi-sub">&nbsp;</span>
          <span class="delta flat" id="d-vend"></span>
        </div>
      </div>
      <div class="kpi c-purple" id="kpi-lin">
        <div class="kpi-lbl">Total Líneas</div>
        <div class="kpi-val" id="k-lin">—</div>
        <div class="kpi-sub-row">
          <span class="kpi-sub" id="k-lin-sub">&nbsp;</span>
          <span class="delta flat" id="d-lin"></span>
        </div>
      </div>
      <div class="kpi c-orange" id="kpi-avg">
        <div class="kpi-lbl">Promedio Líneas / Pedido</div>
        <div class="kpi-val" id="k-avg">—</div>
        <div class="kpi-sub">artículos por pedido</div>
      </div>
      <div class="kpi c-green" id="kpi-apv">
        <div class="kpi-lbl">Promedio Ped. / Vendedor</div>
        <div class="kpi-val" id="k-apv">—</div>
        <div class="kpi-sub" id="k-apv-sub">pedidos por vendedor</div>
      </div>
    </div>
  </div>

  <!-- Flow bar -->
  <div>
    <div class="sec-lbl">Flujo de Facturación del Día</div>
    <div class="flow-bar">
      <div class="flow-cell fl-inf">
        <div class="flow-label">Informado</div>
        <div class="flow-val" id="fl-inf-val">—</div>
        <div class="flow-sub" id="fl-inf-ped">— pedidos · 100%</div>
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
      <div class="flow-cell fl-back">
        <div class="flow-label">Backorder</div>
        <div class="flow-val" id="fl-back-val">—</div>
        <div class="flow-sub" id="fl-back-ped">—</div>
        <div class="flow-pct" id="fl-back-pct">—%</div>
      </div>
      <div class="flow-cell fl-fact">
        <div class="flow-label">Facturado hoy</div>
        <div class="flow-val" id="fl-fact-val">—</div>
        <div class="flow-sub" id="fl-fact-ped">—</div>
        <div class="flow-pct" id="fl-fact-pct">—%</div>
      </div>
    </div>
    <div class="pending-strip" id="pending-strip" style="display:none">
      <div>Pendiente de facturar: <b id="pending-cnt">0</b> pedidos</div>
      <span id="pending-detail"></span>
    </div>
  </div>

  <!-- Meta mensual -->
  <div class="meta-card">
    <div class="sec-lbl">Meta Mensual — Ritmo vs. Mes Anterior</div>
    <div class="meta-row" id="meta-row">
      <div class="meta-label" id="meta-label">Cargando...</div>
    </div>
  </div>

  <!-- Chart + MSPA -->
  <div class="bottom">
    <div class="card">
      <div class="sec-lbl" id="chart-lbl">Tendencia Mensual — Pedidos por Día Hábil (últimos 12 meses)</div>
      <div class="chart-wrap"><canvas id="chart"></canvas></div>
    </div>
    <div class="card">
      <div class="sec-lbl">MSPA — Estado Actual <small style="font-size:9px;color:var(--text3)">(refresca cada 60s)</small></div>
      <div id="err-m" class="err"></div>
      <div id="mspa-body"></div>
    </div>
  </div>

  <!-- Sellers ranking -->
  <div class="sellers-grid">
    <div class="card">
      <div class="sec-lbl top-lbl">🏆 Top 5 Vendedores del Día — Pedidos Válidos</div>
      <div id="sellers-top"></div>
    </div>
    <div class="card">
      <div class="sec-lbl bot-lbl">⚠ Menor Rendimiento — Pedidos Válidos</div>
      <div id="sellers-bot"></div>
    </div>
  </div>

</div>

<script>
let chartObj=null;
let _mspaAge=0, _reactAge=0;

// Semáforo thresholds (% del total informado)
const THR_RET_WARN=20, THR_RET_DNG=35;   // retenidos
const THR_AN_WARN=10,  THR_AN_DNG=20;    // anulados

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
  if(n>=1e9) return '$'+(n/1e9).toFixed(1)+'B';
  if(n>=1e6) return '$'+(n/1e6).toFixed(1)+'M';
  if(n>=1e3) return '$'+Math.round(n/1e3)+'K';
  return '$'+fmtN(n,0);
}
function pct(a,b){return b?((a/b)*100).toFixed(1)+'%':'—'}
function pctNum(a,b){return b?(a/b)*100:0}

function delta(curr,prev){
  if(!prev||!curr) return '';
  const p=((curr-prev)/prev*100);
  const arrow=p>0?'▲':'▼';
  const cls=p>0?'up':'down';
  return `<span class="delta ${cls}">${arrow} ${Math.abs(p).toFixed(1)}%</span>`;
}

function ageFmt(secs){
  if(secs<5) return '<span style="color:#16a34a">ahora</span>';
  if(secs<60) return `<span style="color:#16a34a">hace ${secs}s</span>`;
  const m=Math.floor(secs/60);
  if(m<10) return `<span style="color:#d97706">hace ${m}min</span>`;
  return `<span style="color:#dc2626">hace ${m}min</span>`;
}

function semaforo(pctVal, warnThr, dngThr){
  if(pctVal>=dngThr) return 'danger';
  if(pctVal>=warnThr) return 'warn';
  return 'ok';
}

function renderChart(trend,hasWd){
  if(!trend||!trend.length) return;
  const labels=trend.map(t=>{
    const[y,m]=t.mes.split('-');
    return ['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic'][+m-1]+'\n'+y;
  });
  const barData=hasWd?trend.map(t=>t.avg_dia||t.pedidos):trend.map(t=>t.pedidos);
  const barLabel=hasWd?'Ped/día hábil':'Pedidos';
  const ctx=document.getElementById('chart').getContext('2d');
  if(chartObj) chartObj.destroy();
  chartObj=new Chart(ctx,{
    data:{labels,datasets:[
      {type:'bar',label:barLabel,data:barData,
       backgroundColor:'rgba(37,99,235,.7)',borderColor:'#2563eb',borderWidth:1,yAxisID:'y1',order:2},
      {type:'line',label:'Valor (M$)',data:trend.map(t=>+(t.valor/1e6).toFixed(1)),
       borderColor:'#059669',backgroundColor:'rgba(5,150,105,.07)',
       borderWidth:2.5,pointRadius:4,pointBackgroundColor:'#059669',tension:.35,
       yAxisID:'y2',order:1,fill:true},
    ]},
    options:{
      responsive:true,maintainAspectRatio:false,
      interaction:{mode:'index',intersect:false},
      plugins:{
        legend:{labels:{color:'#475569',font:{size:11},boxWidth:12,padding:14}},
        tooltip:{
          backgroundColor:'#fff',titleColor:'#0f172a',bodyColor:'#475569',
          borderColor:'#e2e8f0',borderWidth:1,
          callbacks:{
            label:ctx=>' '+ctx.dataset.label+': '+fmtN(ctx.parsed.y,1),
            afterBody:items=>{
              const i=items[0].dataIndex,t=trend[i];
              return t.dias_hab?['  Días hábiles: '+t.dias_hab,'  Total pedidos: '+fmtN(t.pedidos,0)]:[];
            }
          }
        }
      },
      scales:{
        x:{ticks:{color:'#94a3b8',font:{size:9}},grid:{color:'#f1f5f9'}},
        y1:{type:'linear',position:'left',ticks:{color:'#2563eb',font:{size:9}},grid:{color:'#f1f5f9'},
            title:{display:true,text:barLabel,color:'#2563eb',font:{size:9}}},
        y2:{type:'linear',position:'right',ticks:{color:'#059669',font:{size:9},callback:v=>v+'M'},
            grid:{drawOnChartArea:false},title:{display:true,text:'Valor M$',color:'#059669',font:{size:9}}}
      }
    }
  });
}

function renderMeta(meta){
  if(!meta){document.getElementById('meta-row').innerHTML='<span style="color:var(--text3);font-size:11px">Sin datos de meta</span>';return;}
  const curr=meta.curr_pedidos, last=meta.last_pedidos;
  const pctProgress=last>0?Math.min((curr/last)*100,120):0;
  const pacePos=meta.days_in_month>0?(meta.day_of_month/meta.days_in_month)*100:0;
  const paceTarget=last>0?(pacePos/100)*last:0;
  const onTrack=curr>=paceTarget;
  const fill=Math.min(pctProgress,100);
  const lbl=meta.last_month?meta.last_month.slice(0,7):'mes anterior';

  // Status tag
  let tagCls='tag-neutral',tagTxt='Sin referencia';
  if(last>0){
    const diff=curr-paceTarget;
    if(onTrack){tagCls='tag-ok';tagTxt=`+${Math.round(diff)} sobre ritmo`;}
    else{const behind=Math.round(paceTarget-curr);tagCls=behind>last*0.1?'tag-danger':'tag-warn';tagTxt=`${behind} por debajo del ritmo`;}
  }

  const wdInfo=meta.curr_wd>0
    ? `${meta.dias_elapsed}/${meta.curr_wd} días hábiles`
    : `Día ${meta.day_of_month}/${meta.days_in_month}`;

  document.getElementById('meta-row').innerHTML=`
    <div class="meta-label">${meta.curr_month} vs ${lbl}</div>
    <div class="meta-nums">
      <span class="meta-curr">${fmtN(curr,0)}</span>
      <span class="meta-sep">de</span>
      <span class="meta-last">${fmtN(last,0)} pedidos</span>
    </div>
    <div class="meta-bar-wrap">
      <div class="meta-bar-bg">
        <div class="meta-bar-fill" style="width:${fill}%;background:${pctProgress>100?'var(--green)':onTrack?'var(--blue)':'var(--amber)'}"></div>
        <div class="meta-bar-pace" style="left:${pacePos.toFixed(1)}%" title="Ritmo esperado: ${Math.round(paceTarget)} pedidos"></div>
      </div>
      <div class="meta-bar-labels"><span>${wdInfo}</span><span>${pctProgress.toFixed(0)}% del mes anterior</span></div>
    </div>
    <div class="meta-tags">
      <span class="meta-tag ${tagCls}">${tagTxt}</span>
      ${meta.curr_wd>0?`<span class="meta-tag tag-neutral">${meta.curr_wd} días háb/mes</span>`:''}
    </div>`;
}

function pillAnulados(pct){
  if(pct===0) return `<span class="s-pill pill-ok">0% anul.</span>`;
  if(pct<10)  return `<span class="s-pill pill-ok">${pct}% anul.</span>`;
  if(pct<25)  return `<span class="s-pill pill-warn">${pct}% anul.</span>`;
  return `<span class="s-pill pill-danger">${pct}% anul.</span>`;
}

function renderSellers(top5,bot5){
  const medals=['🥇','🥈','🥉','4°','5°'];

  function buildTable(sellers,cls){
    if(!sellers||!sellers.length) return '<p style="color:var(--text3);font-size:11px;padding:8px">Sin datos</p>';
    let h=`<table class="seller-table ${cls}">
      <tr><th></th><th>Vendedor</th><th style="text-align:right">Válidos</th><th style="text-align:right">Total</th><th>Anulaciones</th></tr>`;
    sellers.forEach((s,i)=>{
      const rankCls=i<3?`s-medal-${i+1}`:'s-rank';
      h+=`<tr>
        <td class="${rankCls}" style="font-size:${i<3?'14px':'12px'}">${medals[i]}</td>
        <td class="s-name" title="ID ${s.id}">${s.nombre}</td>
        <td class="s-val">${s.validos}</td>
        <td style="color:var(--text3);text-align:right">${s.total}</td>
        <td>${pillAnulados(s.pct_anulados)}</td>
      </tr>`;
    });
    return h+'</table>';
  }

  document.getElementById('sellers-top').innerHTML=buildTable(top5,'seller-top');
  document.getElementById('sellers-bot').innerHTML=buildTable(bot5,'seller-bot');
}

function render(data){
  document.getElementById('err-r').textContent=data.reactor_error?'⚠ Reactor: '+data.reactor_error:'';
  document.getElementById('err-m').textContent=data.mspa_error?'⚠ MSPA: '+data.mspa_error:'';

  _mspaAge  = data.mspa_age  || 0;
  _reactAge = data.reactor_age || 0;

  const r=data.reactor||{};
  const dp=r.target_date_display||'—';
  document.getElementById('date-badge').textContent='Pedidos del '+dp;
  document.getElementById('sec-reactor').textContent='Pedidos Informados · '+dp;

  // KPIs + delta badges
  const c=r.comp||null;
  document.getElementById('k-ped').textContent=fmtN(r.pedidos,0);
  document.getElementById('k-ped-sub').textContent=r.avg_ped_vend?r.avg_ped_vend+' ped/vendedor':'';
  document.getElementById('d-ped').outerHTML=delta(r.pedidos,c?.pedidos)||'<span class="delta flat" id="d-ped"></span>';
  // Re-grab after outerHTML swap
  const dPed=document.getElementById('d-ped');
  if(dPed&&c) dPed.outerHTML=delta(r.pedidos,c.pedidos)||'<span class="delta flat" id="d-ped"></span>';

  document.getElementById('k-vend').textContent=fmtN(r.vendedores,0);
  document.getElementById('k-lin').textContent=fmtN(r.lineas,0);
  document.getElementById('k-lin-sub').textContent=r.avg_lineas?r.avg_lineas+' promedio por pedido':'';
  document.getElementById('k-avg').textContent=r.avg_lineas||'—';
  document.getElementById('k-apv').textContent=r.avg_ped_vend||'—';

  // Delta badges via innerHTML approach
  if(c){
    const mk=id=>document.getElementById(id);
    function setDelta(rowId,curr,prev){
      const el=mk(rowId); if(!el) return;
      const d=delta(curr,prev);
      el.innerHTML=d;
    }
    setDelta('d-ped',r.pedidos,c.pedidos);
    setDelta('d-vend',r.vendedores,c.vendedores);
  }

  // Flow bar
  const bs=r.by_status||{};
  const total=r.pedidos||0;
  const m=data.mspa||{};
  const ret  = bs[15]||{cnt:0,val:0};
  const an   = bs[14]||{cnt:0,val:0};
  const back = m.backorders||{ords:0,val:0};
  const fact_cnt=(bs[13]?.cnt||0)+(bs[18]?.cnt||0);
  const fact_val=m.venta?.val||0;

  document.getElementById('fl-inf-val').textContent=fmtK(r.valor||0);
  document.getElementById('fl-inf-ped').textContent=fmtN(total,0)+' pedidos · 100%';

  document.getElementById('fl-ret-val').textContent=fmtK(ret.val);
  document.getElementById('fl-ret-ped').textContent=fmtN(ret.cnt,0)+' pedidos';
  document.getElementById('fl-ret-pct').textContent=pct(ret.cnt,total);

  document.getElementById('fl-an-val').textContent=fmtK(an.val);
  document.getElementById('fl-an-ped').textContent=fmtN(an.cnt,0)+' pedidos';
  document.getElementById('fl-an-pct').textContent=pct(an.cnt,total);

  document.getElementById('fl-back-val').textContent=fmtK(back.val);
  document.getElementById('fl-back-ped').textContent=fmtN(back.ords,0)+' ord (MSPA)';
  document.getElementById('fl-back-pct').textContent='—';

  document.getElementById('fl-fact-val').textContent=fmtK(fact_val);
  document.getElementById('fl-fact-ped').textContent=fmtN(fact_cnt,0)+' pedidos';
  document.getElementById('fl-fact-pct').textContent=pct(fact_cnt,total);

  // ── Semáforo flow cells ──
  const retPct=pctNum(ret.cnt,total);
  const anPct =pctNum(an.cnt,total);
  const fcRet=document.getElementById('fc-ret');
  const fcAn =document.getElementById('fc-an');
  const aiRet=document.getElementById('ai-ret');
  const aiAn =document.getElementById('ai-an');

  fcRet.classList.remove('pulse-warn','pulse-danger');
  fcAn.classList.remove('pulse-warn','pulse-danger');
  const sRet=semaforo(retPct,THR_RET_WARN,THR_RET_DNG);
  const sAn =semaforo(anPct, THR_AN_WARN, THR_AN_DNG);
  if(sRet==='warn'){fcRet.classList.add('pulse-warn');aiRet.textContent='⚠️';}
  else if(sRet==='danger'){fcRet.classList.add('pulse-danger');aiRet.textContent='🔴';}
  else aiRet.textContent='';
  if(sAn==='warn'){fcAn.classList.add('pulse-warn');aiAn.textContent='⚠️';}
  else if(sAn==='danger'){fcAn.classList.add('pulse-danger');aiAn.textContent='🔴';}
  else aiAn.textContent='';

  // ── Semáforo KPI card (pedidos vs pct anulados) ──
  const kpiPed=document.getElementById('kpi-ped');
  kpiPed.classList.remove('alert-warn','alert-danger');
  if(sAn==='danger') kpiPed.classList.add('alert-danger');
  else if(sAn==='warn') kpiPed.classList.add('alert-warn');

  // Pending strip
  const pend=r.pending||0;
  if(pend>0){
    const det=[];
    if(bs[10]?.cnt) det.push('Nuevo: '+bs[10].cnt);
    if(bs[11]?.cnt) det.push('Pendiente: '+bs[11].cnt);
    if(bs[12]?.cnt) det.push('En Proceso: '+bs[12].cnt);
    if(bs[17]?.cnt) det.push('Generado: '+bs[17].cnt);
    document.getElementById('pending-cnt').textContent=pend;
    document.getElementById('pending-detail').textContent=det.join(' · ');
    document.getElementById('pending-strip').style.display='flex';
  } else {
    document.getElementById('pending-strip').style.display='none';
  }

  // Chart
  if(r.trend&&r.trend.length){
    document.getElementById('chart-lbl').textContent=
      r.has_workdays
        ?'Tendencia Mensual — Promedio Pedidos por Día Hábil (12 meses)'
        :'Tendencia Mensual — Pedidos Informados (12 meses)';
    renderChart(r.trend,r.has_workdays);
  }

  // Meta mensual
  renderMeta(r.meta||null);

  // Sellers ranking
  renderSellers(r.sellers_top5||[], r.sellers_bot5||[]);

  // MSPA
  let mhtml='';
  MSPA_DEF.forEach(row=>{
    const d=m[row.k]||{ords:0,pos:0,val:0};
    const hi=d.val>0&&row.cls!=='venta'?' hi':'';
    mhtml+=`<div class="mspa-row ${row.cls}${hi}">
      <div class="mspa-lbl">${row.l}</div>
      <div><div class="mspa-val">$${fmtK(d.val).replace('$','')}</div>
      <div class="mspa-sub">${d.ords} ord · ${d.pos} pos</div></div>
    </div>`;
  });
  document.getElementById('mspa-body').innerHTML=mhtml;
}

async function load(){
  try{const res=await fetch('/api/data');render(await res.json());}
  catch(e){console.error(e);}
}

// Tick every second — updates freshness display and triggers reload when needed
let _mspaNext=60, _reactRefreshed=false;
function tick(){
  _mspaAge++;  _reactAge++;
  _mspaNext=Math.max(0,_mspaNext-1);
  document.getElementById('fresh-m').innerHTML=ageFmt(_mspaAge);
  document.getElementById('fresh-r').innerHTML=ageFmt(_reactAge);
  if(_mspaNext<=0){load();_mspaNext=60;}
}

// TV mode
function toggleTV(){
  const tv=document.body.classList.toggle('tv');
  document.getElementById('tv-btn').textContent=tv?'☀ Normal':'📺 TV';
  localStorage.setItem('wuerth-tv',tv?'1':'0');
}
if(localStorage.getItem('wuerth-tv')==='1'||new URLSearchParams(location.search).get('tv')==='1'){
  document.body.classList.add('tv');
  document.getElementById('tv-btn').textContent='☀ Normal';
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
        if self.path in ("/","/index.html"):    self.send_html(HTML_PAGE)
        elif self.path.startswith("/api/data"):  self.send_json(get_cached_data())
        else: self.send_response(404); self.end_headers()


def main():
    print("Würth Operations Dashboard")
    print(f"DSN MSPA: {DSN_MSPA}  |  DSN Reactor: {DSN_REACTOR}")
    print(f"MSPA TTL: {MSPA_TTL}s  |  Reactor TTL: {REACTOR_TTL}s (10 min)")
    print(f"SOLO LECTURA  |  http://localhost:{PORT}  |  TV: http://localhost:{PORT}?tv=1")
    print("Ctrl+C para detener\n")
    server=HTTPServer(("0.0.0.0",PORT),Handler)
    try: server.serve_forever()
    except KeyboardInterrupt: print("\nDetenido.")


if __name__=="__main__":
    main()

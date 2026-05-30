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

# Dos TTLs: MSPA se refresca cada 60s, Reactor cada 10 min
MSPA_TTL    = 60
REACTOR_TTL = 600  # 10 minutos

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


# ── Logo (base64 si existe wurth_logo.png en la misma carpeta) ────────────────
def _load_logo():
    here = os.path.dirname(os.path.abspath(__file__))
    for name in ["wurth_logo.png", "logo.png", "wurth.png",
                 "wurth_logo.jpg", "logo.jpg",
                 "wurth_logo.svg", "logo.svg"]:
        path = os.path.join(here, name)
        if os.path.exists(path):
            ext = name.rsplit(".", 1)[-1]
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
    target = rows[0][0] if rows else (date.today() - timedelta(days=1))
    target_str = str(target)

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
        SELECT DATE_FORMAT(date, '%Y-%m') mes, COUNT(*) dias
        FROM work_days
        WHERE date >= DATE_SUB(CURDATE(), INTERVAL 12 MONTH)
        GROUP BY DATE_FORMAT(date, '%Y-%m')
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

    conn.close()

    # Pedidos pendientes de facturar (estados activos, no terminales)
    pending_total = sum(
        by_status.get(s, {}).get("cnt", 0) for s in [10, 11, 12, 17]
    )

    return {
        "target_date":         target_str,
        "target_date_display": target.strftime("%d/%m/%Y") if hasattr(target, "strftime") else str(target),
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

    return {
        "timestamp":     datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "reactor":       reactor or {},
        "mspa":          mspa    or {},
        "reactor_error": r_err,
        "mspa_error":    m_err,
        "reactor_age":   int((datetime.now() - _cache_react_ts).total_seconds()) if _cache_react_ts else 0,
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
body{background:var(--bg);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',system-ui,sans-serif;font-size:13px}

/* ── Header ── */
.hdr{background:#fff;border-bottom:2px solid var(--würth);padding:10px 24px;display:flex;align-items:center;justify-content:space-between;box-shadow:0 1px 4px rgba(0,0,0,.06)}
.hdr-left{display:flex;align-items:center;gap:14px}
.logo-text-fallback{display:flex;align-items:center;gap:6px}
.lw{background:var(--würth);color:#fff;font-weight:900;font-size:16px;padding:5px 9px;border-radius:3px;line-height:1}
.ln{font-size:20px;font-weight:900;letter-spacing:3px;color:var(--würth)}
.div-v{width:1px;height:32px;background:var(--border2);margin:0 4px}
.hdr-title{font-size:14px;font-weight:700;color:var(--text)}
.hdr-sub{font-size:10px;color:var(--text3);margin-top:2px}
.hdr-right{display:flex;align-items:center;gap:18px;flex-shrink:0}
.date-badge{background:#fff7f7;border:1.5px solid var(--würth);border-radius:6px;padding:4px 12px;font-size:12px;color:var(--würth);font-weight:700;white-space:nowrap}
.hdr-meta{font-size:11px;color:var(--text3);text-align:right;line-height:1.8}
.hdr-meta b{color:var(--text2)}
.hdr-meta small{font-size:10px;color:var(--text3)}
.live{display:flex;align-items:center;gap:5px;font-size:11px;color:var(--text3)}
.dot{width:8px;height:8px;border-radius:50%;background:#16a34a;animation:pulse 2s infinite}
@keyframes pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.4;transform:scale(1.3)}}

/* ── Layout ── */
.main{padding:16px 24px;display:flex;flex-direction:column;gap:14px}
.sec-lbl{font-size:9px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:var(--text3);margin-bottom:8px}
.err{color:var(--red);font-size:11px;margin-top:4px}

/* ── KPI ── */
.kpi-grid{display:grid;grid-template-columns:repeat(5,1fr);gap:10px}
.kpi{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:16px;box-shadow:0 1px 3px rgba(0,0,0,.05);position:relative;overflow:hidden}
.kpi::after{content:'';position:absolute;top:0;left:0;right:0;height:3px;border-radius:10px 10px 0 0}
.kpi.c-blue::after{background:var(--blue)}.kpi.c-cyan::after{background:var(--cyan)}
.kpi.c-purple::after{background:var(--purple)}.kpi.c-orange::after{background:var(--orange)}
.kpi.c-green::after{background:var(--green)}
.kpi-lbl{font-size:10px;color:var(--text3);margin-bottom:6px;font-weight:500;text-transform:uppercase;letter-spacing:.5px}
.kpi-val{font-size:32px;font-weight:800;line-height:1}
.c-blue .kpi-val{color:var(--blue)}.c-cyan .kpi-val{color:var(--cyan)}
.c-purple .kpi-val{color:var(--purple)}.c-orange .kpi-val{color:var(--orange)}
.c-green .kpi-val{color:var(--green)}
.kpi-sub{font-size:10px;color:var(--text3);margin-top:5px}

/* ── Flow bar (Informado → Retenido → Anulado → Backorder → Facturado) ── */
.flow-bar{display:grid;grid-template-columns:repeat(5,1fr);gap:1px;background:var(--border);border:1px solid var(--border);border-radius:10px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.05)}
.flow-cell{background:var(--surface);padding:14px 16px;display:flex;flex-direction:column;gap:4px;position:relative}
.flow-cell::after{content:'›';position:absolute;right:-8px;top:50%;transform:translateY(-50%);color:var(--text3);font-size:18px;z-index:1;pointer-events:none}
.flow-cell:last-child::after{display:none}
.flow-label{font-size:9px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase}
.flow-val{font-size:20px;font-weight:800;line-height:1.1}
.flow-sub{font-size:10px;color:var(--text3)}
.flow-pct{font-size:11px;font-weight:600;margin-top:2px}
/* colors per cell */
.fl-inf{border-top:3px solid var(--blue)}
.fl-inf .flow-label,.fl-inf .flow-pct{color:var(--blue)}
.fl-inf .flow-val{color:var(--blue)}
.fl-ret{border-top:3px solid var(--amber);background:var(--amber-bg)}
.fl-ret .flow-label,.fl-ret .flow-pct{color:var(--amber)}
.fl-ret .flow-val{color:var(--amber)}
.fl-an{border-top:3px solid var(--red);background:var(--red-bg)}
.fl-an .flow-label,.fl-an .flow-pct{color:var(--red)}
.fl-an .flow-val{color:var(--red)}
.fl-back{border-top:3px solid var(--orange)}
.fl-back .flow-label,.fl-back .flow-pct{color:var(--orange)}
.fl-back .flow-val{color:var(--orange)}
.fl-fact{border-top:3px solid var(--green);background:var(--green-bg)}
.fl-fact .flow-label,.fl-fact .flow-pct{color:var(--green)}
.fl-fact .flow-val{color:var(--green)}

/* pending strip below flow */
.pending-strip{background:var(--blue-bg);border:1px solid #bfdbfe;border-radius:8px;padding:8px 16px;display:flex;align-items:center;gap:10px;margin-top:8px;font-size:12px;color:var(--blue)}
.pending-strip b{font-size:16px;font-weight:800}
.pending-strip span{color:var(--text3)}

/* ── Bottom ── */
.bottom{display:grid;grid-template-columns:1fr 360px;gap:14px}
.card{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:16px;box-shadow:0 1px 3px rgba(0,0,0,.05)}
.chart-wrap{height:250px;position:relative}

/* ── MSPA ── */
.mspa-row{display:flex;align-items:center;justify-content:space-between;padding:9px 0;border-bottom:1px solid var(--border)}
.mspa-row:last-child{border-bottom:none}
.mspa-lbl{font-size:12px;color:var(--text2);flex:1}
.mspa-val{font-size:14px;font-weight:700;color:var(--text);text-align:right;min-width:80px}
.mspa-sub{font-size:10px;color:var(--text3);text-align:right;margin-top:1px}
.mspa-row.hi .mspa-lbl{color:var(--amber)}.mspa-row.hi .mspa-val{color:var(--amber)}
.mspa-row.venta .mspa-lbl{color:var(--green);font-weight:700}.mspa-row.venta .mspa-val{color:var(--green);font-size:17px}
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
    <div class="hdr-meta">
      Actualizado: <b id="ts">—</b><br>
      MSPA: <b id="cntdown-m">60</b>s &nbsp;|&nbsp; Reactor: <small id="react-age">—</small>
    </div>
    <div class="live"><div class="dot"></div>LIVE</div>
  </div>
</div>

<div class="main">

  <!-- KPIs -->
  <div>
    <div class="sec-lbl" id="sec-reactor">Pedidos Informados · —</div>
    <div id="err-r" class="err"></div>
    <div class="kpi-grid">
      <div class="kpi c-blue">
        <div class="kpi-lbl">Pedidos Informados</div>
        <div class="kpi-val" id="k-ped">—</div>
        <div class="kpi-sub" id="k-ped-sub">&nbsp;</div>
      </div>
      <div class="kpi c-cyan">
        <div class="kpi-lbl">Vendedores Activos</div>
        <div class="kpi-val" id="k-vend">—</div>
        <div class="kpi-sub" id="k-vend-sub">&nbsp;</div>
      </div>
      <div class="kpi c-purple">
        <div class="kpi-lbl">Total Líneas</div>
        <div class="kpi-val" id="k-lin">—</div>
        <div class="kpi-sub" id="k-lin-sub">&nbsp;</div>
      </div>
      <div class="kpi c-orange">
        <div class="kpi-lbl">Promedio Líneas / Pedido</div>
        <div class="kpi-val" id="k-avg">—</div>
        <div class="kpi-sub">artículos por pedido</div>
      </div>
      <div class="kpi c-green">
        <div class="kpi-lbl">Promedio Ped. / Vendedor</div>
        <div class="kpi-val" id="k-apv">—</div>
        <div class="kpi-sub">pedidos por vendedor</div>
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
      <div class="flow-cell fl-ret">
        <div class="flow-label">Retenido</div>
        <div class="flow-val" id="fl-ret-val">—</div>
        <div class="flow-sub" id="fl-ret-ped">—</div>
        <div class="flow-pct" id="fl-ret-pct">—%</div>
      </div>
      <div class="flow-cell fl-an">
        <div class="flow-label">Anulado</div>
        <div class="flow-val" id="fl-an-val">—</div>
        <div class="flow-sub" id="fl-an-ped">—</div>
        <div class="flow-pct" id="fl-an-pct">—%</div>
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

</div>

<script>
let chartObj=null, countdownM=60;

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

function renderChart(trend, hasWd){
  if(!trend||!trend.length) return;
  const labels=trend.map(t=>{
    const[y,m]=t.mes.split('-');
    return ['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic'][+m-1]+'\n'+y;
  });
  // If work_days available, show avg per day; else raw pedidos
  const barData = hasWd
    ? trend.map(t=>t.avg_dia||t.pedidos)
    : trend.map(t=>t.pedidos);
  const barLabel = hasWd ? 'Ped/día hábil' : 'Pedidos';

  const ctx=document.getElementById('chart').getContext('2d');
  if(chartObj) chartObj.destroy();
  chartObj=new Chart(ctx,{
    data:{
      labels,
      datasets:[
        {type:'bar',label:barLabel,data:barData,
         backgroundColor:'rgba(37,99,235,.7)',borderColor:'#2563eb',borderWidth:1,yAxisID:'y1',order:2},
        {type:'line',label:'Valor (M$)',data:trend.map(t=>+(t.valor/1e6).toFixed(1)),
         borderColor:'#059669',backgroundColor:'rgba(5,150,105,.07)',
         borderWidth:2.5,pointRadius:4,pointBackgroundColor:'#059669',tension:.35,
         yAxisID:'y2',order:1,fill:true},
      ]
    },
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
              const i=items[0].dataIndex;
              const t=trend[i];
              return t.dias_hab?['  Días hábiles: '+t.dias_hab,'  Total pedidos: '+fmtN(t.pedidos,0)]:[];
            }
          }
        }
      },
      scales:{
        x:{ticks:{color:'#94a3b8',font:{size:9}},grid:{color:'#f1f5f9'}},
        y1:{type:'linear',position:'left',ticks:{color:'#2563eb',font:{size:9}},
            grid:{color:'#f1f5f9'},
            title:{display:true,text:barLabel,color:'#2563eb',font:{size:9}}},
        y2:{type:'linear',position:'right',
            ticks:{color:'#059669',font:{size:9},callback:v=>v+'M'},
            grid:{drawOnChartArea:false},
            title:{display:true,text:'Valor M$',color:'#059669',font:{size:9}}}
      }
    }
  });
}

function render(data){
  document.getElementById('ts').textContent=data.timestamp||'—';
  document.getElementById('err-r').textContent=data.reactor_error?'⚠ Reactor: '+data.reactor_error:'';
  document.getElementById('err-m').textContent=data.mspa_error?'⚠ MSPA: '+data.mspa_error:'';

  const r=data.reactor||{};
  const dp=r.target_date_display||'—';
  document.getElementById('date-badge').textContent='Pedidos del '+dp;
  document.getElementById('sec-reactor').textContent='Pedidos Informados · '+dp;

  // Reactor age indicator
  const age=data.reactor_age||0;
  const ageMin=Math.floor(age/60);
  document.getElementById('react-age').textContent=
    ageMin>0?'datos de hace '+ageMin+'min':'datos actualizados';

  // KPIs
  document.getElementById('k-ped').textContent=fmtN(r.pedidos,0);
  document.getElementById('k-ped-sub').textContent=r.avg_ped_vend?r.avg_ped_vend+' ped/vendedor':' ';
  document.getElementById('k-vend').textContent=fmtN(r.vendedores,0);
  document.getElementById('k-vend-sub').textContent=' ';
  document.getElementById('k-lin').textContent=fmtN(r.lineas,0);
  document.getElementById('k-lin-sub').textContent=r.avg_lineas?r.avg_lineas+' promedio por pedido':' ';
  document.getElementById('k-avg').textContent=r.avg_lineas||'—';
  document.getElementById('k-apv').textContent=r.avg_ped_vend||'—';

  // Flow bar
  const bs=r.by_status||{};
  const total=r.pedidos||0;
  const m=data.mspa||{};

  const ret  = bs[15]||{cnt:0,val:0};
  const an   = bs[14]||{cnt:0,val:0};
  const back = m.backorders||{ords:0,val:0};
  const fact_cnt = (bs[13]?.cnt||0)+(bs[18]?.cnt||0);
  const fact_val = m.venta?.val||0;

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
        ? 'Tendencia Mensual — Promedio Pedidos por Día Hábil (12 meses)'
        : 'Tendencia Mensual — Pedidos Informados (12 meses)';
    renderChart(r.trend, r.has_workdays);
  }

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
  try{const r=await fetch('/api/data');render(await r.json());}
  catch(e){console.error(e);}
}
function tick(){
  countdownM--;
  document.getElementById('cntdown-m').textContent=countdownM;
  if(countdownM<=0){load();countdownM=60;}
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
        if self.path in ("/","/index.html"): self.send_html(HTML_PAGE)
        elif self.path=="/api/data":         self.send_json(get_cached_data())
        else: self.send_response(404); self.end_headers()


def main():
    print("Würth Operations Dashboard")
    print(f"DSN MSPA: {DSN_MSPA}  |  DSN Reactor: {DSN_REACTOR}")
    print(f"MSPA TTL: {MSPA_TTL}s  |  Reactor TTL: {REACTOR_TTL}s (10 min)")
    print(f"SOLO LECTURA  |  http://localhost:{PORT}")
    print("Ctrl+C para detener\n")
    server=HTTPServer(("0.0.0.0",PORT),Handler)
    try: server.serve_forever()
    except KeyboardInterrupt: print("\nDetenido.")


if __name__=="__main__":
    main()

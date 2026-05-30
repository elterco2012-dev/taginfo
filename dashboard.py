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
CACHE_SECONDS = 60

_cache_lock = threading.Lock()
_cache_data = None
_cache_time = None


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
    target = rows[0][0] if rows else (date.today() - timedelta(days=1))
    target_str = str(target)

    # KPIs — order_placed only (fast)
    rows = run(cur, """
        SELECT COUNT(DISTINCT id) pedidos,
               COUNT(DISTINCT id_user) vendedores,
               SUM(total) valor
        FROM order_placed
        WHERE DATE(order_date) = ?
    """, (target_str,))
    pedidos, vendedores, valor = (rows[0] if rows else (0, 0, 0))
    pedidos    = pedidos    or 0
    vendedores = vendedores or 0
    valor      = float(valor or 0)

    # Line count — separate query to isolate slowness
    rows_lin = run(cur, """
        SELECT COUNT(od.id) lineas
        FROM order_placed op
        JOIN order_detail od ON od.id_order_placed = op.id
        WHERE DATE(op.order_date) = ?
    """, (target_str,))
    lineas = (rows_lin[0][0] or 0) if rows_lin else 0

    # By status — current id_order_status on order_placed (source of truth)
    status_rows = run(cur, """
        SELECT op.id_order_status, os.name, COUNT(*) cnt, SUM(op.total) val
        FROM order_placed op
        JOIN order_status os ON os.id = op.id_order_status
        WHERE DATE(op.order_date) = ?
        GROUP BY op.id_order_status, os.name
        ORDER BY op.id_order_status
    """, (target_str,))
    by_status = {}
    for r in status_rows:
        by_status[int(r[0])] = {"name": r[1], "cnt": r[2], "val": float(r[3] or 0)}

    # Monthly trend — 12 months, order_placed only (fast, no JOIN)
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
    trend = [
        {"mes": r[0], "pedidos": r[1] or 0, "valor": float(r[2] or 0)}
        for r in trend_rows
    ]

    conn.close()

    anulados  = by_status.get(14, {}).get("cnt", 0)
    retenidos = by_status.get(15, {}).get("cnt", 0)

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
        "anulados":     anulados,
        "retenidos":    retenidos,
        "trend":        trend,
    }


# ─────────────────────────────────────────────────────────────────────────────
# MSPA fetch — queries exactas de taginfo2.4gl
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
def fetch_data():
    reactor_data = reactor_error = None
    mspa_data    = mspa_error    = None
    try:
        reactor_data = fetch_reactor()
    except Exception as e:
        reactor_error = str(e)
        print(f"Reactor ERROR: {e}")
    try:
        mspa_data = fetch_mspa()
    except Exception as e:
        mspa_error = str(e)
        print(f"MSPA ERROR: {e}")

    return {
        "timestamp":     datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "reactor":       reactor_data or {},
        "mspa":          mspa_data    or {},
        "reactor_error": reactor_error,
        "mspa_error":    mspa_error,
    }


def get_cached_data():
    global _cache_data, _cache_time
    now = datetime.now()
    with _cache_lock:
        if _cache_data is None or (now - _cache_time).total_seconds() >= CACHE_SECONDS:
            print(f"  [{now.strftime('%H:%M:%S')}] Consultando BDs...")
            try:
                _cache_data = fetch_data()
                _cache_time = now
                print(f"  [{now.strftime('%H:%M:%S')}] OK")
            except Exception as e:
                print(f"  [{now.strftime('%H:%M:%S')}] ERROR: {e}")
                if _cache_data is None:
                    _cache_data = {"error": str(e),
                                   "timestamp": now.strftime("%d/%m/%Y %H:%M:%S"),
                                   "reactor": {}, "mspa": {}}
        return _cache_data


# ─────────────────────────────────────────────────────────────────────────────
# HTML — tema claro
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
  --bg:#f0f2f5;
  --surface:#ffffff;
  --surface2:#f8fafc;
  --border:#e2e8f0;
  --border2:#cbd5e1;
  --text:#0f172a;
  --text2:#475569;
  --text3:#94a3b8;
  --blue:#2563eb;
  --cyan:#0891b2;
  --green:#059669;
  --amber:#d97706;
  --red:#dc2626;
  --orange:#ea580c;
  --purple:#7c3aed;
  --red-bg:#fef2f2;
  --amber-bg:#fffbeb;
  --green-bg:#f0fdf4;
}
*{margin:0;padding:0;box-sizing:border-box}
body{background:var(--bg);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',system-ui,sans-serif;font-size:13px;min-height:100vh}

/* Header */
.hdr{
  background:#ffffff;
  border-bottom:2px solid #cc0000;
  padding:10px 24px;
  display:flex;align-items:center;justify-content:space-between;gap:16px;
  box-shadow:0 1px 4px rgba(0,0,0,.08);
}
.hdr-left{display:flex;align-items:center;gap:14px}
/* Logo SVG text */
.logo-wrap{display:flex;align-items:center;gap:8px}
.logo-shield{
  background:#cc0000;color:#fff;font-weight:900;font-size:16px;
  padding:5px 9px;letter-spacing:2px;border-radius:3px;line-height:1;
}
.logo-text{font-size:20px;font-weight:900;letter-spacing:3px;color:#cc0000}
.hdr-divider{width:1px;height:32px;background:var(--border2);margin:0 4px}
.hdr-title{font-size:14px;font-weight:700;color:var(--text)}
.hdr-sub{font-size:10px;color:var(--text3);margin-top:2px}
.hdr-right{display:flex;align-items:center;gap:18px;flex-shrink:0}
.badge{
  background:#fff7f7;border:1.5px solid #cc0000;
  border-radius:6px;padding:4px 12px;
  font-size:12px;color:#cc0000;font-weight:700;white-space:nowrap;
}
.hdr-meta{font-size:11px;color:var(--text3);text-align:right;line-height:1.8}
.hdr-meta b{color:var(--text2)}
.live{display:flex;align-items:center;gap:5px;font-size:11px;color:var(--text3)}
.dot{width:8px;height:8px;border-radius:50%;background:#16a34a;animation:pulse 2s infinite;flex-shrink:0}
@keyframes pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.4;transform:scale(1.3)}}

/* Layout */
.main{padding:16px 24px;display:flex;flex-direction:column;gap:14px}
.sec-lbl{font-size:9px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:var(--text3);margin-bottom:8px}
.err{color:var(--red);font-size:11px;margin-top:4px}

/* KPI */
.kpi-grid{display:grid;grid-template-columns:repeat(5,1fr);gap:10px}
.kpi{
  background:var(--surface);border:1px solid var(--border);
  border-radius:10px;padding:16px;
  box-shadow:0 1px 3px rgba(0,0,0,.06);
  position:relative;overflow:hidden;
}
.kpi::after{content:'';position:absolute;top:0;left:0;right:0;height:3px;border-radius:10px 10px 0 0}
.kpi.c-blue::after{background:var(--blue)}
.kpi.c-cyan::after{background:var(--cyan)}
.kpi.c-purple::after{background:var(--purple)}
.kpi.c-orange::after{background:var(--orange)}
.kpi.c-green::after{background:var(--green)}
.kpi-lbl{font-size:10px;color:var(--text3);margin-bottom:6px;font-weight:500;text-transform:uppercase;letter-spacing:.5px}
.kpi-val{font-size:32px;font-weight:800;line-height:1}
.c-blue .kpi-val{color:var(--blue)}
.c-cyan .kpi-val{color:var(--cyan)}
.c-purple .kpi-val{color:var(--purple)}
.c-orange .kpi-val{color:var(--orange)}
.c-green .kpi-val{color:var(--green)}
.kpi-sub{font-size:10px;color:var(--text3);margin-top:5px}

/* Status — solo Anulado y Retenido */
.status-wrap{
  background:var(--surface);border:1px solid var(--border);border-radius:10px;
  padding:14px 20px;box-shadow:0 1px 3px rgba(0,0,0,.06);
  display:flex;align-items:center;gap:24px;flex-wrap:wrap;
}
.status-group{display:flex;align-items:center;gap:10px}
.status-pill{
  display:flex;align-items:center;gap:8px;
  border-radius:8px;padding:10px 18px;
  border:1.5px solid;
}
.status-pill.red{background:var(--red-bg);border-color:#fca5a5}
.status-pill.amber{background:var(--amber-bg);border-color:#fcd34d}
.status-dot{width:10px;height:10px;border-radius:50%;flex-shrink:0}
.status-info{display:flex;flex-direction:column}
.status-name{font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:.5px;color:var(--text3)}
.status-cnt{font-size:22px;font-weight:800;line-height:1.1}
.status-val{font-size:11px;font-weight:600;margin-top:2px}
.status-pill.red .status-cnt{color:var(--red)}
.status-pill.red .status-val{color:var(--red)}
.status-pill.amber .status-cnt{color:var(--amber)}
.status-pill.amber .status-val{color:var(--amber)}
.status-divider{width:1px;height:50px;background:var(--border2)}
.status-note{font-size:11px;color:var(--text3);flex:1}

/* Bottom */
.bottom{display:grid;grid-template-columns:1fr 360px;gap:14px}
.card{
  background:var(--surface);border:1px solid var(--border);border-radius:10px;
  padding:16px;box-shadow:0 1px 3px rgba(0,0,0,.06);
}
.chart-wrap{height:250px;position:relative}

/* MSPA */
.mspa-row{
  display:flex;align-items:center;justify-content:space-between;
  padding:10px 0;border-bottom:1px solid var(--border);
}
.mspa-row:last-child{border-bottom:none}
.mspa-lbl{font-size:12px;color:var(--text2);flex:1}
.mspa-val{font-size:14px;font-weight:700;color:var(--text);text-align:right;min-width:90px}
.mspa-sub{font-size:10px;color:var(--text3);text-align:right;margin-top:1px}
.mspa-row.hi .mspa-lbl{color:var(--amber)}
.mspa-row.hi .mspa-val{color:var(--amber)}
.mspa-row.venta .mspa-lbl{color:var(--green);font-weight:700}
.mspa-row.venta .mspa-val{color:var(--green);font-size:17px}
</style>
</head>
<body>

<div class="hdr">
  <div class="hdr-left">
    <div class="logo-wrap">
      <div class="logo-shield">W</div>
      <div class="logo-text">WÜRTH</div>
    </div>
    <div class="hdr-divider"></div>
    <div>
      <div class="hdr-title">Operations Dashboard</div>
      <div class="hdr-sub">Reactor · MSPA · Tiempo Real</div>
    </div>
  </div>
  <div class="hdr-right">
    <div class="badge" id="date-badge">Cargando...</div>
    <div class="hdr-meta">
      Actualizado: <b id="ts">—</b><br>
      Próxima actualización: <b id="cntdown">60</b>s
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
        <div class="kpi-lbl">Valor Informado</div>
        <div class="kpi-val" id="k-val">—</div>
        <div class="kpi-sub">$ARS · precio lista</div>
      </div>
    </div>
  </div>

  <!-- Anulados + Retenidos -->
  <div>
    <div class="sec-lbl">Pedidos Retenidos y Anulados del Día</div>
    <div class="status-wrap">
      <div class="status-group">
        <div class="status-pill red">
          <div class="status-dot" style="background:#dc2626"></div>
          <div class="status-info">
            <span class="status-name">Anulados</span>
            <span class="status-cnt" id="s-anul-cnt">—</span>
            <span class="status-val" id="s-anul-val">$—</span>
          </div>
        </div>
      </div>
      <div class="status-divider"></div>
      <div class="status-group">
        <div class="status-pill amber">
          <div class="status-dot" style="background:#d97706"></div>
          <div class="status-info">
            <span class="status-name">Retenidos</span>
            <span class="status-cnt" id="s-ret-cnt">—</span>
            <span class="status-val" id="s-ret-val">$—</span>
          </div>
        </div>
      </div>
      <div class="status-note" id="s-note">Cargando...</div>
    </div>
  </div>

  <!-- Chart + MSPA -->
  <div class="bottom">
    <div class="card">
      <div class="sec-lbl">Tendencia Mensual — Pedidos Informados (últimos 12 meses)</div>
      <div class="chart-wrap"><canvas id="chart"></canvas></div>
    </div>
    <div class="card">
      <div class="sec-lbl">MSPA — Estado Actual</div>
      <div id="err-m" class="err"></div>
      <div id="mspa-body"></div>
    </div>
  </div>

</div>

<script>
let chartObj=null, countdown=60;

const MSPA_DEF=[
  {k:'backorders', l:'Backorders (Plazos viejos)',    cls:''},
  {k:'bloqueados', l:'Bloqueados por Límite Crédito', cls:''},
  {k:'neg_status', l:'Bloqueados (Status < -1)',       cls:''},
  {k:'futuros',    l:'Pedidos Abiertos (Futuros)',     cls:''},
  {k:'produccion', l:'Producción Abierta',             cls:''},
  {k:'remitos',    l:'Remitos / Facturas Abiertas',    cls:''},
  {k:'venta',      l:'Venta del Día',                  cls:'venta'},
];

function fmtN(n,dec=0){
  if(n===null||n===undefined) return '—';
  return Number(n).toLocaleString('es-AR',{minimumFractionDigits:dec,maximumFractionDigits:dec});
}
function fmtK(n){
  n=Number(n)||0;
  if(n>=1e9) return (n/1e9).toFixed(1)+'B';
  if(n>=1e6) return (n/1e6).toFixed(1)+'M';
  if(n>=1e3) return (n/1e3).toFixed(0)+'K';
  return fmtN(n,0);
}

function renderChart(trend){
  if(!trend||!trend.length) return;
  const labels=trend.map(t=>{
    const[y,m]=t.mes.split('-');
    return ['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic'][+m-1]+'\n'+y;
  });
  const ctx=document.getElementById('chart').getContext('2d');
  if(chartObj) chartObj.destroy();
  chartObj=new Chart(ctx,{
    data:{
      labels,
      datasets:[
        {
          type:'bar',label:'Pedidos',data:trend.map(t=>t.pedidos),
          backgroundColor:'rgba(37,99,235,.75)',borderColor:'#2563eb',
          borderWidth:1,yAxisID:'y1',order:2
        },
        {
          type:'line',label:'Valor (M$)',
          data:trend.map(t=>+(t.valor/1e6).toFixed(1)),
          borderColor:'#059669',backgroundColor:'rgba(5,150,105,.08)',
          borderWidth:2.5,pointRadius:4,pointBackgroundColor:'#059669',
          tension:.35,yAxisID:'y2',order:1,fill:true
        }
      ]
    },
    options:{
      responsive:true,maintainAspectRatio:false,
      interaction:{mode:'index',intersect:false},
      plugins:{
        legend:{labels:{color:'#475569',font:{size:11},boxWidth:12,padding:16}},
        tooltip:{
          backgroundColor:'#fff',titleColor:'#0f172a',bodyColor:'#475569',
          borderColor:'#e2e8f0',borderWidth:1,
          callbacks:{label:ctx=>' '+ctx.dataset.label+': '+fmtN(ctx.parsed.y,0)}
        }
      },
      scales:{
        x:{ticks:{color:'#94a3b8',font:{size:9}},grid:{color:'#f1f5f9'}},
        y1:{
          type:'linear',position:'left',
          ticks:{color:'#2563eb',font:{size:9}},
          grid:{color:'#f1f5f9'},
          title:{display:true,text:'Pedidos',color:'#2563eb',font:{size:9}}
        },
        y2:{
          type:'linear',position:'right',
          ticks:{color:'#059669',font:{size:9},callback:v=>v+'M'},
          grid:{drawOnChartArea:false},
          title:{display:true,text:'Valor M$',color:'#059669',font:{size:9}}
        }
      }
    }
  });
}

function render(data){
  document.getElementById('ts').textContent=data.timestamp||'—';
  document.getElementById('err-r').textContent=data.reactor_error?'⚠ '+data.reactor_error:'';
  document.getElementById('err-m').textContent=data.mspa_error?'⚠ '+data.mspa_error:'';

  const r=data.reactor||{};
  const dp=r.target_date_display||'—';
  document.getElementById('date-badge').textContent='Pedidos del '+dp;
  document.getElementById('sec-reactor').textContent='Pedidos Informados · '+dp;

  document.getElementById('k-ped').textContent=fmtN(r.pedidos,0);
  document.getElementById('k-ped-sub').textContent=(r.pedidos&&r.vendedores)
    ? fmtN(r.avg_ped_vend,1)+' ped/vendedor' : ' ';
  document.getElementById('k-vend').textContent=fmtN(r.vendedores,0);
  document.getElementById('k-vend-sub').textContent=r.vendedores
    ? 'de '+fmtN(r.pedidos,0)+' pedidos' : ' ';
  document.getElementById('k-lin').textContent=fmtN(r.lineas,0);
  document.getElementById('k-lin-sub').textContent=r.lineas&&r.pedidos
    ? fmtN(r.avg_lineas,1)+' promedio por pedido' : ' ';
  document.getElementById('k-avg').textContent=r.avg_lineas||'—';
  document.getElementById('k-val').textContent='$'+fmtK(r.valor||0);

  // Anulados + Retenidos
  const bs=r.by_status||{};
  const an=bs[14]||{cnt:0,val:0};
  const re=bs[15]||{cnt:0,val:0};
  document.getElementById('s-anul-cnt').textContent=fmtN(an.cnt,0);
  document.getElementById('s-anul-val').textContent='$'+fmtK(an.val);
  document.getElementById('s-ret-cnt').textContent=fmtN(re.cnt,0);
  document.getElementById('s-ret-val').textContent='$'+fmtK(re.val);
  const total_an_re=(an.cnt||0)+(re.cnt||0);
  const pct=r.pedidos?((total_an_re/r.pedidos)*100).toFixed(1):0;
  document.getElementById('s-note').textContent=
    total_an_re+' pedidos no facturados ('+pct+'% del total informado)  ·  '
    +'Estado actual según Reactor · '+dp;

  // Chart
  if(r.trend&&r.trend.length) renderChart(r.trend);

  // MSPA
  const m=data.mspa||{};
  let mhtml='';
  MSPA_DEF.forEach(row=>{
    const d=m[row.k]||{ords:0,pos:0,val:0};
    const hi=d.val>0&&row.cls!=='venta'?' hi':'';
    mhtml+=`<div class="mspa-row ${row.cls}${hi}">
      <div class="mspa-lbl">${row.l}</div>
      <div>
        <div class="mspa-val">$${fmtK(d.val)}</div>
        <div class="mspa-sub">${d.ords} ord · ${d.pos} pos</div>
      </div>
    </div>`;
  });
  document.getElementById('mspa-body').innerHTML=mhtml;
}

async function load(){
  try{const r=await fetch('/api/data');render(await r.json());}
  catch(e){console.error(e);}
  countdown=60;
}
function tick(){
  document.getElementById('cntdown').textContent=countdown;
  if(--countdown<0) load();
}
load();
setInterval(tick,1000);
</script>
</body>
</html>
"""


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
        else:
            self.send_response(404); self.end_headers()


def main():
    print("Würth Operations Dashboard")
    print(f"DSN MSPA: {DSN_MSPA}  |  DSN Reactor: {DSN_REACTOR}")
    print(f"FIRMA: {FIRMA}  |  SOLO LECTURA")
    print(f"Escuchando en http://localhost:{PORT}")
    print("Ctrl+C para detener\n")
    server=HTTPServer(("0.0.0.0",PORT),Handler)
    try: server.serve_forever()
    except KeyboardInterrupt: print("\nDetenido.")


if __name__=="__main__":
    main()

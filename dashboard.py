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

    # Find most recent order_date with significant activity
    rows = run(cur, """
        SELECT DATE(order_date) d FROM order_placed
        GROUP BY DATE(order_date) HAVING COUNT(*) >= 50
        ORDER BY d DESC LIMIT 1
    """)
    target = rows[0][0] if rows else (date.today() - timedelta(days=1))
    target_str = str(target)

    # KPIs
    rows = run(cur, """
        SELECT COUNT(DISTINCT op.id), COUNT(DISTINCT op.id_user),
               SUM(op.total), COUNT(od.id)
        FROM order_placed op
        LEFT JOIN order_detail od ON od.id_order_placed = op.id
        WHERE DATE(op.order_date) = ?
    """, (target_str,))
    pedidos, vendedores, valor, lineas = (rows[0] if rows else (0,0,0,0))
    pedidos   = pedidos   or 0
    vendedores= vendedores or 0
    valor     = float(valor or 0)
    lineas    = lineas    or 0

    # By status (current id_order_status on order_placed)
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

    # Last status from history for Anulados + Retenidos
    # (latest entry per order for the target date)
    anul_ret = run(cur, """
        SELECT os.id, os.name, COUNT(DISTINCT osh.id_order_placed) cnt
        FROM order_status_history osh
        JOIN order_status os ON os.id = osh.id_order_status
        WHERE DATE(osh.date_created) >= ?
          AND osh.id_order_status IN (14, 15)
          AND osh.id = (
              SELECT MAX(h2.id) FROM order_status_history h2
              WHERE h2.id_order_placed = osh.id_order_placed
          )
        GROUP BY os.id, os.name
    """, (target_str,))
    anulados  = next((r[2] for r in anul_ret if r[0] == 14), 0)
    retenidos = next((r[2] for r in anul_ret if r[0] == 15), 0)

    # Monthly trend — last 13 months
    trend_rows = run(cur, """
        SELECT DATE_FORMAT(order_date, '%Y-%m') mes,
               COUNT(DISTINCT id) pedidos,
               COUNT(od.id) lineas,
               SUM(op.total) valor
        FROM order_placed op
        LEFT JOIN order_detail od ON od.id_order_placed = op.id
        WHERE op.order_date >= DATE_SUB(CURDATE(), INTERVAL 13 MONTH)
          AND DATE(op.order_date) <= CURDATE()
        GROUP BY DATE_FORMAT(op.order_date, '%Y-%m')
        ORDER BY mes
    """)
    trend = [
        {"mes": r[0], "pedidos": r[1] or 0, "lineas": r[2] or 0, "valor": float(r[3] or 0)}
        for r in trend_rows
    ]

    conn.close()
    return {
        "target_date":         target_str,
        "target_date_display": target.strftime("%d/%m/%Y") if hasattr(target, "strftime") else str(target),
        "pedidos":    pedidos,
        "vendedores": vendedores,
        "valor":      valor,
        "lineas":     lineas,
        "avg_lineas": round(lineas / pedidos, 1) if pedidos else 0,
        "avg_ped_vend": round(pedidos / vendedores, 1) if vendedores else 0,
        "by_status":  by_status,
        "anulados":   anulados,
        "retenidos":  retenidos,
        "trend":      trend,
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
        "timestamp":    datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "reactor":      reactor_data or {},
        "mspa":         mspa_data    or {},
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
                    _cache_data = {"error": str(e), "timestamp": now.strftime("%d/%m/%Y %H:%M:%S"),
                                   "reactor": {}, "mspa": {}}
        return _cache_data


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
:root {
  --bg:#0a0e1a; --surface:#111827; --surface2:#1a2234; --border:#1e2a3a;
  --border2:#2d3a4a; --text:#e2e8f0; --text2:#94a3b8; --text3:#4b5a6e;
  --blue:#3b82f6; --cyan:#06b6d4; --green:#10b981; --amber:#f59e0b;
  --red:#ef4444; --orange:#f97316; --purple:#8b5cf6; --teal:#14b8a6;
  --red-dim:rgba(239,68,68,.1); --amber-dim:rgba(245,158,11,.1);
  --green-dim:rgba(16,185,129,.1); --blue-dim:rgba(59,130,246,.1);
}
*{margin:0;padding:0;box-sizing:border-box}
body{background:var(--bg);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',system-ui,sans-serif;font-size:13px;min-height:100vh}

/* ── Header ── */
.hdr{background:linear-gradient(135deg,#0d1424 0%,#0f1a2e 100%);border-bottom:1px solid var(--border2);padding:10px 24px;display:flex;align-items:center;justify-content:space-between;gap:16px}
.hdr-left{display:flex;align-items:center;gap:14px}
.logo{background:#cc0000;color:#fff;font-weight:900;font-size:18px;padding:4px 10px;letter-spacing:3px;border-radius:4px;flex-shrink:0}
.hdr-title{font-size:15px;font-weight:700;letter-spacing:.3px}
.hdr-sub{font-size:10px;color:var(--text3);margin-top:2px}
.hdr-right{display:flex;align-items:center;gap:18px;flex-shrink:0}
.badge{background:var(--surface2);border:1px solid var(--border2);border-radius:6px;padding:4px 10px;font-size:12px;color:var(--cyan);font-weight:600;white-space:nowrap}
.hdr-meta{font-size:11px;color:var(--text3);text-align:right;line-height:1.7}
.hdr-meta b{color:var(--text2)}
.live{display:flex;align-items:center;gap:6px;font-size:11px;color:var(--text3)}
.dot{width:8px;height:8px;border-radius:50%;background:var(--green);animation:pulse 2s infinite;flex-shrink:0}
@keyframes pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.5;transform:scale(1.3)}}

/* ── Layout ── */
.main{padding:16px 24px;display:flex;flex-direction:column;gap:14px}
.sec-lbl{font-size:9px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:var(--text3);margin-bottom:8px}
.err{color:var(--red);font-size:11px;margin-top:4px}

/* ── KPI Cards ── */
.kpi-grid{display:grid;grid-template-columns:repeat(5,1fr);gap:10px}
.kpi{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:14px 16px;position:relative;overflow:hidden;transition:border-color .2s}
.kpi:hover{border-color:var(--border2)}
.kpi::after{content:'';position:absolute;top:0;left:0;right:0;height:3px;border-radius:10px 10px 0 0}
.kpi.c-blue::after{background:var(--blue)}
.kpi.c-cyan::after{background:var(--cyan)}
.kpi.c-purple::after{background:var(--purple)}
.kpi.c-orange::after{background:var(--orange)}
.kpi.c-green::after{background:var(--green)}
.kpi-lbl{font-size:10px;color:var(--text3);margin-bottom:6px;font-weight:500}
.kpi-val{font-size:30px;font-weight:800;line-height:1}
.kpi-val.c-blue{color:var(--blue)}
.kpi-val.c-cyan{color:var(--cyan)}
.kpi-val.c-purple{color:var(--purple)}
.kpi-val.c-orange{color:var(--orange)}
.kpi-val.c-green{color:var(--green)}
.kpi-sub{font-size:10px;color:var(--text3);margin-top:4px}

/* ── Status flow ── */
.flow{display:flex;flex-wrap:wrap;align-items:center;gap:6px;background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:12px 16px}
.chip{display:flex;align-items:center;gap:5px;border:1px solid var(--border2);border-radius:20px;padding:5px 11px;font-size:12px;white-space:nowrap;transition:all .2s}
.chip-dot{width:7px;height:7px;border-radius:50%;flex-shrink:0}
.chip-name{color:var(--text3)}
.chip-cnt{font-weight:700;color:var(--text)}
.chip.red{border-color:var(--red);background:var(--red-dim)}
.chip.red .chip-cnt{color:var(--red)}
.chip.amber{border-color:var(--amber);background:var(--amber-dim)}
.chip.amber .chip-cnt{color:var(--amber)}
.chip.green{border-color:var(--green);background:var(--green-dim)}
.chip.green .chip-cnt{color:var(--green)}
.arr{color:var(--text3);font-size:14px;flex-shrink:0}

/* ── Bottom grid ── */
.bottom{display:grid;grid-template-columns:1fr 360px;gap:14px}
.card{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:16px}
.chart-wrap{height:250px;position:relative}

/* ── MSPA table ── */
.mspa-row{display:flex;align-items:center;justify-content:space-between;padding:9px 0;border-bottom:1px solid var(--border)}
.mspa-row:last-child{border-bottom:none}
.mspa-lbl{font-size:11px;color:var(--text2);flex:1}
.mspa-nums{display:flex;gap:14px;text-align:right;flex-shrink:0}
.mspa-val{font-size:13px;font-weight:700;color:var(--text);min-width:80px}
.mspa-sub{font-size:10px;color:var(--text3);margin-top:1px}
.mspa-row.hi .mspa-val{color:var(--amber)}
.mspa-row.venta .mspa-val{color:var(--green);font-size:16px}
.mspa-row.venta .mspa-lbl{color:var(--green);font-weight:600}
</style>
</head>
<body>

<div class="hdr">
  <div class="hdr-left">
    <div class="logo">WÜRTH</div>
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

  <!-- KPIs Reactor -->
  <div>
    <div class="sec-lbl" id="sec-reactor">Pedidos Informados · —</div>
    <div id="err-r" class="err"></div>
    <div class="kpi-grid">
      <div class="kpi c-blue">
        <div class="kpi-lbl">Pedidos Informados</div>
        <div class="kpi-val c-blue" id="k-ped">—</div>
        <div class="kpi-sub" id="k-ped-sub">&nbsp;</div>
      </div>
      <div class="kpi c-cyan">
        <div class="kpi-lbl">Vendedores Activos</div>
        <div class="kpi-val c-cyan" id="k-vend">—</div>
        <div class="kpi-sub" id="k-vend-sub">&nbsp;</div>
      </div>
      <div class="kpi c-purple">
        <div class="kpi-lbl">Total Líneas</div>
        <div class="kpi-val c-purple" id="k-lin">—</div>
        <div class="kpi-sub" id="k-lin-sub">&nbsp;</div>
      </div>
      <div class="kpi c-orange">
        <div class="kpi-lbl">Avg Líneas / Pedido</div>
        <div class="kpi-val c-orange" id="k-avg">—</div>
        <div class="kpi-sub" id="k-avg-sub">&nbsp;</div>
      </div>
      <div class="kpi c-green">
        <div class="kpi-lbl">Valor Informado</div>
        <div class="kpi-val c-green" id="k-val">—</div>
        <div class="kpi-sub">$ARS</div>
      </div>
    </div>
  </div>

  <!-- Status flow -->
  <div>
    <div class="sec-lbl">Estado de Pedidos del Día</div>
    <div class="flow" id="flow">
      <span style="color:var(--text3)">Cargando...</span>
    </div>
  </div>

  <!-- Chart + MSPA -->
  <div class="bottom">
    <div class="card">
      <div class="sec-lbl">Tendencia Mensual — Pedidos Informados (últimos 13 meses)</div>
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
let chartObj = null, countdown = 60;

const STATUS = {
  10:{name:'Nuevo',          color:'#3b82f6', cls:''},
  11:{name:'Pendiente',      color:'#06b6d4', cls:''},
  17:{name:'Generado',       color:'#a78bfa', cls:''},
  12:{name:'En Proceso',     color:'#8b5cf6', cls:''},
  13:{name:'Facturado',      color:'#10b981', cls:'green'},
  18:{name:'Fact+Backorder', color:'#34d399', cls:'green'},
  14:{name:'Anulado',        color:'#ef4444', cls:'red'},
  15:{name:'Retenido',       color:'#f59e0b', cls:'amber'},
  16:{name:'Backorder',      color:'#f97316', cls:''},
};
const STATUS_ORDER = [10,11,17,12,13,18,14,15,16];

const MSPA_DEF = [
  {k:'backorders', l:'Backorders (Plazos viejos)',       cls:''},
  {k:'bloqueados', l:'Bloqueados por Límite Crédito',    cls:''},
  {k:'neg_status', l:'Bloqueados (Status < -1)',          cls:''},
  {k:'futuros',    l:'Pedidos Abiertos (Futuros)',        cls:''},
  {k:'produccion', l:'Producción Abierta',                cls:''},
  {k:'remitos',    l:'Remitos / Facturas Abiertas',       cls:''},
  {k:'venta',      l:'Venta del Día',                     cls:'venta'},
];

function fmtN(n, dec=0) {
  if(n===null||n===undefined) return '—';
  return Number(n).toLocaleString('es-AR',{minimumFractionDigits:dec,maximumFractionDigits:dec});
}
function fmtK(n) {
  n = Number(n)||0;
  if(n>=1e9) return (n/1e9).toFixed(1)+'B';
  if(n>=1e6) return (n/1e6).toFixed(1)+'M';
  if(n>=1e3) return (n/1e3).toFixed(0)+'K';
  return fmtN(n,0);
}
function fmtM(n) {
  return '$'+fmtK(n);
}

function renderChart(trend) {
  const labels  = trend.map(t=>{
    const [y,m]=t.mes.split('-');
    return ['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic'][+m-1]+' '+y.slice(2);
  });
  const ctx = document.getElementById('chart').getContext('2d');
  if(chartObj) chartObj.destroy();
  chartObj = new Chart(ctx,{
    data:{
      labels,
      datasets:[
        {type:'bar', label:'Pedidos', data:trend.map(t=>t.pedidos),
         backgroundColor:'rgba(59,130,246,.65)', borderColor:'#3b82f6', borderWidth:1,
         yAxisID:'y1', order:2},
        {type:'line', label:'Líneas', data:trend.map(t=>t.lineas),
         borderColor:'#8b5cf6', backgroundColor:'rgba(139,92,246,.08)',
         borderWidth:2, pointRadius:3, pointBg:'#8b5cf6', tension:.3,
         yAxisID:'y2', order:1, fill:true},
        {type:'line', label:'Valor (M$)', data:trend.map(t=>+(t.valor/1e6).toFixed(1)),
         borderColor:'#10b981', backgroundColor:'transparent',
         borderWidth:2, pointRadius:2, tension:.3,
         yAxisID:'y3', order:0},
      ]
    },
    options:{
      responsive:true, maintainAspectRatio:false,
      interaction:{mode:'index',intersect:false},
      plugins:{
        legend:{labels:{color:'#64748b',font:{size:10},boxWidth:12}},
        tooltip:{backgroundColor:'#1e293b',titleColor:'#e2e8f0',bodyColor:'#94a3b8',
                 callbacks:{label:ctx=>ctx.dataset.label+': '+fmtN(ctx.parsed.y,0)}}
      },
      scales:{
        x:{ticks:{color:'#4b5a6e',font:{size:9}},grid:{color:'#1a2234'}},
        y1:{type:'linear',position:'left',
            ticks:{color:'#3b82f6',font:{size:9}},grid:{color:'#1a2234'},
            title:{display:true,text:'Pedidos',color:'#3b82f6',font:{size:9}}},
        y2:{type:'linear',position:'right',display:false},
        y3:{type:'linear',position:'right',
            ticks:{color:'#10b981',font:{size:9},callback:v=>v+'M'},
            grid:{drawOnChartArea:false},
            title:{display:true,text:'Valor M$',color:'#10b981',font:{size:9}}},
      }
    }
  });
}

function render(data) {
  document.getElementById('ts').textContent = data.timestamp||'—';
  document.getElementById('err-r').textContent = data.reactor_error ? '⚠ '+data.reactor_error : '';
  document.getElementById('err-m').textContent = data.mspa_error    ? '⚠ '+data.mspa_error    : '';

  const r = data.reactor||{};
  const dp = r.target_date_display||'—';
  document.getElementById('date-badge').textContent = 'Pedidos del '+dp;
  document.getElementById('sec-reactor').textContent = 'Pedidos Informados · '+dp;

  document.getElementById('k-ped').textContent = fmtN(r.pedidos,0);
  document.getElementById('k-ped-sub').textContent = r.anulados ? r.anulados+' anulados · '+r.retenidos+' retenidos' : ' ';
  document.getElementById('k-vend').textContent = fmtN(r.vendedores,0);
  document.getElementById('k-vend-sub').textContent = r.avg_ped_vend ? r.avg_ped_vend+' ped/vendedor' : ' ';
  document.getElementById('k-lin').textContent = fmtN(r.lineas,0);
  document.getElementById('k-lin-sub').textContent = ' ';
  document.getElementById('k-avg').textContent = r.avg_lineas||'—';
  document.getElementById('k-avg-sub').textContent = 'líneas por pedido';
  document.getElementById('k-val').textContent = fmtK(r.valor||0);

  // Status flow
  const bs = r.by_status||{};
  const flowEl = document.getElementById('flow');
  let fhtml = '';
  STATUS_ORDER.forEach((sid,i)=>{
    const s = STATUS[sid]||{name:String(sid),color:'#64748b',cls:''};
    const d = bs[sid]||{cnt:0};
    if(i>0) fhtml += '<span class="arr">›</span>';
    fhtml += `<div class="chip ${s.cls}">
      <span class="chip-dot" style="background:${s.color}"></span>
      <span class="chip-name">${s.name}</span>
      <span class="chip-cnt">${d.cnt||0}</span>
    </div>`;
  });
  flowEl.innerHTML = fhtml;

  // Chart
  if(r.trend && r.trend.length) renderChart(r.trend.slice(-13));

  // MSPA
  const m = data.mspa||{};
  let mhtml = '';
  MSPA_DEF.forEach(row=>{
    const d = m[row.k]||{ords:0,pos:0,val:0};
    const hi = d.val>0 && row.cls!=='venta' ? ' hi' : '';
    mhtml += `<div class="mspa-row ${row.cls}${hi}">
      <div class="mspa-lbl">${row.l}</div>
      <div class="mspa-nums">
        <div>
          <div class="mspa-val">${fmtM(d.val)}</div>
          <div class="mspa-sub">${d.ords} ord · ${d.pos} pos</div>
        </div>
      </div>
    </div>`;
  });
  document.getElementById('mspa-body').innerHTML = mhtml;
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
# HTTP server
# ─────────────────────────────────────────────────────────────────────────────
class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def send_json(self, data):
        body = json.dumps(data, ensure_ascii=False, cls=_Enc).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def send_html(self, html):
        body = html.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self.send_html(HTML_PAGE)
        elif self.path == "/api/data":
            self.send_json(get_cached_data())
        else:
            self.send_response(404)
            self.end_headers()


def main():
    print("Würth Operations Dashboard")
    print(f"DSN MSPA: {DSN_MSPA}  |  DSN Reactor: {DSN_REACTOR}")
    print(f"FIRMA: {FIRMA}  |  SOLO LECTURA")
    print(f"Escuchando en http://localhost:{PORT}")
    print("Ctrl+C para detener\n")
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nDetenido.")


if __name__ == "__main__":
    main()

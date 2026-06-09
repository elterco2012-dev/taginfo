"""
Würth Dashboard — FTP Snapshot Job
Genera un JSON con los KPIs actuales y lo sube a www.wurth.com.ar por FTP.
Configurable via variables de entorno:
  FTP_HOST      host FTP  (ej: ftp.wurth.com.ar)
  FTP_USER      usuario FTP
  FTP_PASS      contraseña FTP
  FTP_PATH      directorio remoto donde subir (ej: /dashboard)
  FTP_INTERVAL  segundos entre actualizaciones (default: 600 = 10 min)
  FTP_ENABLED   "1" para activar (default: "0", desactivado)
"""

import ftplib
import io
import json
import os
import threading
import time
from datetime import datetime

FTP_HOST     = os.environ.get("FTP_HOST",     "")
FTP_USER     = os.environ.get("FTP_USER",     "")
FTP_PASS     = os.environ.get("FTP_PASS",     "")
FTP_PATH     = os.environ.get("FTP_PATH",     "/")
FTP_INTERVAL = int(os.environ.get("FTP_INTERVAL", "600"))
FTP_ENABLED  = os.environ.get("FTP_ENABLED",  "0") == "1"

_VIEWER_HTML = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="refresh" content="600">
<title>Würth — Resumen Operativo</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Segoe UI',Arial,sans-serif;background:#f1f5f9;color:#1e293b;min-height:100vh}
header{background:#cc0000;color:#fff;padding:14px 20px;display:flex;align-items:center;gap:12px}
.logo-mark{width:28px;height:28px;background:#fff;border-radius:5px;display:flex;align-items:center;justify-content:center}
.logo-mark span{color:#cc0000;font-weight:900;font-size:16px}
.hdr-title{font-size:16px;font-weight:700}
.hdr-sub{font-size:11px;opacity:.8;margin-top:1px}
.hdr-right{margin-left:auto;text-align:right;font-size:11px;opacity:.85}
.container{padding:16px;max-width:700px;margin:0 auto}
.stamp{font-size:12px;color:#64748b;margin-bottom:14px;text-align:center}
.stamp b{color:#1e293b}
.delay-note{background:#fef9c3;border:1px solid #fde047;border-radius:8px;
            padding:10px 14px;font-size:12px;color:#713f12;margin-bottom:16px;text-align:center}
.section{font-size:11px;font-weight:700;color:#94a3b8;text-transform:uppercase;
         letter-spacing:.06em;margin:20px 0 10px}
.cards{display:grid;grid-template-columns:1fr 1fr;gap:10px}
@media(min-width:500px){.cards{grid-template-columns:repeat(3,1fr)}}
.card{background:#fff;border-radius:10px;padding:14px 16px;box-shadow:0 1px 4px rgba(0,0,0,.07)}
.card-lbl{font-size:11px;color:#64748b;margin-bottom:4px}
.card-val{font-size:22px;font-weight:700;color:#1e293b}
.card-val.red{color:#cc0000}
.card-val.green{color:#16a34a}
.card-sub{font-size:11px;color:#94a3b8;margin-top:3px}
.flow{background:#fff;border-radius:10px;padding:16px;box-shadow:0 1px 4px rgba(0,0,0,.07);margin-top:10px}
.flow-row{display:flex;align-items:center;gap:10px;padding:8px 0;border-bottom:1px solid #f1f5f9}
.flow-row:last-child{border-bottom:none}
.flow-icon{width:32px;height:32px;border-radius:8px;display:flex;align-items:center;
           justify-content:center;font-size:16px;flex-shrink:0}
.flow-body{flex:1;min-width:0}
.flow-name{font-size:13px;font-weight:600;color:#1e293b}
.flow-val{font-size:13px;color:#374151}
.flow-bar-wrap{height:5px;background:#f1f5f9;border-radius:3px;margin-top:4px}
.flow-bar{height:5px;background:#cc0000;border-radius:3px;transition:width .5s}
.error-box{background:#fee2e2;border:1px solid #fca5a5;border-radius:8px;
           padding:12px 16px;font-size:13px;color:#991b1b;margin-bottom:12px}
footer{text-align:center;font-size:11px;color:#94a3b8;padding:24px 16px}
</style>
</head>
<body>
<header>
  <div class="logo-mark"><span>W</span></div>
  <div>
    <div class="hdr-title">Würth — Resumen Operativo</div>
    <div class="hdr-sub">Reactor · MSPA · Snapshot</div>
  </div>
  <div class="hdr-right" id="hdr-ts">Cargando…</div>
</header>

<div class="container">
  <div class="delay-note">
    ⏱ Esta vista es un snapshot con hasta <b id="delay-min">10</b> minutos de retraso.
    Para datos en tiempo real, accedé desde la red interna.
  </div>

  <div id="err-box" class="error-box" style="display:none"></div>

  <div class="stamp">Datos al <b id="stamp-ts">—</b> · Fecha operativa: <b id="stamp-date">—</b></div>

  <div class="section">Pedidos del día (Reactor)</div>
  <div class="cards" id="reactor-cards">
    <div class="card"><div class="card-lbl">Pedidos</div><div class="card-val" id="r-pedidos">—</div></div>
    <div class="card"><div class="card-lbl">Vendedores</div><div class="card-val" id="r-vend">—</div></div>
    <div class="card"><div class="card-lbl">Valor informado</div><div class="card-val" id="r-valor">—</div></div>
    <div class="card"><div class="card-lbl">Ped / vendedor</div><div class="card-val" id="r-pedvend">—</div></div>
    <div class="card"><div class="card-lbl">Líneas / pedido</div><div class="card-val" id="r-lineas">—</div></div>
    <div class="card"><div class="card-lbl">Ticket promedio</div><div class="card-val" id="r-ticket">—</div></div>
  </div>

  <div class="section">Facturación del día (MSPA)</div>
  <div class="cards">
    <div class="card"><div class="card-lbl">Facturado</div><div class="card-val red" id="m-venta">—</div></div>
    <div class="card"><div class="card-lbl">Pedidos fact.</div><div class="card-val" id="m-ords">—</div></div>
    <div class="card"><div class="card-lbl">% Facturado</div><div class="card-val" id="m-pct">—</div></div>
  </div>

  <div class="section">Flujo de pedidos</div>
  <div class="flow" id="flow-section"></div>
</div>

<footer>Würth Argentina · Snapshot generado automáticamente · Esta página no requiere VPN</footer>

<script>
const JSON_URL = 'snapshot.json';
const CACHE_BUST = '?v=' + Date.now();

function fmtN(v, dec=0){
  if(v==null||v===undefined||v==='')return '—';
  const n=Number(v);
  if(isNaN(n))return '—';
  return n.toLocaleString('es-AR',{minimumFractionDigits:dec,maximumFractionDigits:dec});
}
function fmtK(v){
  if(v==null||v===''||isNaN(Number(v)))return '—';
  const n=Number(v);
  if(Math.abs(n)>=1e9) return '$'+fmtN(n/1e9,1)+'B';
  if(Math.abs(n)>=1e6) return '$'+fmtN(n/1e6,1)+'M';
  if(Math.abs(n)>=1e3) return '$'+fmtN(n/1e3,1)+'K';
  return '$'+fmtN(n,0);
}

function set(id, val){ const el=document.getElementById(id); if(el) el.textContent=val; }

async function load(){
  try{
    const res = await fetch(JSON_URL+CACHE_BUST);
    if(!res.ok) throw new Error('HTTP '+res.status);
    const d = await res.json();
    render(d);
  } catch(e){
    const eb=document.getElementById('err-box');
    eb.textContent='No se pudo cargar el snapshot: '+e.message;
    eb.style.display='';
  }
}

function render(d){
  const ts = d.snapshot_ts || d.timestamp || '';
  set('stamp-ts', ts);
  document.getElementById('hdr-ts').textContent = ts ? 'Actualizado: '+ts : '';

  const r = d.reactor || {};
  const m = d.mspa || {};
  const ts2 = d.today_summary || {};

  // Date badge
  const dateDisp = r.target_date_display || r.target_date || '';
  set('stamp-date', dateDisp);

  // Delay minutes
  const interval = d.ftp_interval_secs || 600;
  const delEl = document.getElementById('delay-min');
  if(delEl) delEl.textContent = Math.round(interval/60);

  // Reactor KPIs — use today_summary if available (more current), fall back to reactor
  const ts_ped  = ts2 && ts2.pedidos   != null ? ts2.pedidos   : (r.pedidos || 0);
  const ts_vend = ts2 && ts2.vendedores!= null ? ts2.vendedores: (r.vendedores || 0);
  const ts_val  = ts2 && ts2.valor     != null ? ts2.valor     : (r.valor || 0);
  const ts_avp  = ts2 && ts2.avg_ped_vend!= null ? ts2.avg_ped_vend : null;
  const ts_alin = ts2 && ts2.avg_lineas!= null ? ts2.avg_lineas : null;
  const ts_tkt  = ts2 && ts2.ticket    != null ? ts2.ticket    : null;

  set('r-pedidos', fmtN(ts_ped, 0));
  set('r-vend',    fmtN(ts_vend, 0));
  set('r-valor',   fmtK(ts_val));
  set('r-pedvend', ts_avp  != null ? fmtN(ts_avp,  1) : '—');
  set('r-lineas',  ts_alin != null ? fmtN(ts_alin, 1) : '—');
  set('r-ticket',  ts_tkt  != null ? fmtK(ts_tkt)     : '—');

  // MSPA
  const venta = m.venta || {};
  const pedVal = ts_val || 0;
  const ventaVal = venta.val || 0;
  const pct = pedVal > 0 ? (ventaVal / pedVal * 100) : 0;
  set('m-venta', fmtK(ventaVal));
  set('m-ords',  fmtN(venta.ords, 0));
  set('m-pct',   pct > 0 ? fmtN(pct, 1)+'%' : '—');

  // Flow
  const flow = r.flow_items || [];
  const flowSec = document.getElementById('flow-section');
  if(flow.length){
    const maxVal = Math.max(...flow.map(f=>f.val||0), 1);
    flowSec.innerHTML = flow.map(f=>{
      const pct = Math.round((f.val||0)/maxVal*100);
      const icons = {1:'📋',2:'✅',3:'⏸️',4:'🚚',5:'❌'};
      const ico = icons[f.id] || '📦';
      return `<div class="flow-row">
        <div class="flow-icon">${ico}</div>
        <div class="flow-body">
          <div class="flow-name">${f.name||'Estado '+f.id} <span style="color:#94a3b8;font-weight:400">${fmtN(f.cnt,0)} ped</span></div>
          <div class="flow-val">${fmtK(f.val)}</div>
          <div class="flow-bar-wrap"><div class="flow-bar" style="width:${pct}%"></div></div>
        </div>
      </div>`;
    }).join('');
  } else {
    flowSec.innerHTML = '<div style="padding:12px;color:#94a3b8;font-size:13px">Sin datos de flujo.</div>';
  }

  // Errors
  const errBox = document.getElementById('err-box');
  const errs = [d.reactor_error&&('Reactor: '+d.reactor_error), d.mspa_error&&('MSPA: '+d.mspa_error)].filter(Boolean);
  if(errs.length){ errBox.textContent = '⚠ '+errs.join(' · '); errBox.style.display=''; }
  else errBox.style.display='none';
}

load();
</script>
</body>
</html>
"""


def _build_snapshot_json(data: dict, interval_secs: int) -> bytes:
    snapshot = {
        "snapshot_ts":      datetime.now().strftime("%d/%m/%Y %H:%M"),
        "ftp_interval_secs": interval_secs,
        "timestamp":        data.get("timestamp"),
        "reactor":          data.get("reactor"),
        "mspa":             data.get("mspa"),
        "today_summary":    data.get("today_summary"),
        "reactor_error":    data.get("reactor_error"),
        "mspa_error":       data.get("mspa_error"),
    }
    return json.dumps(snapshot, ensure_ascii=False, default=str, indent=None).encode("utf-8")


def _ftp_upload(json_bytes: bytes, html_bytes: bytes):
    ftp = ftplib.FTP()
    ftp.connect(FTP_HOST, 21, timeout=20)
    ftp.login(FTP_USER, FTP_PASS)
    if FTP_PATH and FTP_PATH != "/":
        try:
            ftp.cwd(FTP_PATH)
        except ftplib.error_perm:
            # Crear directorio si no existe
            parts = FTP_PATH.strip("/").split("/")
            ftp.cwd("/")
            for part in parts:
                try: ftp.cwd(part)
                except ftplib.error_perm: ftp.mkd(part); ftp.cwd(part)

    ftp.storbinary("STOR snapshot.json", io.BytesIO(json_bytes))
    ftp.storbinary("STOR index.html",    io.BytesIO(html_bytes))
    ftp.quit()


def _snapshot_loop(get_data_fn):
    html_bytes = _VIEWER_HTML.encode("utf-8")
    print(f"  [FTP] Snapshot job activo — host={FTP_HOST} path={FTP_PATH} intervalo={FTP_INTERVAL}s")
    while True:
        try:
            data       = get_data_fn()
            json_bytes = _build_snapshot_json(data, FTP_INTERVAL)
            _ftp_upload(json_bytes, html_bytes)
            print(f"  [FTP] Snapshot subido OK — {datetime.now().strftime('%H:%M:%S')} ({len(json_bytes)} bytes)")
        except Exception as e:
            print(f"  [FTP] Error al subir snapshot: {e}")
        time.sleep(FTP_INTERVAL)


def start_snapshot_job(get_data_fn):
    """Inicia el job de FTP snapshot en un thread daemon.
    Solo se activa si FTP_ENABLED=1 y FTP_HOST está configurado.
    """
    if not FTP_ENABLED:
        return
    if not FTP_HOST or not FTP_USER or not FTP_PASS:
        print("  [FTP] FTP_ENABLED=1 pero faltan FTP_HOST / FTP_USER / FTP_PASS. Job no iniciado.")
        return
    t = threading.Thread(target=_snapshot_loop, args=(get_data_fn,), daemon=True)
    t.start()

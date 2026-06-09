"""
Würth Dashboard — FTP Snapshot Job
"""

import ftplib, io, json, os, struct, threading, time, zlib
from datetime import datetime


def _make_png(size: int, r: int, g: int, b: int) -> bytes:
    """Genera un PNG sólido de 'size x size' píxeles sin librerías externas."""
    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff)
    raw = (b'\x00' + bytes([r, g, b]) * size) * size
    return (b'\x89PNG\r\n\x1a\n'
            + chunk(b'IHDR', struct.pack('>IIBBBBB', size, size, 8, 2, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(raw, 6))
            + chunk(b'IEND', b''))


# Ícono rojo Würth (#cc0000) — requerido para el prompt de instalación PWA
_ICON_192 = _make_png(192, 0xcc, 0x00, 0x00)
_ICON_512 = _make_png(512, 0xcc, 0x00, 0x00)

FTP_HOST     = os.environ.get("FTP_HOST",     "")
FTP_USER     = os.environ.get("FTP_USER",     "")
FTP_PASS     = os.environ.get("FTP_PASS",     "")
FTP_PATH     = os.environ.get("FTP_PATH",     "/")
FTP_INTERVAL = int(os.environ.get("FTP_INTERVAL", "300"))
FTP_ENABLED  = os.environ.get("FTP_ENABLED",  "0") == "1"

_SW_JS = """
const CACHE='wurth-snap-v1';
const ASSETS=['./','./index.html','./manifest.json'];
self.addEventListener('install',e=>{
  e.waitUntil(caches.open(CACHE).then(c=>c.addAll(ASSETS)).then(()=>self.skipWaiting()));
});
self.addEventListener('activate',e=>{e.waitUntil(clients.claim());});
self.addEventListener('fetch',e=>{
  const url=new URL(e.request.url);
  if(url.pathname.endsWith('snapshot.json')){
    e.respondWith(fetch(e.request).catch(()=>caches.match(e.request)));return;
  }
  e.respondWith(caches.match(e.request).then(r=>r||fetch(e.request)));
});
"""

_MANIFEST_DICT = {
  "name":"Würth Resumen Operativo","short_name":"Würth Ops",
  "start_url":"./","display":"standalone",
  "background_color":"#f1f5f9","theme_color":"#cc0000",
  "icons":[
    {"src":"icon-192.png","sizes":"192x192","type":"image/png"},
    {"src":"icon-512.png","sizes":"512x512","type":"image/png","purpose":"any maskable"}
  ]
}

_VIEWER_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#cc0000">
<link rel="manifest" href="manifest.json">
<title>Würth — Resumen Operativo</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Segoe UI',Arial,sans-serif;background:#f1f5f9;color:#1e293b;min-height:100vh;padding-bottom:32px}
header{background:#cc0000;color:#fff;padding:14px 16px;display:flex;align-items:center;gap:10px;position:sticky;top:0;z-index:10}
.logo-mark{width:28px;height:28px;background:#fff;border-radius:5px;display:flex;align-items:center;justify-content:center;flex-shrink:0}
.logo-mark span{color:#cc0000;font-weight:900;font-size:16px}
.hdr-title{font-size:15px;font-weight:700;line-height:1.2}
.hdr-sub{font-size:11px;opacity:.8}
.hdr-right{margin-left:auto;text-align:right;font-size:11px;opacity:.9;line-height:1.6}
.refresh-btn{background:rgba(255,255,255,.2);border:none;color:#fff;border-radius:6px;padding:5px 10px;font-size:12px;cursor:pointer}
.container{padding:12px 14px;max-width:720px;margin:0 auto}
.delay-note{background:#fef9c3;border:1px solid #fde047;border-radius:8px;padding:9px 13px;font-size:12px;color:#713f12;margin-bottom:14px}
.section{font-size:10px;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:.07em;margin:18px 0 8px;display:flex;align-items:center;gap:6px}
.section::after{content:'';flex:1;height:1px;background:#e2e8f0}
.cards{display:grid;grid-template-columns:1fr 1fr;gap:9px}
@media(min-width:480px){.cards.c3{grid-template-columns:repeat(3,1fr)}}
@media(min-width:600px){.cards.c6{grid-template-columns:repeat(3,1fr)}}
.card{background:#fff;border-radius:10px;padding:13px 15px;box-shadow:0 1px 3px rgba(0,0,0,.07)}
.card-lbl{font-size:11px;color:#64748b;margin-bottom:3px}
.card-val{font-size:20px;font-weight:700;color:#1e293b}
.card-val.red{color:#cc0000}.card-val.green{color:#16a34a}
.card-sub{font-size:11px;color:#94a3b8;margin-top:2px}
.plan-card{background:#fff;border-radius:10px;padding:15px;box-shadow:0 1px 3px rgba(0,0,0,.07)}
.plan-top{display:flex;align-items:flex-end;gap:12px;flex-wrap:wrap;margin-bottom:10px}
.plan-val{font-size:26px;font-weight:700}.plan-of{font-size:13px;color:#94a3b8;margin-bottom:4px}
.plan-pct{font-size:14px;font-weight:700;margin-bottom:4px}
.plan-pct.ok{color:#16a34a}.plan-pct.warn{color:#d97706}.plan-pct.bad{color:#cc0000}
.plan-bar-wrap{height:8px;background:#f1f5f9;border-radius:4px;margin-bottom:8px;overflow:hidden}
.plan-bar{height:8px;border-radius:4px;transition:width .6s}
.plan-bar.ok{background:#16a34a}.plan-bar.warn{background:#d97706}.plan-bar.bad{background:#cc0000}
.plan-pace{font-size:11px;color:#64748b}.plan-meta{font-size:11px;color:#94a3b8;margin-top:4px}
.flow{background:#fff;border-radius:10px;padding:14px;box-shadow:0 1px 3px rgba(0,0,0,.07)}
.flow-row{display:grid;grid-template-columns:22px 1fr auto;align-items:center;gap:8px;padding:7px 0;border-bottom:1px solid #f1f5f9}
.flow-row:last-child{border-bottom:none}
.flow-dot{width:10px;height:10px;border-radius:50%;margin:auto}
.flow-name{font-size:13px;font-weight:600}.flow-sub{font-size:11px;color:#94a3b8}
.flow-val{font-size:13px;font-weight:600;text-align:right}
.flow-bar-wrap{grid-column:2/-1;height:4px;background:#f1f5f9;border-radius:2px;margin-top:3px}
.flow-bar{height:4px;border-radius:2px}
.sbas{background:#fff;border-radius:10px;box-shadow:0 1px 3px rgba(0,0,0,.07);overflow:hidden}
.sbas-row{display:flex;align-items:center;gap:10px;padding:11px 15px;border-bottom:1px solid #f8fafc}
.sbas-row:last-child{border-bottom:none}
.sbas-dot{width:9px;height:9px;border-radius:50%;flex-shrink:0}
.sbas-name{font-size:13px;color:#374151;flex:1}
.sbas-val{font-size:14px;font-weight:700;text-align:right}
.sbas-sub{font-size:11px;color:#94a3b8;text-align:right}
.hoy-card{background:linear-gradient(135deg,#1e293b 0%,#334155 100%);border-radius:10px;padding:14px 15px;color:#fff;box-shadow:0 1px 3px rgba(0,0,0,.1)}
.hoy-lbl{font-size:11px;opacity:.7;margin-bottom:6px;display:flex;align-items:center;gap:6px}
.live-dot{width:7px;height:7px;border-radius:50%;background:#22c55e;animation:pulse 1.4s infinite;display:inline-block}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}
.hoy-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:6px}
@media(min-width:420px){.hoy-grid{grid-template-columns:repeat(5,1fr)}}
.hoy-v{font-size:18px;font-weight:700}.hoy-s{font-size:10px;opacity:.65;margin-top:1px}
.error-box{background:#fee2e2;border:1px solid #fca5a5;border-radius:8px;padding:11px 14px;font-size:13px;color:#991b1b;margin-bottom:12px}
.stamp{font-size:11px;color:#94a3b8;text-align:center;margin-bottom:12px}
.countdown{font-size:11px;color:#94a3b8;text-align:center;margin-top:12px}
footer{text-align:center;font-size:11px;color:#b0bec5;padding:20px 14px 6px}
</style>
</head>
<body>
<header>
  <div class="logo-mark"><span>W</span></div>
  <div><div class="hdr-title">Würth — Resumen Operativo</div>
       <div class="hdr-sub">Reactor · MSPA · Snapshot</div></div>
  <div class="hdr-right">
    <div id="hdr-ts" style="margin-bottom:3px"></div>
    <button class="refresh-btn" onclick="manualRefresh()">&#8635; Actualizar</button>
  </div>
</header>
<div class="container">
  <div class="delay-note">&#9201; Snapshot — retraso máx. <b id="delay-min">5</b> min. Tiempo real solo desde red interna.</div>
  <div id="err-box" class="error-box" style="display:none"></div>
  <div class="stamp">Datos al <b id="stamp-ts">—</b> · Operativo: <b id="stamp-date">—</b></div>
  <div class="section">Hoy en vivo</div>
  <div class="hoy-card">
    <div class="hoy-lbl" id="hoy-lbl">—</div>
    <div class="hoy-grid">
      <div><div class="hoy-v" id="h-ped">—</div><div class="hoy-s">Pedidos</div></div>
      <div><div class="hoy-v" id="h-vend">—</div><div class="hoy-s">Vendedores</div></div>
      <div><div class="hoy-v" id="h-val">—</div><div class="hoy-s">Valor inf.</div></div>
      <div><div class="hoy-v" id="h-pvend">—</div><div class="hoy-s">Ped/vend</div></div>
      <div><div class="hoy-v" id="h-lin">—</div><div class="hoy-s">Lín/ped</div></div>
    </div>
  </div>
  <div class="section">Plan de ventas mensual</div>
  <div class="plan-card">
    <div class="plan-top">
      <div><div class="plan-val" id="plan-fact">—</div><div class="plan-of" id="plan-of">de —</div></div>
      <div><div class="plan-pct" id="plan-pct">—</div><div class="plan-pace" id="plan-pace"></div></div>
    </div>
    <div class="plan-bar-wrap"><div class="plan-bar" id="plan-bar" style="width:0"></div></div>
    <div class="plan-meta" id="plan-meta"></div>
  </div>
  <div class="section">Indicadores día anterior</div>
  <div class="cards c6">
    <div class="card"><div class="card-lbl">Pedidos</div><div class="card-val" id="r-pedidos">—</div></div>
    <div class="card"><div class="card-lbl">Vendedores</div><div class="card-val" id="r-vend">—</div></div>
    <div class="card"><div class="card-lbl">Valor informado</div><div class="card-val" id="r-valor">—</div></div>
    <div class="card"><div class="card-lbl">Ped / vendedor</div><div class="card-val" id="r-pedvend">—</div></div>
    <div class="card"><div class="card-lbl">Líneas / pedido</div><div class="card-val" id="r-lineas">—</div></div>
    <div class="card"><div class="card-lbl">Ticket promedio</div><div class="card-val" id="r-ticket">—</div></div>
  </div>
  <div class="section">Flujo del día anterior</div>
  <div class="flow" id="flow-section"><div style="padding:10px;color:#94a3b8;font-size:13px">Sin datos.</div></div>
  <div class="section">Facturación MSPA</div>
  <div class="cards c3">
    <div class="card"><div class="card-lbl">Facturado</div><div class="card-val red" id="m-venta">—</div><div class="card-sub" id="m-ords">—</div></div>
    <div class="card"><div class="card-lbl">% Facturado</div><div class="card-val" id="m-pct">—</div></div>
    <div class="card"><div class="card-lbl">Líneas fact.</div><div class="card-val" id="m-pos">—</div></div>
  </div>
  <div class="section">Estado actual MSPA</div>
  <div class="sbas" id="sbas-section"></div>
  <div class="countdown" id="countdown"></div>
</div>
<footer>Würth Argentina · Snapshot automático · Sin VPN</footer>
<script>
if('serviceWorker' in navigator){navigator.serviceWorker.register('sw.js').catch(()=>{});}
const JSON_URL='snapshot.json';
let _nextRefresh=0,_interval=300;
function fmtN(v,dec=0){
  if(v==null||v===''||isNaN(Number(v)))return '—';
  return Number(v).toLocaleString('es-AR',{minimumFractionDigits:dec,maximumFractionDigits:dec});
}
function fmtK(v){
  if(v==null||v===''||isNaN(Number(v)))return '—';
  const n=Number(v);
  if(Math.abs(n)>=1e9)return '$'+fmtN(n/1e9,2)+'B';
  if(Math.abs(n)>=1e6)return '$'+fmtN(n/1e6,1)+'M';
  if(Math.abs(n)>=1e3)return '$'+fmtN(n/1e3,1)+'K';
  return '$'+fmtN(n,0);
}
function set(id,v){const e=document.getElementById(id);if(e)e.textContent=v;}
function setH(id,h){const e=document.getElementById(id);if(e)e.innerHTML=h;}
async function load(){
  try{
    const res=await fetch(JSON_URL+'?v='+Date.now());
    if(!res.ok)throw new Error('HTTP '+res.status);
    render(await res.json());
  }catch(e){
    const eb=document.getElementById('err-box');eb.textContent='Error: '+e.message;eb.style.display='';
  }
}
function manualRefresh(){document.getElementById('hdr-ts').textContent='Actualizando…';load();_nextRefresh=Date.now()+_interval*1000;}
function render(d){
  const r=d.reactor||{},m=d.mspa||{},ts2=d.today_summary||{};
  _interval=d.ftp_interval_secs||300;_nextRefresh=Date.now()+_interval*1000;
  const ts=d.snapshot_ts||'';
  set('stamp-ts',ts);set('hdr-ts',ts?'Al '+ts:'');
  set('stamp-date',r.target_date_display||'—');
  document.getElementById('delay-min').textContent=Math.round(_interval/60);
  const live=ts2.is_today!==false;
  const dp=ts2.date?ts2.date.split('-').reverse().join('/'):'';
  setH('hoy-lbl',live?'Hoy '+dp+' — EN VIVO <span class="live-dot"></span>':'Último día hábil '+dp);
  set('h-ped',fmtN(ts2.pedidos,0));set('h-vend',fmtN(ts2.vendedores,0));
  set('h-val',fmtK(ts2.valor));set('h-pvend',fmtN(ts2.avg_ped_vend,1));set('h-lin',fmtN(ts2.avg_lineas,1));
  const pv=m.plan_ventas||{};
  if(pv.plan_total){
    const pct=pv.pct_plan||0,cls=pct>=95?'ok':pct>=70?'warn':'bad';
    set('plan-fact',fmtK(pv.fact_acum));set('plan-of','de '+fmtK(pv.plan_total));
    setH('plan-pct','<span class="'+cls+'">'+fmtN(pct,1)+'%</span>');
    const meta=r.meta||{},wd=meta.curr_wd||0,el=meta.dias_elapsed||0;
    const paceExp=wd>0?Math.min(el/wd*100,100):0;
    const gap=paceExp>0?(pct-paceExp).toFixed(1):null;
    set('plan-pace',gap!=null?(gap>=0?'▲ '+gap+' pts sobre ritmo':'▼ '+Math.abs(gap)+' pts por debajo'):'');
    const bar=document.getElementById('plan-bar');bar.className='plan-bar '+cls;bar.style.width=Math.min(pct,100)+'%';
    set('plan-meta',el&&wd?'Día hábil '+el+' de '+wd+' · Restante: '+fmtK(pv.plan_total-pv.fact_acum):'');
  }
  set('r-pedidos',fmtN(r.pedidos,0));set('r-vend',fmtN(r.vendedores,0));set('r-valor',fmtK(r.valor));
  set('r-pedvend',r.pedidos&&r.vendedores?fmtN(r.pedidos/r.vendedores,1):'—');
  set('r-lineas',fmtN(r.avg_lineas,1));
  set('r-ticket',r.pedidos&&r.valor?fmtK(r.valor/r.pedidos):'—');
  const bs=r.by_status||{};
  const COL={1:'#3b82f6',2:'#22c55e',3:'#f59e0b',4:'#ef4444',5:'#8b5cf6'};
  const items=Object.entries(bs).map(([id,v])=>({id:+id,name:v.name||'Estado '+id,cnt:v.cnt,val:v.val}));
  items.sort((a,b)=>b.val-a.val);
  const maxV=Math.max(...items.map(f=>f.val||0),1);
  const flowSec=document.getElementById('flow-section');
  flowSec.innerHTML=items.length?items.map(f=>{
    const pct=Math.round((f.val||0)/maxV*100),col=COL[f.id]||'#94a3b8';
    return'<div class="flow-row"><div><div class="flow-dot" style="background:'+col+'"></div></div>'+
      '<div><div class="flow-name">'+f.name+'</div><div class="flow-sub">'+fmtN(f.cnt,0)+' pedidos</div>'+
      '<div class="flow-bar-wrap"><div class="flow-bar" style="width:'+pct+'%;background:'+col+'"></div></div></div>'+
      '<div class="flow-val">'+fmtK(f.val)+'</div></div>';
  }).join(''):'<div style="padding:10px;color:#94a3b8;font-size:13px">Sin datos de flujo.</div>';
  const venta=m.venta||{};
  const pctF=r.valor>0?(venta.val||0)/r.valor*100:0;
  set('m-venta',fmtK(venta.val));set('m-ords',fmtN(venta.ords,0)+' ped · '+fmtN(venta.pos,0)+' lín');
  set('m-pct',pctF>0?fmtN(pctF,1)+'%':'—');set('m-pos',fmtN(venta.pos,0));
  const SBAS=[
    {key:'backorders',label:'Backorders (Plazos viejos)',color:'#f59e0b'},
    {key:'bloqueados',label:'Bloqueados Límite Crédito',color:'#ef4444'},
    {key:'neg_status',label:'Bloqueados (Status < −1)',color:'#ef4444'},
    {key:'futuros',label:'Pedidos Abiertos (Futuros)',color:'#3b82f6'},
    {key:'produccion',label:'Producción Abierta',color:'#8b5cf6'},
    {key:'remitos',label:'Remitos / Facturas Abiertas',color:'#64748b'},
    {key:'venta',label:'Venta del Día',color:'#22c55e'},
  ];
  document.getElementById('sbas-section').innerHTML=SBAS.map(s=>{
    const v=m[s.key]||{ords:0,pos:0,val:0};
    return'<div class="sbas-row"><div class="sbas-dot" style="background:'+s.color+'"></div>'+
      '<div class="sbas-name">'+s.label+'</div>'+
      '<div><div class="sbas-val">'+fmtK(v.val)+'</div>'+
      '<div class="sbas-sub">'+fmtN(v.ords,0)+' ped · '+fmtN(v.pos,0)+' lín</div></div></div>';
  }).join('');
  const eb=document.getElementById('err-box');
  const errs=[d.reactor_error&&'Reactor: '+d.reactor_error,d.mspa_error&&'MSPA: '+d.mspa_error].filter(Boolean);
  if(errs.length){eb.textContent='⚠ '+errs.join(' · ');eb.style.display='';}
  else eb.style.display='none';
}
function tick(){
  const secs=Math.max(0,Math.round((_nextRefresh-Date.now())/1000));
  if(secs===0&&_nextRefresh>0){_nextRefresh=Date.now()+_interval*1000;load();}
  const m2=Math.floor(secs/60),s2=secs%60;
  const cd=document.getElementById('countdown');
  if(cd)cd.textContent=secs>0?'Próxima actualización en '+m2+':'+String(s2).padStart(2,'0'):'Actualizando…';
}
load();setInterval(tick,1000);
</script>
</body></html>"""


def _build_snapshot_json(data: dict, interval_secs: int) -> bytes:
    r = data.get("reactor") or {}
    m = data.get("mspa") or {}
    snapshot = {
        "snapshot_ts":       datetime.now().strftime("%d/%m/%Y %H:%M"),
        "ftp_interval_secs": interval_secs,
        "timestamp":         data.get("timestamp"),
        "reactor": {
            "target_date":         r.get("target_date"),
            "target_date_display": r.get("target_date_display"),
            "pedidos":             r.get("pedidos"),
            "vendedores":          r.get("vendedores"),
            "valor":               r.get("valor"),
            "lineas":              r.get("lineas"),
            "avg_lineas":          r.get("avg_lineas"),
            "avg_ped_vend":        r.get("avg_ped_vend"),
            "by_status":           r.get("by_status"),
            "meta":                r.get("meta"),
        },
        "mspa": {
            "venta":       m.get("venta"),
            "backorders":  m.get("backorders"),
            "bloqueados":  m.get("bloqueados"),
            "neg_status":  m.get("neg_status"),
            "futuros":     m.get("futuros"),
            "produccion":  m.get("produccion"),
            "remitos":     m.get("remitos"),
            "plan_ventas": m.get("plan_ventas"),
        },
        "today_summary":  data.get("today_summary"),
        "reactor_error":  data.get("reactor_error"),
        "mspa_error":     data.get("mspa_error"),
    }
    return json.dumps(snapshot, ensure_ascii=False, default=str).encode("utf-8")


def _ftp_upload(json_bytes, html_bytes, sw_bytes, manifest_bytes):
    ftp = ftplib.FTP()
    ftp.connect(FTP_HOST, 21, timeout=20)
    ftp.login(FTP_USER, FTP_PASS)
    if FTP_PATH and FTP_PATH not in ("/", ""):
        parts = FTP_PATH.strip("/").split("/")
        ftp.cwd("/")
        for part in parts:
            try: ftp.cwd(part)
            except ftplib.error_perm: ftp.mkd(part); ftp.cwd(part)
    ftp.storbinary("STOR snapshot.json", io.BytesIO(json_bytes))
    ftp.storbinary("STOR index.html",    io.BytesIO(html_bytes))
    ftp.storbinary("STOR sw.js",         io.BytesIO(sw_bytes))
    ftp.storbinary("STOR manifest.json", io.BytesIO(manifest_bytes))
    ftp.storbinary("STOR icon-192.png",  io.BytesIO(_ICON_192))
    ftp.storbinary("STOR icon-512.png",  io.BytesIO(_ICON_512))
    ftp.quit()


def _snapshot_loop(get_data_fn):
    print(f"  [FTP] Job activo — host={FTP_HOST} path={FTP_PATH} cada {FTP_INTERVAL}s", flush=True)
    while True:
        try:
            data       = get_data_fn()
            json_bytes = _build_snapshot_json(data, FTP_INTERVAL)
            html_bytes = _VIEWER_HTML.encode("utf-8")
            sw_bytes   = _SW_JS.encode("utf-8")
            man_bytes  = json.dumps(_MANIFEST_DICT, ensure_ascii=False).encode("utf-8")
            _ftp_upload(json_bytes, html_bytes, sw_bytes, man_bytes)
            print(f"  [FTP] OK — {datetime.now().strftime('%H:%M:%S')} ({len(json_bytes)}b)", flush=True)
        except Exception as e:
            print(f"  [FTP] Error: {e}", flush=True)
        time.sleep(FTP_INTERVAL)


def start_snapshot_job(get_data_fn):
    """Inicia el FTP snapshot job en un thread daemon.
    Solo se activa si FTP_ENABLED=1 y FTP_HOST esta configurado.
    """
    print(f"  [FTP] FTP_ENABLED={FTP_ENABLED} FTP_HOST={FTP_HOST!r}", flush=True)
    if not FTP_ENABLED:
        print("  [FTP] Desactivado. Setear FTP_ENABLED=1 para activar.", flush=True)
        return
    if not FTP_HOST or not FTP_USER or not FTP_PASS:
        print("  [FTP] Faltan FTP_HOST / FTP_USER / FTP_PASS. Job no iniciado.", flush=True)
        return
    threading.Thread(target=_snapshot_loop, args=(get_data_fn,), daemon=True).start()

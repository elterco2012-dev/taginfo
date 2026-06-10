"""
ftp_snapshot.py — Sube un snapshot JSON + viewer HTML al servidor FTP.
Corre como daemon thread iniciado por dashboard.py.
SOLO LECTURA: nunca modifica la base de datos.
"""
import os, json, time, ftplib, threading, hashlib, hmac, datetime, zlib, struct, io
from concurrent.futures import ThreadPoolExecutor, TimeoutError as _FuturesTimeout

# ── Configuración por variables de entorno ──────────────────────────────────
FTP_HOST     = os.environ.get("FTP_HOST", "")
FTP_USER     = os.environ.get("FTP_USER", "")
FTP_PASS     = os.environ.get("FTP_PASS", "")
FTP_PATH     = os.environ.get("FTP_PATH", "/")
FTP_INTERVAL = int(os.environ.get("FTP_INTERVAL", "300"))
FTP_ENABLED  = os.environ.get("FTP_ENABLED", "0") == "1"
FTP_AUTH_USER = os.environ.get("FTP_AUTH_USER", "wurth")
FTP_AUTH_PASS = os.environ.get("FTP_AUTH_PASS", "")

# ── HTML del viewer móvil (PWA Fortune-500) ─────────────────────────────────
_VIEWER_HTML = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#c8102e">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="Ventas">
<link rel="manifest" href="manifest.json">
<link rel="apple-touch-icon" href="icon-192.png">
<title>Ventas Würth</title>
<style>
:root{
  --red:#c8102e;--dark:#111;--card:#1a1a1a;--border:#2a2a2a;
  --text:#f0f0f0;--muted:#888;--green:#22c55e;--amber:#f59e0b;
  --blue:#3b82f6;--spark:#c8102e;
}
*{box-sizing:border-box;margin:0;padding:0;-webkit-tap-highlight-color:transparent}
html,body{height:100%;background:#0d0d0d;color:var(--text);font-family:-apple-system,BlinkMacSystemFont,'SF Pro Display',sans-serif;overscroll-behavior:none}
body{display:flex;flex-direction:column;max-width:430px;margin:0 auto;padding:env(safe-area-inset-top) env(safe-area-inset-right) env(safe-area-inset-bottom) env(safe-area-inset-left)}

/* Header */
.hdr{display:flex;align-items:center;justify-content:space-between;padding:16px 20px 8px;gap:8px}
.hdr-left{display:flex;flex-direction:column;gap:2px}
.greeting{font-size:13px;color:var(--muted);font-weight:400}
.hdr-title{font-size:20px;font-weight:700;letter-spacing:-.3px}
.logo{width:36px;height:36px;background:var(--red);border-radius:8px;display:flex;align-items:center;justify-content:center;font-weight:900;font-size:13px;color:#fff;letter-spacing:-.5px;flex-shrink:0}

/* Refresh btn */
.refresh-btn{background:none;border:1px solid var(--border);color:var(--muted);border-radius:20px;padding:6px 14px;font-size:12px;cursor:pointer;display:flex;align-items:center;gap:6px;transition:all .2s}
.refresh-btn:active{transform:scale(.96)}
.refresh-btn.spinning svg{animation:spin .7s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}

/* Timestamp */
.ts-bar{padding:2px 20px 10px;font-size:11px;color:var(--muted);display:flex;align-items:center;gap:8px}
.ts-dot{width:6px;height:6px;border-radius:50%;background:var(--green);flex-shrink:0}
.ts-dot.stale{background:var(--amber)}
.ts-dot.old{background:#666}

/* Quota hero */
.quota-hero{margin:4px 16px 12px;background:var(--card);border:1px solid var(--border);border-radius:16px;padding:16px 18px}
.quota-top{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px}
.quota-label{font-size:12px;color:var(--muted);font-weight:500;text-transform:uppercase;letter-spacing:.5px}
.quota-pct{font-size:36px;font-weight:800;letter-spacing:-1px;line-height:1}
.quota-pct span{font-size:16px;font-weight:500;color:var(--muted)}
.quota-sub{font-size:12px;color:var(--muted);margin-top:2px}
.quota-bar-wrap{height:8px;background:#222;border-radius:4px;overflow:hidden}
.quota-bar-fill{height:100%;border-radius:4px;background:linear-gradient(90deg,#c8102e,#ff4d6d);transition:width 1.2s cubic-bezier(.4,0,.2,1)}
.quota-bar-fill.done{background:linear-gradient(90deg,#16a34a,#22c55e)}

/* Sparkline */
.spark-row{display:flex;gap:10px;margin:4px 16px 12px}
.spark-card{flex:1;background:var(--card);border:1px solid var(--border);border-radius:14px;padding:12px 14px;min-width:0}
.spark-label{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.4px;margin-bottom:4px}
.spark-val{font-size:19px;font-weight:700;letter-spacing:-.4px;margin-bottom:6px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.spark-svg{width:100%;height:32px;display:block}

/* KPI grid */
.kpi-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;padding:0 16px 10px}
.kpi{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:14px 16px}
.kpi-label{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.4px;margin-bottom:6px}
.kpi-val{font-size:22px;font-weight:700;letter-spacing:-.5px;line-height:1.1}
.kpi-val.mono{font-variant-numeric:tabular-nums}
.kpi-sub{font-size:11px;color:var(--muted);margin-top:4px}

/* Delta badge */
.delta{display:inline-flex;align-items:center;gap:3px;font-size:11px;font-weight:600;padding:2px 7px;border-radius:20px;margin-left:6px;vertical-align:middle}
.delta.up{background:rgba(34,197,94,.15);color:#22c55e}
.delta.down{background:rgba(239,68,68,.15);color:#ef4444}
.delta.neutral{background:rgba(156,163,175,.1);color:#9ca3af}

/* Toast */
.toast{position:fixed;bottom:calc(env(safe-area-inset-bottom)+24px);left:50%;transform:translateX(-50%) translateY(20px);background:#333;color:#fff;padding:10px 20px;border-radius:24px;font-size:13px;opacity:0;transition:all .3s;pointer-events:none;white-space:nowrap;z-index:999}
.toast.show{opacity:1;transform:translateX(-50%) translateY(0)}

/* Celebration overlay */
.celeb{position:fixed;inset:0;z-index:9999;pointer-events:none;display:none}
.celeb.active{display:block}
.celeb-msg{position:absolute;top:50%;left:50%;transform:translate(-50%,-60%);text-align:center;animation:popIn .5s cubic-bezier(.34,1.56,.64,1) forwards}
.celeb-emoji{font-size:72px;display:block;margin-bottom:8px}
.celeb-text{font-size:22px;font-weight:800;color:#ffd700;text-shadow:0 2px 20px rgba(0,0,0,.8)}
.celeb-sub{font-size:14px;color:#fff;opacity:.8;margin-top:4px}
@keyframes popIn{from{opacity:0;transform:translate(-50%,-60%) scale(.5)}to{opacity:1;transform:translate(-50%,-60%) scale(1)}}
.confetti-piece{position:absolute;width:8px;height:8px;border-radius:2px;animation:fall linear forwards}
@keyframes fall{0%{transform:translateY(-20px) rotate(0deg);opacity:1}100%{transform:translateY(100vh) rotate(720deg);opacity:0}}

/* Pull-to-refresh indicator */
.ptr-indicator{text-align:center;padding:8px;font-size:12px;color:var(--muted);height:0;overflow:hidden;transition:height .2s}
.ptr-indicator.visible{height:32px}

/* Scrollable content */
.scroll{flex:1;overflow-y:auto;-webkit-overflow-scrolling:touch;padding-bottom:24px}
</style>
</head>
<body>
<div class="ptr-indicator" id="ptr">↓ Actualizando…</div>

<div class="hdr">
  <div class="hdr-left">
    <span class="greeting" id="greeting"></span>
    <span class="hdr-title">Ventas Würth</span>
  </div>
  <div style="display:flex;align-items:center;gap:10px">
    <button class="refresh-btn" id="refreshBtn" onclick="doRefresh()">
      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/></svg>
      Actualizar
    </button>
    <div class="logo">W</div>
  </div>
</div>

<div class="ts-bar">
  <div class="ts-dot" id="tsDot"></div>
  <span id="tsText">Cargando…</span>
</div>

<div class="scroll" id="scrollArea">
  <!-- Quota hero -->
  <div class="quota-hero" id="quotaHero" style="display:none">
    <div class="quota-top">
      <div>
        <div class="quota-label">Plan del mes</div>
        <div class="quota-sub" id="quotaSub"></div>
      </div>
      <div style="text-align:right">
        <div class="quota-pct"><span id="quotaPct">0</span><span>%</span></div>
      </div>
    </div>
    <div class="quota-bar-wrap"><div class="quota-bar-fill" id="quotaBar" style="width:0%"></div></div>
  </div>

  <!-- Sparklines row -->
  <div class="spark-row" id="sparkRow" style="display:none">
    <div class="spark-card">
      <div class="spark-label">Pedidos / día</div>
      <div class="spark-val" id="sparkPedVal">—</div>
      <svg class="spark-svg" id="sparkPed" viewBox="0 0 100 32" preserveAspectRatio="none"></svg>
    </div>
    <div class="spark-card">
      <div class="spark-label">Ventas / día</div>
      <div class="spark-val" id="sparkVenVal">—</div>
      <svg class="spark-svg" id="sparkVen" viewBox="0 0 100 32" preserveAspectRatio="none"></svg>
    </div>
  </div>

  <!-- KPI grid -->
  <div class="kpi-grid" id="kpiGrid" style="display:none">
    <div class="kpi">
      <div class="kpi-label">Venta hoy</div>
      <div class="kpi-val mono" id="kVenta">—</div>
      <div class="kpi-sub" id="kVentaDelta"></div>
    </div>
    <div class="kpi">
      <div class="kpi-label">Pedidos hoy</div>
      <div class="kpi-val" id="kPedidos">—</div>
      <div class="kpi-sub" id="kPedidosDelta"></div>
    </div>
    <div class="kpi">
      <div class="kpi-label">Vendedores</div>
      <div class="kpi-val" id="kVendedores">—</div>
      <div class="kpi-sub" id="kVendedoresDelta"></div>
    </div>
    <div class="kpi">
      <div class="kpi-label">Líns / pedido</div>
      <div class="kpi-val" id="kLineas">—</div>
      <div class="kpi-sub"></div>
    </div>
    <div class="kpi">
      <div class="kpi-label">Backorders</div>
      <div class="kpi-val" id="kBack">—</div>
      <div class="kpi-sub"></div>
    </div>
    <div class="kpi">
      <div class="kpi-label">Remitos</div>
      <div class="kpi-val" id="kRemitos">—</div>
      <div class="kpi-sub"></div>
    </div>
  </div>
</div>

<!-- Toast -->
<div class="toast" id="toast"></div>

<!-- Celebration overlay -->
<div class="celeb" id="celeb">
  <div class="celeb-msg">
    <span class="celeb-emoji">🏆</span>
    <div class="celeb-text">¡Meta alcanzada!</div>
    <div class="celeb-sub">El equipo superó el plan del mes</div>
  </div>
  <canvas id="confettiCanvas" style="position:absolute;inset:0;width:100%;height:100%"></canvas>
</div>

<script>
const INTERVAL = __INTERVAL__;
let _data = null;
let _prevData = null;
let _refreshTimer = null;

// ── Greeting ──────────────────────────────────────────────────────────────
function setGreeting(){
  const h = new Date().getHours();
  const g = h < 12 ? 'Buenos días' : h < 19 ? 'Buenas tardes' : 'Buenas noches';
  document.getElementById('greeting').textContent = g + ', Daniel';
}
setGreeting();

// ── Format helpers ────────────────────────────────────────────────────────
function fmtARS(v){
  if(v===null||v===undefined) return '—';
  return '$' + Number(v).toLocaleString('es-AR',{maximumFractionDigits:0});
}
function fmtNum(v){
  if(v===null||v===undefined) return '—';
  return Number(v).toLocaleString('es-AR');
}
function deltaHtml(cur, prev, isMoney){
  if(prev===null||prev===undefined||cur===null||cur===undefined) return '';
  const diff = cur - prev;
  if(diff===0) return '';
  const sign = diff>0?'▲':'▼';
  const cls = diff>0?'up':'down';
  const val = isMoney ? fmtARS(Math.abs(diff)) : fmtNum(Math.abs(diff));
  return `<span class="delta ${cls}">${sign} ${val} vs ayer</span>`;
}

// ── Count-up animation ────────────────────────────────────────────────────
function countUp(el, target, duration, fmt){
  const start = performance.now();
  const from = 0;
  function step(now){
    const p = Math.min((now-start)/duration, 1);
    const ease = 1-Math.pow(1-p,3);
    const cur = from + (target-from)*ease;
    el.textContent = fmt(cur);
    if(p<1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}

// ── Sparkline SVG ─────────────────────────────────────────────────────────
function drawSpark(svgEl, values){
  if(!values||values.length<2){svgEl.innerHTML='';return;}
  const mn=Math.min(...values), mx=Math.max(...values);
  const range=mx-mn||1;
  const w=100, h=32, pad=2;
  const pts=values.map((v,i)=>{
    const x=pad+(w-2*pad)*i/(values.length-1);
    const y=pad+(h-2*pad)*(1-(v-mn)/range);
    return `${x},${y}`;
  });
  const last=pts[pts.length-1].split(',');
  svgEl.innerHTML=
    `<polyline points="${pts.join(' ')}" fill="none" stroke="var(--spark)" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>` +
    `<circle cx="${last[0]}" cy="${last[1]}" r="2.5" fill="var(--spark)"/>`;
}

// ── Relative time ─────────────────────────────────────────────────────────
function relTime(ts){
  if(!ts) return '';
  const d=new Date(ts), now=new Date();
  const diff=Math.round((now-d)/1000);
  if(diff<5) return 'ahora mismo';
  if(diff<60) return `hace ${diff}s`;
  const m=Math.round(diff/60);
  if(m<60) return `hace ${m} min`;
  const hr=Math.round(m/60);
  return `hace ${hr}h`;
}

// ── Freshness dot ─────────────────────────────────────────────────────────
function freshnessClass(ts){
  if(!ts) return 'old';
  const age=(Date.now()-new Date(ts).getTime())/1000;
  if(age < INTERVAL*1.5) return '';
  if(age < INTERVAL*3) return 'stale';
  return 'old';
}

// ── Celebration ───────────────────────────────────────────────────────────
function maybeCelebrate(pct){
  if(pct<100) return;
  const key='celeb_'+new Date().toDateString();
  if(localStorage.getItem(key)) return;
  localStorage.setItem(key,'1');
  const overlay=document.getElementById('celeb');
  overlay.classList.add('active');
  launchConfetti();
  setTimeout(()=>overlay.classList.remove('active'), 4000);
}
function launchConfetti(){
  const canvas=document.getElementById('confettiCanvas');
  const ctx=canvas.getContext('2d');
  canvas.width=window.innerWidth; canvas.height=window.innerHeight;
  const colors=['#ffd700','#ff4d6d','#22c55e','#3b82f6','#f59e0b','#c8102e'];
  const pieces=Array.from({length:80},()=>({
    x:Math.random()*canvas.width, y:-10,
    r:Math.random()*4+3,
    c:colors[Math.floor(Math.random()*colors.length)],
    sp:Math.random()*4+2,
    ang:Math.random()*360,
    rot:Math.random()*6-3
  }));
  let frame=0;
  function draw(){
    ctx.clearRect(0,0,canvas.width,canvas.height);
    pieces.forEach(p=>{
      p.y+=p.sp; p.ang+=p.rot;
      ctx.save();ctx.translate(p.x,p.y);ctx.rotate(p.ang*Math.PI/180);
      ctx.fillStyle=p.c;ctx.fillRect(-p.r,-p.r,p.r*2,p.r*2);
      ctx.restore();
    });
    frame++;
    if(frame<120) requestAnimationFrame(draw);
  }
  draw();
}

// ── Render ────────────────────────────────────────────────────────────────
function render(d, prev){
  if(!d) return;

  // Timestamp
  const dot=document.getElementById('tsDot');
  const tsText=document.getElementById('tsText');
  dot.className='ts-dot '+freshnessClass(d.ts);
  tsText.textContent=(d.ts?relTime(d.ts):'—') + (d.comp_date?' · '+d.comp_date:'');

  // Quota hero
  const pct=parseFloat(d.plan_pct)||0;
  const hero=document.getElementById('quotaHero');
  hero.style.display='';
  document.getElementById('quotaSub').textContent=
    (d.plan_fact?fmtARS(d.plan_fact):'')+' / '+(d.plan_total?fmtARS(d.plan_total):'');
  const bar=document.getElementById('quotaBar');
  const pctEl=document.getElementById('quotaPct');
  bar.className='quota-bar-fill'+(pct>=100?' done':'');
  // Animate bar + count-up
  requestAnimationFrame(()=>{
    bar.style.width=Math.min(pct,100)+'%';
  });
  countUp(pctEl, pct, 1200, v=>v.toFixed(1));
  maybeCelebrate(pct);

  // Sparklines
  const sparkRow=document.getElementById('sparkRow');
  if(d.spark_pedidos||d.spark_ventas){
    sparkRow.style.display='';
    drawSpark(document.getElementById('sparkPed'), d.spark_pedidos);
    drawSpark(document.getElementById('sparkVen'), d.spark_ventas);
    // Last values
    const lp=(d.spark_pedidos||[]).slice(-1)[0];
    const lv=(d.spark_ventas||[]).slice(-1)[0];
    const spv=document.getElementById('sparkPedVal');
    const svv=document.getElementById('sparkVenVal');
    if(lp!=null) countUp(spv,lp,900,v=>Math.round(v).toLocaleString('es-AR'));
    if(lv!=null) countUp(svv,lv,900,v=>fmtARS(v));
  } else {
    sparkRow.style.display='none';
  }

  // KPI grid
  document.getElementById('kpiGrid').style.display='';
  // Venta hoy
  const vEl=document.getElementById('kVenta');
  if(d.venta_dia!=null) countUp(vEl,d.venta_dia,1000,fmtARS);
  else vEl.textContent='—';
  document.getElementById('kVentaDelta').innerHTML=
    prev?deltaHtml(d.venta_dia,prev.venta_dia,true):'';
  // Pedidos
  const pEl=document.getElementById('kPedidos');
  if(d.pedidos!=null) countUp(pEl,d.pedidos,800,v=>Math.round(v).toString());
  else pEl.textContent='—';
  document.getElementById('kPedidosDelta').innerHTML=
    prev?deltaHtml(d.pedidos,prev.pedidos,false):'';
  // Vendedores
  const vdEl=document.getElementById('kVendedores');
  if(d.vendedores!=null) countUp(vdEl,d.vendedores,700,v=>Math.round(v).toString());
  else vdEl.textContent='—';
  document.getElementById('kVendedoresDelta').innerHTML=
    prev?deltaHtml(d.vendedores,prev.vendedores,false):'';
  // Líneas
  const lEl=document.getElementById('kLineas');
  if(d.avg_lineas!=null) countUp(lEl,d.avg_lineas,700,v=>v.toFixed(1));
  else lEl.textContent='—';
  // Backorders
  document.getElementById('kBack').textContent=d.backorders!=null?fmtNum(d.backorders):'—';
  // Remitos
  document.getElementById('kRemitos').textContent=d.remitos!=null?fmtNum(d.remitos):'—';
}

// ── Fetch & load ──────────────────────────────────────────────────────────
async function loadData(){
  try{
    const r=await fetch('snapshot.json?_='+Date.now());
    if(!r.ok) throw new Error('HTTP '+r.status);
    const d=await r.json();
    _prevData=_data;
    _data=d;
    render(_data,_prevData);
  }catch(e){
    showToast('Error al actualizar: '+e.message);
  }
}

function showToast(msg){
  const t=document.getElementById('toast');
  t.textContent=msg; t.classList.add('show');
  setTimeout(()=>t.classList.remove('show'),3000);
}

function doRefresh(){
  const btn=document.getElementById('refreshBtn');
  btn.classList.add('spinning');
  loadData().then(()=>{
    btn.classList.remove('spinning');
    showToast('Actualizado');
  }).catch(()=>btn.classList.remove('spinning'));
}

// ── Pull-to-refresh ───────────────────────────────────────────────────────
let _ptStart=0, _ptActive=false;
const scrollArea=document.getElementById('scrollArea');
scrollArea.addEventListener('touchstart',e=>{
  if(scrollArea.scrollTop===0) _ptStart=e.touches[0].clientY;
},{ passive:true });
scrollArea.addEventListener('touchmove',e=>{
  if(!_ptStart) return;
  const dy=e.touches[0].clientY-_ptStart;
  if(dy>50&&!_ptActive){
    _ptActive=true;
    document.getElementById('ptr').classList.add('visible');
  }
},{ passive:true });
scrollArea.addEventListener('touchend',()=>{
  if(_ptActive){ _ptActive=false; document.getElementById('ptr').classList.remove('visible'); doRefresh(); }
  _ptStart=0;
},{ passive:true });

// ── Auto-refresh timer ────────────────────────────────────────────────────
function scheduleRefresh(){
  clearTimeout(_refreshTimer);
  _refreshTimer=setTimeout(()=>{ loadData().then(scheduleRefresh); }, INTERVAL*1000);
}

// ── Boot ──────────────────────────────────────────────────────────────────
loadData().then(scheduleRefresh);

// Service Worker
if('serviceWorker' in navigator){
  navigator.serviceWorker.register('sw.js').catch(()=>{});
}
</script>
</body>
</html>
"""

# ── PHP / htaccess / manifest / sw files ────────────────────────────────────
_INDEX_PHP = r"""<?php
$user = $_SERVER['PHP_AUTH_USER'] ?? '';
$pass = $_SERVER['PHP_AUTH_PASS'] ?? '';
$ok_user = getenv('FTP_AUTH_USER') ?: 'wurth';
$ok_hash = getenv('FTP_AUTH_HASH') ?: '';  // SHA-256 hex of password

function safe_hash($s){ return hash('sha256', $s); }

if(!$ok_hash || $user !== $ok_user || !hash_equals($ok_hash, safe_hash($pass))){
    header('WWW-Authenticate: Basic realm="Wurth Ventas"');
    header('HTTP/1.1 401 Unauthorized');
    exit('Acceso denegado');
}

$file = __DIR__ . '/snapshot.json';
if(!file_exists($file)){ http_response_code(503); exit('{"error":"no data"}'); }
header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');
readfile($file);
"""

_HTACCESS = """# Permitir lectura de snapshot.json (lo consume el viewer index.html)
<Files "snapshot.json">
    Require all granted
    Order allow,deny
    Allow from all
</Files>
# No cachear el snapshot para que el celular siempre vea datos frescos
<IfModule mod_headers.c>
    <Files "snapshot.json">
        Header set Cache-Control "no-store, no-cache, must-revalidate"
    </Files>
</IfModule>
"""

_MANIFEST = json.dumps({
    "name": "Ventas Würth",
    "short_name": "Ventas",
    "start_url": "./",
    "display": "standalone",
    "background_color": "#0d0d0d",
    "theme_color": "#c8102e",
    "icons": [
        {"src": "icon-192.png", "sizes": "192x192", "type": "image/png"},
        {"src": "icon-512.png", "sizes": "512x512", "type": "image/png"}
    ]
}, ensure_ascii=False, indent=2)

_SW_JS = r"""const CACHE='wurth-v2';
const ASSETS=['./','./manifest.json','./icon-192.png'];
self.addEventListener('install',e=>e.waitUntil(
  caches.open(CACHE).then(c=>c.addAll(ASSETS)).then(()=>self.skipWaiting())
));
self.addEventListener('activate',e=>e.waitUntil(
  caches.keys().then(ks=>Promise.all(ks.filter(k=>k!==CACHE).map(k=>caches.delete(k))))
    .then(()=>self.clients.claim())
));
self.addEventListener('fetch',e=>{
  if(e.request.url.includes('snapshot.json')){
    e.respondWith(fetch(e.request).catch(()=>new Response('{"error":"offline"}',{headers:{'Content-Type':'application/json'}})));
    return;
  }
  e.respondWith(caches.match(e.request).then(r=>r||fetch(e.request)));
});
"""

# ── PNG icon generator (pure Python, no PIL) ─────────────────────────────────
def _make_png(size):
    """Generate a red Würth-branded square PNG icon."""
    w = h = size
    # Red fill with white "W" letter approximated as pixel art
    pixels = []
    cx, cy = w//2, h//2
    for y in range(h):
        row = []
        for x in range(w):
            # Border
            border = max(size//32, 1)
            in_border = x<border or y<border or x>=w-border or y>=h-border
            if in_border:
                row.extend([0xA0,0x00,0x1A,255])  # dark red border
            else:
                # Draw a simple "W" in white
                # Normalize coords to -1..1
                nx = (x-cx)/(w*0.4)
                ny = (y-cy)/(h*0.4)
                in_w = False
                # W shape: two V shapes
                if abs(ny) < 0.9 and abs(nx) < 0.85:
                    # Left stroke of W
                    if abs(nx+0.6 + ny*0.5) < 0.07 and ny < 0.2:
                        in_w = True
                    # Right stroke of W
                    elif abs(nx-0.6 + ny*0.5) < 0.07 and ny < 0.2:
                        in_w = True
                    # Left-center stroke
                    elif abs(nx+0.2 - ny*0.5) < 0.07 and ny > -0.1:
                        in_w = True
                    # Right-center stroke
                    elif abs(nx-0.2 - ny*0.5) < 0.07 and ny > -0.1:
                        in_w = True
                if in_w:
                    row.extend([255,255,255,255])
                else:
                    row.extend([0xC8,0x10,0x2E,255])  # Würth red
        pixels.append(bytes(row))

    def png_chunk(name, data):
        c = zlib.crc32(name+data) & 0xFFFFFFFF
        return struct.pack('>I',len(data)) + name + data + struct.pack('>I',c)

    raw = b''
    for row in pixels:
        raw += b'\x00' + row  # filter type 0
    compressed = zlib.compress(raw, 9)

    chunks = (
        b'\x89PNG\r\n\x1a\n' +
        png_chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)) +
        png_chunk(b'IDAT', compressed) +
        png_chunk(b'IEND', b'')
    )
    return chunks

# ── Snapshot builder ──────────────────────────────────────────────────────────
def _build_snapshot_json(data, interval):
    """Extract relevant fields from get_cached_data() result into snapshot dict."""
    snap = {"ts": datetime.datetime.now().isoformat(), "interval": interval}
    try:
        # Plan mensual
        plan = data.get("plan") or {}
        snap["plan_pct"]   = plan.get("pct")
        snap["plan_fact"]  = plan.get("fact")
        snap["plan_total"] = plan.get("total")
        snap["target_date"]= plan.get("target_date")

        # Día actual
        hoy = data.get("hoy") or {}
        snap["venta_dia"]  = hoy.get("venta") or hoy.get("valor")
        snap["pedidos"]    = hoy.get("pedidos")
        snap["vendedores"] = hoy.get("vendedores")
        snap["avg_lineas"] = hoy.get("avg_lineas") or hoy.get("lineas")
        snap["backorders"] = hoy.get("backorders")
        snap["remitos"]    = hoy.get("remitos")

        # Comparativo ayer
        comp = data.get("comp") or data.get("ayer") or {}
        snap["d_pedidos"]   = comp.get("pedidos")
        snap["d_valor"]     = comp.get("venta") or comp.get("valor")
        snap["d_vendedores"]= comp.get("vendedores")
        snap["comp_date"]   = comp.get("fecha")

        # Sparklines (últimos N días)
        spark = data.get("spark") or data.get("sparklines") or {}
        snap["spark_pedidos"] = spark.get("pedidos")
        snap["spark_ventas"]  = spark.get("ventas") or spark.get("venta")

        # Fallbacks: try flat keys
        for k in ["venta_dia","pedidos","vendedores","avg_lineas","backorders","remitos",
                  "plan_pct","plan_fact","plan_total"]:
            if snap.get(k) is None and k in data:
                snap[k] = data[k]
    except Exception as e:
        snap["_error"] = str(e)
    return snap

# ── FTP uploader ──────────────────────────────────────────────────────────────
def _ftp_upload_bytes(ftp, remote_path, data_bytes):
    buf = io.BytesIO(data_bytes)
    ftp.storbinary(f"STOR {remote_path}", buf)

def _ftp_upload_text(ftp, remote_path, text):
    _ftp_upload_bytes(ftp, remote_path, text.encode("utf-8"))

def _ensure_dir(ftp, path):
    """Create remote directory tree if needed."""
    if path in ("/", ""):
        return
    parts = [p for p in path.split("/") if p]
    cur = ""
    for p in parts:
        cur += "/" + p
        try:
            ftp.cwd(cur)
        except ftplib.error_perm:
            try:
                ftp.mkd(cur)
            except Exception:
                pass

_DATA_TIMEOUT = 90  # segundos máximos esperando datos de la BD

def _snapshot_loop(get_data_fn, interval):
    """Main loop: build snapshot and upload every `interval` seconds."""
    print(f"[FTP] Job activo — host={FTP_HOST}  cada {interval}s", flush=True)
    _pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="ftp-data")
    while True:
        try:
            fut = _pool.submit(get_data_fn)
            try:
                data = fut.result(timeout=_DATA_TIMEOUT)
            except _FuturesTimeout:
                print(f"[FTP] Timeout obteniendo datos ({_DATA_TIMEOUT}s) — siguiente ciclo en {interval}s", flush=True)
                time.sleep(interval)
                continue
            snap = _build_snapshot_json(data, interval)
            snap_json = json.dumps(snap, ensure_ascii=False, default=str)

            with ftplib.FTP(FTP_HOST, FTP_USER, FTP_PASS, timeout=30) as ftp:
                ftp.set_pasv(True)
                _ensure_dir(ftp, FTP_PATH)
                ftp.cwd(FTP_PATH)

                # snapshot.json
                _ftp_upload_text(ftp, "snapshot.json", snap_json)

                # viewer HTML (replace interval placeholder)
                viewer = _VIEWER_HTML.replace("__INTERVAL__", str(interval))
                _ftp_upload_text(ftp, "index.html", viewer)

                # .htaccess SIEMPRE — pisa cualquier versión vieja que bloquee snapshot.json
                _ftp_upload_text(ftp, ".htaccess", _HTACCESS)

                # PHP proxy solo si hay auth configurada
                if FTP_AUTH_PASS:
                    _ftp_upload_text(ftp, "index.php", _INDEX_PHP)

                # manifest + sw
                _ftp_upload_text(ftp, "manifest.json", _MANIFEST)
                _ftp_upload_text(ftp, "sw.js", _SW_JS)

                # icons (only upload if they don't exist yet — save bandwidth)
                existing = ftp.nlst()
                if "icon-192.png" not in existing:
                    _ftp_upload_bytes(ftp, "icon-192.png", _make_png(192))
                if "icon-512.png" not in existing:
                    _ftp_upload_bytes(ftp, "icon-512.png", _make_png(512))

            now = datetime.datetime.now().strftime("%H:%M:%S")
            print(f"[FTP] OK — {now}", flush=True)
        except Exception as e:
            print(f"[FTP] Error: {e}", flush=True)

        time.sleep(interval)

# ── Public API ────────────────────────────────────────────────────────────────
def start_snapshot_job(get_data_fn):
    """
    Inicia el daemon thread FTP.
    get_data_fn: callable que retorna el dict de datos (get_cached_data en dashboard.py).
    Si FTP_ENABLED=0 o FTP_HOST vacío, imprime aviso y retorna sin iniciar.
    """
    if not FTP_ENABLED:
        print("[FTP] Deshabilitado (FTP_ENABLED != 1). Setear variables de entorno para activar.", flush=True)
        return
    if not FTP_HOST:
        print("[FTP] Sin host (FTP_HOST vacío). Snapshot FTP no iniciado.", flush=True)
        return
    t = threading.Thread(
        target=_snapshot_loop,
        args=(get_data_fn, FTP_INTERVAL),
        daemon=True,
        name="ftp-snapshot"
    )
    t.start()

"""
ftp_snapshot.py — Sube un snapshot JSON + viewer HTML al servidor FTP.
Corre como daemon thread iniciado por dashboard.py.
SOLO LECTURA: nunca modifica la base de datos.
"""
import os, json, time, ftplib, threading, hashlib, hmac, datetime, zlib, struct, io, base64
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

# ── Logo loader ──────────────────────────────────────────────────────────────
def _load_logo_html():
    here = os.path.dirname(os.path.abspath(__file__))
    for name in ["og-image.png", "wurth_logo.png", "logo.png", "wurth.png",
                 "wurth_logo.jpg", "logo.jpg", "wurth_logo.svg", "logo.svg"]:
        path = os.path.join(here, name)
        if os.path.exists(path):
            ext  = name.rsplit(".", 1)[-1]
            mime = "image/svg+xml" if ext == "svg" else f"image/{ext}"
            with open(path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            return f'<img src="data:{mime};base64,{b64}" style="height:32px;width:auto;display:block" alt="Würth">'
    # Fallback: texto
    return '<span style="color:#fff;font-weight:900;font-size:18px;font-style:italic">W</span>'

# ── HTML del viewer móvil (PWA v2 — vista gerencial) ────────────────────────
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
  --red:#c8102e;--red-soft:#ff4d6d;
  --bg:#0c0d10;--card:#16181d;--card2:#1b1e24;--line:#23262e;
  --text:#f4f6fa;--text2:#aab2c0;--text3:#6c7480;
  --green:#22c55e;--amber:#f5a623;--amber-bg:rgba(245,166,35,.12);--amber-border:rgba(245,166,35,.28);
  --green-bg:rgba(34,197,94,.1);--green-border:rgba(34,197,94,.25);
  --spark-color:#7c8593;
}
*{box-sizing:border-box;margin:0;padding:0;-webkit-tap-highlight-color:transparent}
html,body{height:100%;background:var(--bg);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,'SF Pro Display','Inter',sans-serif;overscroll-behavior:none;font-variant-numeric:tabular-nums}
body{display:flex;flex-direction:column;max-width:430px;margin:0 auto;padding:env(safe-area-inset-top) env(safe-area-inset-right) env(safe-area-inset-bottom) env(safe-area-inset-left)}

/* ── Header ── */
.hdr{display:flex;align-items:flex-start;justify-content:space-between;padding:18px 20px 8px;gap:10px}
.hdr-left{display:flex;flex-direction:column;gap:2px}
.greeting{font-size:14px;color:var(--text3);font-weight:400}
.hdr-title{font-size:22px;font-weight:800;letter-spacing:-.4px;color:var(--text)}
.logo{width:44px;height:44px;background:transparent;border-radius:11px;display:flex;align-items:center;justify-content:center;flex-shrink:0;overflow:hidden}

/* ── Refresh btn ── */
.refresh-btn{background:none;border:1px solid var(--line);color:var(--text3);border-radius:20px;padding:7px 14px;font-size:12px;cursor:pointer;display:flex;align-items:center;gap:6px;transition:all .2s}
.refresh-btn:active{transform:scale(.96)}
.refresh-btn.spinning svg{animation:spin .7s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}

/* ── Timestamp ── */
.ts-bar{padding:2px 20px 12px;font-size:11px;color:var(--text3);display:flex;align-items:center;gap:7px}
.ts-dot{width:7px;height:7px;border-radius:50%;background:var(--green);flex-shrink:0;box-shadow:0 0 7px rgba(34,197,94,.5)}
.ts-dot.stale{background:var(--amber);box-shadow:0 0 7px rgba(245,166,35,.4)}
.ts-dot.old{background:#555;box-shadow:none}

/* ── Alert banner ── */
.alert-bar{margin:0 16px 12px;display:flex;align-items:flex-start;gap:10px;border-radius:14px;padding:12px 14px;border:1px solid}
.alert-bar.warn{background:var(--amber-bg);border-color:var(--amber-border)}
.alert-bar.ok{background:var(--green-bg);border-color:var(--green-border)}
.alert-bar svg{width:18px;height:18px;flex-shrink:0;margin-top:1px}
.alert-bar.warn svg{color:var(--amber)}
.alert-bar.ok svg{color:var(--green)}
.alert-txt{font-size:13px;line-height:1.4}
.alert-bar.warn .alert-txt{color:#f5c97a}
.alert-bar.warn .alert-txt b{color:var(--amber);font-weight:700}
.alert-bar.ok .alert-txt{color:#86efac}
.alert-bar.ok .alert-txt b{color:var(--green);font-weight:700}

/* ── Hero plan ── */
.hero{margin:0 16px 12px;background:linear-gradient(155deg,#1c1f26,#141519);border:1px solid var(--line);border-radius:20px;padding:20px}
.hero-lbl{font-size:11px;font-weight:700;letter-spacing:1.3px;text-transform:uppercase;color:var(--text3);margin-bottom:12px}
.hero-figs{display:flex;align-items:baseline;gap:10px;margin-bottom:16px}
.hero-curr{font-size:42px;font-weight:800;color:var(--text);line-height:.95;letter-spacing:-1.5px}
.hero-total{font-size:18px;color:var(--text3);font-weight:500}
.hero-bar-row{display:flex;align-items:center;gap:12px;margin-bottom:6px}
.hero-pct{font-size:17px;font-weight:800;color:var(--amber);min-width:52px}
.hero-pct.ok-color{color:var(--green)}
.bar-bg{flex:1;height:12px;background:#0a0b0e;border-radius:6px;position:relative;overflow:visible;border:1px solid #1e2128}
.bar-fill{height:100%;border-radius:6px;background:linear-gradient(90deg,var(--red),var(--red-soft));transition:width 1.2s cubic-bezier(.4,0,.2,1)}
.bar-fill.done{background:linear-gradient(90deg,#16a34a,var(--green))}
.bar-pace{position:absolute;top:-4px;bottom:-4px;width:2px;background:rgba(255,255,255,.5);border-radius:2px}
.hero-sep{border:none;border-top:1px solid var(--line);margin:16px 0}
.hero-proy{display:flex;align-items:flex-start;justify-content:space-between}
.proy-l{font-size:11px;color:var(--text3);text-transform:uppercase;letter-spacing:.6px;margin-bottom:4px}
.proy-s{font-size:11px;color:var(--text3);margin-top:4px}
.proy-v{font-size:24px;font-weight:800;color:var(--red-soft);letter-spacing:-.5px}
.proy-pct{font-size:12px;color:var(--text3);text-align:right;margin-top:2px}

/* ── Live 2-col grid ── */
.live-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:0 16px 12px}
.live-card{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:15px 16px}
.lc-badge{display:flex;align-items:center;gap:5px;font-size:10px;font-weight:800;letter-spacing:.5px;color:var(--green);text-transform:uppercase;margin-bottom:8px}
.pdot{width:6px;height:6px;border-radius:50%;background:var(--green);box-shadow:0 0 6px rgba(34,197,94,.6);animation:pulse 2s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.3}}
.lc-lbl{font-size:11px;color:var(--text3);text-transform:uppercase;letter-spacing:.4px;font-weight:600;margin-bottom:6px}
.lc-val{font-size:28px;font-weight:800;color:var(--text);line-height:1;letter-spacing:-.5px}
.lc-sub{font-size:11px;color:var(--text3);margin-top:6px}
.spark-svg{width:100%;height:28px;display:block;margin-top:10px}

/* ── Detalle operativo (colapsable) ── */
.detail{margin:0 16px 12px;background:var(--card);border:1px solid var(--line);border-radius:16px;overflow:hidden}
.detail-head{display:flex;align-items:center;justify-content:space-between;padding:14px 16px;cursor:pointer;user-select:none;-webkit-user-select:none}
.detail-head-txt{font-size:12px;font-weight:700;color:var(--text2);text-transform:uppercase;letter-spacing:.6px}
.detail-chev{color:var(--text3);transition:transform .25s;flex-shrink:0}
.detail.open .detail-chev{transform:rotate(180deg)}
.detail-body{display:none;padding:0 16px 6px}
.detail.open .detail-body{display:block}
.detail-row{display:flex;align-items:center;justify-content:space-between;padding:12px 0;border-top:1px solid var(--line)}
.detail-row .k{font-size:13px;color:var(--text2);display:flex;align-items:center;gap:7px}
.detail-row .v{font-size:15px;font-weight:700;color:var(--text)}
.sem{display:inline-block;width:7px;height:7px;border-radius:50%;flex-shrink:0}
.sem.ok{background:var(--green)}.sem.warn{background:var(--amber)}

/* ── Footer ── */
.app-foot{text-align:center;font-size:11px;color:var(--text3);padding:6px 16px 20px;line-height:1.5}

/* ── Toast ── */
.toast{position:fixed;bottom:calc(env(safe-area-inset-bottom)+24px);left:50%;transform:translateX(-50%) translateY(20px);background:#333;color:#fff;padding:10px 20px;border-radius:24px;font-size:13px;opacity:0;transition:all .3s;pointer-events:none;white-space:nowrap;z-index:999}
.toast.show{opacity:1;transform:translateX(-50%) translateY(0)}

/* ── Celeb overlay ── */
.celeb{position:fixed;inset:0;z-index:9999;pointer-events:none;display:none}
.celeb.active{display:block}
.celeb-msg{position:absolute;top:50%;left:50%;transform:translate(-50%,-60%);text-align:center;animation:popIn .5s cubic-bezier(.34,1.56,.64,1) forwards}
.celeb-emoji{font-size:72px;display:block;margin-bottom:8px}
.celeb-text{font-size:22px;font-weight:800;color:#ffd700;text-shadow:0 2px 20px rgba(0,0,0,.8)}
.celeb-sub{font-size:14px;color:#fff;opacity:.8;margin-top:4px}
@keyframes popIn{from{opacity:0;transform:translate(-50%,-60%) scale(.5)}to{opacity:1;transform:translate(-50%,-60%) scale(1)}}

/* ── Scroll ── */
.scroll{flex:1;overflow-y:auto;-webkit-overflow-scrolling:touch;padding-bottom:8px}
</style>
</head>
<body>

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
    <div class="logo">@@LOGO@@</div>
  </div>
</div>

<div class="ts-bar">
  <div class="ts-dot" id="tsDot"></div>
  <span id="tsText">Cargando…</span>
</div>

<div class="scroll" id="scrollArea">

  <!-- Alerta de ritmo -->
  <div class="alert-bar" id="alertBar" style="display:none">
    <svg id="alertIco" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></svg>
    <div class="alert-txt" id="alertTxt"></div>
  </div>

  <!-- Hero: plan del mes -->
  <div class="hero" id="heroBlock" style="display:none">
    <div class="hero-lbl">Plan del mes · facturación acumulada</div>
    <div class="hero-figs">
      <span class="hero-curr" id="hCurr">—</span>
      <span class="hero-total" id="hTotal"></span>
    </div>
    <div class="hero-bar-row">
      <span class="hero-pct" id="hPct">—</span>
      <div class="bar-bg">
        <div class="bar-fill" id="hBar" style="width:0%"></div>
        <div class="bar-pace" id="hPace" style="left:0%;display:none"></div>
      </div>
    </div>
    <hr class="hero-sep">
    <div class="hero-proy">
      <div>
        <div class="proy-l">Proyección de cierre</div>
        <div class="proy-s" id="hProySub"></div>
      </div>
      <div style="text-align:right">
        <div class="proy-v" id="hProyV">—</div>
        <div class="proy-pct" id="hProyPct"></div>
      </div>
    </div>
  </div>

  <!-- Live: venta hoy + pedidos hoy -->
  <div class="live-grid" id="liveGrid" style="display:none">
    <div class="live-card">
      <div class="lc-badge"><span class="pdot"></span>Hoy</div>
      <div class="lc-lbl">Venta del día</div>
      <div class="lc-val" id="lVenta">—</div>
      <svg class="spark-svg" id="sparkVen" viewBox="0 0 100 28" preserveAspectRatio="none"></svg>
    </div>
    <div class="live-card">
      <div class="lc-badge"><span class="pdot"></span>Hoy</div>
      <div class="lc-lbl">Pedidos hoy</div>
      <div class="lc-val" id="lPedidos">—</div>
      <svg class="spark-svg" id="sparkPed" viewBox="0 0 100 28" preserveAspectRatio="none"></svg>
    </div>
  </div>

  <!-- Detalle operativo (colapsable) -->
  <div class="detail" id="detailBlock" style="display:none">
    <div class="detail-head" onclick="document.getElementById('detailBlock').classList.toggle('open')">
      <span class="detail-head-txt">Detalle operativo</span>
      <svg class="detail-chev" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m6 9 6 6 6-6"/></svg>
    </div>
    <div class="detail-body">
      <div class="detail-row"><span class="k">Vendedores activos</span><span class="v" id="dVend">—</span></div>
      <div class="detail-row"><span class="k">Líneas / pedido</span><span class="v" id="dLin">—</span></div>
      <div class="detail-row"><span class="k"><span class="sem warn"></span>Backorders</span><span class="v" id="dBack">—</span></div>
      <div class="detail-row"><span class="k"><span class="sem" id="dRemSem"></span>Remitos abiertos</span><span class="v" id="dRem">—</span></div>
    </div>
  </div>

  <div class="app-foot">Datos en tiempo real · Reactor · MSPA</div>
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
let _data = null, _prevData = null, _refreshTimer = null;

// ── Greeting ─────────────────────────────────────────────────────────────
function setGreeting(){
  const h=new Date().getHours();
  const g=h<12?'Buenos días':h<19?'Buenas tardes':'Buenas noches';
  document.getElementById('greeting').textContent=g+', Daniel';
}
setGreeting();

// ── Format helpers ────────────────────────────────────────────────────────
function fmtK(v){
  if(v==null) return '—';
  const n=Number(v);
  if(n>=1e9) return '$'+(n/1e9).toLocaleString('es-AR',{minimumFractionDigits:1,maximumFractionDigits:1})+'B';
  if(n>=1e6) return '$'+(n/1e6).toLocaleString('es-AR',{minimumFractionDigits:1,maximumFractionDigits:1})+'M';
  if(n>=1e3) return '$'+(n/1e3).toLocaleString('es-AR',{minimumFractionDigits:0,maximumFractionDigits:0})+'K';
  return '$'+n.toLocaleString('es-AR',{maximumFractionDigits:0});
}
function fmtN(v,dec){
  if(v==null) return '—';
  return Number(v).toLocaleString('es-AR',{minimumFractionDigits:dec||0,maximumFractionDigits:dec||0});
}

// ── Sparkline SVG ─────────────────────────────────────────────────────────
function drawSpark(svgEl,values){
  if(!values||values.length<2){svgEl.innerHTML='';return;}
  const mn=Math.min(...values),mx=Math.max(...values),range=mx-mn||1;
  const w=100,h=28,pad=2;
  const pts=values.map((v,i)=>{
    const x=pad+(w-2*pad)*i/(values.length-1);
    const y=pad+(h-2*pad)*(1-(v-mn)/range);
    return x.toFixed(1)+','+y.toFixed(1);
  });
  const lp=pts[pts.length-1].split(',');
  const c='var(--spark-color)';
  svgEl.innerHTML=`<polyline points="${pts.join(' ')}" fill="none" stroke="${c}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/><circle cx="${lp[0]}" cy="${lp[1]}" r="2.5" fill="${c}"/>`;
}

// ── Relative time ─────────────────────────────────────────────────────────
function relTime(ts){
  if(!ts) return '';
  const diff=Math.round((Date.now()-new Date(ts).getTime())/1000);
  if(diff<5) return 'ahora mismo';
  if(diff<60) return `hace ${diff}s`;
  const m=Math.round(diff/60);
  return m<60?`hace ${m} min`:`hace ${Math.round(m/60)}h`;
}
function freshnessClass(ts){
  if(!ts) return 'old';
  const age=(Date.now()-new Date(ts).getTime())/1000;
  if(age<INTERVAL*1.5) return '';
  if(age<INTERVAL*3) return 'stale';
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
  const canvas=document.getElementById('confettiCanvas');
  const ctx=canvas.getContext('2d');
  canvas.width=window.innerWidth; canvas.height=window.innerHeight;
  const colors=['#ffd700','#ff4d6d','#22c55e','#3b82f6','#f59e0b','#c8102e'];
  const pieces=Array.from({length:80},()=>({x:Math.random()*canvas.width,y:-10,r:Math.random()*4+3,c:colors[Math.floor(Math.random()*colors.length)],sp:Math.random()*4+2,ang:Math.random()*360,rot:Math.random()*6-3}));
  let frame=0;
  (function draw(){ctx.clearRect(0,0,canvas.width,canvas.height);pieces.forEach(p=>{p.y+=p.sp;p.ang+=p.rot;ctx.save();ctx.translate(p.x,p.y);ctx.rotate(p.ang*Math.PI/180);ctx.fillStyle=p.c;ctx.fillRect(-p.r,-p.r,p.r*2,p.r*2);ctx.restore();});if(++frame<120)requestAnimationFrame(draw);})();
  setTimeout(()=>overlay.classList.remove('active'),4000);
}

// ── Render ────────────────────────────────────────────────────────────────
function render(d){
  if(!d) return;

  // Timestamp
  document.getElementById('tsDot').className='ts-dot '+freshnessClass(d.ts);
  document.getElementById('tsText').textContent=(d.ts?relTime(d.ts):'—')+(d.comp_date?' · '+d.comp_date:'');

  // Alerta de ritmo
  const alertBar=document.getElementById('alertBar');
  const pct=parseFloat(d.plan_pct)||0;
  const pace=parseFloat(d.plan_pace)||0;
  if(d.plan_total&&pace>0){
    alertBar.style.display='';
    const onTrack=pct>=pace;
    const gap=Math.abs(pace-pct).toLocaleString('es-AR',{minimumFractionDigits:1,maximumFractionDigits:1});
    alertBar.className='alert-bar '+(onTrack?'ok':'warn');
    const icoPaths=onTrack
      ?'<path d="M22 7 13.5 15.5 8.5 10.5 2 17"/><path d="M16 7h6v6"/>'
      :'<path d="M16 17h6v-6"/><path d="m22 17-8.5-8.5-5 5L2 7"/>';
    document.getElementById('alertIco').innerHTML=icoPaths;
    document.getElementById('alertTxt').innerHTML=onTrack
      ?`Plan <b>en ritmo</b> · ${fmtN(pct,1)}% vs ${fmtN(pace,1)}% esperado · proyección ${fmtK(d.proy)}`
      :`Plan <b>${gap} pts por debajo del ritmo</b> · ${fmtN(pct,1)}% vs ${fmtN(pace,1)}% esperado · proyección ${fmtK(d.proy)}`;
  } else {
    alertBar.style.display='none';
  }

  // Hero plan
  const heroBlock=document.getElementById('heroBlock');
  if(d.plan_total){
    heroBlock.style.display='';
    document.getElementById('hCurr').textContent=fmtK(d.plan_fact);
    document.getElementById('hTotal').textContent='/ '+fmtK(d.plan_total);
    const pctEl=document.getElementById('hPct');
    pctEl.textContent=fmtN(pct,1)+'%';
    pctEl.className='hero-pct'+(pct>=pace?' ok-color':'');
    const bar=document.getElementById('hBar');
    bar.className='quota-bar-fill'+(pct>=100?' done':'');
    requestAnimationFrame(()=>{ bar.style.width=Math.min(pct,100)+'%'; });
    // Marcador de ritmo esperado
    const paceEl=document.getElementById('hPace');
    if(pace>0&&pace<100){
      paceEl.style.display='';
      paceEl.style.left=pace.toFixed(1)+'%';
    } else { paceEl.style.display='none'; }
    // Proyección
    document.getElementById('hProyV').textContent=fmtK(d.proy);
    document.getElementById('hProyPct').textContent=d.proy_pct?fmtN(d.proy_pct,1)+'% del plan':'';
    const subParts=[];
    if(d.dia_habil&&d.dias_tot) subParts.push(`Día hábil ${d.dia_habil} de ${d.dias_tot}`);
    if(d.plan_fact&&d.plan_total) subParts.push(`Restante ${fmtK(d.plan_total-d.plan_fact)}`);
    document.getElementById('hProySub').textContent=subParts.join(' · ');
    maybeCelebrate(pct);
  } else {
    heroBlock.style.display='none';
  }

  // Live cards
  const liveGrid=document.getElementById('liveGrid');
  liveGrid.style.display='';
  document.getElementById('lVenta').textContent=fmtK(d.venta_dia);
  document.getElementById('lPedidos').textContent=d.pedidos!=null?fmtN(d.pedidos):'—';
  drawSpark(document.getElementById('sparkVen'), d.spark_ventas);
  drawSpark(document.getElementById('sparkPed'), d.spark_pedidos);

  // Detalle operativo
  const detailBlock=document.getElementById('detailBlock');
  detailBlock.style.display='';
  document.getElementById('dVend').textContent=d.vendedores!=null?fmtN(d.vendedores):'—';
  document.getElementById('dLin').textContent=d.avg_lineas!=null?fmtN(d.avg_lineas,1):'—';
  document.getElementById('dBack').textContent=d.backorders!=null?fmtN(d.backorders):'—';
  document.getElementById('dRem').textContent=d.remitos!=null?fmtN(d.remitos):'—';
  const remSem=document.getElementById('dRemSem');
  const remVal=parseInt(d.remitos)||0;
  remSem.className='sem '+(remVal>0?'warn':'ok');
}

// ── Fetch & load ──────────────────────────────────────────────────────────
async function loadData(){
  document.getElementById('tsText').textContent='Actualizando…';
  try{
    const r=await fetch('snapshot.json?_='+Date.now());
    if(!r.ok) throw new Error('HTTP '+r.status);
    const d=await r.json();
    _data=d;
    render(_data);
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
  loadData().then(()=>{ btn.classList.remove('spinning'); showToast('Actualizado'); }).catch(()=>btn.classList.remove('spinning'));
}

// ── Pull-to-refresh ───────────────────────────────────────────────────────
let _ptStart=0, _ptActive=false;
const scrollArea=document.getElementById('scrollArea');
scrollArea.addEventListener('touchstart',e=>{ if(scrollArea.scrollTop===0) _ptStart=e.touches[0].clientY; },{passive:true});
scrollArea.addEventListener('touchmove',e=>{ if(!_ptStart) return; if(e.touches[0].clientY-_ptStart>50&&!_ptActive) _ptActive=true; },{passive:true});
scrollArea.addEventListener('touchend',()=>{ if(_ptActive){ _ptActive=false; doRefresh(); } _ptStart=0; },{passive:true});

// ── Auto-refresh ──────────────────────────────────────────────────────────
function scheduleRefresh(){
  clearTimeout(_refreshTimer);
  _refreshTimer=setTimeout(()=>loadData().then(scheduleRefresh), INTERVAL*1000);
}
loadData().then(scheduleRefresh);

if('serviceWorker' in navigator) navigator.serviceWorker.register('sw.js').catch(()=>{});
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

_SW_JS = r"""const CACHE='wurth-__CACHE_VER__';
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
    """Extract relevant fields from get_cached_data() result into snapshot dict.

    Estructura real de get_cached_data():
      data = {
        "reactor": {pedidos, vendedores, valor, lineas, avg_lineas,
                    comp:{pedidos,vendedores,valor,date}, sparklines:{pedidos[],ventas[]}},
        "mspa":    {backorders:{ords,pos,val}, remitos:{ords,pos,val},
                    plan_ventas:{plan_total, fact_acum, pct_plan, sellers[]}},
        "today_summary": {date, is_today, pedidos, vendedores, valor, lineas, avg_lineas, ticket},
      }
    """
    snap = {"ts": datetime.datetime.now().isoformat(), "interval": interval}
    try:
        reactor = data.get("reactor") or {}
        mspa    = data.get("mspa") or {}
        hoy     = data.get("today_summary") or {}

        # ── Plan de ventas mensual (MSPA) ──────────────────────────────
        plan = mspa.get("plan_ventas") or {}
        snap["plan_pct"]   = plan.get("pct_plan")
        snap["plan_fact"]  = plan.get("fact_acum")
        snap["plan_total"] = plan.get("plan_total")

        # ── Ritmo esperado y proyección ────────────────────────────────
        meta = reactor.get("meta") or {}
        dias_elapsed = meta.get("dias_elapsed") or 0
        curr_wd      = meta.get("curr_wd") or 0
        fact_acum    = plan.get("fact_acum") or 0
        plan_total   = plan.get("plan_total") or 0
        snap["plan_pace"]  = round(dias_elapsed / curr_wd * 100, 2) if curr_wd else None
        snap["dia_habil"]  = dias_elapsed
        snap["dias_tot"]   = curr_wd
        proy = round(fact_acum / dias_elapsed * curr_wd) if dias_elapsed else None
        snap["proy"]       = proy
        snap["proy_pct"]   = round(proy / plan_total * 100, 2) if (proy and plan_total) else None

        # ── KPIs del día (today_summary = dato vivo de hoy) ────────────
        snap["venta_dia"]  = hoy.get("valor")
        snap["pedidos"]    = hoy.get("pedidos")
        snap["vendedores"] = hoy.get("vendedores")
        snap["avg_lineas"] = hoy.get("avg_lineas")
        snap["comp_date"]  = hoy.get("date")

        # ── Backorders / Remitos (MSPA, contar órdenes) ────────────────
        bo = mspa.get("backorders") or {}
        rm = mspa.get("remitos") or {}
        snap["backorders"] = bo.get("ords")
        snap["remitos"]    = rm.get("ords")

        # ── Comparativo día hábil anterior (reactor.comp) ──────────────
        comp = reactor.get("comp") or {}
        snap["d_pedidos"]    = comp.get("pedidos")
        snap["d_valor"]      = comp.get("valor")
        snap["d_vendedores"] = comp.get("vendedores")

        # ── Sparklines (reactor) ───────────────────────────────────────
        spark = reactor.get("sparklines") or {}
        snap["spark_pedidos"] = spark.get("pedidos")
        # ventas viene en millones (val/1e6) — reescalar a pesos para el viewer
        ventas_m = spark.get("ventas") or []
        snap["spark_ventas"] = [round(v * 1e6) for v in ventas_m] if ventas_m else None
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

                # viewer HTML — inyectar intervalo, versión de caché y logo
                cache_ver = datetime.datetime.now().strftime("%Y%m%d%H%M")
                logo_html = _load_logo_html()
                viewer = (_VIEWER_HTML
                          .replace("__INTERVAL__", str(interval))
                          .replace("@@LOGO@@", logo_html))
                _ftp_upload_text(ftp, "index.html", viewer)

                # SW con versión única para forzar actualización en cliente
                sw = _SW_JS.replace("__CACHE_VER__", cache_ver)
                _ftp_upload_text(ftp, "sw.js", sw)

                # .htaccess SIEMPRE — pisa cualquier versión vieja que bloquee snapshot.json
                _ftp_upload_text(ftp, ".htaccess", _HTACCESS)

                # PHP proxy solo si hay auth configurada
                if FTP_AUTH_PASS:
                    _ftp_upload_text(ftp, "index.php", _INDEX_PHP)

                # manifest
                _ftp_upload_text(ftp, "manifest.json", _MANIFEST)

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

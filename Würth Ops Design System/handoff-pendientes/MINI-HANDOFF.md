# MINI-HANDOFF — completar el dashboard.py (lo que falta de la v3)

Para Claude Code. Esto se aplica **sobre tu `dashboard.py` actual** (el que ya tiene
hero, KPIs neutros, flow bar, modo TV, date picker). NO reescribe nada: sólo **agrega**
4 cosas que faltaron. Respetá los IDs/clases que ya existen.

## ⚠️ Regla de oro
No toques las consultas SQL ni la lógica existente (días hábiles, comp, plan, cache).
Sólo agregás: datos derivados nuevos, HTML nuevo, CSS nuevo y JS de hidratación.

---

# 1) BANDA DE ALERTAS POR EXCEPCIÓN  ⭐ (lo más importante)

Una franja arriba del hero que **sólo aparece si hay excepciones**. Reemplaza la
necesidad del pulso en las celdas del flujo (ver punto 5).

### 1a. CSS — agregar al `<style>`
```css
.alerts{display:flex;flex-direction:column;gap:8px}
.alert{display:flex;align-items:center;gap:10px;padding:11px 16px;border-radius:var(--r-card);border:1px solid;font-size:13px}
.alert .ico{width:17px;height:17px;flex-shrink:0}
.alert b{font-weight:700}
.alert .a-act{margin-left:auto;font-size:11px;font-weight:600;text-decoration:none;white-space:nowrap;opacity:.8;color:inherit}
.alert.warn{background:var(--amber-bg);border-color:var(--amber);color:var(--amber)}
.alert.danger{background:var(--red-bg);border-color:var(--red);color:var(--neg-fg)}
.alert.danger .ico{color:var(--red)}
```

### 1b. HTML — primer hijo de `<div class="main">`, ANTES del `<div class="hero">`
```html
<div class="alerts" id="alerts-band"></div>
```

### 1c. JS — función + llamarla dentro de tu render/hidratación
Usá los **umbrales que ya definiste arriba** (`THR_RET_WARN=20`, `THR_RET_DNG=35`, etc.).
`d` = el objeto de datos ya hidratado (reactor + mspa). Ajustá los accesos a tus campos reales.
```js
function renderAlerts(d){
  const band = document.getElementById('alerts-band');
  const out = [];
  const ICO = {
    pause:'<svg class="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M10 15V9M14 15V9"/></svg>',
    down:'<svg class="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M16 17h6v-6"/><path d="m22 17-8.5-8.5-5 5L2 7"/></svg>',
    ban:'<svg class="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="m4.9 4.9 14.2 14.2"/></svg>'
  };
  // % retenidos sobre informados (usá tus variables reales)
  const inf = d.flow_informado || d.pedidos || 0;
  const ret = d.flow_retenido  || 0;
  const retPct = inf ? ret/inf*100 : 0;
  if (retPct >= THR_RET_WARN)
    out.push({sev: retPct>=THR_RET_DNG?'danger':'warn', ico:ICO.pause,
      msg:`<b>Retenidos en ${retPct.toFixed(1).replace('.',',')}%</b> — por encima del objetivo de ${THR_RET_WARN}% (${ret} pedidos)`,
      act:'Ver retenidos →'});
  // anulados
  const anPct = inf ? (d.flow_anulado||0)/inf*100 : 0;
  if (anPct >= THR_AN_WARN)
    out.push({sev: anPct>=THR_AN_DNG?'danger':'warn', ico:ICO.ban,
      msg:`<b>Anulados en ${anPct.toFixed(1).replace('.',',')}%</b> — revisar (${d.flow_anulado||0} pedidos)`,
      act:'Ver anulados →'});
  // plan por debajo del ritmo
  if (d.plan_pct != null && d.plan_pace != null && d.plan_pct < d.plan_pace)
    out.push({sev:'warn', ico:ICO.down,
      msg:`Plan de ventas <b>${(d.plan_pace-d.plan_pct).toFixed(1).replace('.',',')} pts por debajo del ritmo</b> (${d.plan_pct.toFixed(1).replace('.',',')}% vs ${d.plan_pace}%)`,
      act:'Ver plan →'});

  band.style.display = out.length ? 'flex' : 'none';
  band.innerHTML = out.map(a =>
    `<div class="alert ${a.sev}">${a.ico}<span>${a.msg}</span><a class="a-act" href="#">${a.act}</a></div>`
  ).join('');
}
// Llamala donde hidratás el resto: renderAlerts(datos);
```
> Dejé fuera "vendedores sin facturar" y "crédito bloqueado" como pediste. Para sumarlas
> después, agregá dos `out.push(...)` siguiendo el mismo molde.

---

# 2) SPARKLINES EN LOS KPI  ⭐ (llenan los KPI anchos con tendencia real)

### 2a. Datos nuevos — en `fetch_reactor`, agregá una serie de ~14 días hábiles
No cambia lo existente; es una query extra. Devolvela en el dict de retorno.
```python
# Serie últimos 14 días con actividad (pedidos y valor por día)
spark_rows = run(cur, """
    SELECT DATE(order_date) d,
           COUNT(DISTINCT id) pedidos,
           SUM(total) valor
    FROM order_placed
    WHERE order_date >= DATE_SUB(?, INTERVAL 25 DAY)
      AND DATE(order_date) <= ?
    GROUP BY DATE(order_date)
    HAVING COUNT(*) >= 20
    ORDER BY d DESC LIMIT 14
""", (target_str, target_str))
spark_rows = list(reversed(spark_rows))  # cronológico
spark = {
    "pedidos":  [int(r[1] or 0) for r in spark_rows],
    "valor":    [round(float(r[2] or 0)/1e6, 2) for r in spark_rows],
    "ped_vend": [],  # opcional: si querés, calculá ped/vend por día con otra query
}
# ...y en el return de fetch_reactor agregá:  "spark": spark,
```

### 2b. CSS
```css
.kpi-top{display:flex;align-items:flex-end;justify-content:space-between;gap:10px}
.spark{width:90px;height:32px;flex-shrink:0;opacity:.9}
```

### 2c. HTML — envolvé el `.kpi-val` existente en un `.kpi-top` con un slot para el spark
Ejemplo para "Pedidos / Vendedor":
```html
<div class="kpi-top">
  <div class="kpi-val num" id="k-vend">—</div>
  <span id="spark-vend"></span>
</div>
```
(Idem para el otro KPI con `id="spark-avg"`, etc.)

### 2d. JS — generador de sparkline SVG (sin librerías) + inyección
```js
function sparkline(data, color='auto', w=90, h=32){
  if(!data || data.length<2) return '';
  const mn=Math.min(...data), mx=Math.max(...data), rng=(mx-mn)||1, pad=2;
  const step=(w-pad*2)/(data.length-1);
  const pts=data.map((v,i)=>[pad+i*step, h-pad-((v-mn)/rng)*(h-pad*2)]);
  const d=pts.map((p,i)=>(i?'L':'M')+p[0].toFixed(1)+' '+p[1].toFixed(1)).join(' ');
  const area=d+` L${pts.at(-1)[0].toFixed(1)} ${h} L${pts[0][0].toFixed(1)} ${h} Z`;
  const up=data.at(-1)>=data[0];
  const c=color==='auto'?(up?'var(--green)':'var(--red)'):color;
  const id='sg'+Math.random().toString(36).slice(2,7);
  return `<svg class="spark" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none">
    <defs><linearGradient id="${id}" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="${c}" stop-opacity="0.18"/><stop offset="100%" stop-color="${c}" stop-opacity="0"/>
    </linearGradient></defs>
    <path d="${area}" fill="url(#${id})"/>
    <path d="${d}" fill="none" stroke="${c}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
    <circle cx="${pts.at(-1)[0].toFixed(1)}" cy="${pts.at(-1)[1].toFixed(1)}" r="2" fill="${c}"/>
  </svg>`;
}
// al hidratar:
// document.getElementById('spark-vend').innerHTML = sparkline(d.spark.ped_vend);
// document.getElementById('spark-avg').innerHTML  = sparkline(d.spark.valor);
```
> Si una serie viene vacía, `sparkline` devuelve '' y no rompe nada.

---

# 3) ESTADO DE CONEXIÓN CON PUNTOS DE COLOR

Tenés la frescura como texto. Sumale un punto por fuente. Ya calculás `reactor_age`,
`mspa_age`, `reactor_error`, `mspa_error` en `get_cached_data` — usalos.

### 3a. CSS
```css
.conn{display:flex;flex-direction:column;gap:3px;font-size:10px;color:var(--text3);text-align:right;line-height:1.4}
.conn-row{display:flex;align-items:center;gap:5px;justify-content:flex-end}
.conn-dot{width:7px;height:7px;border-radius:50%;flex-shrink:0}
.conn-dot.ok{background:var(--green)}
.conn-dot.slow{background:var(--amber)}
.conn-dot.down{background:var(--red)}
```

### 3b. HTML — reemplazá el bloque `.freshness` por:
```html
<div class="conn">
  <span class="conn-row"><span class="conn-dot ok" id="dot-m"></span>MSPA · <b id="next-m">—</b></span>
  <span class="conn-row"><span class="conn-dot ok" id="dot-r"></span>Reactor · <b id="next-r">—</b></span>
</div>
```

### 3c. JS — al hidratar, derivá el estado
```js
function connState(ageSec, err, slowSec, downSec){
  if(err) return 'down';
  if(ageSec > downSec) return 'down';
  if(ageSec > slowSec) return 'slow';
  return 'ok';
}
// MSPA refresca 60s → lento si >120s, caído si >600s. Reactor 600s → lento >900, caído >1800.
document.getElementById('dot-m').className = 'conn-dot ' + connState(d.mspa_age, d.mspa_error, 120, 600);
document.getElementById('dot-r').className = 'conn-dot ' + connState(d.reactor_age, d.reactor_error, 900, 1800);
```

---

# 4) (OPCIONAL) QUITAR EL PULSO REDUNDANTE DEL FLUJO

Si sumás la banda de alertas (punto 1), el pulso de las celdas dice la misma alarma dos
veces. Para calmarlo, sacá las clases `pulse-warn` / `pulse-danger` que agregás a
`#fc-ret` / `#fc-an` (dejá el `.alert-icon` si querés un indicador estático). El borde
ámbar/rojo de la celda ya alcanza como señal secundaria.

---

# PROMPT para pegar en Claude Code
> Sobre mi `dashboard.py` actual (no reescribas lo existente), agregá las 4 mejoras de
> este MINI-HANDOFF en orden: (1) banda de alertas por excepción arriba del hero usando
> mis umbrales THR_*, (2) sparklines SVG en los KPI con una query extra de 14 días hábiles
> en fetch_reactor, (3) puntos de color de estado de conexión por fuente reusando
> reactor_age/mspa_age/errores, (4) quitar el pulso redundante del flujo. Mantené IDs y
> clases existentes, el español, light/dark y la lógica de datos intacta. Mostrame los diffs.

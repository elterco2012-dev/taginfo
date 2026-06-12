# MINI-FIX #2 — pulido final del dashboard.py (diagnóstico sobre captura real)

Para Claude Code. Esto se aplica **sobre tu `dashboard.py` actual**. Son arreglos
puntuales detectados mirando el dashboard ya corriendo. NO reescribas nada: corregí
sólo lo indicado. Orden por prioridad.

## ⚠️ Regla de oro
No toques las consultas SQL ni la lógica de negocio. Sólo: el render del gráfico,
el formateo de un número, una nota aclaratoria y un par de detalles de layout.

═══════════════════════════════════════════════════════════════════════════
# 🔴 FIX 1 — La card "Tendencia Mensual" aparece EN BLANCO  (lo más urgente)
═══════════════════════════════════════════════════════════════════════════
El `<canvas>` del gráfico no dibuja nada. Causas probables (revisá en este orden):

### A. El canvas no tiene altura cuando Chart.js se instancia
Chart.js necesita que el contenedor tenga tamaño al crear el gráfico. Asegurate de:
1. Que el `<canvas>` esté dentro de `<div class="chart-wrap" style="position:relative;height:248px">`.
2. Crear el chart con `responsive:true, maintainAspectRatio:false`.
3. Instanciar el chart DESPUÉS de que la card es visible (no dentro de un bloque oculto).

### B. Se crea el chart antes de tener los datos / se crea dos veces
Si hidratás por fetch, el chart puede crearse con `TREND` vacío, o crearse de nuevo en
cada refresh sin destruir el anterior (deja un canvas “tomado” y no redibuja).
**Patrón correcto** (guardá la instancia y destruila antes de recrear):
```js
let trendChart = null;
function renderTrend(trend){
  const cv = document.getElementById('trend-canvas');   // tu id real
  if(!cv || !window.Chart) return;
  if(!trend || !trend.length){                           // empty state, no card vacía
    cv.closest('.chart-wrap').innerHTML =
      '<div style="display:flex;height:100%;align-items:center;justify-content:center;color:var(--text-3);font-size:12px">Sin datos de tendencia para este período</div>';
    return;
  }
  const labels = trend.map(t=>{ const [y,m]=t.mes.split('-');
    return ['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic'][+m-1]+' '+y.slice(2); });
  const barData  = trend.map(t=> t.dias_hab ? +(t.pedidos/t.dias_hab).toFixed(1) : 0);
  const lineData = trend.map(t=> t.dias_hab ? +((t.valor/1e6)/t.dias_hab).toFixed(2) : 0);
  const dark = document.body.classList.contains('dark');
  const tick = dark?'#64748b':'#94a3b8', grid = dark?'#1e293b':'#f1f5f9';
  if(trendChart) trendChart.destroy();                   // <-- clave: destruir antes
  trendChart = new Chart(cv.getContext('2d'), {
    data:{ labels, datasets:[
      {type:'bar', label:'Pedidos / día hábil', data:barData,
       backgroundColor:dark?'rgba(148,163,184,.35)':'rgba(203,213,225,.8)',
       borderColor:dark?'#475569':'#cbd5e1', borderWidth:1, yAxisID:'y1', order:2},
      {type:'line', label:'M$ / día hábil', data:lineData, borderColor:'#cc0000',
       backgroundColor:'rgba(204,0,0,.06)', borderWidth:2.5, pointRadius:2.5,
       pointBackgroundColor:'#cc0000', tension:.35, yAxisID:'y2', order:1, fill:true}
    ]},
    options:{ responsive:true, maintainAspectRatio:false,
      interaction:{mode:'index',intersect:false},
      plugins:{legend:{labels:{color:dark?'#cbd5e1':'#475569',font:{size:11},
        boxWidth:12,padding:16,usePointStyle:true}}},
      scales:{
        x:{ticks:{color:tick,font:{size:9}},grid:{display:false}},
        y1:{type:'linear',position:'left',title:{display:true,text:'pedidos/día',color:tick,font:{size:9}},
            ticks:{color:tick,font:{size:9}},grid:{color:grid}},
        y2:{type:'linear',position:'right',title:{display:true,text:'M$/día',color:tick,font:{size:9}},
            ticks:{color:'#cc0000',font:{size:9},callback:v=>v.toFixed(1).replace('.',',')},
            grid:{drawOnChartArea:false}}
      }
    }
  });
}
// llamala al hidratar y también al cambiar dark/TV: renderTrend(data.reactor.trend);
```
> Verificá el **id real** del canvas y que `data.reactor.trend` exista y NO esté vacío.
> El backend ya arma `trend` (lista de {mes,pedidos,valor,dias_hab}); si llega vacío,
> es que `wd_map`/`trend_rows` vino sin filas para el rango — logueá `len(trend)`.

### C. Si usás dark/TV: recreá el gráfico al togglear
Al cambiar de tema el canvas queda con colores viejos. Llamá `renderTrend(...)` de nuevo
dentro de `toggleDark()` y `toggleTV()` (con los datos ya en memoria).

═══════════════════════════════════════════════════════════════════════════
# 🔴 FIX 2 — "6.2" con punto en vez de coma  (Promedio Líneas / Pedido)
═══════════════════════════════════════════════════════════════════════════
Ese KPI no pasa por el formateador es-AR (los demás muestran "2,8" con coma).
Buscá dónde se inyecta `avg_lineas` en el HTML/JS y aplicale el formateador con 1 decimal.

```js
// MAL (deja el punto del Number):
el.textContent = d.avg_lineas;            // -> "6.2"
// BIEN:
el.textContent = fmtN(d.avg_lineas, 1);   // -> "6,2"
// fmtN en JS:
function fmtN(n,dec=0){ return Number(n||0).toLocaleString('es-AR',
  {minimumFractionDigits:dec, maximumFractionDigits:dec}); }
```
Revisá que **todos** los decimales usen `fmtN(x,1)`: avg_lineas, avg_ped_vend, los %
del flujo, el pct del plan. Cualquier `.toFixed()` suelto deja punto — reemplazalo por
`fmtN()` o agregale `.replace('.',',')`.

═══════════════════════════════════════════════════════════════════════════
# 🟠 FIX 3 — "Facturado $0" contradice "Venta del día $106,8M"
═══════════════════════════════════════════════════════════════════════════
En el flujo, la celda "Facturado" muestra $0 / 0 pedidos, pero MSPA facturó $106,8M y el
Top facturación tiene ventas. Para un gerente parece un error. Dos opciones (elegí una):

**Opción A (rápida, sólo aclarar):** agregá una nota al pie de la celda Facturado:
```html
<div class="flow-sub" style="color:var(--text-3)">
  Cierre en Reactor · facturación MSPA del día: <b id="flow-fact-mspa">$106,8M</b>
</div>
```
Así queda claro que "Facturado" mide el cierre de pedidos en Reactor, distinto de la
facturación contable de MSPA.

**Opción B (mejor, alinear el dato):** si lo que querés mostrar como "Facturado" es la
venta real del día, alimentá esa celda con el valor de MSPA (`venta.val` / `venta.ords`)
en lugar del status de Reactor. Decidilo según qué significa "Facturado" para el negocio.

═══════════════════════════════════════════════════════════════════════════
# 🟡 FIX 4 — Strip "Indicadores del día": sólo 2 KPIs muy anchos
═══════════════════════════════════════════════════════════════════════════
Quedan 2 tarjetas estiradas a todo el ancho con mucho aire vacío. Dos caminos:

**A. Sumar 2 KPIs** (la grilla ya es `repeat(4,1fr)`):
```js
// Ticket promedio del día
'$' + fmtK(d.valor / (d.pedidos||1))      // valor por pedido informado
// % facturado del informado
fmtN(d.flow_facturado_pct, 1) + '%'
```
**B.** Si preferís 2, cambiá la grilla a `grid-template-columns:repeat(2,1fr)` con
`max-width:760px` para que no se estiren tanto.
> Recomiendo A: llenan el espacio con información útil y dan simetría con el resto.

═══════════════════════════════════════════════════════════════════════════
# ✅ Lo que YA está muy bien (no tocar)
═══════════════════════════════════════════════════════════════════════════
- Banda de alertas (1 alerta, clara). · Conn-dots con "datos al". · Sparklines con color
  por tendencia. · Semáforos MSPA. · Proyección de cierre. · Empty states "Sin movimiento".
- Modo histórico, export, TV, dark. Todo correcto.

═══════════════════════════════════════════════════════════════════════════
# (RECOMENDADO) FIX 5 — Auto-refresh sin recargar la página
═══════════════════════════════════════════════════════════════════════════
Si lo vas a colgar en una pantalla: que el refresco NO use location.reload() (pierde
scroll, modo TV y dark cada 60s). Hacé fetch al endpoint de datos y re-hidratá el DOM.
```js
async function refrescar(){
  try{
    const r = await fetch('/data' + (window.__override?('?date='+window.__override):''));
    const data = await r.json();
    hidratar(data);          // tu función que llena el DOM (la misma del load inicial)
    renderTrend(data.reactor.trend);
  }catch(e){ /* marcá conn-dot en 'down' */ }
}
setInterval(refrescar, 60000);   // sin reload: conserva scroll/TV/dark
```

# PROMPT para pegar en Claude Code
> Sobre mi dashboard.py actual (no reescribas lo existente), aplicá este MINI-FIX #2 en
> orden: (1) el gráfico de Tendencia Mensual aparece en blanco — diagnosticá y arreglá el
> render de Chart.js (destruir instancia previa, responsive sin mantener ratio, recrear al
> cambiar dark/TV, empty state si no hay datos); (2) el KPI "Promedio Líneas / Pedido"
> muestra "6.2" con punto — pasalo por el formateador es-AR a "6,2" y revisá que todos los
> decimales usen coma; (3) en el flujo, "Facturado $0" contradice la venta MSPA — agregá la
> nota aclaratoria (opción A); (4) sumá 2 KPIs al strip de indicadores para llenar el ancho;
> (5) si es viable, pasá el auto-refresh a fetch sin recargar la página. Mantené el español,
> light/dark y la lógica de datos intacta. Mostrame los diffs.

# MINI-FIX #3 — pulido fino (diagnóstico sobre captura real, light + dark)

Para Claude Code. Se aplica **sobre tu `dashboard.py` actual**. Son 4 detalles de
acabado detectados mirando el dashboard ya corriendo. NO reescribas nada: corregí sólo
lo indicado. El dashboard ya está muy bien — esto es pulido, no errores.

## ⚠️ Regla de oro
No toques las consultas SQL ni la lógica de negocio. Sólo: color de sparklines, el
render del delta cuando es 0, contexto temporal de un strip, y un decimal de tooltip.

═══════════════════════════════════════════════════════════════════════════
# ⭐ FIX 1 — Sparklines de un solo color neutro (hoy se contradicen con el delta)
═══════════════════════════════════════════════════════════════════════════
Problema: el color "auto" del sparkline (verde si la serie de 14 días sube, rojo si baja)
NO coincide con la flecha del delta. Ej: "Pedidos Informados ↓1,5%" muestra sparkline
VERDE; "Venta del Día" muestra ROJO. Para un gerente, verde debe significar "bien"
siempre — un número que baja con spark verde confunde.

Regla pro: el sparkline muestra la FORMA de la tendencia (contexto), no un juicio.
El juicio lo da la flecha del delta. → Pintá todos los sparklines de un gris neutro.

### Cambio: en la llamada a `sparkline(...)`, pasá un color fijo en vez de 'auto'
```js
// ANTES:  sparkline(serie)            // color 'auto' -> verde/rojo según pendiente
// AHORA:  sparkline(serie, 'var(--text-3)')   // gris neutro, igual en todas las cards
```
Si tu función tiene el color hardcodeado adentro, cambiá el default:
```js
function sparkline(data, color='var(--text-3)', w=90, h=32){  // <- default neutro
  ...
  const c = color;            // <- quitá la rama 'auto' (verde/rojo)
  ...
}
```
> Opcional fino: bajá la opacidad del trazo a ~0.7 para que el sparkline no compita con
> el número. El número es el protagonista; el spark es fondo.

═══════════════════════════════════════════════════════════════════════════
# FIX 2 — "↓0,0%": no mostrar flecha cuando el cambio es exactamente 0
═══════════════════════════════════════════════════════════════════════════
Hoy "Pedidos / Vendedor" y "Líneas / Pedido" muestran "↓ 0,0%": flecha roja hacia abajo
con cero. Se lee como problema cuando no hay cambio. Mostralo neutro.

### En tu función que arma el delta:
```js
function deltaHTML(curr, prev){
  if(!prev || !curr) return '';
  const p = (curr - prev) / prev * 100;
  const EPS = 0.05;                       // umbral de "sin cambio"
  if(Math.abs(p) < EPS){                  // neutro: sin flecha, gris
    return '<span class="delta flat" style="color:var(--text-3)">— sin cambio</span>';
  }
  const up = p > 0;
  const ico = up ? ICO.arrowUp : ICO.arrowDown;   // tus SVGs
  return `<span class="delta ${up?'up':'down'}">${ico}${Math.abs(p).toFixed(1).replace('.',',')}%</span>`;
}
```
CSS (si no existe la clase flat):
```css
.delta.flat{display:inline-flex;align-items:center;gap:3px;font-size:11px;font-weight:600}
```

═══════════════════════════════════════════════════════════════════════════
# FIX 3 — Diferenciar visualmente "Indicadores del día" vs "Hoy en tiempo real"
═══════════════════════════════════════════════════════════════════════════
Hay métricas repetidas en dos strips (Ped/Vendedor, Ticket Promedio, Líneas/Pedido):
una para el día seleccionado (04/06) y otra para HOY en vivo (05/06). Un gerente ve
"3,0" y "2,2" para lo mismo y duda. El contexto temporal tiene que gritar más.

### Opción recomendada: badge "EN VIVO" + fondo sutil en el strip de tiempo real
HTML — en el encabezado del strip "Hoy ... (en tiempo real)":
```html
<div class="sec-lbl">
  Hoy 05/06/2026 — Pedidos informados
  <span class="live-badge"><span class="live-dot"></span>EN VIVO</span>
</div>
```
CSS:
```css
.live-badge{display:inline-flex;align-items:center;gap:5px;margin-left:8px;
  font-size:9px;font-weight:800;letter-spacing:.6px;color:var(--green);
  background:var(--green-bg);padding:2px 7px;border-radius:20px}
.live-dot{width:6px;height:6px;border-radius:50%;background:var(--green);
  animation:ring 2.4s ease-out infinite}
/* y darle al contenedor de ese strip un fondo apenas distinto: */
.kpi-grid.is-live{background:linear-gradient(0deg,var(--green-bg),var(--green-bg)),var(--border)}
.kpi-grid.is-live .kpi{background:var(--surface)}   /* mantené las celdas blancas */
```
> Alternativa mínima: sólo el badge "EN VIVO", sin tocar fondos. Ya alcanza para
> despejar la duda de qué strip es el del día y cuál el de ahora.

═══════════════════════════════════════════════════════════════════════════
# FIX 4 — Tooltip del gráfico: decimal con punto ("160.04" → "160,0")
═══════════════════════════════════════════════════════════════════════════
En el tooltip de Chart.js los valores salen con punto. Pasalos por es-AR.
```js
options:{
  plugins:{
    tooltip:{
      callbacks:{
        label: (ctx)=>{
          const v = ctx.parsed.y;
          const txt = Number(v).toLocaleString('es-AR',{minimumFractionDigits:1,maximumFractionDigits:1});
          return `${ctx.dataset.label}: ${txt}`;
        }
      }
    }
  }
}
```

═══════════════════════════════════════════════════════════════════════════
# ✅ Lo que YA está muy bien (no tocar)
═══════════════════════════════════════════════════════════════════════════
- Gráfico de tendencia renderizando con tooltip. · Flujo con valores reales y nota de
  cierre Reactor vs MSPA. · 4 KPIs en el strip. · Banda de alertas única. · Conn-dots.
- Proyección de cierre. · Semáforos MSPA con empty states $0. · Dark mode impecable.

# PROMPT para pegar en Claude Code
> Sobre mi dashboard.py actual (no reescribas lo existente), aplicá este MINI-FIX #3:
> (1) pintá todos los sparklines de un gris neutro (var(--text-3)) en vez del color auto
> verde/rojo, porque hoy contradicen la flecha del delta; (2) cuando el delta es 0,0%
> mostralo neutro "— sin cambio" en gris, sin flecha; (3) diferenciá el strip "Hoy en
> tiempo real" del de "Indicadores del día" con un badge EN VIVO y un fondo sutil, porque
> hay métricas repetidas y se confunden; (4) en el tooltip del gráfico formateá los
> decimales a es-AR con coma. Mantené el español, light/dark y la lógica intacta. Mostrame los diffs.

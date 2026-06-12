# MINI-FIX FINAL — el 10% que falta para nivel Fortune 500 (NOC / Bloomberg)

Para Claude Code. Se aplica **sobre tu `dashboard.py` actual** (vista normal + modo kiosk).
4 cambios de consistencia y densidad. NO reescribas nada: ajustá sólo lo indicado.

## ⚠️ Regla de oro
No toques las consultas SQL ni la lógica. Sólo: color de sparklines, densidad de 2
paneles del kiosk, estilo del gráfico, y una franja persistente.

═══════════════════════════════════════════════════════════════════════════
# ⭐ FIX 1 — TODOS los sparklines en GRIS NEUTRO  (lo más importante, no negociable)
═══════════════════════════════════════════════════════════════════════════
Hoy los sparklines se pintan verde/rojo según su propia pendiente, y eso CONTRADICE la
flecha del delta: "Pedidos Informados ↓2,3%" sale con sparkline VERDE; "Pedido Promedio"
sale ROJO. Un ejecutivo lo ve y desconfía del tablero. En Bloomberg los sparklines son
monocromáticos justamente por esto.

Regla: el sparkline muestra la FORMA de la tendencia (contexto). El juicio (subió/bajó)
lo da SOLO la flecha del delta.

### Cambio: pintá todos los sparklines de gris, quitá la rama verde/rojo
```js
// En tu función sparkline(...), cambiá el color a fijo neutro:
function sparkline(data, color='var(--text-3)', w=90, h=32){   // default neutro
  ...
  const c = color;          // <- borrá cualquier 'auto' que elija verde/rojo
  ...
}
// Y en TODAS las llamadas, no pases color (o pasá 'var(--text-3)').
```
> Opcional fino: trazo a opacity ~0.7 para que el sparkline no compita con el número.
> Aplica IGUAL en la vista normal y en el kiosk si éste tuviera sparklines.

═══════════════════════════════════════════════════════════════════════════
# FIX 2 — Llenar el vacío en el KIOSK (data-ink ratio)  ⭐
═══════════════════════════════════════════════════════════════════════════
En el Tablero 1 del kiosk, "Venta del Día" y "Pedidos Informados" son dos cajas enormes
con un número chiquito flotando en el medio → el vacío se lee como "falta data". Una sala
NOC llena el espacio con información útil.

Elegí UNA (o combiná):

**A. Mini-ranking de vendedores del día** (recomendado — aprovecha que ya lo calculás):
Reemplazá una de las dos cajas grandes por un Top 5 facturación compacto:
```html
<div class="panel b1-rank">
  <div class="kt-eyebrow">🏆 Top facturación · hoy</div>
  <!-- filas: rank · nombre · valor (font ~26-30px) -->
</div>
```
**B. Desglose** que ya tengas (por sucursal / línea de producto), 3-4 ítems con barra.
**C. Si no hay más data:** agrandá los números y subí el padding para que la caja se
sienta intencional, y sumá un sparkline grande (gris) de la métrica dentro de la caja.

> Objetivo: que ningún panel del wallboard tenga >40% de espacio vacío.

═══════════════════════════════════════════════════════════════════════════
# FIX 3 — Limpiar el gráfico de tendencia (las barras compiten con la línea)
═══════════════════════════════════════════════════════════════════════════
En el Tablero 2, las barras grises pelean con la línea roja; el ojo no sabe qué mirar.
Bajá las barras a "fantasma" para que la LÍNEA sea la protagonista.

```js
// dataset de barras:
backgroundColor: 'rgba(203,213,225,.35)',   // mucho más tenue (era .75)
borderColor: 'rgba(203,213,225,.5)', borderWidth: 0,
// dataset de línea: dejala fuerte (#cc0000, borderWidth 3, pointRadius 3)
// y subí un poco su relleno para dar cuerpo:
backgroundColor: 'rgba(204,0,0,.08)',
```
> Alternativa más radical (muy NOC): sacá las barras y dejá SOLO la línea de M$/día.
> Si las dejás, que queden claramente de fondo.

═══════════════════════════════════════════════════════════════════════════
# FIX 4 — Franja "métrica norte" PERSISTENTE en el kiosk (ambos tableros)
═══════════════════════════════════════════════════════════════════════════
Bloomberg/NYSE tienen UN número que nunca desaparece. Tu Plan se va cuando rota al
Tablero 2. Agregá una franja fina, SIEMPRE visible, con el norte del negocio.

### HTML — dentro de la top bar (o como sub-barra bajo la alerta), en AMBOS tableros:
```html
<div class="kt-north">
  <span>PLAN <b class="num">29,3%</b></span><span class="sep">·</span>
  <span>PROYECCIÓN <b class="num">$2,8B</b></span><span class="sep">·</span>
  <span>VENTA HOY <b class="num">$127,6M</b></span><span class="sep">·</span>
  <span class="north-tag warn">8,8 pts bajo ritmo</span>
</div>
```
### CSS:
```css
.kt-north{display:flex;align-items:center;gap:16px;font-size:19px;color:var(--text-2);
  padding:0 44px;height:54px;background:var(--panel-2);border-bottom:1px solid var(--border)}
.kt-north b{color:var(--text);font-weight:800;margin-left:6px}
.kt-north .sep{color:var(--text-3)}
.kt-north .north-tag{margin-left:auto;font-size:15px;font-weight:700;padding:4px 12px;
  border-radius:8px;background:var(--amber-bg);color:#b45309}
```
> Renderizala SIEMPRE (fuera del switch de board1/board2). Ajustá los `.kt-board.top1`
> para descontar su altura (hoy `top:166px`; con la franja, `top:220px`).

═══════════════════════════════════════════════════════════════════════════
# Pulido opcional (lujo)
═══════════════════════════════════════════════════════════════════════════
- Subtítulos ("349 pedidos facturados") un punto MÁS tenues (var(--text-3)) para que el
  número respire.
- El punto verde de "EN VIVO · PARCIAL" que pulse suave (keyframe de opacidad 2s) — el
  micro-movimiento comunica "vivo" desde lejos.

═══════════════════════════════════════════════════════════════════════════
# ✅ Lo que YA está nivel Fortune 500 (no tocar)
═══════════════════════════════════════════════════════════════════════════
- Plan como héroe + proyección. · Kiosk claro full-screen sin barras. · Controles
  discretos + teclado. · Estado de conexión + "datos al". · Alerta única. · Semáforos MSPA.

# PROMPT para pegar en Claude Code
> Sobre mi dashboard.py (no reescribas lo existente), aplicá este MINI-FIX FINAL: (1) pintá
> TODOS los sparklines de gris neutro var(--text-3) y quitá el color auto verde/rojo —
> contradicen la flecha del delta; (2) en el Tablero 1 del kiosk llená el vacío de las cajas
> "Venta del Día"/"Pedidos Informados" con un mini Top-5 facturación del día (o un desglose
> que ya calcule), ningún panel con >40% vacío; (3) en el gráfico de tendencia bajá las
> barras a fantasma (rgba ~.35, sin borde) para que la línea roja sea protagonista; (4)
> agregá una franja "métrica norte" persistente en AMBOS tableros del kiosk con PLAN % ·
> PROYECCIÓN · VENTA HOY · tag de ritmo, y ajustá el top de los boards para descontar su
> altura. Mantené español, modo claro y la lógica intacta. Mostrame los diffs.

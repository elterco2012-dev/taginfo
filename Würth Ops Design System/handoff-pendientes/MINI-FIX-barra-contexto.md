# MINI-FIX — fusionar alerta + franja norte en UNA sola barra de contexto

Para Claude Code. Hoy en el kiosk hay DOS barras apiladas que se pisan: la banda de
alerta (ámbar, con ícono y texto resaltado) y la franja "norte" monocromática debajo
(PLAN · PROYECCIÓN · VENTA HOY). El 29,3% y el "8,8 pts bajo ritmo" aparecen duplicados.
Fusionalas en UNA sola barra de contexto persistente que se adapta. NO toques la lógica.

## ⚠️ Regla de oro
Sólo presentación: unir las dos barras en una. Mantené el cálculo de la alerta intacto.

## Qué querés (decisión del usuario)
Conservar el ESTILO de la alerta (color de fondo, ícono de línea cayendo, letras de
color) — NO el gris monocromático de la franja norte, que no resalta y nadie nota.
Entonces: **la barra fusionada hereda el look de la alerta**, y le sumamos las métricas
norte (Plan/Proyección/Venta) integradas, siempre visibles en AMBOS tableros.

## Estructura de la barra fusionada
Una sola fila, persistente en board 1 y board 2:
```
[icono]  Plan de ventas 8,8 pts por debajo del ritmo — 29,3% vs 38,1% esperado a hoy
         · PROYECCIÓN $2,8B · VENTA HOY $127,6M                      [8,8 pts bajo ritmo]
```
- **Con excepción:** fondo ámbar/rojo, ícono `trendingDown`, texto de color (como la
  alerta actual). Las métricas norte van en la MISMA barra, no en una franja aparte.
- **Sin excepción (plan en ritmo):** la barra se pone verde/neutra, ícono `checkCircle`,
  texto "Plan en ritmo · 38,4% vs 38,1%" + las mismas métricas norte. Nunca desaparece.

## HTML (reemplaza las dos barras por esta)
```html
<div class="kt-ctxbar warn">           <!-- warn | danger | ok según estado -->
  <svg class="ico">…trendingDown…</svg>
  <span class="ctx-alert">Plan de ventas <b>8,8 pts por debajo del ritmo</b> — 29,3% vs 38,1% esperado a hoy</span>
  <span class="ctx-sep">·</span>
  <span class="ctx-metric">PROYECCIÓN <b class="num">$2,8B</b></span>
  <span class="ctx-sep">·</span>
  <span class="ctx-metric">VENTA HOY <b class="num">$127,6M</b></span>
  <span class="ctx-tag">8,8 pts bajo ritmo</span>
</div>
```
> El "PLAN 29,3%" ya está dentro del texto de alerta ("29,3% vs 38,1%"), así que NO lo
> repitas como métrica aparte. Métricas extra = sólo Proyección y Venta hoy.

## CSS
```css
.kt-ctxbar{display:flex;align-items:center;gap:16px;height:72px;padding:0 44px;font-size:23px;font-weight:600;border-bottom:1px solid}
.kt-ctxbar .ico{width:30px;height:30px;flex-shrink:0}
.kt-ctxbar b{font-weight:800}
.kt-ctxbar .ctx-sep{color:currentColor;opacity:.4}
.kt-ctxbar .ctx-metric{font-size:20px;font-weight:600;opacity:.92}
.kt-ctxbar .ctx-metric b{margin-left:6px}
.kt-ctxbar .ctx-tag{margin-left:auto;font-size:16px;font-weight:800;padding:5px 14px;border-radius:8px;white-space:nowrap}
/* estados (heredan el look de la alerta, NO el gris de la franja) */
.kt-ctxbar.warn{background:var(--amber-bg);color:#b45309;border-color:#fcd9a4}
.kt-ctxbar.warn .ctx-tag{background:#fff;color:#b45309}
.kt-ctxbar.danger{background:var(--red-bg);color:#b91c1c;border-color:#fbcdcd}
.kt-ctxbar.danger .ctx-tag{background:#fff;color:#b91c1c}
.kt-ctxbar.ok{background:var(--green-bg);color:#15803d;border-color:#b7ecca}
.kt-ctxbar.ok .ctx-tag{background:#fff;color:#15803d}
```

## Ajustes
- **Eliminá** la antigua `.kt-alert` y la `.kt-north` (las dos barras viejas).
- Renderizá `.kt-ctxbar` SIEMPRE (fuera del switch board1/board2), después de la top bar.
- Ajustá el top de los boards a la nueva altura: `.kt-board.top1{ top: 168px }` aprox
  (96px top bar + 72px ctxbar). Verificá que no se solape.
- El estado (warn/danger/ok) y el texto salen de tu lógica de alertas existente.

## Verificación
- UNA sola barra de contexto, con color e ícono (no monocromática).
- Sin 29,3%/"8,8 pts" duplicados.
- Persiste en ambos tableros (en el board 2 es la única referencia al plan → cumple su rol).
- Si el plan está en ritmo, la barra se pone verde y dice "en ritmo" (no desaparece).

## PROMPT para Claude Code
> En el kiosk de mi dashboard.py, fusioná la banda de alerta y la franja "norte" en UNA
> sola barra de contexto persistente (.kt-ctxbar) que conserve el ESTILO de la alerta
> (fondo de color, ícono de línea, letras de color) y NO el gris de la franja. Que muestre
> el texto de alerta + PROYECCIÓN + VENTA HOY (sin repetir el 29,3% que ya está en el texto),
> con un tag de ritmo a la derecha. Estados warn/danger/ok según mi lógica; si el plan está
> en ritmo, la barra se pone verde y dice "en ritmo", nunca desaparece. Eliminá las dos
> barras viejas (.kt-alert y .kt-north) y ajustá el top de los boards a la nueva altura.
> Persistente en ambos tableros. No toques la lógica de datos. Mostrame el diff.

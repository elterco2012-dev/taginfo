# HANDOFF — Dashboard Würth v3 (para Claude Code)

Paquete para portar el rediseño completo (v3) a tu `dashboard.py` real.
La v3 = v2 (refinamiento visual) **+** diseño de información y UX.

## Archivos de este paquete
- **`dashboard-v3.css`** — hoja de estilos autocontenida (tokens + todos los estilos v3:
  alertas, sparklines, semáforos, conexión, skeleton, modo TV). Pegala en tu `<style>`.
- **`snippets-v3.py`** — la **lógica** que el CSS no cubre: sparkline SVG, alertas por
  excepción (con los umbrales), estado de conexión, semáforos, meta-chips, skeleton/TV/export.
- **`icons.txt`** — set de íconos Lucide + función `icon()` en Python.
- **`format-es-AR.txt`** — formateadores `fmt_n` / `fmt_k` / `pct` (Python y JS).

> El código fuente vivo de referencia está en `ui_kits/operations-dashboard-v3/`
> (CSS + componentes React). Si Claude Code prefiere leer el original, está ahí.

---

## ⚠️ Regla de oro
**No toques las consultas SQL ni la lógica de negocio** (días hábiles, pace, fallbacks
MSPA, refresco). Sólo cambiás el **HTML que generás** y el **CSS**. La v3 sí necesita
**dos datos nuevos** que quizá hoy no traés (ver abajo).

---

## Datos nuevos que pide la v3
1. **Series para sparklines:** los últimos ~14 días hábiles de cada KPI
   (pedidos, valor, pedidos/vendedor, líneas/pedido). Una query `GROUP BY fecha LIMIT 14`.
2. **Metas/objetivos** por KPI (al menos pedidos y valor del día). Si ya tenés el plan
   mensual, podés derivar la meta diaria dividiendo por días hábiles.
3. **Frescura por fuente:** la hora del último dato de MSPA y de Reactor, para el
   estado de conexión y los sellos "datos al". Ya tenés algo similar (los contadores
   de refresco); reusalo.

Si alguno no está disponible todavía, el componente degrada bien: sin serie no dibuja
sparkline, sin meta no muestra el chip, sin frescura mostrá "—".

---

## PROMPT sugerido para arrancar

> Quiero llevar mi `dashboard.py` (Würth, es-AR, read-only) a la versión v3 de un
> rediseño. Te paso: `dashboard-v3.css` (estilos), `snippets-v3.py` (lógica:
> sparklines, alertas, conexión, semáforos, metas), `icons.txt` y `format-es-AR.txt`.
> **No cambies las consultas SQL ni la lógica de datos existente.** Integrá, en este orden:
>
> 1. Pegá `dashboard-v3.css` y cargá la fuente IBM Plex Sans (link de Google Fonts).
> 2. Aplicá los **formateadores es-AR** a todos los números y la clase `.num` (tabular).
> 3. Reestructurá el HTML con la jerarquía v3: header → banda de alertas → HERO (Plan) →
>    strip de KPIs con sparkline+meta → flow bar → (gráfico + MSPA con semáforos) → rankings.
> 4. Sumá la **banda de alertas por excepción** (`build_alerts`/`render_alerts`); si no
>    hay alertas, no se renderiza. Dejá los umbrales como están y avisame cuáles son.
> 5. Sumá **estado de conexión + "datos al"** en el header y en cada card.
> 6. Sumá los botones **export (window.print)**, **modo TV** (toggle `body.tv`) y dark.
> 7. Para los **sparklines** necesito una query de los últimos 14 días hábiles por KPI;
>    proponé la consulta y dónde engancharla (sin tocar lo existente).
>
> Mantené el rojo Würth `#cc0000`, el español y light/dark. Mostrame los cambios.

---

## Mapa de marcado v3 (orden dentro de `.main`)
```html
<div class="hdr"> … logo · título · [conn: 2 filas con conn-dot + "datos al"] · date-badge · botones download/tv/moon … </div>

<div class="main">
  {render_alerts(d)}                      <!-- banda; vacía si no hay excepciones -->

  <div class="hero"> … Plan de Ventas (héroe) + Venta del Día / Pedidos … </div>

  <div class="sec"><div class="sec-lbl">Indicadores del día · últimos 14 días hábiles</div>
    <div class="kpi-grid">
      <div class="kpi"><div class="kpi-lbl">…</div>
        <div class="kpi-top"><div class="kpi-val num">…</div>{sparkline(serie)}</div>
        <div class="kpi-foot">{delta}{meta_chip(curr,target)}</div></div>
      …×4
    </div></div>

  <div class="sec"> … flow-bar (Informado→Retenido→Anulado→Facturado) … </div>

  <div class="bottom">
    <div class="card"> … gráfico tendencia + <span class="stamp">datos al …</span> … </div>
    <div class="card"> … MSPA: cada fila con <span class="mspa-sem {sev}"></span> … </div>
  </div>

  <div class="sec"> … 3 rankings de vendedores … </div>
</div>
```

### Alertas (HTML que emite `render_alerts`)
```html
<div class="alerts">
  <div class="alert warn">{icon}<span>…<b>…</b>…</span><a class="a-act" href="#">Ver … →</a></div>
  <div class="alert danger">…</div>
</div>
```
Severidades: `warn` (ámbar) / `danger` (rojo). Sólo agregá las que crucen umbral.

### Conexión en el header
```html
<div class="conn">
  <span class="conn-row"><span class="conn-dot ok"></span>MSPA OK · datos al <b>14:32:07</b></span>
  <span class="conn-row"><span class="conn-dot slow"></span>Reactor lento · <b>14:25:00</b></span>
</div>
```
`conn-dot`: `ok` (verde, pulsa) · `slow` (ámbar) · `down` (rojo).

### Modo TV / Export / Skeleton
- **TV:** botón que hace `document.body.classList.toggle('tv')`. El CSS agranda números.
- **Export:** botón → `window.print()`. El `@media print` ya oculta controles.
- **Skeleton:** si cargás async, poné `class="main is-loading"` mientras esperás los
  datos y quitala al llegar; el shimmer lo hace el CSS solo. (Si generás server-side
  de una, no hace falta.)

---

## Estados de color (recordatorio)
- **Plan:** verde si ≥100%, rojo Würth si en ritmo (≥pace), ámbar si por debajo.
- **Deltas:** verde sube / rojo baja (clases `.up` / `.down`).
- **KPIs:** número siempre neutro; color sólo en delta/meta/sparkline.
- **Sparkline `auto`:** verde si la serie sube, rojo si baja.
- **Semáforo MSPA:** `mspa-sem` (verde) / `.warn` (ámbar) / `.danger` (rojo).

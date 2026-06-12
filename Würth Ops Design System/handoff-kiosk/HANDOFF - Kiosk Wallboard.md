# HANDOFF — KIOSK / WALLBOARD para dashboard.py (modo CLARO, sala de control)

Para Claude Code. Agrega un **modo kiosk de pantalla de pared** a tu `dashboard.py` y
**reemplaza el kiosk paginado actual** (el del play / X / “PÁGINA 1 DE 2”). El kiosk nuevo
es un **tablero que se estira a toda la TV (sin barras), en modo claro, sin scroll, con
controles discretos, y rota en silencio entre 2 tableros.**

## Archivos de este paquete
- **`kiosk.html`** — el kiosk COMPLETO y funcionando (vanilla JS, sin React/Babel). Es la
  referencia exacta: copiá de acá el HTML/CSS/JS.
- **`kiosk.css`** — los estilos del kiosk (modo claro, tipos grandes, 2 tableros, controles).

> Abrí `kiosk.html` en un navegador para ver el objetivo exacto.

---

## ⚠️ Reglas de oro
1. **No toques las consultas SQL ni la lógica de negocio.** El kiosk consume los MISMOS datos.
2. **Vanilla JS, sin React ni Babel.** Un wallboard NO debe compilar código en el navegador.
3. **Reemplazá el kiosk viejo** (sacá play, flechas y la “X” flotante).

---

## Novedades de esta versión (vs. el primer handoff de kiosk)
1. **Modo CLARO** — fondo gris claro, paneles blancos, texto oscuro, barra superior blanca
   con línea roja Würth. Combina con el dashboard normal y con la marca.
2. **Se estira a toda la TV (sin barras negras)** — el escalado usa `scale(sx, sy)` no
   uniforme para llenar el 100% del viewport. En una TV 16:9 no hay distorsión visible.
3. **Controles operables** — barra abajo a la derecha (aparece al mover el mouse, se oculta
   a los 3s): ◀ anterior · ⏸ pausar · ▶ siguiente · indicador “1 / 2” · ⛶ pantalla completa
   · ✕ salir. **Dots clickeables.** **Teclado:** ← → cambian, espacio pausa, F pantalla, Esc sale.
4. **Logo Würth** visible (sin filtros que lo desvirtúen).
5. **Carga a prueba de red** — el primer pintado NO tiene recursos externos. El font y
   Chart.js se cargan dinámicamente por JS después de renderizar. Si el CDN falla, el
   tablero igual se ve (y el gráfico muestra un mensaje de fallback).

---

## Arquitectura a implementar

### 1. Ruta / modo kiosk
Serví el kiosk como vista aparte: `GET /kiosk`. Devuelve el HTML del kiosk con su `<style>`
(de `kiosk.css`) y su `<script>` (de `kiosk.html`). La TV abre `http://servidor:puerto/kiosk`.

### 2. Escalado a pantalla completa (sin barras)
```js
function fitStage(){
  const sx = window.innerWidth/1920, sy = window.innerHeight/1080;
  document.getElementById('stage').style.transform = 'scale('+sx+','+sy+')';   // estira, sin letterbox
}
fitStage(); window.addEventListener('resize', fitStage);
```
> Si preferís SIN distorsión y aceptás bandas mínimas, usá `Math.min(sx,sy)` para ambos.
> Para una TV 16:9 el estiramiento es imperceptible; por eso va así por defecto.

### 3. Los 2 tableros
- **Tablero 1 — Operación hoy:** Plan GIGANTE + Proyección de cierre + Venta del Día +
  Pedidos Informados (con “vs. mismo día hábil mes anterior”) + Flujo del día + strip
  **“En vivo · parcial”** subordinado.
- **Tablero 2 — Tendencia & estado:** gráfico (Chart.js) + MSPA con semáforos + ritmo mensual.

HTML/CSS exacto en `kiosk.html` / `kiosk.css`. Copialo y enchufá tus datos reales.

### 4. Controles + rotación
Ya está todo en `kiosk.html`: `goTo(n)`, `next()`, `prev()`, `togglePause()`, `toggleFull()`,
`exitKiosk()`. La barra de controles vive FUERA del `.stage` (no escala, siempre clickeable).
- **`exitKiosk()`**: en el mock va a `index.html`. **En producción apuntalo a tu dashboard
  normal**, ej. `window.location.href = '/'`.
- Rotación cada `ROTATE_MS` (18s, ajustable). Pausa congela la barra de progreso.

### 5. Datos — enchufar los reales (NO inventar)
En `kiosk.html` los datos son constantes mock (`PLAN`, `FLOW`, `VENTA`, `PEDIDOS`, `HOY`,
`MSPA`, `TREND`) con la MISMA forma que devuelve tu backend. Reemplazá cada una por tus
valores reales. Mantené los formateadores `fmtN`/`fmtK` (es-AR, coma decimal).

> **Empty state del strip “EN VIVO”:** a primera hora HOY viene en 0. En vez de mostrar una
> fila de `$0 / 0,0`, mostrá un texto calmo: *“Aún sin movimiento hoy · primeros pedidos en
> breve”*. (En el mock los valores van cargados; agregá el check `if (HOY.pedidos === 0)`.)

### 6. Refresco en su lugar (sin recargar)
```js
async function refrescar(){
  try{
    const r = await fetch('/data'); const d = await r.json();
    Object.assign(PLAN, d.plan); Object.assign(FLOW, d.flow); /* …etc… */
    render();                    // redibuja el tablero activo, sin perder rotación/scroll
  }catch(e){ /* poné los kt-dot en 'down' */ }
}
setInterval(refrescar, 60000);
```

### 7. Robustez (lo que evita la pantalla en blanco) — YA implementado
- El primer pintado **no tiene `<link>` ni `<script>` externos**. El font se inyecta con
  `setTimeout` y Chart.js con `ensureChartJs()` recién cuando se muestra el Tablero 2.
- **Recomendado en producción:** hosteá Chart.js y la fuente **localmente** en tu server,
  así el wallboard funciona con sólo red local (sin internet). Cambiá las URLs del CDN por
  rutas locales.

---

## Checklist de aceptación
- [ ] `/kiosk` abre un tablero CLARO a pantalla completa, **sin barras negras**, sin scroll.
- [ ] Logo Würth visible; barra superior blanca con línea roja.
- [ ] Plan gigante + proyección + flujo + “en vivo” subordinado en el Tablero 1.
- [ ] Rota a Tendencia/MSPA/Ritmo cada ~18s; dots clickeables; barra de progreso.
- [ ] Al mover el mouse aparece la barra de controles (prev/pausa/next/pantalla/salir).
- [ ] Teclado: ← → cambian, espacio pausa, F pantalla, Esc sale.
- [ ] Carga aunque el CDN vaya lento (primer pintado sin recursos externos).
- [ ] Refresco por fetch sin `location.reload()`.
- [ ] Strip “EN VIVO” con empty state cuando el día viene en 0.

## PROMPT para pegar en Claude Code
> Agregá un modo kiosk/wallboard a mi dashboard.py y reemplazá el kiosk paginado actual
> (sacá play, flechas y la “X”). Usá como referencia EXACTA los archivos kiosk.html y
> kiosk.css de este paquete: tablero en MODO CLARO, vanilla JS (sin React/Babel), que se
> ESTIRA a toda la TV sin barras negras (transform scale(sx,sy)), sin scroll, con controles
> que aparecen al mover el mouse (anterior/pausa/siguiente/pantalla completa/SALIR), dots
> clickeables y atajos de teclado (← → espacio F Esc). Servílo en /kiosk; exitKiosk() debe
> ir a mi dashboard normal '/'. Copiá el HTML/CSS/JS y enchufá MIS datos reales en lugar de
> las constantes mock (PLAN, FLOW, VENTA, PEDIDOS, HOY, MSPA, TREND) manteniendo mis
> formateadores es-AR. Agregá empty state en el strip EN VIVO cuando el día viene en 0.
> El primer pintado NO debe tener recursos externos: cargá font y Chart.js por JS después
> de renderizar (ideal: hostealos localmente). Refresco por fetch sin location.reload().
> No toques las consultas SQL ni la lógica existente. Mostrame los diffs.

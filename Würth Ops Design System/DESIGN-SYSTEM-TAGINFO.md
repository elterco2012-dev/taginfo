# DESIGN SYSTEM — TagInfo / Würth Ops

> **Fuente de verdad única y portable.** Este documento contiene todo lo necesario para
> reconstruir el design system *TagInfo / Würth Ops* en otra cuenta o instancia, sin
> acceso a los archivos originales. Está derivado del repositorio `elterco2012-dev/taginfo`
> (https://github.com/elterco2012-dev/taginfo): `dashboard.py` (dashboard de operaciones
> moderno) y `taginfo_web.py` (terminal verde legacy). Idioma de producto: **Español
> (Argentina, es-AR)**.

---

## 0. Resumen del sistema

Es el sistema visual de una herramienta interna **read-only** de monitoreo de ventas para
una operación **Würth** en Argentina, que fusiona dos ERPs: **Reactor** (MySQL) y **MSPA**
(Informix). Tiene **dos superficies** que comparten una sola marca:

| Superficie | Origen | Estética | Uso |
|---|---|---|---|
| **Operations Dashboard** | `dashboard.py` | Slate moderno, light **+** dark, regla roja Würth, KPIs, gráficos | Producto principal. Dashboards, reportes, KPIs, kiosk de pared. |
| **DAILY INFO 2 SALES** (terminal) | `taginfo_web.py` | Verde fósforo sobre negro, Courier, reglas ASCII | Vistas "ERP crudo", lectura de estado legacy. |

**Una sola marca de color:** rojo Würth `#cc0000`, usado con moderación (logo, regla del
header, acción primaria, barra de plan). El resto de la UI la cargan los neutros slate y
una paleta de acentos **semánticos** (no decorativos).

---

# 1. TOKENS DE DISEÑO

## 1.1 Colores — JSON

```json
{
  "brand": {
    "wurth-red":        "#cc0000",
    "wurth-red-hover":  "#b00000",
    "wurth-red-bg":     "#fff7f7",
    "wurth-red-bg-dk":  "#3b0d0d"
  },
  "neutral-light": {
    "bg":        "#f0f2f5",
    "surface":   "#ffffff",
    "surface-2": "#f8fafc",
    "border":    "#e2e8f0",
    "border-2":  "#cbd5e1",
    "text":      "#0f172a",
    "text-2":    "#475569",
    "text-3":    "#94a3b8"
  },
  "neutral-dark": {
    "bg":        "#0f172a",
    "surface":   "#1e293b",
    "surface-2": "#0f1a30",
    "border":    "#334155",
    "border-2":  "#475569",
    "text":      "#f1f5f9",
    "text-2":    "#cbd5e1",
    "text-3":    "#64748b"
  },
  "accent": {
    "blue":   "#2563eb",
    "cyan":   "#0891b2",
    "green":  "#059669",
    "amber":  "#d97706",
    "orange": "#ea580c",
    "red":    "#dc2626",
    "purple": "#7c3aed"
  },
  "accent-bg-light": {
    "blue-bg":  "#eff6ff",
    "green-bg": "#f0fdf4",
    "amber-bg": "#fffbeb",
    "red-bg":   "#fef2f2"
  },
  "accent-bg-dark": {
    "blue-bg":  "#0d2045",
    "green-bg": "#052e16",
    "amber-bg": "#3b2800",
    "red-bg":   "#3b0d0d"
  },
  "status-pills": {
    "pos-bg": "#dcfce7", "pos-fg": "#15803d",
    "neg-bg": "#fee2e2", "neg-fg": "#b91c1c",
    "flat-bg": "#f1f5f9", "flat-fg": "#94a3b8"
  },
  "terminal": {
    "term-bg":        "#000000",
    "term-fg":        "#b4d900",
    "term-fg-dim":    "#4a6400",
    "term-fg-dimmer": "#3a4a00",
    "term-row-hover": "#0a1400",
    "term-error":     "#ff4444",
    "term-bar-bg":    "#b4d900",
    "term-bar-fg":    "#000000"
  }
}
```

### Significado semántico de los acentos (no decorar con ellos)
- **blue** `#2563eb` → "informado" / KPI primario.
- **green** `#059669` → ventas / positivo / "facturado".
- **amber** `#d97706` → advertencia / "retenido".
- **red** `#dc2626` → peligro / "anulado".
- **cyan** `#0891b2`, **orange** `#ea580c` → KPIs secundarios.
- **purple** `#7c3aed` → acento extra, raro.
- **Regla de oro:** el color codifica **estado**, no jerarquía. Los números de KPI van en
  neutro (`--text`); el color se reserva para deltas, estados, alertas y los "ticks".

## 1.2 Colores — Variables CSS (light por defecto, dark por clase)

```css
:root{
  /* Marca */
  --wurth-red:#cc0000; --wurth-red-hover:#b00000;
  --wurth-red-bg:#fff7f7; --wurth-red-bg-dk:#3b0d0d;
  /* Neutros / superficies */
  --bg:#f0f2f5; --surface:#ffffff; --surface-2:#f8fafc;
  --border:#e2e8f0; --border-2:#cbd5e1;
  --text:#0f172a; --text-2:#475569; --text-3:#94a3b8;
  /* Acentos funcionales */
  --blue:#2563eb; --cyan:#0891b2; --green:#059669;
  --amber:#d97706; --orange:#ea580c; --red:#dc2626; --purple:#7c3aed;
  /* Fondos tintados */
  --blue-bg:#eff6ff; --green-bg:#f0fdf4; --amber-bg:#fffbeb; --red-bg:#fef2f2;
  /* Pills de estado */
  --pos-bg:#dcfce7; --pos-fg:#15803d;
  --neg-bg:#fee2e2; --neg-fg:#b91c1c;
  --flat-bg:#f1f5f9; --flat-fg:#94a3b8;
}
body.dark, .theme-dark{
  --bg:#0f172a; --surface:#1e293b; --surface-2:#0f1a30;
  --border:#334155; --border-2:#475569;
  --text:#f1f5f9; --text-2:#cbd5e1; --text-3:#64748b;
  --blue-bg:#0d2045; --green-bg:#052e16; --amber-bg:#3b2800; --red-bg:#3b0d0d;
  --shadow-card:0 1px 3px rgba(0,0,0,.3); --shadow-pop:0 8px 24px rgba(0,0,0,.5);
}
/* Terminal (paleta aparte, sólo en la superficie terminal) */
:root{
  --term-bg:#000000; --term-fg:#b4d900; --term-fg-dim:#4a6400;
  --term-fg-dimmer:#3a4a00; --term-row-hover:#0a1400; --term-error:#ff4444;
  --term-bar-bg:#b4d900; --term-bar-fg:#000000;
}
```

> **Nota dark mode:** en el dashboard original `--surface-2` = `#1e293b` (igual que
> surface); en la v3 evolucionada `--surface-2` = `#0f1a30` (un punto más oscuro para
> insets). Usá `#0f1a30` en sistemas nuevos.

## 1.3 Tipografía

**Familias**
```css
--font-sans: 'IBM Plex Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
--font-mono: 'Courier New', Courier, ui-monospace, monospace;   /* y terminal */
--font-term: 'Courier New', Courier, ui-monospace, monospace;
```
- El dashboard **v1/v2** usaba el **system stack** nativo. La **v3** introdujo
  **IBM Plex Sans** (Google Fonts, pesos 400/500/600/700) como fuente de números dedicada
  por sus tabular-nums. Recomendado para sistemas nuevos; cae al system stack si no carga.
- **Números:** SIEMPRE `font-variant-numeric: tabular-nums; font-feature-settings:"tnum"`
  (clase `.num`) en cualquier cifra que se actualice, para que los dígitos no "salten".

**Pesos**
```
--fw-normal:400  --fw-medium:500  --fw-semibold:600
--fw-bold:700    --fw-extrabold:800  --fw-black:900
```

**Escala de tamaños (px) + line-height + uso por jerarquía**

| Token | px | Peso | LH | Uso |
|---|---|---|---|---|
| `--fs-display` | 32 (hero hasta 46–64) | 700–800 | 1.0–1.1 | Número hero de KPI / Plan |
| `--fs-stat` | 22 (plan 26) | 700–800 | 1.1 | Valor de flujo, stat del hero |
| `--fs-h` | 14 | 700 | 1.3 | Títulos de card / header |
| `--fs-body` | 13 | 400 | 1.5 | Cuerpo base |
| `--fs-sm` | 12 | 400 | 1.5 | Celdas de tabla, secundario |
| `--fs-xs` | 11 | 400 | 1.4 | Captions |
| `--fs-2xs` | 10 | 400/600 | 1.4 | Labels de KPI, subtexto |
| `--fs-3xs` | 9 | 700 | 1.0 | Eyebrows de sección (UPPERCASE, tracking 1.4–2px) |

**Letter-spacing**
```
--ls-label: 2px;    /* labels de sección en mayúscula (1.4px en v3) */
--ls-wordmark: 3px; /* wordmark WÜRTH */
```

**Terminal**: `Courier New` 16px / peso 400 / line-height 1.5; banner centrado 17px /700
/ tracking 2px; barra de título inversa (fondo lima, texto negro) 700.

**Clases tipográficas semánticas** (superficie dashboard):
```css
.ty-display { font:800 32px/1.1 var(--font-sans); }
.ty-stat    { font:800 22px/1.1 var(--font-sans); }
.ty-h       { font:700 14px/1.3 var(--font-sans); color:var(--text); }
.ty-body    { font:400 13px/1.5 var(--font-sans); color:var(--text); }
.ty-sm      { font:400 12px/1.5 var(--font-sans); color:var(--text-2); }
.ty-caption { font:400 10px/1.4 var(--font-sans); color:var(--text-3); }
.ty-section { font:700 9px/1 var(--font-sans); text-transform:uppercase;
              letter-spacing:2px; color:var(--text-3); }
.ty-mono    { font:400 13px/1.5 var(--font-mono); }
.ty-term    { font:400 16px/1.5 var(--font-term); color:var(--term-fg); background:var(--term-bg); }
```

## 1.4 Espaciado, radios, sombras, breakpoints

**Escala de espaciado (px)**
```css
--sp-1:4px; --sp-2:6px; --sp-3:8px; --sp-4:10px;
--sp-5:14px; --sp-6:16px; --sp-7:20px; --sp-8:24px;
```
Padding de card típico 16–20px; gaps de grilla 10–18px; gutters de página 24–28px.

**Radios de borde**
```css
--r-card:10px;   /* cards, KPIs, flow bars, popovers, alertas */
--r-ctrl:6px;    /* botones, inputs, badges, state-tags */
--r-pill:20px;   /* pills de delta/estado (12px en variantes chicas) */
/* terminal: 0 (sin redondeo) */
```

**Sombras / elevación** (suaves, casi planas)
```css
--shadow-card:   0 1px 3px rgba(0,0,0,.05);  /* card en reposo (dark: .3) */
--shadow-header: 0 1px 4px rgba(0,0,0,.06);  /* header sticky */
--shadow-pop:    0 8px 24px rgba(0,0,0,.15); /* popovers/menús (dark: .5) */
```
> La v3 prefiere **hairline plano de 1px sin sombra** en las cards (border-only). Elegí
> *una* estrategia: borde **o** sombra, no ambas.

**Breakpoints**
```css
@media (max-width:1080px){ /* hero→1col, bottom→1col, sellers→1col, kpi→2col */ }
@media (max-width:980px) { /* variante v1: kpi→2col, bottom→1col */ }
@media print { /* ocultar controles del header; break-inside:avoid en cards */ }
```

**Contenedor**: `.main { max-width:1440px; margin:0 auto; padding:20px 28px 40px; }`
(v2 usaba 1400px). **Nunca** dejar el contenido a ancho completo en monitores grandes
(salvo modo TV/kiosk).

---

# 2. INVENTARIO DE COMPONENTES

Convenciones: todos consumen las variables CSS de §1.2. Los números llevan la clase
`.num` (tabular). Base global:

```css
*{margin:0;padding:0;box-sizing:border-box}
body{background:var(--bg);color:var(--text);font-family:var(--font-sans);
     font-size:13px;transition:background .25s,color .25s}
.num{font-variant-numeric:tabular-nums;font-feature-settings:"tnum"}
.ico{width:15px;height:15px;stroke-width:1.75;vertical-align:-2px;flex-shrink:0}
.ico-sm{width:13px;height:13px;stroke-width:1.75;vertical-align:-2px}
```

## 2.1 Header (sticky, regla roja, conexión, controles)

```css
.hdr{position:sticky;top:0;z-index:50;background:var(--surface);
  border-bottom:1px solid var(--border);padding:0 28px;height:58px;
  display:flex;align-items:center;justify-content:space-between}
.hdr::before{content:'';position:absolute;left:0;top:0;bottom:0;width:3px;background:var(--wurth-red)}
.hdr-left{display:flex;align-items:center;gap:14px}
.hdr-logo{height:30px;width:auto}
.div-v{width:1px;height:26px;background:var(--border)}
.hdr-title{font-size:13px;font-weight:700;color:var(--text);white-space:nowrap;letter-spacing:-.1px}
.hdr-sub{font-size:10px;color:var(--text-3);margin-top:1px;letter-spacing:.3px}
.hdr-right{display:flex;align-items:center;gap:14px;flex-shrink:0}
/* Estado de conexión por fuente */
.conn{display:flex;flex-direction:column;gap:3px;font-size:10px;color:var(--text-3);text-align:right;line-height:1.3}
.conn-row{display:flex;align-items:center;gap:5px;justify-content:flex-end}
.conn-dot{width:7px;height:7px;border-radius:50%;flex-shrink:0}
.conn-dot.ok{background:var(--green);box-shadow:0 0 0 0 rgba(5,150,105,.5);animation:ring 2.4s ease-out infinite}
.conn-dot.slow{background:var(--amber)}
.conn-dot.down{background:var(--red)}
.conn b{color:var(--text-2);font-variant-numeric:tabular-nums}
@keyframes ring{0%{box-shadow:0 0 0 0 rgba(5,150,105,.4)}70%,100%{box-shadow:0 0 0 5px rgba(5,150,105,0)}}
/* Botón de ícono (dark toggle, export, TV) */
.icon-btn{display:flex;align-items:center;justify-content:center;cursor:pointer;
  border:1px solid var(--border-2);border-radius:6px;width:32px;height:30px;
  background:transparent;color:var(--text-2);transition:all .15s}
.icon-btn:hover{background:var(--surface-2);color:var(--text)}
.icon-btn.on{background:var(--wurth-red);border-color:var(--wurth-red);color:#fff}  /* estado activo */
.icon-btn .ico{width:16px;height:16px}
```
```html
<div class="hdr">
  <div class="hdr-left">
    <img class="hdr-logo" src="wurth-logo.png" alt="Würth">
    <div class="div-v"></div>
    <div>
      <div class="hdr-title">Operations Dashboard</div>
      <div class="hdr-sub">Reactor · MSPA · Sala de Control</div>
    </div>
  </div>
  <div class="hdr-right">
    <div class="conn">
      <span class="conn-row"><span class="conn-dot ok"></span>MSPA OK · datos al <b>14:32:07</b></span>
      <span class="conn-row"><span class="conn-dot slow"></span>Reactor lento · <b>14:25:00</b></span>
    </div>
    <button class="icon-btn" title="Exportar">…</button>
    <button class="icon-btn" title="Modo TV">…</button>
    <button class="icon-btn" title="Modo oscuro">…</button>
  </div>
</div>
```
**Variantes/estados:** `conn-dot` = `ok` (verde, pulsa) / `slow` (ámbar) / `down` (rojo).
`icon-btn` normal / `.on` (activo, fondo rojo) / `:hover`.

## 2.2 Logo (marca + fallback CSS)
Imagen `wurth-logo.png` (shield-W rojo + wordmark). Si no carga, fallback en texto:
```html
<span style="display:inline-flex;align-items:center;gap:6px">
  <span style="background:#cc0000;color:#fff;font-weight:900;font-size:18px;
               padding:6px 10px;border-radius:3px;line-height:1">W</span>
  <span style="font-size:22px;font-weight:900;letter-spacing:3px;color:#cc0000">WÜRTH</span>
</span>
```

## 2.3 Date badge + popover

```css
.date-badge{display:flex;align-items:center;gap:6px;background:transparent;
  border:1px solid var(--border-2);border-radius:6px;padding:5px 12px;font-size:12px;
  color:var(--text);font-weight:600;white-space:nowrap;cursor:pointer;user-select:none;
  position:relative;transition:background .15s}
.date-badge:hover{background:var(--surface-2)}
.date-badge .ico{color:var(--text-3)}
.date-pop{position:absolute;top:calc(100% + 8px);right:0;z-index:999;background:var(--surface);
  border:1px solid var(--border-2);border-radius:10px;box-shadow:var(--shadow-pop);
  padding:14px;min-width:230px;text-align:left}
.date-pop h4{font-size:11px;font-weight:700;margin-bottom:8px}
.date-pop input{border:1px solid var(--border-2);border-radius:6px;padding:7px 10px;
  font-size:13px;color:var(--text);background:var(--surface-2);width:100%}
body.dark .date-pop input{color-scheme:dark}
.date-pop .hint{font-size:10px;color:var(--text-3);margin-top:8px;line-height:1.4}
.date-pop .go{margin-top:10px;width:100%;background:var(--wurth-red);color:#fff;border:none;
  border-radius:6px;padding:7px;font-size:12px;font-weight:700;cursor:pointer}
.date-pop .go:hover{background:var(--wurth-red-hover)}
.date-pop .clr{margin-top:5px;width:100%;background:transparent;color:var(--text-3);
  border:1px solid var(--border);border-radius:6px;padding:6px;font-size:11px;cursor:pointer}
```
**Estados:** badge `:hover`; popover abierto/cerrado; `.go` (acción primaria roja, hover
#b00000); `.clr` (acción secundaria neutra). Modo histórico: cuando se elige fecha pasada,
mostrar banner de contexto.

## 2.4 Botones (primario / fantasma / texto)

```css
.btn{border-radius:6px;padding:7px 16px;font-size:12px;font-weight:700;cursor:pointer;border:none}
.btn.primary{background:var(--wurth-red);color:#fff}
.btn.primary:hover{background:var(--wurth-red-hover)}            /* press: mismo #b00000 */
.btn.ghost{background:transparent;color:var(--text-2);border:1px solid var(--border-2);font-weight:600}
.btn.ghost:hover{background:var(--border);color:var(--text)}
.btn.clear{background:transparent;color:var(--text-3);border:1px solid var(--border);font-weight:400}
.btn:disabled{opacity:.5;cursor:not-allowed}                    /* estado disabled */
```

## 2.5 Banda de alertas (por excepción)

```css
.alerts{display:flex;flex-direction:column;gap:8px}
.alert{display:flex;align-items:center;gap:10px;padding:11px 16px;border-radius:var(--r-card);
  border:1px solid;font-size:13px}
.alert .ico{width:17px;height:17px;flex-shrink:0}
.alert b{font-weight:700}
.alert .a-act{margin-left:auto;font-size:11px;font-weight:600;text-decoration:none;
  white-space:nowrap;opacity:.8;color:inherit}
.alert.warn{background:var(--amber-bg);border-color:var(--amber);color:var(--amber)}
.alert.danger{background:var(--red-bg);border-color:var(--red);color:var(--neg-fg)}
.alert.danger .ico{color:var(--red)}
```
```html
<div class="alerts">
  <div class="alert warn"><!--icon-->
    <span>Plan de ventas <b>8,8 pts por debajo del ritmo</b> (29,3% vs 38%)</span>
    <a class="a-act" href="#">Ver plan →</a>
  </div>
</div>
```
**Lógica:** se construye una lista; si está vacía, **no se renderiza la banda**.
Severidades `warn` / `danger` por umbral. Una alarma = una vez (no duplicar con el pulso
del flujo). Umbrales por defecto: retenidos ≥20% warn, ≥30–35% danger; plan < ritmo → warn.

## 2.6 Hero — Plan de Ventas (métrica norte)

```css
.hero{display:grid;grid-template-columns:1.5fr 1fr;gap:1px;background:var(--border);
  border:1px solid var(--border);border-radius:var(--r-card);overflow:hidden}
.hero-main{background:var(--surface);padding:22px 26px}
.hero-side{background:var(--surface);padding:22px 26px;display:flex;flex-direction:column;
  justify-content:center;gap:18px}
.hero-eyebrow{display:flex;align-items:center;gap:6px;font-size:10px;font-weight:700;
  letter-spacing:1.4px;text-transform:uppercase;color:var(--text-3);margin-bottom:14px;white-space:nowrap}
.hero-eyebrow .ico{width:13px;height:13px;color:var(--wurth-red)}
.hero-figs{display:flex;align-items:baseline;gap:10px;margin-bottom:4px}
.hero-curr{font-size:46px;font-weight:700;color:var(--text);line-height:1;letter-spacing:-1px;font-variant-numeric:tabular-nums}
.hero-total{font-size:18px;color:var(--text-3);font-weight:600;font-variant-numeric:tabular-nums}
.hero-pct-line{display:flex;align-items:center;gap:10px;margin:14px 0 8px}
.hero-pct{font-size:14px;font-weight:700;font-variant-numeric:tabular-nums}
.plan-bar-bg{background:var(--border);border-radius:6px;height:12px;position:relative;overflow:hidden;flex:1}
.plan-bar-fill{height:100%;border-radius:6px;transition:width .8s ease}
.plan-bar-pace{position:absolute;top:-3px;bottom:-3px;width:2px;background:var(--text);z-index:2}
.plan-bar-pace::after{content:'';position:absolute;top:-3px;left:-2px;border-left:3px solid transparent;
  border-right:3px solid transparent;border-top:4px solid var(--text)}
.hero-foot{display:flex;justify-content:space-between;font-size:11px;color:var(--text-3);margin-top:4px;font-variant-numeric:tabular-nums}
.hero-stat .l{font-size:10px;color:var(--text-3);text-transform:uppercase;letter-spacing:.5px;margin-bottom:4px}
.hero-stat .v{font-size:28px;font-weight:700;color:var(--text);line-height:1;font-variant-numeric:tabular-nums}
.hero-stat .d{margin-top:6px;display:flex;align-items:center;gap:8px}
.hsep{height:1px;background:var(--border)}
/* state-tag (en ritmo / por debajo) */
.state-tag{display:inline-flex;align-items:center;gap:4px;font-size:11px;padding:3px 9px;
  border-radius:6px;font-weight:600;white-space:nowrap}
.state-ok{background:var(--pos-bg);color:var(--pos-fg)}
.state-warn{background:var(--amber-bg);color:var(--amber)}
```
**Color de la barra (lógica):** verde si pct ≥ 100; rojo Würth si en ritmo (pct ≥ pace);
ámbar si por debajo. El `state-tag` sigue la misma regla. La columna lateral muestra
Venta del Día + Pedidos Informados con su delta. Incluir Proyección de cierre.

## 2.7 KPI card (sparkline + meta + delta)

```css
.kpi-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:1px;background:var(--border);
  border:1px solid var(--border);border-radius:var(--r-card);overflow:hidden}
.kpi{background:var(--surface);padding:15px 18px;display:flex;flex-direction:column;gap:0}
.kpi-lbl{font-size:10px;color:var(--text-3);margin-bottom:7px;font-weight:600;text-transform:uppercase;letter-spacing:.4px}
.kpi-top{display:flex;align-items:flex-end;justify-content:space-between;gap:10px}
.kpi-val{font-size:25px;font-weight:700;line-height:1;color:var(--text);font-variant-numeric:tabular-nums}
.spark{width:74px;height:30px;flex-shrink:0;opacity:.9}    /* trazo SIEMPRE gris --text-3 */
.kpi-foot{display:flex;align-items:center;gap:8px;margin-top:9px;flex-wrap:wrap}
.delta{display:inline-flex;align-items:center;gap:2px;font-size:11px;font-weight:700;font-variant-numeric:tabular-nums}
.delta .ico{width:13px;height:13px}
.delta.up{color:var(--pos-fg)}.delta.down{color:var(--neg-fg)}
.meta-chip{display:inline-flex;align-items:center;gap:4px;font-size:10px;color:var(--text-3);font-variant-numeric:tabular-nums}
.meta-chip .dot{width:6px;height:6px;border-radius:50%}
.meta-chip .dot.ok{background:var(--green)}.meta-chip .dot.warn{background:var(--amber)}
.kpi-sub{font-size:10px;color:var(--text-3);font-variant-numeric:tabular-nums}
```
**Sparkline (SVG, sin librerías), trazo gris neutro:**
```js
function sparkline(data, color='var(--text-3)', w=74, h=30){
  if(!data||data.length<2) return '';
  const mn=Math.min(...data),mx=Math.max(...data),rng=(mx-mn)||1,pad=2;
  const step=(w-pad*2)/(data.length-1);
  const pts=data.map((v,i)=>[pad+i*step, h-pad-((v-mn)/rng)*(h-pad*2)]);
  const d=pts.map((p,i)=>(i?'L':'M')+p[0].toFixed(1)+' '+p[1].toFixed(1)).join(' ');
  const c=color;
  return `<svg class="spark" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none">
    <path d="${d}" fill="none" stroke="${c}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
    <circle cx="${pts.at(-1)[0].toFixed(1)}" cy="${pts.at(-1)[1].toFixed(1)}" r="2" fill="${c}"/></svg>`;
}
```
**Delta:** `up` (verde, ▲) / `down` (rojo, ▼). **meta-chip:** dot `ok` (verde, llegó) /
`warn` (ámbar, no llegó).

## 2.8 Flow bar (lifecycle de pedidos)

```css
.flow-bar{display:flex;align-items:stretch;background:var(--surface);border:1px solid var(--border);
  border-radius:var(--r-card);overflow:hidden}
.flow-cell{flex:1;padding:15px 20px;display:flex;flex-direction:column;gap:5px;min-width:0;border-left:1px solid var(--border)}
.flow-cell:first-child{border-left:none}
.flow-dot{display:flex;align-items:center;gap:7px}
.flow-tick{width:8px;height:8px;border-radius:2px}
.flow-label{font-size:10px;font-weight:700;letter-spacing:.6px;text-transform:uppercase;color:var(--text-2)}
.flow-val{font-size:24px;font-weight:700;line-height:1;color:var(--text);font-variant-numeric:tabular-nums}
.flow-sub{font-size:11px;color:var(--text-3);font-variant-numeric:tabular-nums}
.tk-blue{background:var(--blue)}.tk-amber{background:var(--amber)}.tk-red{background:var(--red)}.tk-green{background:var(--green)}
```
4 celdas: **Informado** (tk-blue) → **Retenido** (tk-amber) → **Anulado** (tk-red) →
**Facturado** (tk-green). El color va sólo en el tick de 8px; el número es neutro.

## 2.9 Panel MSPA (filas con semáforo)

```css
.card{background:var(--surface);border:1px solid var(--border);border-radius:var(--r-card);padding:18px 20px}
.card-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:14px}
.card-head .stamp{font-size:10px;color:var(--text-3);font-variant-numeric:tabular-nums}
.mspa-row{display:flex;align-items:center;justify-content:space-between;padding:10px 0;border-bottom:1px solid var(--border)}
.mspa-row:last-child{border-bottom:none}
.mspa-l{display:flex;align-items:center;gap:9px}
.mspa-sem{width:7px;height:7px;border-radius:50%;background:var(--green);flex-shrink:0}
.mspa-sem.warn{background:var(--amber)}.mspa-sem.danger{background:var(--red)}
.mspa-lbl{font-size:12px;color:var(--text-2)}
.mspa-val{font-size:14px;font-weight:700;color:var(--text);text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums}
.mspa-val .s-sub{font-size:10px;color:var(--text-3);font-weight:400;white-space:nowrap;margin-top:1px}
.mspa-row.venta{border-top:1px solid var(--border);margin-top:2px;padding-top:13px}
.mspa-row.venta .mspa-lbl{color:var(--text);font-weight:700}
.mspa-row.venta .mspa-val{color:var(--green);font-size:18px}
.mspa-row.venta .mspa-sem{background:var(--green)}
```
**Variantes de fila:** normal / `.venta` (destacada, verde, con borde superior) /
semáforo `ok|warn|danger`.

## 2.10 Tablas de ranking (vendedores)

```css
.sellers-wrap{display:grid;grid-template-columns:repeat(3,1fr);gap:18px}
.seller-tbl{width:100%;border-collapse:collapse;font-size:12px}
.seller-tbl th{font-size:9px;font-weight:700;letter-spacing:.8px;text-transform:uppercase;
  color:var(--text-3);padding:0 8px 8px;border-bottom:1px solid var(--border);text-align:left}
.seller-tbl td{padding:9px 8px;border-bottom:1px solid var(--border)}
.seller-tbl tr:last-child td{border-bottom:none}
.seller-tbl tr:hover td{background:var(--surface-2)}
.s-rank{font-weight:700;color:var(--text-3);width:20px;font-size:12px;font-variant-numeric:tabular-nums;text-align:center}
.s-name{font-weight:600;color:var(--text)}
.s-sub{font-size:10px;color:var(--text-3);font-weight:400;font-variant-numeric:tabular-nums}
.s-val{font-weight:700;text-align:right;white-space:nowrap;color:var(--text);font-variant-numeric:tabular-nums}
.head-ico{display:flex;align-items:center;gap:6px}
.head-ico .ico{width:14px;height:14px}
.ic-fact{color:var(--green)}.ic-ret{color:var(--amber)}.ic-an{color:var(--red)}
```
3 paneles: **Top facturación** (ic-fact verde), **Más retenidos** (ic-ret ámbar), **Más
anulados** (ic-an rojo). El color sólo en el ícono del título; valores neutros.

## 2.11 Gráfico de tendencia (Chart.js)
Combo: barras *fantasma* gris (`rgba(203,213,225,.35)`, sin borde) = pedidos/día hábil
en eje izq; línea roja Würth protagonista (`#cc0000`, width 2.5–3, fill `rgba(204,0,0,.06–.08)`)
= M$/día hábil en eje der. Títulos en ambos ejes; `x` sin grid; coma decimal en ticks.
Contenedor `.chart-wrap{height:248px;position:relative}`. Destruir la instancia antes de
recrear; recrear al togglear dark/TV.

## 2.12 Status pills / tags

```css
.pill{display:inline-block;padding:2px 8px;border-radius:12px;font-size:10px;font-weight:700}
.tag{font-size:10px;padding:3px 10px;border-radius:12px;font-weight:600}
.tag.ok{background:var(--pos-bg);color:var(--pos-fg)}
.tag.warn{background:var(--amber-bg);color:var(--amber)}
.tag.danger{background:var(--neg-bg);color:var(--neg-fg)}
.tag.neutral{background:var(--flat-bg);color:var(--flat-fg)}
```

## 2.13 Skeleton (loading)

```css
@keyframes shimmer{0%{background-position:-200px 0}100%{background-position:200px 0}}
.main.is-loading .hero,.main.is-loading .kpi-grid,
.main.is-loading .flow-bar,.main.is-loading .card{position:relative;overflow:hidden}
.main.is-loading .hero::after,.main.is-loading .kpi-grid::after,
.main.is-loading .flow-bar::after,.main.is-loading .card::after{content:'';position:absolute;
  inset:0;z-index:5;background:var(--surface);
  background-image:linear-gradient(90deg,var(--surface) 0px,var(--surface-2) 80px,var(--surface) 160px);
  background-size:260px 100%;animation:shimmer 1.2s infinite linear}
.main.is-loading .alerts{display:none}
```
Aplicar `class="main is-loading"` mientras se cargan los datos; quitar al llegar.

## 2.14 Modo TV / pared

```css
body.tv{font-size:15px}
body.tv .main{max-width:100%;gap:26px;padding:26px 40px}
body.tv .hero-curr{font-size:64px}
body.tv .hero-stat .v{font-size:40px}
body.tv .kpi-val{font-size:34px}
body.tv .flow-val{font-size:32px}
body.tv .spark{width:96px;height:38px}
body.tv .mspa-lbl{font-size:14px}
body.tv .mspa-val{font-size:17px}
body.tv .seller-tbl{font-size:14px}
```
Toggle `body.classList.toggle('tv')`. Para pantallas muy apaisadas existe además un
**modo kiosk/wallboard**: stage fijo **1920×1080** escalado por JS
(`transform:scale(min(vw/1920, vh/1080))`), fondo claro, sin scroll ni chrome, que rota en
silencio entre 2 tableros (~18s) con barra de progreso fina; vanilla JS (sin React/Babel),
Chart.js con `defer` o local para que el primer pintado no dependa del CDN.

## 2.15 Terminal "DAILY INFO 2 SALES"

```css
body{background:var(--term-bg);color:var(--term-fg);font-family:var(--font-term);font-size:16px;padding:12px 16px}
.screen{max-width:1040px}
.title-bar{color:var(--term-bar-fg);background:var(--term-bar-bg);padding:2px 6px;margin-bottom:4px;font-weight:700;letter-spacing:1px}
.title-bar.plain{background:transparent;color:var(--term-fg);font-weight:700}
.sep{color:var(--term-fg);overflow:hidden;white-space:nowrap;height:1.2em}   /* relleno con '=' */
.center{text-align:center;padding:4px 0;font-weight:700;letter-spacing:2px;font-size:17px}
table{width:100%;border-collapse:collapse;margin-top:8px}
th{text-align:right;padding:2px 8px;font-weight:400;color:var(--term-fg);border-bottom:1px solid var(--term-fg);font-size:15px}
th.left{text-align:left}
td{padding:6px 8px;vertical-align:middle}
td.label{color:var(--term-fg)} td.colon{text-align:center;width:20px}
td.val,td.num{text-align:right;color:var(--term-fg);border-bottom:1px dashed var(--term-fg-dimmer)}
tr:hover td{background:var(--term-row-hover)}
tr.total td{border-top:1px solid var(--term-fg);border-bottom:none;font-weight:700;padding-top:8px}
.footer{margin-top:14px;color:var(--term-fg-dim);font-size:13px}
.footer b{color:var(--term-fg)}
.dot,.cursor{animation:blink 1s step-end infinite}
@keyframes blink{0%,100%{opacity:1}50%{opacity:0}}
.err{color:var(--term-error);margin-top:8px}
```
Banner inverso `taginfo2-1: 1.Anzeige 2.Taginfo EK 3.Taginfo Kunde` + `Anzeige
Tagesinformation` + reglas `=` enmarcando `DAILY INFO 2 SALES`. Tabla de 7 métricas con
columnas Value / Number Order / Number Pos; cursor `_` parpadea; footer con timestamp +
`●` LIVE. Sin emoji, sin web fonts.

## 2.16 Formateadores es-AR (obligatorios)
```js
const fmtN = (n,d=0)=>Number(n||0).toLocaleString('es-AR',{minimumFractionDigits:d,maximumFractionDigits:d});
const fmtK = (n)=>{ n=Number(n)||0;
  if(n>=1e9) return '$'+(n/1e9).toFixed(1).replace('.',',')+'B';
  if(n>=1e6) return '$'+(n/1e6).toFixed(1).replace('.',',')+'M';
  if(n>=1e3) return '$'+Math.round(n/1e3)+'K';
  return '$'+fmtN(n,0); };
const pct = (a,b)=> b ? ((a/b)*100).toFixed(1).replace('.',',')+'%' : '—';
```

---

# 3. GUÍAS DE USO  *(orden intencional: tono antes que catálogo)*

## 3.1 Tono visual del sistema
- **Operacional, denso, declarativo.** Escrito para un gerente que escanea de un vistazo,
  no para clientes. Sin voz de marketing, sin signos de exclamación.
- **Plano.** Sin gradientes decorativos, sin glassmorphism, sin imágenes/ilustraciones.
  Fondos sólidos. El único raster es el logo Würth.
- **Color = significado.** Si todo está coloreado, nada resalta. Neutros para la
  estructura; acentos sólo para estado/alerta/delta.
- **Movimiento contenido.** Transiciones de tema .25–.3s; barras .8s; pulso "live" 2–2.4s.
  Sin bounces ni slides. La v3 eliminó el pulso de "alarma" por fatiga visual.

## 3.2 Contenido / copy
- **Español es-AR.** Números `1.234.567,89` (punto miles, coma decimal). Moneda abreviada
  `$1,2B` / `$3,4M` / `$45K`. Fechas `dd/mm/yyyy` (dashboard) y `dd.mm.yyyy` (terminal).
- **Title Case** en títulos de card y secciones; **UPPERCASE** + tracking en eyebrows.
- **Impersonal / tercera persona.** Toque informal argentino sólo en hints ("Ingresá la
  fecha a consultar", "Volver al día actual").
- **Vocabulario de dominio (reusar literal):** lifecycle *Informado → Retenido → Anulado
  → Facturado*; *Backorders (Plazos viejos)*, *Bloqueados por Límite Crédito*, *Pedidos
  Abiertos (Futuros)*, *Producción Abierta*, *Remitos/Facturas Abiertas*, *Venta del Día*,
  *Plan de Ventas*, *Ritmo Mensual*, *Pedidos/Vendedor*, *Días hábiles*, *Vendedor (Vend.)*.
- **Frescura:** la app es "LIVE"; comunica cuándo refresca cada fuente ("MSPA actualiza en
  45s", "datos al HH:MM:SS").
- **Acentos correctos:** *Día, Crédito, Producción, Líneas, Anulado, Würth*.

## 3.3 Iconografía
- **No hay icon font ni sprite propio.** Tres vías, todas válidas:
  1. **Lucide** (https://lucide.dev) como SVG inline, stroke 1.75px, viewBox 24×24,
     `stroke="currentColor"` (hereda color del contexto). Es el set canónico de la v2/v3.
  2. **Símbolos Unicode / tipográficos:** `▲ ▼` deltas, `›` chevrons de flujo, `ⓘ` info,
     `:` colons alineados, `=`/`...`/`●` en el terminal.
  3. **Emoji funcional (legacy v1):** `📅 🌙 📊 🏆 ⏸ ✕ ●`. La v2+ los reemplazó por Lucide;
     en sistemas nuevos preferir Lucide. El terminal **no** usa emoji.
- **Sparklines en gris neutro** (`--text-3`), nunca verde/rojo: la forma da contexto, el
  juicio lo da la flecha del delta. (Color en el sparkline contradice el delta.)

## 3.4 Cuándo usar cada componente (mapa rápido)
- **Hero (Plan)** → la métrica norte del negocio; siempre arriba, dominante.
- **KPI strip** → 4 indicadores secundarios, neutros, con sparkline + meta + delta.
- **Flow bar** → el lifecycle de pedidos del día (4 etapas con tick de color).
- **Alert banner** → SOLO si algo cruza umbral (management by exception). Si no hay, no se
  renderiza. Una alarma se dice **una** vez, en el nivel de mayor jerarquía.
- **MSPA panel** → filas label/valor con semáforo (ok/warn/danger) y fila "venta" destacada.
- **Seller tables** → 3 rankings (facturación / retenidos / anulados).
- **Trend chart** → Chart.js combo: barras *fantasma* (orders/día hábil) + línea roja
  protagonista (M$/día hábil), títulos en ambos ejes.
- **Conn state + "datos al"** → confianza: estado por fuente (ok verde pulsa / slow ámbar
  / down rojo) + timestamp real.
- **Terminal** → sólo para vistas "ERP crudo" legacy; no mezclar con la superficie slate.

## 3.5 Estados (convención global)
- **Hover:** filas → `--surface-2`; botones → oscurecen fill o pasan a `--border`; rojo
  primario → `--wurth-red-hover` (#b00000). Terminal: fila → `--term-row-hover`.
- **Active/press:** rojo a `#b00000`; sin shrink/scale.
- **Disabled:** opacity .5, `cursor:not-allowed` (convención; aplicar a botones/inputs).
- **Error:** borde + texto `--red`/`--neg-fg`; en terminal `--term-error` `#ff4444`.
- **Loading:** skeleton shimmer (no "Cargando..."): overlay con gradiente que recorre.
- **Empty:** estado calmo explícito ("Sin movimiento", "Todo en orden ✓"), nunca cero mudo.
- **Alert por umbral (semáforo):** ok → warn (ámbar) → danger (rojo), por threshold.

---

# 4. INSTRUCCIONES DE RECONSTRUCCIÓN

## 4.1 Estructura de archivos a recrear
```
DESIGN-SYSTEM-TAGINFO.md     ← este documento (fuente de verdad)
colors_and_type.css          ← tokens §1.2 + clases .ty-* §1.3
assets/wurth-logo.png        ← logo (o fallback CSS §2.2 si no se tiene el PNG)
ui_kits/operations-dashboard/  ← dashboard moderno (componentes §2.1–2.13)
ui_kits/taginfo-terminal/      ← terminal verde (§2.15)
```

## 4.2 Orden de implementación recomendado
1. Crear `colors_and_type.css` con TODOS los tokens de §1.2 y las clases `.ty-*` de §1.3.
2. Cargar IBM Plex Sans (Google Fonts, 400/500/600/700) + fallback system stack.
3. Montar el shell: `.hdr` (§2.1) + `.main` (max-width 1440, §1.4).
4. Construir, en orden de página: alert banner (§2.5) → hero/Plan (§2.6) → KPI strip
   (§2.7) → flow bar (§2.8) → bottom (chart §2.11 + MSPA §2.9) → seller tables (§2.10).
5. Añadir formateadores es-AR (§2.16), skeleton (§2.13), modo TV/kiosk (§2.14).
6. (Opcional) Superficie terminal (§2.15) como vista aparte.

## 4.3 PROMPT LISTO PARA PEGAR (en otra instancia de Claude Design)

> Quiero que reconstruyas un design system llamado **"TagInfo / Würth Ops"** usando como
> **única fuente de verdad** el documento `DESIGN-SYSTEM-TAGINFO.md` que te adjunto. Es el
> sistema visual de una herramienta interna read-only de monitoreo de ventas (marca Würth,
> español es-AR) con dos superficies: un **Operations Dashboard** moderno (slate, light+dark,
> rojo Würth `#cc0000` como única marca) y un **terminal "DAILY INFO 2 SALES"** verde fósforo
> legacy. Hacé lo siguiente, respetando los valores EXACTOS del documento (no inventes hexes,
> tamaños ni nombres):
>
> 1. **Tokens:** creá `colors_and_type.css` con todas las variables CSS de la sección 1
>    (colores light + dark + terminal, tipografía, espaciado, radios, sombras, breakpoints)
>    y las clases tipográficas `.ty-*`. Cargá IBM Plex Sans con fallback al system stack.
> 2. **Componentes:** implementá TODOS los de la sección 2 con su CSS y HTML/JS tal cual el
>    documento (header con estado de conexión, date badge+popover, botones, banda de alertas
>    por excepción, hero del Plan, KPI con sparkline gris + meta + delta, flow bar, panel
>    MSPA con semáforos, tablas de ranking, gráfico Chart.js, pills, skeleton, modo TV/kiosk,
>    terminal, y los formateadores es-AR). Respetá variantes y estados (hover, disabled,
>    error, loading, empty, semáforo ok/warn/danger).
> 3. **Reglas (sección 3):** color = significado (KPIs neutros, color sólo en estado/delta/
>    alerta); números siempre con `.num` (tabular-nums) y coma decimal es-AR; una alarma se
>    dice una sola vez; sparklines en gris neutro; movimiento contenido; sin gradientes ni
>    imágenes; íconos Lucide inline (stroke 1.75, currentColor). Mantené el vocabulario de
>    dominio literal (Informado → Retenido → Anulado → Facturado, Plan de Ventas, etc.).
> 4. **Entregables:** un `index.html` del dashboard que arme una vista realista interactiva
>    (con datos de ejemplo es-AR), y un `index.html` del terminal. Verificá visualmente.
>
> No resumas ni omitas componentes. El documento es exhaustivo y autosuficiente; si algo no
> está en él, seguí las convenciones de la sección 3 y dejá una nota. Al terminar, listá qué
> archivos creaste y cualquier sustitución que hayas tenido que hacer (por ejemplo, el logo:
> usá el fallback CSS de §2.2 si no se provee `wurth-logo.png`).

## 4.4 Checklist de fidelidad post-reconstrucción
- [ ] Rojo Würth `#cc0000` SOLO en logo, regla del header, acción primaria y barra de plan.
- [ ] KPIs neutros; color únicamente en delta/estado/alerta/tick.
- [ ] Todos los números con `.num` + coma decimal es-AR (`$3,4M`, `6,2`, `29,3%`).
- [ ] Sparklines en gris neutro (no verde/rojo).
- [ ] Banda de alertas se oculta si no hay excepciones.
- [ ] Hero del Plan domina; incluye proyección de cierre y marcador de ritmo.
- [ ] Gráfico: barras fantasma + línea roja protagonista, títulos en ambos ejes.
- [ ] Light **y** dark funcionan (toggle `body.dark`); modo TV agranda números.
- [ ] Terminal: Courier, verde `#b4d900` sobre negro, reglas `=`, sin emoji.
- [ ] Estados: hover/disabled/error/loading(skeleton)/empty/semáforo presentes.

---

*Fin del documento. Derivado de `elterco2012-dev/taginfo`. Este archivo es autosuficiente:
contiene todos los tokens, el código de todos los componentes, las reglas de uso y el prompt
de reconstrucción necesarios para recrear el sistema sin acceso a los archivos originales.*

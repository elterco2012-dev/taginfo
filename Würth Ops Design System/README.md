# Würth Ops — Design System

A design system reconstructed from the **`taginfo`** repository: a set of internal,
read-only **operations dashboards** built for a **Würth** sales/distribution
operation in Argentina. The repo wires two legacy ERP systems together —
**Reactor** (MySQL) and **MSPA** (an Informix-based ERP, the old German
"taginfo2" green-screen) — and surfaces the day's sales flow to managers.

This system captures the **Würth brand** (red `#cc0000`, the shield-W logo) and the
two distinct UI surfaces the repo ships, so future dashboards, slides, and mocks
can be built on-brand and consistent.

> **Note on the brand.** Würth is a real industrial-supply company; the logo and
> red are its registered marks. They are included here because they appear in the
> source repository (an internal tool). Use them only for internal Würth-operation
> work, not to imply official endorsement.

---

## Sources

Everything here was reconstructed from a single GitHub repository:

- **`elterco2012-dev/taginfo`** — https://github.com/elterco2012-dev/taginfo
  - `dashboard.py` — the **Operations Dashboard** (modern light/dark web app, Chart.js, KPI cards, seller leaderboards). The richest UI source.
  - `taginfo_web.py` — **DAILY INFO 2 SALES**, a retro green-screen terminal emulation of the legacy `taginfo2` ERP screen.
  - `og-image.png` — the Würth logo (192×192), copied to `assets/wurth-logo.png`.
  - `scripts/` — ~57 DB-exploration / query-verification Python scripts (no UI; not used for design).

Explore the repo further to build higher-fidelity designs: the two `*.py` files
embed their full HTML/CSS/JS inline, so they are the source of truth for layout,
tokens, and copy.

There was **no Figma file, slide deck, or separate front-end codebase** — the
entire UI lives inline in those two Python HTTP servers.

---

## The two surfaces

| Surface | File | Look | Use for |
|---|---|---|---|
| **Operations Dashboard** | `dashboard.py` | Modern slate UI, light **+** dark mode, Würth-red header rule, KPI cards, flow bar, Chart.js trend, seller tables | The primary product. Any new manager-facing dashboard, report, or KPI view. |
| **DAILY INFO 2 SALES** (TagInfo) | `taginfo_web.py` | Retro **green-on-black** terminal, Courier monospace, ASCII rules, blinking cursor | Legacy/"raw ERP" views, status read-outs, anything evoking the old taginfo2 green-screen. |

Both are **Spanish-language** (Argentina locale, `es-AR` number formatting) and
**read-only** monitoring tools — no forms, no destructive actions.

---

## CONTENT FUNDAMENTALS

**Language & locale.** All UI copy is **Spanish (Argentina)**. Numbers use `es-AR`
formatting: `1.234.567,89` (period thousands, comma decimals). Currency is
abbreviated for big values — `$1,2B`, `$3,4M`, `$45K`. Dates are `dd/mm/yyyy` on
the modern dashboard and `dd.mm.yyyy` on the terminal.

**Tone.** Terse, operational, declarative — written for a sales manager scanning at
a glance, not for end-customers. No marketing voice, no exclamation points.
Labels are nouns or noun phrases: *"Pedidos Informados"*, *"Venta del Día"*,
*"Plan de Ventas"*, *"Ritmo Mensual"*.

**Person.** Impersonal / third-person. The UI states facts about the business
("Facturación Acumulada del Mes vs. Plan"); it does not address the user as *vos/tú*
or speak as *we*. The one informal touch is occasional Argentine phrasing in hints
("Ingresá la fecha a consultar", "Volver al día actual").

**Casing.** **Title Case** for section labels and card headers
(*"Top 5 Facturación del Día"*). **UPPERCASE** with wide letter-spacing for the
tiny eyebrow/section labels (`PEDIDOS INFORMADOS`, `FLUJO DEL DÍA`). The terminal
uses UPPERCASE for its centered banner (`DAILY INFO 2 SALES`).

**Accents matter.** Spanish accents are used correctly — *Día, Crédito, Producción,
Líneas, Anulado, Würth* (note the umlaut on Würth). Keep them.

**Status vocabulary** (the domain language — reuse verbatim):
- **Informado** → **Retenido** → **Anulado** → **Facturado** (the order lifecycle / "flujo del día")
- *Backorders (Plazos viejos)*, *Bloqueados por Límite Crédito*, *Bloqueados (Status < -1)*,
  *Pedidos Abiertos (Futuros)*, *Producción Abierta*, *Remitos / Facturas Abiertas*, *Venta del Día*
- Metrics: *Pedidos*, *Vendedores*, *Pedidos / Vendedor*, *Promedio Líneas / Pedido*, *Días hábiles*
- *Vendedor* (seller) is abbreviated *Vend.* when no name is known.

**Emoji.** Used sparingly as **functional iconography** in the modern dashboard
only — `📅` (date picker), `🌙` (dark toggle), `📊` (plan), `🏆` `⏸` `✕` (seller
leaderboard headers), `▲ ▼` (deltas), `●` (live dot), `›` (flow chevron, via CSS),
`ⓘ` (info tooltip). The terminal uses **no emoji** — only ASCII (`=` rules, `:`
colons, `●`/`...` blink). Don't add decorative emoji beyond this set.

**Freshness language.** The app is always "LIVE"; it tells you when data refreshes
("MSPA actualiza en 45s", "Reactor actualiza en 8min", "actualizando…").

---

## VISUAL FOUNDATIONS

### Colors
- **One brand color: Würth red `#cc0000`.** Reserved for the logo, the 2px header
  bottom-rule, the primary action button, the date badge outline, and the
  sales-plan progress fill. It is an accent, never a background wash.
- **Slate neutral ramp** carries the UI: bg `#f0f2f5`, white surfaces, `#e2e8f0`
  hairlines, text ramp `#0f172a / #475569 / #94a3b8`.
- **Functional accent palette** is strictly semantic, not decorative:
  blue `#2563eb` = primary/"informed", green `#059669` = sales/positive/"facturado",
  amber `#d97706` = warning/"retenido", red `#dc2626` = danger/"anulado",
  cyan `#0891b2` & orange `#ea580c` = secondary KPI accents.
- Each accent has a **pale tinted background** (`--*-bg`) used to fill alert cards
  and flow cells, plus **pill fills** for deltas/tags (green `#dcfce7`/`#15803d`,
  red `#fee2e2`/`#b91c1c`).
- **Terminal palette is separate & monochrome:** phosphor lime `#b4d900` on pure
  black `#000`, with dim greens `#4a6400` / `#3a4a00` for footer & separators and
  `#ff4444` for errors.

### Type
- **Modern UI:** the **native system stack** (`-apple-system, BlinkMacSystemFont,
  'Segoe UI', system-ui, sans-serif`) — no web fonts loaded. Base 13px. Big KPI
  numbers 32px/800, flow values 22px/800, plan current 26px/800. Section eyebrows
  are 9px/700 UPPERCASE with 2px tracking. Weights run heavy (700–900) for numbers,
  normal/medium for body.
- **Terminal:** `'Courier New', Courier, monospace` at 16px, normal weight, with a
  bold inverse title bar.
- See `colors_and_type.css` for the full token set and `.ty-*` semantic classes.

### Spacing, radii, borders
- **Spacing** is tight and grid-driven: 16px card padding, 10–14px grid gaps,
  16–24px page gutters. Scale: 4 / 6 / 8 / 10 / 14 / 16 / 20 / 24.
- **Radii:** 10px on cards / KPIs / flow bars / popovers; 6px on buttons, inputs,
  badges; 12–20px on pills.
- **Borders** are 1px slate hairlines (`#e2e8f0`). The header gets a **2px Würth-red
  bottom rule**. KPI/flow cards use a **3px colored top accent stripe** (`::after` /
  `border-top`) to encode their semantic color.

### Cards & elevation
- Cards are white, 1px-bordered, 10px-radius, with a **very soft** shadow
  `0 1px 3px rgba(0,0,0,.05)` — almost flat. Alert KPIs swap their border + bg to
  the tinted accent. Popovers/menus lift higher: `0 8px 24px rgba(0,0,0,.15)`.
- No heavy drop shadows, no glows, no gradients (except subtle chart fills).

### Backgrounds
- Flat. Light mode is a near-white `#f0f2f5` field; dark mode is deep slate
  `#0f172a`. **No imagery, gradients, textures, or illustration** anywhere. The
  terminal background is pure black. Charts use faint translucent fills only.

### Animation & motion
- Restrained and purposeful. **Theme switch:** `transition: background .3s, color .3s`.
  **Bars/progress** animate width over `.8s`. **Live dot:** a 2s `pulse`
  (opacity + scale). **Alert flow cells** breathe with a `bgpulse` (3s warn / 1.8s
  danger). **Terminal cursor/dot** blinks 1s step-end. No bounces, no slides, no
  easing flourishes — gentle ease/linear only.

### States
- **Hover:** subtle — row backgrounds wash to `--surface-2` / `#0a1400` (terminal);
  buttons darken their fill or shift to `--border`; the red button drops to
  `opacity:.88`. **Press/active:** Würth red goes to `#b00000`. No shrink/scale on
  press.
- **Alert states** are encoded by **threshold semáforo** (traffic-light): ok →
  warn (amber) → danger (red), driven by numeric thresholds, switching border, bg
  tint, and a pulsing animation.

### Layout rules
- **Sticky top header** with red rule. Content in a max-padded column of stacked
  sections, each introduced by an uppercase eyebrow label. **CSS Grid everywhere:**
  4-up KPI grid, 4-cell flow bar, 1fr/360px two-column bottom, 3-up seller panels.
  Fully responsive via `repeat(N, 1fr)`. The terminal is a single full-width
  monospace table.

### Transparency & blur
- Minimal. Accent backgrounds are solid pale tints, not alpha overlays. Chart fills
  use low-alpha (`rgba(...,.07–.7)`). **No backdrop-blur / frosted glass** anywhere.

### Imagery vibe
- There is essentially **no photography or illustration** — this is a dense data
  tool. The only raster asset is the Würth logo. If imagery is ever needed, keep it
  clean, corporate, and neutral; never warm/filtered/grainy.

---

## ICONOGRAPHY

The source ships **no icon font, no SVG icon set, and no PNG icon sprite.** Icons are
expressed three ways, all of which you should preserve:

1. **Emoji as functional glyphs** (modern dashboard only): `📅` date, `🌙` dark mode,
   `📊` plan, `🏆` top sellers, `⏸` retained, `✕` cancelled, `●` live. These are the
   product's de-facto icon set. Keep this exact, small vocabulary; do **not** expand
   it into decorative emoji.
2. **Unicode symbols / typographic marks:** `▲ ▼` deltas, `›` flow chevrons (CSS
   `content`), `ⓘ` info, `:` aligned colons, `=` ASCII rules and `...`/`●` blink in
   the terminal.
3. **The Würth logo** (`assets/wurth-logo.png`) — the only brand mark. The code also
   has a CSS text fallback (`W` in a red box + `WÜRTH` wordmark, 900 weight, 3px
   tracking) for when the image is missing; reuse that fallback pattern if you can't
   load the PNG.

**Substitution guidance.** If a design genuinely needs line icons (this product
mostly doesn't), substitute **Lucide** (https://lucide.dev) at ~1.75px stroke to sit
naturally with the slate UI — and **flag the substitution**, since it is not part of
the original. Prefer emoji/Unicode to match the source first.

---

## Index / manifest

Root files:
- **`README.md`** — this file: context, sources, content & visual foundations, iconography.
- **`colors_and_type.css`** — all color + type tokens (light, dark, terminal) and `.ty-*` classes.
- **`SKILL.md`** — Agent-Skills-compatible entry point.
- **`assets/`** — `wurth-logo.png` (brand mark).
- **`preview/`** — the Design System tab cards (swatches, type specimens, components, terminal).

UI kits (`ui_kits/<product>/`):
- **`ui_kits/operations-dashboard/`** — modern light/dark dashboard recreation
  (`index.html` + JSX components: header, KPI cards, flow bar, plan/meta bars,
  trend chart, MSPA panel, seller leaderboards). The faithful recreation of `dashboard.py`.
- **`ui_kits/operations-dashboard-v2/`** — a **"professional" refinement** of the
  dashboard (same data) applying: clear hierarchy (Plan = hero), neutral KPIs with
  color reserved for state, `tabular-nums` + consistent es-AR decimals, Lucide line
  icons instead of emoji, single flat-hairline elevation, calmer motion, and a
  legible dual-axis chart. Use this as the target for new dashboards.
- **`ui_kits/operations-dashboard-v3/`** — a further **information-design / UX**
  iteration on v2 covering 4 levels: (1) context in numbers — sparklines + targets +
  explicit comparisons; (2) management-by-exception — an alert banner that only shows
  on threshold breaches, plus subtle MSPA semáforos; (3) trust/operation — per-source
  connection state, "datos al" timestamps, skeletons, export/print; (4) polish — a TV
  wall mode, dedicated tabular number font (IBM Plex Sans). The most advanced target.
- **`ui_kits/taginfo-terminal/`** — the DAILY INFO 2 SALES green-screen recreation
  (`index.html` + terminal JSX components).

Root-level: **`Dashboard — Evolución v1 v2 v3.html`** — a 3-up side-by-side comparison
of all three dashboard versions, with a drawer explaining every change across both
rounds of improvement.

Each `ui_kits/<product>/README.md` documents that surface's components and screens.

# Operations Dashboard — UI kit

Cosmetic recreation of the modern **Würth Operations Dashboard** (`dashboard.py`).
A read-only, real-time sales-monitoring view that fuses two ERP feeds
(**Reactor** / MySQL and **MSPA** / Informix). Spanish (es-AR), light **+** dark mode.

## Run
Open `index.html`. Everything is fake/static data (`data.js`) — no backend.

Interactions that work:
- **🌙 Oscuro / ☀️ Claro** — toggles dark mode (adds `body.dark`; chart recolors).
- **Date badge** — opens a popover; pick a date → switches the dataset
  (two days are seeded: 28/05 and 27/05). "Volver al día actual" resets.
- **LIVE countdown** — the MSPA freshness counter ticks down each second.
- Chart.js trend, seller-table row hovers.

## Files
| File | What |
|---|---|
| `index.html` | Page shell; loads React, Babel, Chart.js, tokens + styles, then scripts. |
| `dashboard.css` | Structural/component CSS, lifted from `dashboard.py` and tokenised against `colors_and_type.css`. |
| `data.js` | Fake data + `fmtN` / `fmtK` / `pct` es-AR formatters. |
| `components.jsx` | All components (exported to `window`). |
| `app.jsx` | App shell: dark-mode + date state, live countdown, layout. |
| `wurth-logo.png`, `styles.css` | Local copies of the brand mark and token sheet. |

## Components (in `components.jsx`)
- **`Header`** — logo, title, date-badge popover, freshness counters, LIVE dot, dark toggle.
- **`KpiGrid`** / `Kpi` / `Delta` — 4-up KPI cards with top accent stripe + ▲▼ deltas.
- **`FlowBar`** — Informado → Retenido → Anulado → Facturado, with `›` chevrons and amber/red pulse on threshold.
- **`PlanBar`** — sales-plan progress with amber pace marker (Würth-red fill).
- **`MetaBar`** — monthly pace vs. prior month.
- **`TrendChart`** — Chart.js combo (bars = orders/working-day, line = M$/working-day); recolors with theme.
- **`MspaPanel`** — MSPA status rows (label/value, highlight + venta variants).
- **`SellerPanels`** / `SellerTable` — three ranked leaderboards (facturación / retenidos / anulados) with medal colors.

## Notes
- Built for fidelity to the original layout, **not** production logic. Thresholds,
  comparisons and "working-day" math are simplified.
- Uses the system font stack and Chart.js from CDN, exactly as the source does.

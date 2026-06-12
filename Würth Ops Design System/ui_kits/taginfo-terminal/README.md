# TagInfo Terminal — "DAILY INFO 2 SALES" UI kit

Cosmetic recreation of the legacy green-screen view (`taginfo_web.py`): a
minimalist, read-only emulation of the old **taginfo2** ERP terminal screen,
served straight from MSPA (Informix). Phosphor lime on pure black, Courier New.

## Run
Open `index.html`. Fake data; refreshes itself every 60s (the "Venta diaria"
row jitters slightly each cycle and the timestamp/countdown update live).

## Files
| File | What |
|---|---|
| `index.html` | Shell; loads React, Babel, tokens + `terminal.css`, then `app.jsx`. |
| `terminal.css` | Green-screen styles (lifted from `taginfo_web.py`). |
| `app.jsx` | Whole screen in one file: `TitleBars`, `DataTable`, `Footer`, `Terminal`. |
| `styles.css` | Local copy of the token sheet (uses the `--term-*` vars). |

## Anatomy (matches the source)
- **Inverse title bar** — `taginfo2-1: 1.Anzeige 2.Taginfo EK 3.Taginfo Kunde`
  (the original German menu chrome) + `Anzeige Tagesinformation`.
- **ASCII `=` rules** framing the centered `DAILY INFO 2 SALES` banner.
- **Fecha** line with a blinking block cursor.
- **Data table** — the seven metrics (Backorders, Bloqueados, Status < -1,
  Pedidos Abiertos, Producción, Remitos/Facturas, Venta diaria) with Value /
  Number Order / Number Pos columns, dashed row underlines, hover wash.
- **Footer** — last-update timestamp, next-refresh countdown, blinking `●` LIVE.

## Notes
- Pure recreation; numbers are invented. Keep the German menu strings and Spanish
  metric labels verbatim — they are part of the legacy system's character.
- No emoji or web fonts here by design — only Courier New and ASCII glyphs.

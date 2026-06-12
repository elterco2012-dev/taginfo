---
name: wurth-ops-design
description: Use this skill to generate well-branded interfaces and assets for the Würth Operations tooling (the taginfo dashboards), either for production or throwaway prototypes/mocks/etc. Contains essential design guidelines, colors, type, the Würth logo, and UI kit components for prototyping the modern Operations Dashboard and the legacy DAILY INFO 2 SALES green-screen terminal.
user-invocable: true
---

Read the `README.md` file within this skill, and explore the other available files.

If creating visual artifacts (slides, mocks, throwaway prototypes, etc), copy assets
out and create static HTML files for the user to view. If working on production code,
you can copy assets and read the rules here to become an expert in designing with this
brand.

If the user invokes this skill without any other guidance, ask them what they want to
build or design, ask some questions, and act as an expert designer who outputs HTML
artifacts _or_ production code, depending on the need.

## What's here
- `README.md` — product context, sources, content & visual foundations, iconography, manifest.
- `colors_and_type.css` — all color + type tokens (light, dark, terminal) and `.ty-*` classes. Import this; don't hard-code hexes.
- `assets/wurth-logo.png` — the only brand mark (red shield-W + WÜRTH wordmark). A CSS text fallback is documented in the README.
- `preview/` — Design System reference cards (swatches, type specimens, components, terminal).
- `ui_kits/operations-dashboard/` — modern light/dark dashboard recreation (React/JSX components + Chart.js).
- `ui_kits/taginfo-terminal/` — the legacy green-screen "DAILY INFO 2 SALES" recreation.

## Quick rules of thumb
- **One brand color:** Würth red `#cc0000`, used sparingly (logo, header rule, primary button, plan bar). Slate neutrals carry the UI.
- **Two surfaces, two moods:** modern slate dashboard (system font, light+dark) vs. retro phosphor-green terminal (Courier New on black). Don't mix them.
- **Spanish (es-AR):** numbers `1.234.567,89`, currency `$3,4M`, dates `dd/mm/yyyy` (dashboard) / `dd.mm.yyyy` (terminal). Title Case headers, UPPERCASE eyebrows.
- **Semantic accents:** blue=informed, green=sales/facturado, amber=retenido/warning, red=anulado/danger.
- **Restrained motion:** soft .3s theme fades, .8s bar fills, 2s pulses. Flat, near-shadowless cards, 10px radii, no gradients or imagery.
- **Icons:** a small, fixed emoji/Unicode set (`📅 🌙 📊 🏆 ⏸ ✕ ▲ ▼ ● › ⓘ`). No icon font ships; substitute Lucide only if truly needed, and flag it.

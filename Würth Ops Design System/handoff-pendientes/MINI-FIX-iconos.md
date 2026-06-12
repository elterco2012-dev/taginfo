# MINI-FIX — reemplazar los 3 emoji por íconos de línea Lucide

Para Claude Code. Cambio chico de consistencia: los chips del Plan de Ventas usan emoji
(📅 ⏳ 💰) que rompen el sistema de íconos Lucide del resto del dashboard. Cambialos por
SVG Lucide monocromáticos. NO toques el texto ni el layout.

## ⚠️ Regla de oro
Sólo reemplazar los 3 glifos emoji por `<svg>` Lucide. Nada más.

## Por qué
- El resto del dashboard ya usa íconos de línea Lucide → los emoji son inconsistentes.
- Los emoji se ven distinto en cada equipo/OS (Windows TV vs Mac vs navegador).
- El color multicolor del emoji (💰 dorado, 📅 azul) ensucia tu código de color por estado.

## El fix
Buscá los 3 chips bajo la barra del Plan ("Día hábil 8 de 21", "13 días hábiles
restantes", "Restante: $2,6B") y reemplazá el emoji inicial por `icon(...)`:

```
📅  →  icon('calendar')      (Día hábil X de Y)
⏳  →  icon('hourglass')     (N días hábiles restantes)
💰  →  icon('wallet')        (Restante: $X)
```

### Agregá estos paths a tu diccionario ICONS (si no están):
```js
calendar:  '<rect width="18" height="18" x="3" y="4" rx="2"/><path d="M3 10h18M8 2v4M16 2v4"/>',
hourglass: '<path d="M5 22h14M5 2h14M17 22v-4.172a2 2 0 0 0-.586-1.414L12 12l-4.414 4.414A2 2 0 0 0 7 17.828V22M7 2v4.172a2 2 0 0 0 .586 1.414L12 12l4.414-4.414A2 2 0 0 0 17 6.172V2"/>',
wallet:    '<path d="M19 7V4a1 1 0 0 0-1-1H5a2 2 0 0 0 0 4h15a1 1 0 0 1 1 1v4h-3a2 2 0 0 0 0 4h3a1 1 0 0 1-1 1v-1a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5"/><path d="M3 5v14a2 2 0 0 0 2 2h15a1 1 0 0 0 1-1v-4"/>',
```
> Si tu `icon()` ya pone `class="ico"` con `stroke="currentColor"`, los íconos heredan el
> gris del chip automáticamente. Asegurate de que el color del chip sea var(--text-3) o
> el color de texto del chip, para que queden monocromáticos (no del color del emoji).

### Tamaño / alineación
Que el SVG quede ~14-15px y alineado verticalmente con el texto del chip:
```css
.plan-chip .ico{width:14px;height:14px;vertical-align:-2px;color:var(--text-3)}
```
(usá la clase real de tus chips).

## Verificación
- Los 3 chips muestran íconos de línea finos en gris, no emoji de colores.
- Se ven idénticos en la TV, en Mac y en el navegador.
- El texto y los chips quedan exactamente igual que antes.

## PROMPT para Claude Code
> En mi dashboard.py, los 3 chips bajo la barra del Plan de Ventas usan emoji (📅 ⏳ 💰).
> Reemplazalos por íconos de línea Lucide monocromáticos con mi función icon(): calendar,
> hourglass y wallet, en color var(--text-3), ~14px, alineados con el texto. Agregá los
> paths al diccionario ICONS si faltan. No toques el texto ni el layout de los chips. Es
> sólo para mantener consistencia con el resto de los íconos Lucide del dashboard. Mostrame el diff.

# HANDOFF — App móvil "Ventas Würth" v2.0 (vista para dirección)

Para Claude Code. Mejora la app móvil existente con una **vista curada para gerencia**
(Daniel). Misma app, menos ruido, más decisión. Referencia visual exacta: el archivo
`propuesta-2.html` (mockup HTML autocontenido que muestra el objetivo).

## ⚠️ Regla de oro
No toques las consultas SQL ni la lógica de datos. Sólo presentación y orden de la
pantalla principal. La app sigue consumiendo los mismos datos que ya trae.

## Qué cambiar (5 puntos)

### 1. Números abreviados es-AR (lo más importante)
Hoy muestra `$1.095.297.511 / $3.648.337.980` → ilegible en celular.
Usá el formato abreviado, igual que el dashboard web:
- `$1,1B / $3,6B` (plan), `$171,7M` (ventas/día), `$86,6M` (venta hoy).
- Función: B (≥1e9), M (≥1e6), K (≥1e3), con **coma decimal** es-AR.

### 2. El Plan es el héroe (primera tarjeta, grande)
Mostrá arriba: `$1,1B / $3,6B`, el `30,0%` y la barra de progreso CON marcador de
ritmo esperado, y **agregá la Proyección de cierre** (`$2,8B · 77,0% del plan`) +
`Día hábil 8 de 21 · restante $2,6B`. Hoy la app no muestra la proyección y es lo que
más le importa a un gerente.

### 3. Alerta arriba de todo (por excepción)
Si el plan está fuera de ritmo, una barra ámbar: *"Plan 8,8 pts por debajo del ritmo ·
proyección $2,8B (77%)"*. Si todo OK, en verde o sin barra. Es lo primero que se ve.

### 4. Lo operativo, PLEGADO
Backorders, Remitos, Vendedores, Líneas/pedido NO van en la pantalla principal con el
mismo peso que el Plan. Mandalos a una sección **"Detalle operativo" colapsable** (un
toque para abrir). Lo que queda arriba: Plan + Venta hoy + Pedidos hoy.

### 5. Sparklines neutros
Hoy están en rojo. Pasalos a **gris neutro** (#7c8593 o similar). Muestran la tendencia;
el color se reserva para estado/alertas.

## Jerarquía final de la pantalla (de arriba a abajo)
1. Saludo + frescura (ya lo tenés). 2. **Alerta** (si hay). 3. **Plan del mes** (héroe,
con proyección). 4. **Venta hoy** + **Pedidos hoy** (en vivo, sparkline gris).
5. **Detalle operativo** (plegado): Vendedores, Líneas/pedido, Backorders, Remitos.

## Mantené (ya está bien)
Modo oscuro, saludo "Buenas tardes, Daniel", el "hace 16s" con punto verde, el logo W,
la grilla táctil de 2 columnas.

## PROMPT para Claude Code
> Mejorá mi app móvil "Ventas Würth" con una vista curada para gerencia, sin tocar la
> lógica de datos. Usá como referencia visual el archivo propuesta-2.html. Cambios: (1)
> números abreviados es-AR ($1,1B, $86,6M — no los enteros largos); (2) el Plan del mes
> como héroe arriba, agregando la proyección de cierre ($2,8B / 77%) y el ritmo esperado
> en la barra; (3) una barra de alerta por excepción arriba cuando el plan está fuera de
> ritmo; (4) mandá lo operativo (backorders, remitos, vendedores, líneas/pedido) a una
> sección "Detalle operativo" colapsable, dejando arriba sólo Plan + Venta hoy + Pedidos
> hoy; (5) sparklines en gris neutro en vez de rojo. Mantené el modo oscuro, el saludo y
> el logo. Mostrame los cambios.

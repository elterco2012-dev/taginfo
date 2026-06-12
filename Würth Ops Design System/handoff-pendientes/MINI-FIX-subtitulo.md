# MINI-FIX — subtítulo del header del KIOSK

Para Claude Code. Cambio de copy mínimo, sólo en el subtítulo del header del kiosk.
NO toques el título principal ni la lógica.

## Qué cambiar
En el header del kiosk, el subtítulo dice:
```
Reactor · MSPA · Sala de control
```
"Sala de control" describe DÓNDE se muestra el tablero — metadato que no aporta a quien
lo mira. Reemplazalo por algo que agregue contexto operativo. Dejá "Reactor · MSPA"
(son las fuentes de datos y dan confianza).

### Cambio
```
Reactor · MSPA · Sala de control   →   Reactor · MSPA · Actualización automática
```

- El **título principal** "Operaciones · Tiempo Real" queda IGUAL.
- En el **dashboard normal** (navegador), el subtítulo "Reactor · MSPA · Tiempo Real"
  queda IGUAL — este cambio es SOLO para el kiosk.

> Alternativas si preferís otra: "Fuentes: Reactor · MSPA" o "Reactor · MSPA · Solo lectura".

## PROMPT para Claude Code
> En el header del kiosk de mi dashboard.py, cambiá el subtítulo "Reactor · MSPA · Sala de
> control" por "Reactor · MSPA · Actualización automática". No toques el título principal
> "Operaciones · Tiempo Real" ni el subtítulo del dashboard normal. Es sólo copy. Mostrame el diff.

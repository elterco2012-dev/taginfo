# MINI-FIX #4 — formato del promedio en los sparklines del hero

Para Claude Code. Se aplica **sobre tu `dashboard.py` actual**. Un solo arreglo de
formato. NO toques nada más.

## El problema
En el hero, bajo el sparkline de **Venta del Día**, la etiqueta dice **"prom 14d: $169"**
— le falta la abreviatura: debería ser **"prom 14d: $169M"**. Ese promedio de 14 días no
está pasando por el mismo `fmtK()` que usás para el resto de los montos (que sí muestran
$513,9M, $179,2M, $376K, etc.).

## La causa probable
Ese label se arma aparte (concatenando `'$' + valor` o con un `.toFixed()` directo), en
vez de llamar a `fmtK()`. Por eso un valor en millones queda como "$169" pelado.

## El fix
Buscá dónde se construye el texto **"prom 14d: …"** del sparkline de Venta del Día
(y por consistencia, los de los demás KPIs del hero/strip) y pasá el promedio por `fmtK`:

```js
// MAL (deja "$169"):
label.textContent = 'prom 14d: $' + Math.round(prom);
// o:  'prom 14d: $' + prom.toFixed(0);

// BIEN (usa el mismo formateador que el resto → "$169M"):
label.textContent = 'prom 14d: ' + fmtK(prom);
```

Donde `fmtK` es el que ya tenés definido:
```js
function fmtK(n){
  n = Number(n) || 0; const neg = n < 0; n = Math.abs(n);
  let s;
  if (n >= 1e9) s = '$' + (n/1e9).toFixed(1).replace('.', ',') + 'B';
  else if (n >= 1e6) s = '$' + (n/1e6).toFixed(1).replace('.', ',') + 'M';
  else if (n >= 1e3) s = '$' + Math.round(n/1e3) + 'K';
  else s = '$' + fmtN(n, 0);
  return (neg ? '−' : '') + s;
}
```

### Importante: que la serie y el promedio estén en la MISMA unidad
Si para dibujar el sparkline normalizaste la serie de Venta del Día a millones (ej.
`valor/1e6` → 169), entonces el promedio te queda en "169" y por eso aparece "$169".
Dos opciones:
- **Recomendada:** calculá el promedio sobre los **valores originales en pesos** y pasalo
  por `fmtK(prom)` → "$169M". (El sparkline puede seguir usando la serie normalizada para
  el trazo; sólo el label necesita el valor real.)
- O si el promedio ya está en millones, reconstruí: `fmtK(prom * 1e6)`.

## Verificación
- Venta del Día → "prom 14d: **$169M**" (no "$169").
- Revisá de paso los otros labels "prom 14d" del hero/strip (Pedidos, Pedido Promedio,
  etc.): los de **cantidad** van con `fmtN(prom)` ("prom 14d: 500"); los de **plata** con
  `fmtK(prom)` ("$330K", "$169M"). Que ninguno quede con "$" + número crudo.

## PROMPT para pegar en Claude Code
> En mi dashboard.py, el label del sparkline de "Venta del Día" en el hero muestra
> "prom 14d: $169" sin la M. Hacé que ese promedio de 14 días pase por mi función fmtK()
> (igual que el resto de los montos) para que muestre "$169M". Asegurate de que el
> promedio se calcule sobre el valor real en pesos, no sobre la serie normalizada a
> millones. Revisá también los demás labels "prom 14d" del hero y del strip: los de plata
> con fmtK, los de cantidad con fmtN, ninguno con "$" + número crudo. No toques nada más.
> Mostrame el diff.

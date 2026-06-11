# CLAUDE.md — Wurth Operations Dashboard (taginfo)

## Qué es el proyecto

Dashboard operativo interno para Wurth Argentina. Muestra en tiempo real:
- Plan de ventas mensual vs. facturación acumulada (MSPA)
- Pedidos informados del día (Reactor)
- KPIs diarios: pedidos/vendedor, líneas/pedido, ticket promedio, % facturado
- Flujo del día: Informado → Retenido → Anulado → Facturado
- Tendencia mensual (12 meses, promedio por día hábil)
- Backorders, bloqueados, producción abierta (MSPA)
- Versión mobile PWA (viewer en FTP) para celular

Usado por Daniel y el equipo comercial de Wurth Argentina.

---

## Archivos principales

| Archivo | Función |
|---|---|
| `dashboard.py` | Servidor Python (ThreadingHTTPServer puerto 8765). Toda la lógica: queries SQL, HTML, CSS, JS en un solo archivo (~2100 líneas) |
| `ftp_snapshot.py` | Daemon FTP. Sube `snapshot.json` + `index.html` + `.htaccess` al servidor cada N segundos. Se inicia desde `dashboard.py main()` |
| `iniciar_dashboard.bat` | Launcher Windows con auto-restart. Carga `ftp_credenciales.bat` antes de arrancar |
| `ftp_credenciales.bat` | **LOCAL ONLY — gitignoreado**. Contiene `set FTP_PASS=...`. Nunca commitear |
| `setup_tarea.bat` | Crea tarea programada Windows `WurthDashboard` que corre `iniciar_dashboard.bat` al login |
| `check_features.py` | Script de verificación. Corre automáticamente como pre-commit hook. Falla si faltan features críticos |
| `GUIA-DESPLIEGUE-VM.md` | Guía de instalación en VM/servidor |

---

## Bases de datos

**DOS conexiones distintas, ambas SOLO LECTURA:**

### Reactor (MySQL via pyodbc)
- DSN: `"Wurth Reactor Produccion"`
- Tablas clave:
  - `order_placed` — pedidos. Campos: `id`, `order_date`, `total`, `id_user`, `id_order_status`
  - `order_detail` — líneas de pedido. JOIN con `order_placed`
  - `order_status` — estados. Status 14 = anulado, status 15 = retenido, status 13/18 = facturado
  - `work_days_log` — mapea fecha calendario → número de día hábil del mes (`real_date`, `working_day`)
  - `work_days` — días hábiles totales por mes (`year`, `month`, `days`)
  - `user` (singular, no `users`) — vendedores. Campos: `id`, `username`, `name`, `surname`

### MSPA (Informix via pyodbc)
- DSN: `"MSPA"`
- Datos de facturación, plan de ventas, backorders, bloqueados
- TTL cache: 60 segundos

---

## RESTRICCIÓN CRÍTICA

**NUNCA usar INSERT, UPDATE, DELETE, DDL en ninguna query.**
Solo SELECT. El sistema es de solo lectura.

---

## Arquitectura del servidor

```python
# En main():
from ftp_snapshot import start_snapshot_job
start_snapshot_job(get_cached_data)   # ← DEBE estar siempre
server = HTTPServer(("0.0.0.0", PORT), Handler)
server.serve_forever()
```

- `get_cached_data()` — función central que devuelve datos frescos o del cache
- Cache Reactor: 600s TTL. Cache MSPA: 60s TTL
- `fetch_reactor(target_date)` — acepta `?date=YYYY-MM-DD` para ver días históricos
- `target_str` = último día hábil con datos (de `work_days_log`), NO `CURDATE()`

---

## Features implementados

### Trend chart (gráfico tendencia mensual)
- Query filtra solo fechas en `wd_log` (días hábiles) hasta `target_str`
- Divide por `elapsed_wd` para mes actual, por `dias_tot` para meses cerrados
- **Sin filtro de status** — incluye todos los estados
- Esto hace que numerador y divisor cuenten exactamente los mismos días → promedio correcto

### Kiosk mode
- Botón en toolbar (ícono de marcos/fullscreen)
- Basado en **scroll** (no show/hide de divs — eso rompía el layout)
- Página 1: scroll al top (hero, KPIs, flujo, hoy)
- Página 2: scroll a `#kiosk-p2` (ritmo, gráfico, MSPA)
- Barra inferior: etiqueta izquierda, 2 dots clicables al centro, progreso + pausa + salir a la derecha
- Timer: 20 segundos por página
- Fullscreen automático al entrar
- Auto-start con `?kiosk=1` en la URL
- Activa también `body.tv` (fuentes grandes)

### Días hábiles restantes
- Chip en el hero footer: "X días hábiles restantes"
- Gris neutro normal, amarillo suave si quedan ≤3 días
- Calculado como `diasHab - diasElapsed`

### Sparklines
- Últimos 14 días hábiles (desde `wd_log`)
- 4 KPIs: pedidos, ventas, ped/vendedor, líneas/pedido

### FTP / PWA mobile
- `ftp_snapshot.py` sube cada N segundos a `www.wurth.com.ar` (FileZilla config: user `wurth_demotel`)
- Sube: `snapshot.json`, `index.html` (PWA viewer), `.htaccess` (Allow from all + no-cache), íconos
- `.htaccess` siempre se sube para evitar que servidor bloquee `snapshot.json`
- Contraseña FTP en `ftp_credenciales.bat` (gitignoreado)

### Ranking de vendedores
- **Oculto** con `display:none` por pedido de Daniel. No borrado, fácil de re-habilitar.

### Modo TV
- `body.tv` — fuentes más grandes, sin rotación automática
- Botón separado del kiosk

---

## Problemas conocidos y soluciones

| Problema | Causa | Solución |
|---|---|---|
| FTP no arranca | `start_snapshot_job` se pierde en merges | Verificar que esté en `main()` |
| Gráfico muestra promedio inflado | Había 2 queries `trend_rows`, la segunda (con CURDATE) pisaba la primera | Un solo query filtrando por wd_log |
| `ftp_credenciales.bat` se pisa con git pull | Estaba trackeado. Ahora gitignoreado | Nunca commitear ese archivo |
| Conflictos de merge pisan features | `-X ours` o `--theirs` toma versión sin features | Siempre correr `python3 check_features.py` después de resolver conflictos |
| Puerto 8765 en TIME_WAIT | Proceso anterior no liberó el puerto | Esperar 1-2 min o matar proceso con netstat + taskkill |

---

## Cómo correr el proyecto (Windows)

```bat
cd C:\taginfo
git pull origin claude/gifted-johnson-BoqhJ
iniciar_dashboard.bat
```

Abrir browser en `http://localhost:8765`

`ftp_credenciales.bat` debe existir localmente con:
```bat
set FTP_HOST=www.wurth.com.ar
set FTP_USER=wurth_demotel
set FTP_PASS=TuContraseñaReal
set FTP_PATH=/download/w20260609a01/
set FTP_PATH_WEB=/download/w20260611a01/
```

`FTP_PATH` = app móvil (Daniel). `FTP_PATH_WEB` = dashboard web completo (opcional, dejar vacío para no subir).

---

## Rama de desarrollo

`claude/gifted-johnson-BoqhJ` en `elterco2012-dev/taginfo`

Antes de cada commit corre automáticamente `check_features.py` (pre-commit hook).
Si falla, corregir lo que falta antes de continuar.

---

## Pendientes / trabajo en progreso

- Verificar que el promedio del gráfico de junio coincida con $161.839.869 (7 días hábiles)
- Confirmar que el kiosk (scroll-based) funciona correctamente en la PC de producción
- Migrar proyecto a cuenta Team de Wurth cuando esté lista

# CLAUDE.md — Wurth Operations Dashboard (taginfo)

## Qué es el proyecto

Dashboard operativo interno para Wurth Argentina. Muestra en tiempo real:
- Plan de ventas mensual vs. facturación acumulada (MSPA)
- Pedidos informados del día (Reactor)
- KPIs diarios: pedidos/vendedor, líneas/pedido, ticket promedio, % facturado
- Flujo del día: Informado → Retenido → Anulado → Facturado
- Tendencia mensual (12 meses, promedio por día hábil)
- Backorders, bloqueados, producción abierta (MSPA)
- App móvil PWA (viewer en FTP) para celular
- Dashboard web completo accesible desde internet vía FTP (idéntico al local, con kiosk)

Usado por Daniel y el equipo comercial de Wurth Argentina. La VM corre en un servidor Windows
dentro de la red de Wurth; el dashboard local es `http://localhost:8765` y el externo vía FTP.

---

## Archivos principales

| Archivo | Función |
|---|---|
| `dashboard.py` | Servidor Python (ThreadingHTTPServer puerto 8765). Toda la lógica: queries SQL, HTML, CSS, JS en un solo archivo (~2700+ líneas) |
| `ftp_snapshot.py` | Daemon FTP. Sube snapshot + HTML al servidor cada N segundos. Se inicia desde `dashboard.py main()` |
| `iniciar_dashboard.bat` | Launcher Windows con auto-restart loop. Carga `ftp_credenciales.bat` antes de arrancar |
| `ftp_credenciales.bat` | **LOCAL ONLY — gitignoreado**. Contiene credenciales FTP. Nunca commitear |
| `setup_tarea.bat` | Crea tareas programadas Windows `WurthDashboard` y `WurthDashboardWatchdog` que arrancan con SYSTEM al bootear |
| `watchdog_dashboard.bat` | Watchdog: verifica que `localhost:8765` responda cada 60s; si no responde mata Python para que el loop de iniciar_dashboard.bat lo relance |
| `check_features.py` | Script de verificación. Corre como pre-commit hook. Falla si faltan features críticos |
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
- Cache TTL: 600s

### MSPA (Informix via pyodbc)
- DSN: `"MSPA"`
- Datos de facturación, plan de ventas, backorders, bloqueados
- Cache TTL: 60s

**Los DSN deben estar configurados como "DSN de sistema" (no "DSN de usuario") para que
la cuenta SYSTEM pueda acceder a ellos. Verificar en "Orígenes de datos ODBC (32 bits)".**

---

## RESTRICCIONES CRÍTICAS

**NUNCA usar INSERT, UPDATE, DELETE, DDL en ninguna query.**
Solo SELECT. El sistema es de solo lectura.

**NUNCA commitear `ftp_credenciales.bat`.** Está en `.gitignore`. Contiene la contraseña FTP.

---

## Arquitectura del servidor

```python
# En main() — estas dos líneas DEBEN estar siempre:
from ftp_snapshot import start_snapshot_job
start_snapshot_job(get_cached_data, get_web_html)   # ← segundo arg para dashboard web
server = HTTPServer(("0.0.0.0", PORT), Handler)
server.serve_forever()
```

- `get_cached_data()` — función central que devuelve datos frescos o del cache
- `fetch_reactor(target_date)` — acepta `?date=YYYY-MM-DD` para ver días históricos
- `target_str` = último día hábil con datos (de `work_days_log`), NO `CURDATE()`
- `get_web_html()` — retorna `(dash_html, kiosk_html)` para el dashboard estático FTP

### FTP Snapshot daemon (`ftp_snapshot.py`)
Dos rutas de subida por ciclo (cada `FTP_INTERVAL` segundos):

| Variable | Ruta FTP | Qué sube | Para qué |
|---|---|---|---|
| `FTP_PATH` | `/download/w20260609a01/` | `snapshot.json` + `index.html` PWA + `.htaccess` | App móvil para celular |
| `FTP_PATH_WEB` | `/download/w20260611a01/` | `snapshot.json` + `index.html` dashboard + `kiosk.html` + `.htaccess` | Dashboard web desde PC |

Si `FTP_PATH_WEB` está vacío, solo sube la app móvil. El `.htaccess` se sube siempre para
evitar que el servidor bloquee `snapshot.json` (Access-Control + no-cache headers).

### Versión web estática (`get_web_html()` en `dashboard.py`)
Transforma el HTML dinámico en versión estática mediante `.replace()`:
- `fetch(url)` → `fetch('snapshot.json?_='+Date.now())`
- Botón de fecha histórica oculto (`display:none`)
- Detección de snapshot obsoleto: si `data.timestamp` tiene más de 600s de antigüedad,
  muestra "DESACTUALIZADO" en lugar de "OK"
- Kiosk: carga Chart.js desde CDN (no `/static/chart.min.js` que es path local)
- Links internos `/kiosk` → `/kiosk.html`, `/'` → `/index.html`

---

## Features implementados

### ctxBar — barra de contexto (reemplaza alertRibbon + northStrip)
Barra persistente debajo del topBar. Color según situación:
- `ok` (verde): plan en ritmo
- `warn` (ámbar): menos de 10 pts por debajo del ritmo
- `danger` (rojo): 10+ pts por debajo del ritmo

Muestra: ícono trending, alerta de ritmo, separador, Restante, separador, Venta hoy.
Solo muestra "En ritmo" como tag cuando está en ritmo (no muestra tag cuando está atrasado).
`.kt-board.top1{top:168px}` = 96px topBar + 72px ctxbar.

### Kiosk mode
- Botón en toolbar (ícono fullscreen/marcos)
- Basado en **scroll** (NO show/hide de divs — eso rompía el layout)
- Página 1: scroll al top (hero, KPIs, flujo, tabla del día)
- Página 2: scroll a `#kiosk-p2` (ritmo, gráfico tendencia, MSPA)
- Barra inferior: etiqueta izquierda, 2 dots clicables al centro, progreso + pausa + salir derecha
- Timer: **30 segundos** por página (`ROTATE_MS=30000`)
- Fullscreen automático al entrar
- Auto-start con `?kiosk=1` en la URL
- Activa también `body.tv` (fuentes grandes)

### Trend chart (gráfico tendencia mensual)
- Query filtra solo fechas en `wd_log` (días hábiles) hasta `target_str`
- Divide por `elapsed_wd` para mes actual, por `dias_tot` para meses cerrados
- **Sin filtro de status** — incluye todos los estados
- Un solo query (sin CURDATE) → numerador y divisor cuentan los mismos días → promedio correcto

### Días hábiles restantes
- Chip en el hero footer: "X días hábiles restantes"
- Gris neutro normal, amarillo suave si quedan ≤3 días
- Calculado como `diasHab - diasElapsed`

### Sparklines
- Últimos 14 días hábiles (desde `wd_log`)
- 4 KPIs: pedidos, ventas, ped/vendedor, líneas/pedido

### App móvil PWA (v2)
- `_VIEWER_HTML` en `ftp_snapshot.py`
- Funciones: `fmtK()`, alert banner de ritmo, hero plan con proyección, live cards, detalle colapsable
- Logo de Wurth (base64 embebido)
- Service Worker con cache busting por timestamp `YYYYMMDDHHMM`

### Íconos — sistema Lucide SVG
- Dict `ICONS` en el JS del kiosk con paths SVG inline
- Función `ico(name, w)` renderiza `<svg>` del tamaño pedido
- Íconos disponibles: `trendingUp`, `trendingDown`, `calendar`, `hourglass`, `wallet`, y otros

### Modo TV
- `body.tv` — fuentes más grandes, sin rotación automática
- Botón separado del kiosk en la toolbar

### Ranking de vendedores
- **Oculto** con `display:none` por pedido de Daniel. No borrado, fácil de re-habilitar.

### KPI alignment fix
- `.kpi-top{height:44px}` — altura fija para que todos los KPI cards tengan el valor alineado
  independientemente de si tienen 1 o 2 líneas en el footer

### MSPA rows
- Muestran `N ped · N lin` (pedidos y líneas). El texto anterior era `ord`/`pos`, ahora es `ped`/`lin`.

---

## Infraestructura y despliegue (VM)

### VM de producción
- Nombre: `DASHBOARD-DANIE`
- OS: Windows (con Windows Update activo)
- Uptime: la VM NO se reinicia diariamente (verificado). El corte nocturno del 12/06/2026
  fue por **cierre de sesión RDP**, no por reinicio.

### Tareas programadas (setup actual en producción)
Las tareas corren como `NT AUTHORITY\SYSTEM` — sin contraseña, sobreviven reinicios y
cierres de sesión de cualquier usuario:

| Tarea | Trigger | Delay | Qué hace |
|---|---|---|---|
| `WurthDashboard` | ONSTART | 1 min | Corre `iniciar_dashboard.bat` con auto-restart |
| `WurthDashboardWatchdog` | ONSTART | 2 min | Verifica HTTP cada 60s, mata Python si cuelga |

**Importante:** como son `ONSTART`, solo arrancan automáticamente al bootear. Si la VM no
se reinicia, usar `Start-ScheduledTask -TaskName "WurthDashboard"` para arrancarlas a mano.

### Cómo recrear las tareas (si se pierden)
En PowerShell como Administrador (NO usar `.\setup_tarea.bat` desde PowerShell — usa CMD):

```powershell
# Dashboard principal
$action  = New-ScheduledTaskAction -Execute "C:\taginfo\iniciar_dashboard.bat"
$trigger = New-ScheduledTaskTrigger -AtStartup
$trigger.Delay = "PT1M"
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
$settings  = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
Register-ScheduledTask -TaskName "WurthDashboard" -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force

# Watchdog
$action  = New-ScheduledTaskAction -Execute "C:\taginfo\watchdog_dashboard.bat"
$trigger = New-ScheduledTaskTrigger -AtStartup
$trigger.Delay = "PT2M"
Register-ScheduledTask -TaskName "WurthDashboardWatchdog" -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force

# Arrancar ahora (sin reiniciar)
Start-ScheduledTask -TaskName "WurthDashboard"
Start-ScheduledTask -TaskName "WurthDashboardWatchdog"
```

**Nota:** `setup_tarea.bat` también funciona pero solo desde CMD (no PowerShell).

### Verificar estado en producción

```powershell
# Estado de las tareas
Get-ScheduledTask "WurthDashboard","WurthDashboardWatchdog" | Get-ScheduledTaskInfo | Format-Table TaskName, State, LastRunTime, LastTaskResult

# Confirmar que Python corre como SYSTEM (LastTaskResult 267009 = corriendo)
Get-WmiObject Win32_Process -Filter "Name='python.exe'" | ForEach-Object { "{0}  ->  {1}\{2}" -f $_.ProcessId, $_.GetOwner().Domain, $_.GetOwner().User }

# Ver logs
Get-Content C:\taginfo\logs\dashboard.log -Tail 30
```

### Windows Update / reinicios
- Configurar "Horas activas" en Windows Update para evitar reinicios en horario laboral
- El máximo es 18 horas (ej: 06:00 a 00:00)
- Si Update tiene pendiente muchos días, puede forzar reinicio igual al vencer el grace period
- Si la VM se reinicia, las tareas arrancan solas (son ONSTART)

---

## Configuración del entorno

### `ftp_credenciales.bat` (LOCAL ONLY — gitignoreado, NUNCA commitear)
```bat
set FTP_HOST=www.wurth.com.ar
set FTP_USER=wurth_demotel
set FTP_PASS=TuContraseñaReal
set FTP_PATH=/download/w20260609a01/
set FTP_PATH_WEB=/download/w20260611a01/
```

- `FTP_PATH` = app móvil (Daniel, celular)
- `FTP_PATH_WEB` = dashboard web completo (PC externa). Dejar vacío para no subir.

### Python
- Path en VM: `C:\Users\Dashboard-Daniel\AppData\Local\Programs\Python\Python312-32\python.exe`
- Python 32 bits (requerido por los drivers ODBC de 32 bits)

### Cómo correr manualmente (Windows)
```bat
cd C:\taginfo
git pull origin claude/gifted-johnson-BoqhJ
iniciar_dashboard.bat
```
Abrir browser en `http://localhost:8765`

---

## Rama de desarrollo

`claude/gifted-johnson-BoqhJ` en `elterco2012-dev/taginfo`

Antes de cada commit corre automáticamente `check_features.py` (pre-commit hook).
Si falla, corregir lo que falta antes de continuar.

---

## Problemas conocidos y soluciones

| Problema | Causa | Solución |
|---|---|---|
| FTP no arranca | `start_snapshot_job` se pierde en merges | Verificar que esté en `main()` con ambos args |
| Dashboard web FTP no actualiza | `FTP_PATH_WEB` no está en `ftp_credenciales.bat` | Agregar `set FTP_PATH_WEB=/download/w20260611a01/` |
| Gráfico no carga en kiosk web | Kiosk usaba `/static/chart.min.js` (path local) | `get_web_html()` reemplaza por CDN de chart.js |
| Snapshot muestra "MSPA OK" con datos viejos | Solo chequeaba `data.*_error`, nunca la edad | `get_web_html()` parsea `data.timestamp` y muestra "DESACTUALIZADO" si >600s |
| Gráfico muestra promedio inflado | 2 queries `trend_rows`, el segundo (CURDATE) pisaba el primero | Un solo query filtrando por wd_log |
| Dashboard se cortaba al cerrar sesión RDP | Corría en sesión de usuario, no como servicio | Tarea programada corre como `NT AUTHORITY\SYSTEM` |
| Tarea programada no existe / se perdió | Nunca fue creada o se borró | Recrear con PowerShell (ver sección Infraestructura) |
| `schtasks /Create` en PowerShell no crea la tarea | El `^` de continuación de línea no funciona en PS | Usar `New-ScheduledTask*` cmdlets nativos de PowerShell |
| `ftp_credenciales.bat` se pisa con git pull | Estaba trackeado. Ahora gitignoreado | Nunca commitear ese archivo |
| Conflictos de merge pisan features | `-X ours` o `--theirs` toma versión sin features | Siempre correr `python3 check_features.py` después de resolver conflictos |
| Puerto 8765 en TIME_WAIT | Proceso anterior no liberó el puerto | Esperar 1-2 min o matar con `netstat -ano \| findstr :8765` + `taskkill /PID N /F` |
| DSN ODBC no disponible con cuenta SYSTEM | DSN configurado como "DSN de usuario" | Recrear los DSN en la pestaña "DSN de sistema" en "Orígenes de datos ODBC (32 bits)" |
| KPI cards desalineados verticalmente | Cards 1 y 2 tienen footer de 2 líneas, los otros 1 | `.kpi-top{height:44px}` fija la altura del área de valor |
| `setup_tarea.bat` falla en PowerShell | `.\setup_tarea.bat` en PS no ejecuta igual que CMD | Abrir CMD como admin y correr ahí, o usar los cmdlets de PS directamente |

---

## Pendientes / trabajo en progreso

- **Redirect mobile automático**: cuando alguien abre el dashboard local desde un celular,
  redirigir a la app PWA (`/download/w20260609a01/`). Feature postergado por Daniel
  ("quiero presentarlo como novedad"). No implementar sin confirmación explícita.
- Verificar que el promedio del gráfico de junio coincida con $161.839.869 (7 días hábiles)
- Migrar proyecto a cuenta Team de Wurth cuando esté lista
- Activar Windows License en la VM (`Activar Windows` aparece en esquina — no afecta funcionamiento pero es pendiente)

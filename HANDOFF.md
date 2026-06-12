# HANDOFF.md — Wurth Operations Dashboard
**Fecha de handoff:** 2026-06-12
**Rama de desarrollo:** `claude/gifted-johnson-BoqhJ` en `elterco2012-dev/taginfo`

---

## Estado de la sesión

### Completado en esta sesión ✅

| Tarea | Detalle |
|---|---|
| Dashboard web vía FTP | `get_web_html()` genera versión estática idéntica al dashboard local, incluyendo kiosk mode. Se sube a `FTP_PATH_WEB` |
| Detección de datos obsoletos (web) | La versión FTP muestra "DESACTUALIZADO" si `data.timestamp` tiene >600s. Antes siempre mostraba "OK" |
| Chart.js en kiosk web | El kiosk estático cargaba `/static/chart.min.js` (path local). Se reemplaza por CDN en `get_web_html()` |
| ctxBar (barra de contexto) | Reemplazó `alertRibbon()` + `northStrip()`. Una sola barra color-coded (ok/warn/danger) con ícono trending, alerta de ritmo, Restante, Venta hoy |
| Íconos Lucide SVG | Sistema `ico(name, w)` con dict `ICONS` en el JS del kiosk. Elimina dependencia de emojis |
| KPI alignment | `.kpi-top{height:44px}` fija altura del área de valor para que los 4 KPI cards queden alineados |
| Kiosk timer 30s | `ROTATE_MS=30000` (era 20s) |
| App móvil PWA v2 | Rediseño completo en `ftp_snapshot.py`: `fmtK()`, alert banner, hero plan con proyección, live cards, detalle colapsable, logo Wurth |
| Tareas programadas como SYSTEM | `WurthDashboard` y `WurthDashboardWatchdog` corren como `NT AUTHORITY\SYSTEM`. Sobreviven reinicios y cierres de sesión RDP |
| `setup_tarea.bat` actualizado | Ya no pide contraseña de usuario. Usa cuenta SYSTEM |
| CLAUDE.md completo | Reescrito con toda la arquitectura, decisiones técnicas, infraestructura y problemas conocidos |
| Diagnóstico de corte nocturno | El corte del 12/06 02:32 fue cierre de sesión RDP (no reinicio). Resuelto con tarea SYSTEM |

### Verificado en producción ✅
- Python corre como `NT AUTHORITY\SYSTEM` (PID verificado con `Get-WmiObject`)
- Watchdog activo (`LastTaskResult: 267009` = corriendo)
- Test de cierre de sesión RDP: el FTP siguió actualizando mientras la sesión estaba cerrada
- Las dos rutas FTP (`w20260609a01` app móvil + `w20260611a01` dashboard web) actualizando correctamente

---

## Tareas pendientes (orden de prioridad)

### 1. Redirect automático mobile (POSTERGADO por Daniel)
Cuando alguien abra `http://localhost:8765` desde un celular, redirigir automáticamente
a la app PWA en FTP. Feature listo para implementar pero Daniel quiere presentarlo como
novedad en otro momento. **No implementar sin confirmación explícita de Daniel.**

### 2. Validar promedio del gráfico de tendencia de junio
Verificar que el promedio de junio en el trend chart coincida con `$161.839.869`
(base: 7 días hábiles). Es una validación de exactitud, no un bug conocido.

### 3. Activar licencia de Windows en la VM
`"Activar Windows"` aparece en la esquina inferior derecha de la VM. No afecta el
funcionamiento pero es deuda técnica pendiente.

### 4. Migrar a cuenta Team de Wurth
Cuando la cuenta Team de Wurth Argentina esté lista, migrar el repo desde
`elterco2012-dev/taginfo` a esa organización.

---

## Decisiones técnicas importantes

### Por qué la tarea corre como SYSTEM (no como usuario)
La tarea original usaba las credenciales de `Dashboard-Daniel`. Si la contraseña del
usuario vencía o cambiaba, la tarea dejaba de funcionar (era exactamente lo que ocurría).
Con `NT AUTHORITY\SYSTEM` no hay contraseña que expire. El riesgo de seguridad adicional
es bajo: red interna, app de solo lectura, sin escritura a DBs.

**Prerequisito crítico:** los DSN ODBC (`"Wurth Reactor Produccion"` y `"MSPA"`) deben
estar en la pestaña **"DSN de sistema"** (no "DSN de usuario") en "Orígenes de datos ODBC
(32 bits)". SYSTEM no puede ver los DSN de usuario.

### Por qué el kiosk usa scroll en vez de show/hide
Mostrar/ocultar divs rompía el layout (charts, KPIs se recalculaban). El scroll-based
kiosk mantiene todo el DOM renderizado y simplemente desplaza la vista.

### Por qué `get_web_html()` usa `.replace()` en vez de templates
El dashboard entero está en un solo archivo Python (`dashboard.py`). Separarlo en
templates agregaría complejidad sin beneficio claro. Los `.replace()` son quirúrgicos
y fáciles de auditar. Si se agregan nuevos features al dashboard local, hay que verificar
que `get_web_html()` siga funcionando correctamente.

### Por qué hay dos rutas FTP
- `FTP_PATH` (`w20260609a01`): app móvil PWA para celular. Existe desde el inicio.
- `FTP_PATH_WEB` (`w20260611a01`): dashboard completo para acceso desde PC externa.
  Agregado el 11/06/2026. Si `FTP_PATH_WEB` está vacío, solo sube la app móvil.

---

## Errores conocidos y pistas

### `setup_tarea.bat` no funciona desde PowerShell
El `^` de continuación de línea de CMD no funciona en PowerShell. El bat se ve como que
corre pero los `schtasks /Create` fallan silenciosamente.
**Solución:** usar los cmdlets nativos de PowerShell (ver sección de comandos abajo),
o abrir CMD como Administrador y correr el bat desde ahí.

### DSN ODBC no disponible con cuenta SYSTEM
Si el dashboard arranca con SYSTEM pero no puede conectarse a Reactor o MSPA, los DSN
están configurados como "DSN de usuario".
**Solución:** abrir "Orígenes de datos ODBC (32 bits)" → pestaña "DSN de sistema" →
recrear los DSN con los mismos nombres exactos.

### Puerto 8765 en TIME_WAIT
Si el dashboard crasheó recientemente, el puerto puede quedar en TIME_WAIT 1-2 minutos.
```bat
netstat -ano | findstr :8765
taskkill /PID <numero> /F
```

### FTP dashboard web no actualiza
Verificar que `FTP_PATH_WEB` esté seteado en `ftp_credenciales.bat`. Si está vacío,
`ftp_snapshot.py` salta la subida del dashboard web silenciosamente.

### `start_snapshot_job` se pierde en merges
Si después de un merge el FTP deja de funcionar, verificar que en `main()` esté:
```python
start_snapshot_job(get_cached_data, get_web_html)
```
Con ambos argumentos. El segundo (`get_web_html`) es para el dashboard web.

---

## Comandos clave

### Verificar estado en producción (PowerShell)
```powershell
# Estado tareas
Get-ScheduledTask "WurthDashboard","WurthDashboardWatchdog" | Get-ScheduledTaskInfo | Format-Table TaskName, State, LastRunTime, LastTaskResult

# Confirmar que Python corre como SYSTEM
Get-WmiObject Win32_Process -Filter "Name='python.exe'" | ForEach-Object { "{0}  ->  {1}\{2}" -f $_.ProcessId, $_.GetOwner().Domain, $_.GetOwner().User }

# Ver logs en vivo
Get-Content C:\taginfo\logs\dashboard.log -Tail 30 -Wait

# Ver logs del watchdog
Get-Content C:\taginfo\logs\watchdog.log -Tail 20
```

### Recrear tareas como SYSTEM (PowerShell como Administrador)
```powershell
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
$settings  = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

# Dashboard
$action  = New-ScheduledTaskAction -Execute "C:\taginfo\iniciar_dashboard.bat"
$trigger = New-ScheduledTaskTrigger -AtStartup; $trigger.Delay = "PT1M"
Register-ScheduledTask -TaskName "WurthDashboard" -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force

# Watchdog
$action  = New-ScheduledTaskAction -Execute "C:\taginfo\watchdog_dashboard.bat"
$trigger = New-ScheduledTaskTrigger -AtStartup; $trigger.Delay = "PT2M"
Register-ScheduledTask -TaskName "WurthDashboardWatchdog" -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force

# Arrancar ahora sin reiniciar
Start-ScheduledTask -TaskName "WurthDashboard"
Start-ScheduledTask -TaskName "WurthDashboardWatchdog"
```

### Actualizar código en la VM
```bat
cd C:\taginfo
git pull origin claude/gifted-johnson-BoqhJ
```
Las tareas levantan el código nuevo en el próximo restart automático (o forzar
`Stop-ScheduledTask` + `Start-ScheduledTask`).

### Correr manualmente (debug)
```bat
cd C:\taginfo
iniciar_dashboard.bat
```
Abrir `http://localhost:8765`. El modo oscuro está en `?dark=1`.

---

## Variables de entorno (ftp_credenciales.bat — LOCAL ONLY, gitignoreado)
```bat
set FTP_HOST=www.wurth.com.ar
set FTP_USER=wurth_demotel
set FTP_PASS=<contraseña real>
set FTP_PATH=/download/w20260609a01/
set FTP_PATH_WEB=/download/w20260611a01/
```
Este archivo NO está en el repo. Debe existir en `C:\taginfo\` en la VM.
`FTP_PATH_WEB` fue agregado el 12/06/2026 — verificar que esté en la VM.

---

## Rutas importantes en la VM
```
C:\taginfo\               → raíz del proyecto
C:\taginfo\logs\          → dashboard.log, watchdog.log
C:\taginfo\ftp_credenciales.bat  → credenciales FTP (LOCAL, no en git)
C:\Users\Dashboard-Daniel\AppData\Local\Programs\Python\Python312-32\python.exe
```

## URLs
- Dashboard local: `http://localhost:8765`
- App móvil FTP: `http://www.wurth.com.ar/download/w20260609a01/`
- Dashboard web FTP: `http://www.wurth.com.ar/download/w20260611a01/`
- Kiosk local: `http://localhost:8765/kiosk`
- Kiosk web: `http://www.wurth.com.ar/download/w20260611a01/kiosk.html`

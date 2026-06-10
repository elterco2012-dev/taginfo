# Guía de despliegue — Dashboard Würth en VM dedicada

Esta guía cubre **clonar una VM existente** en vSphere y dejar el dashboard
corriendo 24/7 como servicio de Windows, sin depender de tu PC.

> ⚠️ **Antes de empezar:** clonar toca el vSphere productivo. Si tenés
> cualquier duda en un paso, frená y consultá con quien administra la
> infraestructura. Es preferible preguntar que romper algo en la red.

---

## FASE 0 — Qué necesitás antes de arrancar

- [ ] Acceso al **vSphere Client** con permisos para clonar VMs
- [ ] Saber una **IP libre** en la red interna (pedila a IT o revisá DHCP)
- [ ] Credenciales de **administrador de dominio** para re-unir la VM
- [ ] Los datos de conexión a **Reactor (MySQL)** y **MSPA (Informix)**
- [ ] Confirmar que la red de la VM llega a ambas bases

---

## FASE 1 — Elegir qué VM clonar

**Cloná SOLO un servidor miembro simple. NUNCA:**
- ❌ SRVDC1 / SRVDC2 (Domain Controllers — corrompe Active Directory)
- ❌ APP Contable (sistema productivo)
- ❌ LNX-OpenSuse-MSPA (es Linux y es la base MSPA)

**Candidatos OK** (servidores miembro Windows, sin rol crítico):
- ✅ NPrint, Qview, o un File Server secundario

> El objetivo de clonar es **heredar Symantec + dominio + políticas de
> seguridad** ya configuradas, para no hacerlas a mano.

---

## FASE 2 — Clonar la VM en vSphere

1. En vSphere Client, click derecho sobre la VM elegida.
2. **Clone → Clone to Virtual Machine...**
3. Nombre de la nueva VM: `SRV-DASHBOARDS`
4. Seleccioná el mismo host/cluster y datastore con espacio.
5. En **Select clone options**, NO marques "Power on" todavía.
6. Finalizá y esperá que termine el clonado.

> Dejala **apagada** hasta cambiarle el nombre e IP, para que no choque
> con el original en la red.

---

## FASE 3 — Primer arranque y cambios de identidad

Encendé la VM nueva y entrá por consola de vSphere (no por RDP todavía,
para evitar conflicto de IP).

### 3.1 — Cambiar IP

1. Panel de control → Red → adaptador → Propiedades → IPv4.
2. Asigná la **IP libre** que conseguiste (ej: `10.60.20.50`).
3. Máscara, gateway y DNS: los mismos que el resto de la red
   (DNS apunta al DC: `10.60.20.22`).

### 3.2 — Cambiar nombre del equipo

1. Este equipo → Propiedades → Cambiar configuración → Cambiar.
2. Nombre: `SRV-DASHBOARDS`
3. **No** lo unas al dominio todavía — primero reiniciá con el nombre nuevo.
4. Reiniciá.

### 3.3 — Re-unir al dominio

1. Tras reiniciar: Propiedades → Cambiar → Dominio: `wurth-ar.local`
2. Pedirá credenciales de admin de dominio.
3. Reiniciá de nuevo.

> Esto regenera la identidad de la máquina en el dominio (evita el conflicto
> de SID del clon).

### 3.4 — Verificar Symantec

1. Abrí el cliente Symantec.
2. Confirmá que esté **reportando a la consola** y con definiciones al día.
3. Si quedó con la identidad del original, en IT pueden re-asignarlo.

---

## FASE 4 — Instalar Python y dependencias

### 4.1 — Python

1. Descargá Python 3.12 (64-bit) de python.org.
2. Al instalar, marcá **"Add Python to PATH"**.
3. Verificá en CMD:
   ```cmd
   python --version
   ```

### 4.2 — pyodbc

```cmd
python -m pip install pyodbc
```

### 4.3 — Drivers ODBC

Necesitás los mismos drivers que en tu PC actual:
- **MySQL ODBC** (para Reactor)
- **Informix ODBC / IBM Informix Client SDK** (para MSPA)

> Copiá la configuración exacta desde tu PC: Panel de control →
> Herramientas administrativas → **Orígenes de datos ODBC (64-bit)**.
> Ahí ves cómo están configurados los DSN `Wurth Reactor Produccion` y `MSPA`.

### 4.4 — Configurar los DSN en la VM

En la VM, abrí **Orígenes de datos ODBC (64-bit)** → pestaña **DSN de sistema**
(no de usuario, para que el servicio los vea) y creá:

- `Wurth Reactor Produccion` → apuntando al MySQL de Reactor
- `MSPA` → apuntando al Informix de MSPA

Replicá servidor, puerto, base, usuario y contraseña de tu PC.

---

## FASE 5 — Traer el código

```cmd
cd C:\
git clone https://github.com/elterco2012-dev/taginfo.git dashboard
cd dashboard
git checkout claude/gifted-johnson-BoqhJ
```

Probá que levante a mano primero:

```cmd
python dashboard.py
```

Abrí en la misma VM: `http://localhost:8765`
Si ves datos, el acceso a las bases funciona. Cortá con `Ctrl+C`.

---

## FASE 6 — Dejarlo como servicio de Windows (arranque automático)

Usamos **NSSM** (Non-Sucking Service Manager), la forma más simple y robusta.

### 6.1 — Instalar NSSM

1. Descargá NSSM de https://nssm.cc/download
2. Descomprimí y copiá `nssm.exe` (carpeta `win64`) a `C:\dashboard\`

### 6.2 — Crear el servicio

En CMD **como administrador**:

```cmd
cd C:\dashboard
nssm install WurthDashboard
```

Se abre una ventana. Configurá:
- **Path:** `C:\Python312\python.exe` (ruta real de tu python)
- **Startup directory:** `C:\dashboard`
- **Arguments:** `dashboard.py`

Pestaña **Details:**
- Display name: `Würth Operations Dashboard`

Pestaña **Exit actions:**
- Restart si falla (viene por defecto) → así se recupera solo.

Click **Install service**.

### 6.3 — Iniciar el servicio

```cmd
nssm start WurthDashboard
```

Verificá en **services.msc** que `WurthDashboard` esté "En ejecución" y
"Automático".

> A partir de acá, arranca solo con Windows y se reinicia si se cae.

---

## FASE 7 — Acceso desde la red

### 7.1 — Abrir el puerto en el Firewall de Windows

En CMD como administrador:

```cmd
netsh advfirewall firewall add rule name="Dashboard 8765" dir=in action=allow protocol=TCP localport=8765
```

### 7.2 — Acceder desde cualquier PC

Desde cualquier máquina de la red:
```
http://SRV-DASHBOARDS:8765
```
o por IP:
```
http://10.60.20.50:8765
```

> NO abrir este puerto al exterior / internet. Solo red interna.

---

## FASE 8 — Mantenimiento / actualizaciones

Cuando haya cambios nuevos en el código:

```cmd
cd C:\dashboard
nssm stop WurthDashboard
git pull origin claude/gifted-johnson-BoqhJ
nssm start WurthDashboard
```

---

## Checklist final

- [ ] VM clonada, renombrada, re-IP y re-unida al dominio
- [ ] Symantec reportando OK
- [ ] Python + pyodbc instalados
- [ ] DSN de sistema `Wurth Reactor Produccion` y `MSPA` configurados
- [ ] Código clonado y probado a mano (ve datos en localhost:8765)
- [ ] Servicio `WurthDashboard` en Automático y corriendo
- [ ] Puerto 8765 abierto solo en red interna
- [ ] Acceso confirmado desde otra PC de la red
- [ ] NO expuesto a internet

---

## Si algo falla

| Síntoma | Posible causa |
|---------|---------------|
| No carga `localhost:8765` en la VM | Servicio no arrancó → `nssm status WurthDashboard` |
| Carga pero sin datos / error DB | DSN mal configurado o VM sin acceso a las bases |
| No carga desde otra PC | Firewall (Fase 7.1) o IP/nombre mal |
| Se cae solo | Revisá logs; NSSM lo reinicia, pero mirá el por qué |

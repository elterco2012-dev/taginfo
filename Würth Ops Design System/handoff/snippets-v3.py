# Snippets clave de la v3 (lógica que va más allá del CSS)
# Portá estos patrones a tu dashboard.py. El CSS ya está en dashboard-v3.css.

# ─────────────────────────────────────────────────────────────────────
# 1) SPARKLINE — mini-gráfico SVG sin librerías
#    Recibe una lista de ~14 valores (días hábiles) y dibuja la tendencia.
#    color='auto' → verde si el último ≥ primero, rojo si baja.
# ─────────────────────────────────────────────────────────────────────
def sparkline(data, color="auto", w=74, h=30):
    if not data or len(data) < 2:
        return ""
    mn, mx = min(data), max(data)
    rng = (mx - mn) or 1
    pad = 2
    step = (w - pad * 2) / (len(data) - 1)
    pts = [(pad + i * step, h - pad - ((v - mn) / rng) * (h - pad * 2)) for i, v in enumerate(data)]
    d = " ".join(("L" if i else "M") + f"{x:.1f} {y:.1f}" for i, (x, y) in enumerate(pts))
    area = f"{d} L{pts[-1][0]:.1f} {h} L{pts[0][0]:.1f} {h} Z"
    up = data[-1] >= data[0]
    c = ("var(--green)" if up else "var(--red)") if color == "auto" else color
    gid = "sg" + str(abs(hash(tuple(data))) % 99999)
    return f'''<svg class="spark" viewBox="0 0 {w} {h}" preserveAspectRatio="none">
  <defs><linearGradient id="{gid}" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="{c}" stop-opacity="0.18"/><stop offset="100%" stop-color="{c}" stop-opacity="0"/>
  </linearGradient></defs>
  <path d="{area}" fill="url(#{gid})"/>
  <path d="{d}" fill="none" stroke="{c}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
  <circle cx="{pts[-1][0]:.1f}" cy="{pts[-1][1]:.1f}" r="2" fill="{c}"/>
</svg>'''

# Necesitás guardar/consultar los últimos ~14 días hábiles por métrica.
# Si no tenés histórico a mano, una query con GROUP BY fecha LIMIT 14 alcanza.


# ─────────────────────────────────────────────────────────────────────
# 2) ALERTAS POR EXCEPCIÓN — sólo se muestran si cruzan umbral.
#    Devolvé una lista; si está vacía, NO renderices la banda.
#    AJUSTÁ LOS UMBRALES a tu operación real.
# ─────────────────────────────────────────────────────────────────────
RET_WARN, RET_DANGER = 20.0, 30.0   # % de retenidos

def build_alerts(d):
    out = []
    ret = d["flow"]["retenido"]["pct"]
    if ret >= RET_WARN:
        out.append({
            "sev": "danger" if ret >= RET_DANGER else "warn",
            "ico": "pauseCircle",
            "msg": f'<b>Retenidos en {fmt_n(ret,1)}%</b> — por encima del objetivo de 20% '
                   f'({fmt_n(d["flow"]["retenido"]["v"])} pedidos)',
            "act": "Ver retenidos →",
        })
    if d["plan"]["pct"] < d["plan"]["pace"]:
        gap = d["plan"]["pace"] - d["plan"]["pct"]
        out.append({
            "sev": "warn", "ico": "trendingDown",
            "msg": f'Plan de ventas <b>{fmt_n(gap,1)} pts por debajo del ritmo</b> '
                   f'({fmt_n(d["plan"]["pct"],1)}% vs {d["plan"]["pace"]}%)',
            "act": "Ver plan →",
        })
    # OCULTAS a pedido (descomentar para reactivar):
    # if d.get("sin_facturar", 0) > 0:
    #     out.append({"sev": "danger" if d["sin_facturar"] >= 5 else "warn", "ico": "userX",
    #         "msg": f'<b>{fmt_n(d["sin_facturar"])} vendedores</b> activos aún sin facturar hoy',
    #         "act": "Ver detalle →"})
    # credito = next((m for m in d["mspa"] if "Crédito" in m["k"]), None)
    # if credito and credito.get("sev","ok") != "ok":
    #     out.append({"sev": credito["sev"], "ico": "creditCard",
    #         "msg": f'<b>{fmt_k(credito["val"])}</b> bloqueado por límite de crédito '
    #                f'({fmt_n(credito["ords"])} pedidos)', "act": "Revisar →"})
    return out

def render_alerts(d):
    alerts = build_alerts(d)
    if not alerts:
        return ""   # sin alertas → la banda no aparece
    rows = "".join(
        f'<div class="alert {a["sev"]}">{icon(a["ico"])}<span>{a["msg"]}</span>'
        f'<a class="a-act" href="#">{a["act"]}</a></div>'
        for a in alerts
    )
    return f'<div class="alerts">{rows}</div>'


# ─────────────────────────────────────────────────────────────────────
# 3) ESTADO DE CONEXIÓN + "DATOS AL"
#    sev: "ok" (verde, pulsa) | "slow" (ámbar) | "down" (rojo).
#    Derivalo de cuán viejo es el último dato vs ahora.
# ─────────────────────────────────────────────────────────────────────
def conn_state(segundos_desde_ultimo_dato, umbral_lento=120, umbral_caido=600):
    if segundos_desde_ultimo_dato is None:   return "down"
    if segundos_desde_ultimo_dato > umbral_caido:  return "down"
    if segundos_desde_ultimo_dato > umbral_lento:  return "slow"
    return "ok"

# En el header:
#   <span class="conn-row"><span class="conn-dot {sev}"></span>
#     MSPA {ok|lento|sin conexión} · datos al <b>{HH:MM:SS}</b></span>
# En cada card el sello "datos al": <span class="stamp">datos al {HH:MM:SS}</span>


# ─────────────────────────────────────────────────────────────────────
# 4) SEMÁFOROS EN MSPA
#    Cada fila lleva un punto: <span class="mspa-sem {warn|danger}"></span>
#    sev por fila según tus reglas (ej. crédito bloqueado > X → "danger").
# ─────────────────────────────────────────────────────────────────────
def mspa_sem(sev):
    return "mspa-sem" + (f" {sev}" if sev and sev != "ok" else "")


# ─────────────────────────────────────────────────────────────────────
# 5) META / OBJETIVO junto al KPI
# ─────────────────────────────────────────────────────────────────────
def meta_chip(curr, target, fmt=fmt_n):
    if not target:
        return ""
    ok = curr >= target
    return (f'<span class="meta-chip"><span class="dot {"ok" if ok else "warn"}"></span>'
            f'meta {fmt(target)}</span>')


# ─────────────────────────────────────────────────────────────────────
# 6) SKELETON  → al generar server-side normalmente no hace falta.
#    Si tu front hace fetch async, poné class="main is-loading" mientras
#    carga y sacala al llegar los datos (el CSS hace el shimmer solo).
#
# 7) MODO TV  → un botón que togglea class="tv" en <body>. El CSS agranda
#    los números para leer a distancia. (body.tv en dashboard-v3.css)
#
# 8) EXPORT  → botón que llama window.print(); el CSS @media print ya
#    oculta los controles y evita cortar cards.

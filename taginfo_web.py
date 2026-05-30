"""
TagInfo Web - DAILY INFO 2 SALES
Servidor HTTP minimalista (sin Flask). Solo pyodbc.
SOLO LECTURA - no INSERT/UPDATE/DELETE/DDL.

Uso:
    python.exe taginfo_web.py
Abrir: http://localhost:8765
"""

import json
import decimal
import pyodbc
import threading
from datetime import date, datetime
from http.server import BaseHTTPRequestHandler, HTTPServer

class _Enc(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            return float(o)
        return super().default(o)


DSN = "MSPA"
FIRMA = 1
PORT = 8765

# Cache para no golpear la BD en cada request del browser
_cache_lock = threading.Lock()
_cache_data = None
_cache_time = None
CACHE_SECONDS = 60  # refrescar datos como máximo cada 60s


def get_conn():
    return pyodbc.connect(f"DSN={DSN};", autocommit=True)


def run(cur, sql):
    try:
        cur.execute(sql)
        return cur.fetchall()
    except Exception as e:
        print(f"  SQL ERROR: {e}")
        return []



def fetch_data():
    conn = get_conn()
    cur = conn.cursor()

    def q1(sql):
        rows = run(cur, sql)
        if rows:
            return rows[0][0] or 0, rows[0][1] or 0, float(rows[0][2]) if rows[0][2] else 0.0
        return 0, 0, 0.0

    # ── 1. Backorders (Plazos viejos / selrueck) ─────────────────────────
    # Fuente: taginfo2.4gl selrueck
    # termin <= TODAY, kzentns='0', aufkstat>=0, aufart IN(0,2,4,6,7,8)
    # (auftme-gliefme)>0, liefsp<>'2'&&<>'9' OR liefspkz='1'
    # valor: poswert/auftme * (auftme - gliefme)
    back_ords, back_pos, back_val = q1(f"""
        SELECT COUNT(DISTINCT f092.auftrag), COUNT(*),
               SUM(f092.poswert/f092.auftme * (f092.auftme - f092.gliefme))
          FROM f090, f092, kund
         WHERE f092.firma={FIRMA} AND f090.firma=f092.firma AND kund.firma=f090.firma
           AND f090.auftrag=f092.auftrag AND kund.kdnr=f090.kdnr
           AND f092.termin <= TODAY
           AND f092.kzentns = '0'
           AND f090.aufkstat >= 0
           AND f090.aufart IN ('0','2','4','6','7','8')
           AND (f092.auftme - f092.gliefme) > 0
           AND f092.kzerl = '0'
           AND f092.auftme <> 0
           AND ((kund.liefsp <> '2' AND kund.liefsp <> '9') OR f090.liefspkz = '1')
    """)

    # ── 2. Bloqueados por Limite credito (selkredlim) ────────────────────
    # Fuente: taginfo2.4gl selkredlim
    # posstat<9, (aufkstat>=0 OR aufkstat=-9), liefsp='2'OR'9' AND liefspkz<>'1'
    bloq_ords, bloq_pos, bloq_val = q1(f"""
        SELECT COUNT(DISTINCT f092.auftrag), COUNT(*),
               SUM(f092.poswert/f092.auftme * (f092.auftme - f092.gliefme))
          FROM f090, f092, kund
         WHERE f092.firma={FIRMA} AND f090.firma=f092.firma AND kund.firma=f090.firma
           AND f090.auftrag=f092.auftrag AND kund.kdnr=f090.kdnr
           AND f092.posstat < 9
           AND (f090.aufkstat >= 0 OR f090.aufkstat = -9)
           AND f090.aufart IN ('0','2','4','6','7','8')
           AND (f092.auftme - f092.gliefme) > 0
           AND f092.kzerl = '0'
           AND f092.auftme <> 0
           AND ((kund.liefsp = '2' OR kund.liefsp = '9') AND f090.liefspkz <> '1')
    """)

    # ── 3. Bloqueado Status < -1 (selneg) ───────────────────────────────
    # Fuente: taginfo2.4gl selneg — aufkstat < -1, sin kredlim
    stat_ords, stat_pos, stat_val = q1(f"""
        SELECT COUNT(DISTINCT f092.auftrag), COUNT(*),
               SUM(f092.poswert/f092.auftme * (f092.auftme - f092.gliefme))
          FROM f090, f092, kund
         WHERE f092.firma={FIRMA} AND f090.firma=f092.firma AND kund.firma=f090.firma
           AND f090.auftrag=f092.auftrag AND kund.kdnr=f090.kdnr
           AND f092.posstat < 9
           AND f090.aufkstat < -1
           AND f090.aufart IN ('0','2','4','6','7','8')
           AND (f092.auftme - f092.gliefme) > 0
           AND f092.kzerl = '0'
           AND f092.auftme <> 0
           AND ((kund.liefsp <> '2' AND kund.liefsp <> '9') OR f090.liefspkz = '1')
    """)

    # ── 4. Pedidos Abiertos (Plazos futuros / seloffen) ──────────────────
    # Fuente: taginfo2.4gl seloffen — termin > TODAY, aufkstat>=0
    fut_ords, fut_pos, fut_val = q1(f"""
        SELECT COUNT(DISTINCT f092.auftrag), COUNT(*),
               SUM(f092.poswert/f092.auftme * (f092.auftme - f092.gliefme))
          FROM f090, f092, kund
         WHERE f092.firma={FIRMA} AND f090.firma=f092.firma AND kund.firma=f090.firma
           AND f090.auftrag=f092.auftrag AND kund.kdnr=f090.kdnr
           AND f092.termin > TODAY
           AND f090.aufkstat >= 0
           AND f090.aufart IN ('0','2','4','6','7','8')
           AND (f092.auftme - f092.gliefme) > 0
           AND f092.kzerl = '0'
           AND f092.auftme <> 0
           AND ((kund.liefsp <> '2' AND kund.liefsp <> '9') OR f090.liefspkz = '1')
    """)

    # ── 5. Produccion (selentns via f103) ───────────────────────────────
    # Fuente: taginfo2.4gl selentns — f103 kzdfue=0, valor: poswert/auftme*sollme
    prod_ords, prod_pos, prod_val = q1(f"""
        SELECT COUNT(DISTINCT f103.auftrag), COUNT(*),
               SUM(f092.poswert/f092.auftme * f103.sollme)
          FROM f103, f090, f092
         WHERE f103.firma={FIRMA} AND f090.firma=f103.firma AND f092.firma=f103.firma
           AND f103.auftrag=f090.auftrag AND f103.auftrag=f092.auftrag
           AND f103.posnr=f092.posnr
           AND f092.auftme <> 0
           AND (f103.kzdfue = 0 OR f103.kzdfue IS NULL)
    """)

    # ── 6. Remitos/Facturas abiertas (self105 + self107) ─────────────────
    # Fuente: taginfo2.4gl self105 (Lieferscheine) + self107 (Rechnungen)
    ls_ords, ls_pos, ls_val = q1(f"""
        SELECT COUNT(DISTINCT f105.auftrag), COUNT(*),
               SUM(f092.poswert/f092.auftme * f105.liefme)
          FROM f105, f090, f092
         WHERE f105.firma={FIRMA} AND f090.firma=f105.firma AND f092.firma=f105.firma
           AND f105.auftrag=f090.auftrag AND f105.auftrag=f092.auftrag
           AND f105.posnr=f092.posnr AND f092.auftme <> 0
           AND f105.liefnr IN (SELECT liefnr FROM f104
                                WHERE f104.firma={FIRMA} AND f104.liefstat < 9)
    """)
    re_ords, re_pos, re_val = q1(f"""
        SELECT COUNT(DISTINCT f107.auftrag), COUNT(*),
               SUM(f092.poswert/f092.auftme * f107.faktme)
          FROM f107, f090, f092, f106
         WHERE f107.firma={FIRMA} AND f107.firma=f106.firma AND f107.liefnr=f106.liefnr
           AND f090.firma=f107.firma AND f092.firma=f107.firma
           AND f107.auftrag=f090.auftrag AND f107.auftrag=f092.auftrag
           AND f107.posnr=f092.posnr AND f107.lieflfdnr=0 AND f092.auftme <> 0
           AND f090.aufart IN ('0','2','4','6','7','8')
           AND (f106.periode='0' OR f106.periode=' ' OR f106.periode IS NULL)
    """)
    rem_ords = ls_ords + re_ords
    rem_pos  = ls_pos  + re_pos
    rem_val  = ls_val  + re_val

    # ── 7. Venta diaria (sbascur) ────────────────────────────────────────
    # Fuente: taginfo2.4gl sbascur — sbas redat=TODAY, todos belegart
    venta_ords, venta_pos, venta_val = q1(f"""
        SELECT COUNT(DISTINCT auftrag), COUNT(*), SUM(netwert)
          FROM sbas
         WHERE firma={FIRMA} AND redat=TODAY
    """)

    conn.close()

    return {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "fecha": date.today().strftime("%d.%m.%Y"),
        "rows": [
            {"label": "Backorders (Plazos viejos)",        "val": back_val,  "ords": back_ords,  "pos": back_pos},
            {"label": "Bloqueados por Limite credito",     "val": bloq_val,  "ords": bloq_ords,  "pos": bloq_pos},
            {"label": "Bloqueado (Status< -1)",            "val": stat_val,  "ords": stat_ords,  "pos": stat_pos},
            {"label": "Pedidos Abiertos (Plazos futuros)", "val": fut_val,   "ords": fut_ords,   "pos": fut_pos},
            {"label": "Ordenes de produccion abiertas",    "val": prod_val,  "ords": prod_ords,  "pos": prod_pos},
            {"label": "Remitos/Facturas abiertas",         "val": rem_val,   "ords": rem_ords,   "pos": rem_pos},
            {"label": "Venta diaria",                      "val": venta_val, "ords": venta_ords, "pos": venta_pos},
        ],
    }


def get_cached_data():
    global _cache_data, _cache_time
    now = datetime.now()
    with _cache_lock:
        if _cache_data is None or (now - _cache_time).total_seconds() >= CACHE_SECONDS:
            print(f"  [{now.strftime('%H:%M:%S')}] Consultando BD...")
            try:
                _cache_data = fetch_data()
                _cache_time = now
                print(f"  [{now.strftime('%H:%M:%S')}] OK")
            except Exception as e:
                print(f"  [{now.strftime('%H:%M:%S')}] ERROR: {e}")
                if _cache_data is None:
                    _cache_data = {"error": str(e), "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"), "rows": []}
        return _cache_data


HTML_PAGE = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>DAILY INFO 2 SALES</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    background: #000;
    color: #b4d900;
    font-family: 'Courier New', Courier, monospace;
    font-size: 16px;
    padding: 12px 16px;
  }
  .title-bar {
    color: #000;
    background: #b4d900;
    padding: 2px 6px;
    margin-bottom: 4px;
    font-weight: bold;
    letter-spacing: 1px;
  }
  .sep { color: #b4d900; letter-spacing: 0; }
  .center { text-align: center; padding: 4px 0; font-weight: bold; letter-spacing: 2px; font-size: 17px; }
  .meta { margin: 6px 0 4px 0; }
  .meta span { margin-right: 32px; }
  table { width: 100%; border-collapse: collapse; margin-top: 8px; }
  th {
    text-align: right;
    padding: 2px 8px;
    font-weight: normal;
    color: #b4d900;
    border-bottom: 1px solid #b4d900;
    font-size: 15px;
  }
  th.left { text-align: left; }
  td { padding: 6px 8px; vertical-align: middle; }
  td.label { color: #b4d900; }
  td.colon { color: #b4d900; text-align: center; width: 20px; }
  td.val, td.num {
    text-align: right;
    color: #b4d900;
    border-bottom: 1px dashed #3a4a00;
    min-width: 120px;
  }
  td.num { min-width: 70px; }
  tr:hover td { background: #0a1400; }
  .footer {
    margin-top: 14px;
    color: #4a6400;
    font-size: 13px;
  }
  .footer span { color: #b4d900; }
  .dot { animation: blink 1s step-end infinite; }
  @keyframes blink { 0%,100%{opacity:1} 50%{opacity:0} }
  .error { color: #ff4444; margin-top: 8px; }
</style>
</head>
<body>
<div class="title-bar">taginfo2-1:  1.Anzeige  2.Taginfo EK  3.Taginfo Kunde  Hecho</div>
<div class="title-bar" style="background:transparent;color:#b4d900;">Anzeige Tagesinformation</div>
<div class="sep" id="sep1"></div>
<div class="center">DAILY INFO 2 SALES</div>
<div class="sep" id="sep2"></div>

<div class="meta">
  <span>Fecha : <span id="fecha">—</span></span>
  <span style="float:right;margin-right:0">
    &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
    <b>Value</b>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
    <b>Number<br>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Order</b>&nbsp;&nbsp;&nbsp;
    <b>Number<br>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Pos</b>
  </span>
</div>

<table>
  <thead>
    <tr>
      <th class="left" style="width:46%"></th>
      <th style="width:4%"></th>
      <th style="width:24%">Value</th>
      <th style="width:13%">Number<br>Order</th>
      <th style="width:13%">Number<br>Pos</th>
    </tr>
  </thead>
  <tbody id="tbody">
    <tr><td colspan="5" style="text-align:center;padding:20px;color:#4a6400;">Cargando<span class="dot">...</span></td></tr>
  </tbody>
</table>

<div class="footer" id="footer">
  Última actualización: <span id="ts">—</span>
  &nbsp;|&nbsp; Próxima en <span id="countdown">—</span>s
  &nbsp;|&nbsp; <span class="dot" id="live">●</span> LIVE
</div>
<div class="error" id="errmsg"></div>

<script>
const REFRESH = 60;  // segundos entre actualizaciones
let countdown = REFRESH;
let timer;

function fmtVal(n) {
  if (n === 0 || n === null) return '0.00';
  return n.toLocaleString('es-AR', {minimumFractionDigits:2, maximumFractionDigits:2});
}

function fmtNum(n) {
  if (!n) return '0';
  return n.toLocaleString('es-AR');
}

function render(data) {
  if (data.error) {
    document.getElementById('errmsg').textContent = 'Error: ' + data.error;
    return;
  }
  document.getElementById('errmsg').textContent = '';
  document.getElementById('fecha').textContent = data.fecha || '—';
  document.getElementById('ts').textContent = data.timestamp || '—';

  const sep = '='.repeat(100);
  document.getElementById('sep1').textContent = sep;
  document.getElementById('sep2').textContent = sep;

  const tbody = document.getElementById('tbody');
  tbody.innerHTML = '';
  for (const row of data.rows) {
    const tr = document.createElement('tr');
    tr.innerHTML =
      `<td class="label">${row.label}</td>` +
      `<td class="colon">:</td>` +
      `<td class="val">${fmtVal(row.val)}</td>` +
      `<td class="num">${fmtNum(row.ords)}</td>` +
      `<td class="num">${fmtNum(row.pos)}</td>`;
    tbody.appendChild(tr);
  }
}

async function load() {
  try {
    const r = await fetch('/api/data');
    const data = await r.json();
    render(data);
  } catch(e) {
    document.getElementById('errmsg').textContent = 'Error de conexión: ' + e;
  }
  countdown = REFRESH;
}

function tick() {
  document.getElementById('countdown').textContent = countdown;
  if (countdown <= 0) { load(); }
  else { countdown--; }
}

load();
timer = setInterval(tick, 1000);
</script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # silenciar log por cada request

    def send_json(self, data):
        body = json.dumps(data, ensure_ascii=False, cls=_Enc).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def send_html(self, html):
        body = html.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self.send_html(HTML_PAGE)
        elif self.path == "/api/data":
            self.send_json(get_cached_data())
        else:
            self.send_response(404)
            self.end_headers()


def main():
    print(f"TagInfo Web — DAILY INFO 2 SALES")
    print(f"DSN: {DSN}  |  FIRMA: {FIRMA}  |  SOLO LECTURA")
    print(f"Escuchando en http://localhost:{PORT}")
    print(f"Ctrl+C para detener\n")
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nDetenido.")


if __name__ == "__main__":
    main()

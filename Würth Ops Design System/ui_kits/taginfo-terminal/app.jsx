/* DAILY INFO 2 SALES — terminal recreation (cosmetic, fake data) */
const { useState, useEffect, useRef } = React;

const fmtVal = (n) => Number(n || 0).toLocaleString('es-AR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const fmtNum = (n) => Number(n || 0).toLocaleString('es-AR');

// Base rows mirror taginfo_web.py's 7 metrics.
const BASE = [
  { label: 'Backorders (Plazos viejos)', val: 1245800, ords: 142, pos: 318 },
  { label: 'Bloqueados por Limite credito', val: 842300, ords: 64, pos: 121 },
  { label: 'Bloqueado (Status< -1)', val: 318900, ords: 22, pos: 47 },
  { label: 'Pedidos Abiertos (Plazos futuros)', val: 8420110, ords: 388, pos: 902 },
  { label: 'Ordenes de produccion abiertas', val: 3110450, ords: 95, pos: 240 },
  { label: 'Remitos/Facturas abiertas', val: 2204600, ords: 156, pos: 410 },
  { label: 'Venta diaria', val: 3402190, ords: 57, pos: 188 },
];

// jitter the live "venta diaria" row a touch on each refresh
function snapshot() {
  const rows = BASE.map(r => ({ ...r }));
  const v = rows[6];
  v.val += Math.round((Math.random() - 0.3) * 60000);
  v.ords += Math.floor(Math.random() * 3);
  v.pos += Math.floor(Math.random() * 6);
  return rows;
}

const RULE = '='.repeat(100);

function TitleBars() {
  return (
    <React.Fragment>
      <div className="title-bar">taginfo2-1:&nbsp;&nbsp;1.Anzeige&nbsp;&nbsp;2.Taginfo EK&nbsp;&nbsp;3.Taginfo Kunde&nbsp;&nbsp;Hecho</div>
      <div className="title-bar plain">Anzeige Tagesinformation</div>
    </React.Fragment>
  );
}

function DataTable({ rows }) {
  return (
    <table>
      <thead>
        <tr>
          <th className="left" style={{ width: '46%' }}></th>
          <th style={{ width: '4%' }}></th>
          <th style={{ width: '24%' }}>Value</th>
          <th style={{ width: '13%' }}>Number<br />Order</th>
          <th style={{ width: '13%' }}>Number<br />Pos</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((r, i) => (
          <tr key={i}>
            <td className="label">{r.label}</td>
            <td className="colon">:</td>
            <td className="val">{fmtVal(r.val)}</td>
            <td className="num">{fmtNum(r.ords)}</td>
            <td className="num">{fmtNum(r.pos)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function Footer({ ts, countdown }) {
  return (
    <div className="footer">
      Última actualización: <b>{ts}</b>
      &nbsp;|&nbsp; Próxima en <b>{countdown}</b>s
      &nbsp;|&nbsp; <span className="dot">●</span> LIVE
    </div>
  );
}

function Terminal() {
  const REFRESH = 60;
  const [rows, setRows] = useState(snapshot());
  const [ts, setTs] = useState(new Date());
  const [countdown, setCountdown] = useState(REFRESH);
  const cd = useRef(REFRESH);

  useEffect(() => {
    const t = setInterval(() => {
      cd.current -= 1;
      if (cd.current <= 0) { setRows(snapshot()); setTs(new Date()); cd.current = REFRESH; }
      setCountdown(cd.current);
    }, 1000);
    return () => clearInterval(t);
  }, []);

  const fecha = ts.toLocaleDateString('es-AR', { day: '2-digit', month: '2-digit', year: 'numeric' }).replace(/\//g, '.');
  const tsStr = ts.toISOString().slice(0, 19).replace('T', ' ');

  return (
    <div className="screen">
      <TitleBars />
      <div className="sep">{RULE}</div>
      <div className="center">DAILY INFO 2 SALES</div>
      <div className="sep">{RULE}</div>
      <div className="meta">
        <span>Fecha : <b style={{ color: 'var(--term-fg)' }}>{fecha}</b><span className="cursor">_</span></span>
      </div>
      <DataTable rows={rows} />
      <Footer ts={tsStr} countdown={countdown} />
      <div className="hint">Solo lectura · refresco automático cada 60s · fuente: MSPA (Informix)</div>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<Terminal />);

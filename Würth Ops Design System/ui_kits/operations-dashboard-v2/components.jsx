/* Würth Operations Dashboard v2 — components (professional refinement) */
const { useState, useRef, useEffect } = React;

/* ── Header ───────────────────────────────────────────────────────────── */
function Header({ dateDisplay, dark, onToggleDark, onPickDate, onClearDate, freshM, freshR }) {
  const [open, setOpen] = useState(false);
  const [val, setVal] = useState('2026-05-27');
  return (
    <div className="hdr">
      <div className="hdr-left">
        <img className="hdr-logo" src="wurth-logo.png" alt="Würth" />
        <div className="div-v"></div>
        <div>
          <div className="hdr-title">Operations Dashboard</div>
          <div className="hdr-sub">Reactor · MSPA · Tiempo Real</div>
        </div>
      </div>
      <div className="hdr-right">
        <div className="date-badge" onClick={() => setOpen(o => !o)}>
          <Icon name="calendar" /> <span className="num">{dateDisplay}</span>
          {open && (
            <div className="date-pop" onClick={e => e.stopPropagation()}>
              <h4>Seleccionar fecha</h4>
              <input type="date" value={val} onChange={e => setVal(e.target.value)} />
              <div className="hint">Ingresá la fecha a consultar.</div>
              <button className="go" onClick={() => { onPickDate(val); setOpen(false); }}>Ver fecha</button>
              <button className="clr" onClick={() => { onClearDate(); setOpen(false); }}>Volver al día actual</button>
            </div>
          )}
        </div>
        <div className="freshness">
          MSPA en <b className="num">{freshM}s</b><br />
          Reactor en <b className="num">{freshR}min</b>
        </div>
        <div className="live"><div className="dot"></div>LIVE</div>
        <button className="mode-btn" onClick={onToggleDark} title={dark ? 'Modo claro' : 'Modo oscuro'}>
          <Icon name={dark ? 'sun' : 'moon'} />
        </button>
      </div>
    </div>
  );
}

/* ── Delta (color only on state) ──────────────────────────────────────── */
function Delta({ curr, prev }) {
  if (!prev || !curr) return null;
  const p = (curr - prev) / prev * 100;
  const up = p >= 0;
  return (
    <div className={'delta ' + (up ? 'up' : 'down')}>
      <Icon name={up ? 'arrowUp' : 'arrowDown'} cls="ico-sm" />
      {Math.abs(p).toFixed(1).replace('.', ',')}% <span style={{ color: 'var(--text-3)', fontWeight: 400 }}>vs. comp.</span>
    </div>
  );
}

/* ── HERO: Plan (dominant) + two headline stats ───────────────────────── */
function Hero({ d }) {
  const plan = d.plan;
  const onTrack = plan.pct >= plan.pace;
  const done = plan.pct >= 100;
  const fillColor = done ? 'var(--green)' : onTrack ? 'var(--wurth-red)' : 'var(--amber)';
  const stateCls = done || onTrack ? 'state-ok' : 'state-warn';
  const stateIco = done || onTrack ? 'checkCircle' : 'trendingDown';
  const stateTxt = done ? 'Plan cumplido' : onTrack ? 'En ritmo' : 'Por debajo del ritmo';
  return (
    <div className="hero">
      <div className="hero-main">
        <div className="hero-eyebrow"><Icon name="target" /> Plan de Ventas · Facturación acumulada del mes</div>
        <div className="hero-figs">
          <span className="hero-curr">{fmtK(plan.fact_acum)}</span>
          <span className="hero-total">/ {fmtK(plan.plan_total)}</span>
        </div>
        <div className="hero-pct-line">
          <span className="hero-pct" style={{ color: fillColor }}>{fmtN(plan.pct, 1)}%</span>
          <div className="plan-bar-bg">
            <div className="plan-bar-fill" style={{ width: Math.min(plan.pct, 100) + '%', background: fillColor }}></div>
            <div className="plan-bar-pace" style={{ left: plan.pace + '%' }}></div>
          </div>
          <span className={'state-tag ' + stateCls}><Icon name={stateIco} cls="ico-sm" /> {stateTxt}</span>
        </div>
        <div className="hero-foot">
          <span>Ritmo esperado a hoy: <b className="num">{plan.pace}%</b></span>
          <span>Restante: <b className="num">{fmtK(plan.plan_total - plan.fact_acum)}</b></span>
        </div>
      </div>
      <div className="hero-side">
        <div className="hero-stat">
          <div className="l">Venta del Día · MSPA</div>
          <div className="v">{fmtK(d.valor)}</div>
          <div className="d"><Delta curr={d.valor} prev={d.comp.valor} /></div>
        </div>
        <div className="hsep"></div>
        <div className="hero-stat">
          <div className="l">Pedidos Informados</div>
          <div className="v">{fmtN(d.pedidos)}</div>
          <div className="d"><Delta curr={d.pedidos} prev={d.comp.pedidos} /></div>
        </div>
      </div>
    </div>
  );
}

/* ── KPI strip (secondary, neutral) ───────────────────────────────────── */
function Kpi({ label, value, sub, delta }) {
  return (
    <div className="kpi">
      <div className="kpi-lbl">{label}</div>
      <div className="kpi-val">{value}</div>
      {delta}
      {sub && <div className="kpi-sub">{sub}</div>}
    </div>
  );
}
function KpiStrip({ d }) {
  return (
    <div className="sec">
      <div className="sec-lbl">Indicadores del día</div>
      <div className="kpi-grid">
        <Kpi label="Vendedores activos" value={fmtN(d.vendedores)} sub={`${fmtN(d.lineas)} líneas totales`} />
        <Kpi label="Pedidos / Vendedor" value={fmtN(d.avg_ped_vend, 1)} delta={<Delta curr={d.avg_ped_vend} prev={d.comp.avg_ped_vend} />} />
        <Kpi label="Promedio Líneas / Pedido" value={fmtN(d.avg_lineas, 1)} delta={<Delta curr={d.avg_lineas} prev={d.comp.avg_lineas} />} />
        <Kpi label="Ticket promedio" value={fmtK(d.valor / d.pedidos)} sub="valor / pedido informado" />
      </div>
    </div>
  );
}

/* ── Flow bar (neutral numbers, color only on the tick) ───────────────── */
function FlowSeg({ tick, label, val, sub }) {
  return (
    <div className="flow-cell">
      <div className="flow-dot"><span className={'flow-tick ' + tick}></span><span className="flow-label">{label}</span></div>
      <div className="flow-val">{val}</div>
      <div className="flow-sub">{sub}</div>
    </div>
  );
}
function Arrow() { return <div className="flow-arrow"><Icon name="arrowRight" /></div>; }
function FlowBar({ flow }) {
  return (
    <div className="sec">
      <div className="sec-lbl">Flujo del día · informado → facturado</div>
      <div className="flow-bar">
        <FlowSeg tick="tk-blue" label="Informado" val={fmtN(flow.informado.v)} sub={fmtK(flow.informado.val)} />
        <Arrow /><FlowSeg tick="tk-amber" label="Retenido" val={fmtN(flow.retenido.v)} sub={fmtN(flow.retenido.pct, 1) + '%'} />
        <Arrow /><FlowSeg tick="tk-red" label="Anulado" val={fmtN(flow.anulado.v)} sub={fmtN(flow.anulado.pct, 1) + '%'} />
        <Arrow /><FlowSeg tick="tk-green" label="Facturado" val={fmtN(flow.facturado.v)} sub={fmtN(flow.facturado.pct, 1) + '%'} />
      </div>
    </div>
  );
}

/* ── MSPA panel (line icons per row) ──────────────────────────────────── */
const MSPA_ICONS = {
  'Backorders (Plazos viejos)': 'clock',
  'Bloqueados por Límite Crédito': 'creditCard',
  'Bloqueados (Status < -1)': 'lock',
  'Pedidos Abiertos (Futuros)': 'fileText',
  'Producción Abierta': 'factory',
  'Remitos / Facturas Abiertas': 'truck',
  'Venta del Día': 'banknote',
};
function MspaPanel({ rows }) {
  return (
    <div className="card">
      <div className="card-head"><div className="sec-lbl"><Icon name="layers" /> MSPA · Estado actual</div><span style={{ fontSize: '10px', color: 'var(--text-3)' }}>refresca 60s</span></div>
      {rows.map((r, i) => (
        <div key={i} className={'mspa-row' + (r.venta ? ' venta' : r.hi ? ' hi' : '')}>
          <span className="mspa-l"><Icon name={MSPA_ICONS[r.k] || 'fileText'} /><span className="mspa-lbl">{r.k}</span></span>
          <span className="mspa-val">{fmtK(r.val)}<div className="s-sub">{fmtN(r.ords)} ord · {fmtN(r.pos)} pos</div></span>
        </div>
      ))}
    </div>
  );
}

/* ── Sellers ──────────────────────────────────────────────────────────── */
function SellerTable({ rows, unit }) {
  return (
    <table className="seller-tbl">
      <thead><tr><th></th><th>Vendedor</th><th style={{ textAlign: 'right' }}>{unit}</th></tr></thead>
      <tbody>
        {rows.map((s, i) => (
          <tr key={i}>
            <td className="s-rank">{i + 1}</td>
            <td><div className="s-name">{s.nombre}</div><div className="s-sub">{fmtN(s.cnt)} {unit === 'Valor' ? 'pedidos' : unit.toLowerCase()}</div></td>
            <td className="s-val">{fmtK(s.val)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
function SellerPanels({ d }) {
  return (
    <div className="sec">
      <div className="sec-lbl">Ranking de vendedores</div>
      <div className="sellers-wrap">
        <div className="card"><div className="card-head"><div className="head-ico"><Icon name="trophy" cls="ico ic-fact" /><span className="sec-lbl" style={{ letterSpacing: '.6px' }}>Top facturación</span></div></div><SellerTable rows={d.sellers_fact} unit="Valor" /></div>
        <div className="card"><div className="card-head"><div className="head-ico"><Icon name="pauseCircle" cls="ico ic-ret" /><span className="sec-lbl" style={{ letterSpacing: '.6px' }}>Más retenidos</span></div></div><SellerTable rows={d.sellers_ret} unit="Retenidos" /></div>
        <div className="card"><div className="card-head"><div className="head-ico"><Icon name="ban" cls="ico ic-an" /><span className="sec-lbl" style={{ letterSpacing: '.6px' }}>Más anulados</span></div></div><SellerTable rows={d.sellers_an} unit="Anulados" /></div>
      </div>
    </div>
  );
}

/* ── Trend chart ──────────────────────────────────────────────────────── */
function TrendChart({ dark }) {
  const ref = useRef(null);
  const chart = useRef(null);
  useEffect(() => {
    const labels = TREND.map(t => { const [y, m] = t.mes.split('-'); return MONTHS[+m - 1] + ' ' + y.slice(2); });
    const bar = TREND.map(t => +(t.pedidos / t.dias_hab).toFixed(1));
    const line = TREND.map(t => +((t.valor / 1e6) / t.dias_hab).toFixed(2));
    const tick = dark ? '#64748b' : '#94a3b8';
    const grid = dark ? '#1e293b' : '#f1f5f9';
    if (chart.current) chart.current.destroy();
    chart.current = new Chart(ref.current.getContext('2d'), {
      data: {
        labels, datasets: [
          { type: 'bar', label: 'Pedidos / día hábil', data: bar, backgroundColor: dark ? 'rgba(148,163,184,.35)' : 'rgba(203,213,225,.8)', borderColor: dark ? '#475569' : '#cbd5e1', borderWidth: 1, yAxisID: 'y1', order: 2 },
          { type: 'line', label: 'M$ / día hábil', data: line, borderColor: '#cc0000', backgroundColor: 'rgba(204,0,0,.06)', borderWidth: 2.5, pointRadius: 2.5, pointBackgroundColor: '#cc0000', tension: .35, yAxisID: 'y2', order: 1, fill: true },
        ]
      },
      options: {
        responsive: true, maintainAspectRatio: false, interaction: { mode: 'index', intersect: false },
        plugins: { legend: { labels: { color: dark ? '#cbd5e1' : '#475569', font: { size: 11 }, boxWidth: 12, padding: 16, usePointStyle: true } } },
        scales: {
          x: { ticks: { color: tick, font: { size: 9 } }, grid: { display: false } },
          y1: { type: 'linear', position: 'left', title: { display: true, text: 'pedidos/día', color: tick, font: { size: 9 } }, ticks: { color: tick, font: { size: 9 } }, grid: { color: grid } },
          y2: { type: 'linear', position: 'right', title: { display: true, text: 'M$/día', color: tick, font: { size: 9 } }, ticks: { color: '#cc0000', font: { size: 9 }, callback: v => v.toFixed(1).replace('.', ',') }, grid: { drawOnChartArea: false } },
        }
      }
    });
    return () => chart.current && chart.current.destroy();
  }, [dark]);
  return (
    <div className="card">
      <div className="card-head"><div className="sec-lbl"><Icon name="trendingUp" /> Tendencia mensual · por día hábil</div></div>
      <div className="chart-wrap"><canvas ref={ref}></canvas></div>
    </div>
  );
}

Object.assign(window, { Header, Hero, KpiStrip, FlowBar, MspaPanel, SellerPanels, TrendChart });

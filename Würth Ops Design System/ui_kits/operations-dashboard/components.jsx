/* Würth Operations Dashboard — UI components (cosmetic recreation) */
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
          {dateDisplay} 📅
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
          MSPA actualiza en <b className="fresh-g">{freshM}s</b><br />
          Reactor actualiza en <b className="fresh-g">{freshR}min</b>
        </div>
        <div className="live"><div className="dot"></div>LIVE</div>
        <button className="mode-btn" onClick={onToggleDark}>{dark ? '☀️ Claro' : '🌙 Oscuro'}</button>
      </div>
    </div>
  );
}

/* ── KPI cards ────────────────────────────────────────────────────────── */
function Delta({ curr, prev }) {
  if (!prev || !curr) return null;
  const p = (curr - prev) / prev * 100;
  const up = p > 0;
  return <div className={'delta ' + (up ? 'up' : 'down')}>{up ? '▲' : '▼'} {Math.abs(p).toFixed(1).replace('.', ',')}%</div>;
}
function Kpi({ cls, label, value, sub, delta }) {
  return (
    <div className={'kpi ' + cls}>
      <div className="kpi-lbl">{label}</div>
      <div className="kpi-val">{value}</div>
      {delta}
      {sub && <div className="kpi-sub">{sub}</div>}
    </div>
  );
}
function KpiGrid({ d }) {
  const retWarn = d.flow.retenido.pct >= 20;
  return (
    <div>
      <div className="sec-lbl">Pedidos Informados · {d.date_display}</div>
      <div className="kpi-grid">
        <Kpi cls="c-blue" label="Pedidos Informados" value={fmtN(d.pedidos)} delta={<Delta curr={d.pedidos} prev={d.comp.pedidos} />} />
        <Kpi cls="c-cyan" label="Pedidos / Vendedor" value={fmtN(d.avg_ped_vend, 1)} sub={`${d.vendedores} vendedores activos`} delta={<Delta curr={d.avg_ped_vend} prev={d.comp.avg_ped_vend} />} />
        <Kpi cls="c-orange" label="Promedio Líneas / Pedido" value={fmtN(d.avg_lineas, 1)} sub={`${fmtN(d.lineas)} líneas`} delta={<Delta curr={d.avg_lineas} prev={d.comp.avg_lineas} />} />
        <Kpi cls="c-green" label="Venta del Día · MSPA" value={fmtK(d.valor)} sub={`vs. ${fmtK(d.comp.valor)} día comparable`} />
      </div>
    </div>
  );
}

/* ── Flow bar ─────────────────────────────────────────────────────────── */
function FlowBar({ flow }) {
  const retDanger = flow.retenido.pct >= 35, retWarn = flow.retenido.pct >= 20;
  return (
    <div>
      <div className="sec-lbl">Flujo del Día — Pedidos Informados → Facturación</div>
      <div className="flow-bar">
        <div className="flow-cell fl-inf">
          <div className="flow-label">Informado</div>
          <div className="flow-val">{fmtN(flow.informado.v)}</div>
          <div className="flow-sub">{fmtK(flow.informado.val)}</div>
        </div>
        <div className={'flow-cell fl-ret' + (retWarn ? ' pulse' : '')}>
          <div className="flow-label">Retenido</div>
          <div className="flow-val">{fmtN(flow.retenido.v)}</div>
          <div className="flow-pct">{fmtN(flow.retenido.pct, 1)}%</div>
        </div>
        <div className="flow-cell fl-an">
          <div className="flow-label">Anulado</div>
          <div className="flow-val">{fmtN(flow.anulado.v)}</div>
          <div className="flow-pct">{fmtN(flow.anulado.pct, 1)}%</div>
        </div>
        <div className="flow-cell fl-fact">
          <div className="flow-label">Facturado</div>
          <div className="flow-val">{fmtN(flow.facturado.v)}</div>
          <div className="flow-pct">{fmtN(flow.facturado.pct, 1)}%</div>
        </div>
      </div>
    </div>
  );
}

/* ── Plan de ventas ───────────────────────────────────────────────────── */
function PlanBar({ plan }) {
  const onTrack = plan.pct >= plan.pace;
  const color = plan.pct >= 100 ? 'var(--green)' : onTrack ? 'var(--wurth-red)' : 'var(--amber)';
  const tagCls = plan.pct >= 100 ? 'tag-ok' : onTrack ? 'tag-ok' : 'tag-warn';
  return (
    <div className="meta-card">
      <div className="sec-lbl" style={{ color: 'var(--wurth-red)' }}>📊 Plan de Ventas — Facturación Acumulada del Mes vs. Plan</div>
      <div className="meta-row">
        <div className="meta-nums"><span className="plan-curr">{fmtK(plan.fact_acum)}</span><span className="plan-total">/ {fmtK(plan.plan_total)}</span></div>
        <div className="plan-bar-bg">
          <div className="plan-bar-fill" style={{ width: Math.min(plan.pct, 100) + '%', background: color }}>{fmtN(plan.pct, 1)}%</div>
          <div className="plan-bar-pace" style={{ left: plan.pace + '%' }}></div>
        </div>
        <span className={'meta-tag ' + tagCls}>{onTrack ? 'En ritmo' : 'Por debajo del ritmo'}</span>
      </div>
    </div>
  );
}

/* ── Ritmo mensual ────────────────────────────────────────────────────── */
function MetaBar({ meta }) {
  const progPct = Math.min(meta.curr / meta.last * 100, 120);
  const paceTarget = meta.pace / 100 * meta.last;
  const onTrack = meta.curr >= paceTarget;
  const tagCls = onTrack ? 'tag-ok' : 'tag-warn';
  const diff = Math.round(meta.curr - paceTarget);
  return (
    <div className="meta-card">
      <div className="sec-lbl">Ritmo Mensual — Pedidos vs. Mes Anterior</div>
      <div className="meta-row">
        <div style={{ fontSize: '11px', color: 'var(--text-2)', whiteSpace: 'nowrap' }}>{meta.curr_month} vs {meta.last_month}</div>
        <div className="meta-nums"><span className="meta-curr">{fmtN(meta.curr)}</span><span className="meta-sep">de</span><span className="meta-last">{fmtN(meta.last)} pedidos</span></div>
        <div className="meta-bar-wrap">
          <div className="meta-bar-bg">
            <div className="meta-bar-fill" style={{ width: Math.min(progPct, 100) + '%', background: progPct > 100 ? 'var(--green)' : onTrack ? 'var(--blue)' : 'var(--amber)' }}></div>
            <div className="meta-bar-pace" style={{ left: meta.pace + '%' }}></div>
          </div>
          <div className="meta-bar-labels"><span>{progPct.toFixed(0)}% del mes anterior</span></div>
        </div>
        <span className={'meta-tag ' + tagCls}>{onTrack ? `+${diff} sobre ritmo` : `${Math.abs(diff)} por debajo del ritmo`}</span>
      </div>
    </div>
  );
}

/* ── MSPA panel ───────────────────────────────────────────────────────── */
function MspaPanel({ rows }) {
  return (
    <div className="card">
      <div className="sec-lbl">MSPA — Estado Actual <small style={{ fontSize: '9px', color: 'var(--text-3)' }}>(refresca cada 60s)</small></div>
      {rows.map((r, i) => (
        <div key={i} className={'mspa-row' + (r.venta ? ' venta' : r.hi ? ' hi' : '')}>
          <span className="mspa-lbl">{r.k}</span>
          <span className="mspa-val">{fmtK(r.val)}<div className="s-sub" style={{ textAlign: 'right' }}>{fmtN(r.ords)} ord · {fmtN(r.pos)} pos</div></span>
        </div>
      ))}
    </div>
  );
}

/* ── Seller leaderboards ──────────────────────────────────────────────── */
function SellerTable({ rows, valCls, unit }) {
  return (
    <table className="seller-tbl">
      <thead><tr><th></th><th>Vendedor</th><th style={{ textAlign: 'right' }}>{unit}</th></tr></thead>
      <tbody>
        {rows.map((s, i) => (
          <tr key={i}>
            <td className={'s-rank ' + (i < 3 ? 'med-' + (i + 1) : '')}>{i + 1}</td>
            <td><div className="s-name">{s.nombre}</div><div className="s-sub">{fmtN(s.cnt)} {unit === 'Valor' ? 'pedidos' : unit.toLowerCase()}</div></td>
            <td className={'s-val ' + valCls}>{fmtK(s.val)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
function SellerPanels({ d }) {
  return (
    <div className="sellers-wrap">
      <div className="card"><div className="sec-lbl lbl-fact">🏆 Top 5 Facturación del Día</div><SellerTable rows={d.sellers_fact} valCls="fact-val" unit="Valor" /></div>
      <div className="card"><div className="sec-lbl lbl-ret">⏸ Top 5 con Más Retenidos</div><SellerTable rows={d.sellers_ret} valCls="ret-val" unit="Retenidos" /></div>
      <div className="card"><div className="sec-lbl lbl-an">✕ Top 5 con Más Anulados</div><SellerTable rows={d.sellers_an} valCls="an-val" unit="Anulados" /></div>
    </div>
  );
}

/* ── Trend chart (Chart.js) ───────────────────────────────────────────── */
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
          { type: 'bar', label: 'Ped/día hábil', data: bar, backgroundColor: 'rgba(37,99,235,.7)', borderColor: '#2563eb', borderWidth: 1, yAxisID: 'y1', order: 2 },
          { type: 'line', label: 'M$/día hábil', data: line, borderColor: '#059669', backgroundColor: 'rgba(5,150,105,.07)', borderWidth: 2.5, pointRadius: 3, pointBackgroundColor: '#059669', tension: .35, yAxisID: 'y2', order: 1, fill: true },
        ]
      },
      options: {
        responsive: true, maintainAspectRatio: false, interaction: { mode: 'index', intersect: false },
        plugins: { legend: { labels: { color: dark ? '#cbd5e1' : '#475569', font: { size: 11 }, boxWidth: 12, padding: 14 } } },
        scales: {
          x: { ticks: { color: tick, font: { size: 9 } }, grid: { color: grid } },
          y1: { type: 'linear', position: 'left', ticks: { color: '#2563eb', font: { size: 9 } }, grid: { color: grid } },
          y2: { type: 'linear', position: 'right', ticks: { color: '#059669', font: { size: 9 }, callback: v => v.toFixed(1) + 'M' }, grid: { drawOnChartArea: false } },
        }
      }
    });
    return () => chart.current && chart.current.destroy();
  }, [dark]);
  return (
    <div className="card">
      <div className="sec-lbl">Tendencia Mensual — Pedidos &amp; Valor por Día Hábil</div>
      <div className="chart-wrap"><canvas ref={ref}></canvas></div>
    </div>
  );
}

Object.assign(window, { Header, KpiGrid, FlowBar, PlanBar, MetaBar, MspaPanel, SellerPanels, TrendChart });

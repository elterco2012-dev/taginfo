/* Würth Operations Dashboard v3 — components */
const { useState, useRef, useEffect } = React;

/* ── Sparkline (SVG puro, sin librerías) ──────────────────────────────── */
function Sparkline({ data, color = 'var(--text-3)', w = 74, h = 30 }) {
  if (!data || data.length < 2) return null;
  const min = Math.min(...data), max = Math.max(...data);
  const range = max - min || 1;
  const pad = 2;
  const step = (w - pad * 2) / (data.length - 1);
  const pts = data.map((v, i) => [pad + i * step, h - pad - ((v - min) / range) * (h - pad * 2)]);
  const d = pts.map((p, i) => (i ? 'L' : 'M') + p[0].toFixed(1) + ' ' + p[1].toFixed(1)).join(' ');
  const area = d + ` L${pts[pts.length - 1][0].toFixed(1)} ${h} L${pts[0][0].toFixed(1)} ${h} Z`;
  const up = data[data.length - 1] >= data[0];
  const c = color === 'auto' ? (up ? 'var(--green)' : 'var(--red)') : color;
  const gid = 'sg' + Math.random().toString(36).slice(2, 7);
  return (
    <svg className="spark" viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none">
      <defs><linearGradient id={gid} x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stopColor={c} stopOpacity="0.18" /><stop offset="100%" stopColor={c} stopOpacity="0" />
      </linearGradient></defs>
      <path d={area} fill={`url(#${gid})`} />
      <path d={d} fill="none" stroke={c} strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx={pts[pts.length - 1][0]} cy={pts[pts.length - 1][1]} r="2" fill={c} />
    </svg>
  );
}

/* ── Header (con estado de conexión + datos al + export + TV) ─────────── */
function Header({ d, dark, tv, onToggleDark, onToggleTV, onExport, onPickDate, onClearDate }) {
  const [open, setOpen] = useState(false);
  const [val, setVal] = useState('2026-05-27');
  const connTxt = { ok: 'OK', slow: 'lento', down: 'sin conexión' };
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
        <div className="conn">
          <span className="conn-row"><span className={'conn-dot ' + d.conn.mspa}></span>MSPA {connTxt[d.conn.mspa]} · datos al <b>{d.datos_al.mspa}</b></span>
          <span className="conn-row"><span className={'conn-dot ' + d.conn.reactor}></span>Reactor {connTxt[d.conn.reactor]} · <b>{d.datos_al.reactor}</b></span>
        </div>
        <div className="date-badge" onClick={() => setOpen(o => !o)}>
          <Icon name="calendar" /> <span className="num">{d.date_display}</span>
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
        <button className="icon-btn" onClick={onExport} title="Exportar / Imprimir"><Icon name="download" /></button>
        <button className={'icon-btn' + (tv ? ' on' : '')} onClick={onToggleTV} title="Modo pantalla (TV)"><Icon name="tv" /></button>
        <button className="icon-btn" onClick={onToggleDark} title={dark ? 'Modo claro' : 'Modo oscuro'}><Icon name={dark ? 'sun' : 'moon'} /></button>
      </div>
    </div>
  );
}

/* ── Banda de ALERTAS (sólo aparece si hay excepciones) ───────────────── */
function buildAlerts(d) {
  const out = [];
  if (d.flow.retenido.pct >= 20)
    out.push({ sev: d.flow.retenido.pct >= 30 ? 'danger' : 'warn', ico: 'pauseCircle',
      msg: <span><b>Retenidos en {fmtN(d.flow.retenido.pct, 1)}%</b> — por encima del objetivo de 20% ({fmtN(d.flow.retenido.v)} pedidos)</span>,
      act: 'Ver retenidos →' });
  if (d.plan.pct < d.plan.pace)
    out.push({ sev: 'warn', ico: 'trendingDown',
      msg: <span>Plan de ventas <b>{fmtN(d.plan.pace - d.plan.pct, 1)} pts por debajo del ritmo</b> esperado ({fmtN(d.plan.pct, 1)}% vs {d.plan.pace}%)</span>,
      act: 'Ver plan →' });
  // Ocultas a pedido: "vendedores sin facturar" y "bloqueados por límite de crédito".
  // Para reactivarlas, descomentar:
  // if (d.sin_facturar > 0)
  //   out.push({ sev: d.sin_facturar >= 5 ? 'danger' : 'warn', ico: 'userX',
  //     msg: <span><b>{fmtN(d.sin_facturar)} vendedores</b> activos aún sin facturar hoy</span>, act: 'Ver detalle →' });
  // const credito = d.mspa.find(m => m.k.includes('Crédito'));
  // if (credito && credito.sev !== 'ok')
  //   out.push({ sev: credito.sev, ico: 'creditCard',
  //     msg: <span><b>{fmtK(credito.val)}</b> bloqueado por límite de crédito ({fmtN(credito.ords)} pedidos)</span>,
  //     act: 'Revisar →' });
  return out;
}
function AlertBanner({ d }) {
  const alerts = buildAlerts(d);
  if (!alerts.length) return null;
  return (
    <div className="alerts">
      {alerts.map((a, i) => (
        <div key={i} className={'alert ' + a.sev}>
          <Icon name={a.ico} />{a.msg}<a className="a-act" href="#">{a.act}</a>
        </div>
      ))}
    </div>
  );
}

/* ── Delta ────────────────────────────────────────────────────────────── */
function Delta({ curr, prev, label }) {
  if (!prev || !curr) return null;
  const p = (curr - prev) / prev * 100;
  const up = p >= 0;
  return (
    <span className={'delta ' + (up ? 'up' : 'down')}>
      <Icon name={up ? 'arrowUp' : 'arrowDown'} cls="ico-sm" />
      {Math.abs(p).toFixed(1).replace('.', ',')}%{label && <span style={{ color: 'var(--text-3)', fontWeight: 400 }}>&nbsp;{label}</span>}
    </span>
  );
}

/* ── HERO ─────────────────────────────────────────────────────────────── */
function Hero({ d }) {
  const plan = d.plan, onTrack = plan.pct >= plan.pace, done = plan.pct >= 100;
  const fillColor = done ? 'var(--green)' : onTrack ? 'var(--wurth-red)' : 'var(--amber)';
  const stateCls = done || onTrack ? 'state-ok' : 'state-warn';
  const stateIco = done || onTrack ? 'checkCircle' : 'trendingDown';
  const stateTxt = done ? 'Plan cumplido' : onTrack ? 'En ritmo' : 'Por debajo del ritmo';
  return (
    <div className="hero">
      <div className="hero-main">
        <div className="hero-eyebrow"><Icon name="target" /> Plan de Ventas · Facturación acumulada del mes</div>
        <div className="hero-figs"><span className="hero-curr">{fmtK(plan.fact_acum)}</span><span className="hero-total">/ {fmtK(plan.plan_total)}</span></div>
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
        <div className="hero-stat"><div className="l">Venta del Día · MSPA</div><div className="v">{fmtK(d.valor)}</div>
          <div className="d"><Delta curr={d.valor} prev={d.comp.valor} label={'vs. ' + d.comp.label} /></div></div>
        <div className="hsep"></div>
        <div className="hero-stat"><div className="l">Pedidos Informados</div><div className="v">{fmtN(d.pedidos)}</div>
          <div className="d"><Delta curr={d.pedidos} prev={d.comp.pedidos} label={'vs. ' + d.comp.label} /></div></div>
      </div>
    </div>
  );
}

/* ── KPI con sparkline + meta ─────────────────────────────────────────── */
function Kpi({ label, value, spark, sparkColor, delta, sub, meta }) {
  return (
    <div className="kpi">
      <div className="kpi-lbl">{label}</div>
      <div className="kpi-top">
        <div className="kpi-val">{value}</div>
        {spark && <Sparkline data={spark} color={sparkColor || 'auto'} />}
      </div>
      <div className="kpi-foot">
        {delta}
        {meta}
        {sub && <span className="kpi-sub">{sub}</span>}
      </div>
    </div>
  );
}
function MetaChip({ curr, target, unit }) {
  if (!target) return null;
  const ok = curr >= target;
  return <span className="meta-chip"><span className={'dot ' + (ok ? 'ok' : 'warn')}></span>meta {unit ? unit(target) : fmtN(target)}</span>;
}
function KpiStrip({ d }) {
  const sp = d.spark;
  return (
    <div className="sec">
      <div className="sec-lbl">Indicadores del día · últimos 14 días hábiles</div>
      <div className="kpi-grid">
        <Kpi label="Pedidos Informados" value={fmtN(d.pedidos)} spark={sp.pedidos}
          delta={<Delta curr={d.pedidos} prev={d.comp.pedidos} />}
          meta={<MetaChip curr={d.pedidos} target={d.meta_pedidos} />} />
        <Kpi label="Venta del Día" value={fmtK(d.valor)} spark={sp.valor}
          delta={<Delta curr={d.valor} prev={d.comp.valor} />}
          meta={<MetaChip curr={d.valor} target={d.meta_valor} unit={fmtK} />} />
        <Kpi label="Pedidos / Vendedor" value={fmtN(d.avg_ped_vend, 1)} spark={sp.ped_vend}
          delta={<Delta curr={d.avg_ped_vend} prev={d.comp.avg_ped_vend} />}
          sub={`${fmtN(d.vendedores)} activos`} />
        <Kpi label="Líneas / Pedido" value={fmtN(d.avg_lineas, 1)} spark={sp.lineas}
          delta={<Delta curr={d.avg_lineas} prev={d.comp.avg_lineas} />}
          sub={`${fmtN(d.lineas)} líneas`} />
      </div>
    </div>
  );
}

/* ── FLOW ─────────────────────────────────────────────────────────────── */
function FlowSeg({ tick, label, val, sub }) {
  return (
    <div className="flow-cell">
      <div className="flow-dot"><span className={'flow-tick ' + tick}></span><span className="flow-label">{label}</span></div>
      <div className="flow-val">{val}</div><div className="flow-sub">{sub}</div>
    </div>
  );
}
function FlowBar({ flow }) {
  return (
    <div className="sec">
      <div className="sec-lbl">Flujo del día · informado → facturado</div>
      <div className="flow-bar">
        <FlowSeg tick="tk-blue" label="Informado" val={fmtN(flow.informado.v)} sub={fmtK(flow.informado.val)} />
        <FlowSeg tick="tk-amber" label="Retenido" val={fmtN(flow.retenido.v)} sub={fmtN(flow.retenido.pct, 1) + '%'} />
        <FlowSeg tick="tk-red" label="Anulado" val={fmtN(flow.anulado.v)} sub={fmtN(flow.anulado.pct, 1) + '%'} />
        <FlowSeg tick="tk-green" label="Facturado" val={fmtN(flow.facturado.v)} sub={fmtN(flow.facturado.pct, 1) + '%'} />
      </div>
    </div>
  );
}

/* ── MSPA con semáforos + "datos al" ──────────────────────────────────── */
const MSPA_SEM = (sev) => 'mspa-sem' + (sev && sev !== 'ok' ? ' ' + sev : '');
function MspaPanel({ rows, stamp }) {
  return (
    <div className="card">
      <div className="card-head"><div className="sec-lbl"><Icon name="layers" /> MSPA · Estado actual</div><span className="stamp">datos al {stamp}</span></div>
      {rows.map((r, i) => (
        <div key={i} className={'mspa-row' + (r.venta ? ' venta' : '')}>
          <span className="mspa-l"><span className={MSPA_SEM(r.venta ? 'ok' : r.sev)}></span><span className="mspa-lbl">{r.k}</span></span>
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
      <tbody>{rows.map((s, i) => (
        <tr key={i}><td className="s-rank">{i + 1}</td>
          <td><div className="s-name">{s.nombre}</div><div className="s-sub">{fmtN(s.cnt)} {unit === 'Valor' ? 'pedidos' : unit.toLowerCase()}</div></td>
          <td className="s-val">{fmtK(s.val)}</td></tr>))}
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
function TrendChart({ dark, stamp }) {
  const ref = useRef(null), chart = useRef(null);
  useEffect(() => {
    const labels = TREND.map(t => { const [y, m] = t.mes.split('-'); return MONTHS[+m - 1] + ' ' + y.slice(2); });
    const bar = TREND.map(t => +(t.pedidos / t.dias_hab).toFixed(1));
    const line = TREND.map(t => +((t.valor / 1e6) / t.dias_hab).toFixed(2));
    const tick = dark ? '#64748b' : '#94a3b8', grid = dark ? '#1e293b' : '#f1f5f9';
    if (chart.current) chart.current.destroy();
    chart.current = new Chart(ref.current.getContext('2d'), {
      data: { labels, datasets: [
        { type: 'bar', label: 'Pedidos / día hábil', data: bar, backgroundColor: dark ? 'rgba(148,163,184,.35)' : 'rgba(203,213,225,.8)', borderColor: dark ? '#475569' : '#cbd5e1', borderWidth: 1, yAxisID: 'y1', order: 2 },
        { type: 'line', label: 'M$ / día hábil', data: line, borderColor: '#cc0000', backgroundColor: 'rgba(204,0,0,.06)', borderWidth: 2.5, pointRadius: 2.5, pointBackgroundColor: '#cc0000', tension: .35, yAxisID: 'y2', order: 1, fill: true } ] },
      options: { responsive: true, maintainAspectRatio: false, interaction: { mode: 'index', intersect: false },
        plugins: { legend: { labels: { color: dark ? '#cbd5e1' : '#475569', font: { size: 11 }, boxWidth: 12, padding: 16, usePointStyle: true } } },
        scales: { x: { ticks: { color: tick, font: { size: 9 } }, grid: { display: false } },
          y1: { type: 'linear', position: 'left', title: { display: true, text: 'pedidos/día', color: tick, font: { size: 9 } }, ticks: { color: tick, font: { size: 9 } }, grid: { color: grid } },
          y2: { type: 'linear', position: 'right', title: { display: true, text: 'M$/día', color: tick, font: { size: 9 } }, ticks: { color: '#cc0000', font: { size: 9 }, callback: v => v.toFixed(1).replace('.', ',') }, grid: { drawOnChartArea: false } } } }
    });
    return () => chart.current && chart.current.destroy();
  }, [dark]);
  return (
    <div className="card">
      <div className="card-head"><div className="sec-lbl"><Icon name="trendingUp" /> Tendencia mensual · por día hábil</div><span className="stamp">datos al {stamp}</span></div>
      <div className="chart-wrap"><canvas ref={ref}></canvas></div>
    </div>
  );
}

Object.assign(window, { Header, AlertBanner, Hero, KpiStrip, FlowBar, MspaPanel, SellerPanels, TrendChart, Sparkline });

/* @ds-bundle: {"format":3,"namespace":"WRthOpsDesignSystem_1c80d1","components":[],"sourceHashes":{"ui_kits/operations-dashboard-v2/app.jsx":"991ad6346b18","ui_kits/operations-dashboard-v2/components.jsx":"f567f65ea1ba","ui_kits/operations-dashboard-v2/data.js":"4893f0d18309","ui_kits/operations-dashboard-v2/icons.jsx":"86ca02c275d8","ui_kits/operations-dashboard-v3/app.jsx":"7d3ce303ec8a","ui_kits/operations-dashboard-v3/components.jsx":"08cfd0a3982a","ui_kits/operations-dashboard-v3/data.js":"92f6e6a81eb7","ui_kits/operations-dashboard-v3/icons.jsx":"2aa55ce6423e","ui_kits/operations-dashboard/app.jsx":"ca2490d8a83f","ui_kits/operations-dashboard/components.jsx":"32af247e8a0c","ui_kits/operations-dashboard/data.js":"4893f0d18309","ui_kits/taginfo-terminal/app.jsx":"c67271a0ef10"},"inlinedExternals":[],"unexposedExports":[]} */

(() => {

const __ds_ns = (window.WRthOpsDesignSystem_1c80d1 = window.WRthOpsDesignSystem_1c80d1 || {});

const __ds_scope = {};

(__ds_ns.__errors = __ds_ns.__errors || []);

// ui_kits/operations-dashboard-v2/app.jsx
try { (() => {
/* App shell v2 */
const {
  useState: useS,
  useEffect: useE
} = React;
function App() {
  const [dark, setDark] = useS(false);
  const [dateKey, setDateKey] = useS('2026-05-28');
  const [freshM, setFreshM] = useS(45);
  const [freshR] = useS(8);
  useE(() => {
    document.body.classList.toggle('dark', dark);
  }, [dark]);
  useE(() => {
    const t = setInterval(() => setFreshM(s => s <= 1 ? 60 : s - 1), 1000);
    return () => clearInterval(t);
  }, []);
  const d = window.DASH_DATA[dateKey] || window.DASH_DATA['2026-05-28'];
  return /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement(Header, {
    dateDisplay: d.date_display,
    dark: dark,
    onToggleDark: () => setDark(v => !v),
    onPickDate: v => setDateKey(window.DASH_DATA[v] ? v : '2026-05-27'),
    onClearDate: () => setDateKey('2026-05-28'),
    freshM: freshM,
    freshR: freshR
  }), /*#__PURE__*/React.createElement("div", {
    className: "main"
  }, /*#__PURE__*/React.createElement(Hero, {
    d: d
  }), /*#__PURE__*/React.createElement(KpiStrip, {
    d: d
  }), /*#__PURE__*/React.createElement(FlowBar, {
    flow: d.flow
  }), /*#__PURE__*/React.createElement("div", {
    className: "bottom"
  }, /*#__PURE__*/React.createElement(TrendChart, {
    dark: dark
  }), /*#__PURE__*/React.createElement(MspaPanel, {
    rows: d.mspa
  })), /*#__PURE__*/React.createElement(SellerPanels, {
    d: d
  })));
}
ReactDOM.createRoot(document.getElementById('root')).render(/*#__PURE__*/React.createElement(App, null));
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/operations-dashboard-v2/app.jsx", error: String((e && e.message) || e) }); }

// ui_kits/operations-dashboard-v2/components.jsx
try { (() => {
/* Würth Operations Dashboard v2 — components (professional refinement) */
const {
  useState,
  useRef,
  useEffect
} = React;

/* ── Header ───────────────────────────────────────────────────────────── */
function Header({
  dateDisplay,
  dark,
  onToggleDark,
  onPickDate,
  onClearDate,
  freshM,
  freshR
}) {
  const [open, setOpen] = useState(false);
  const [val, setVal] = useState('2026-05-27');
  return /*#__PURE__*/React.createElement("div", {
    className: "hdr"
  }, /*#__PURE__*/React.createElement("div", {
    className: "hdr-left"
  }, /*#__PURE__*/React.createElement("img", {
    className: "hdr-logo",
    src: "wurth-logo.png",
    alt: "W\xFCrth"
  }), /*#__PURE__*/React.createElement("div", {
    className: "div-v"
  }), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    className: "hdr-title"
  }, "Operations Dashboard"), /*#__PURE__*/React.createElement("div", {
    className: "hdr-sub"
  }, "Reactor \xB7 MSPA \xB7 Tiempo Real"))), /*#__PURE__*/React.createElement("div", {
    className: "hdr-right"
  }, /*#__PURE__*/React.createElement("div", {
    className: "date-badge",
    onClick: () => setOpen(o => !o)
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "calendar"
  }), " ", /*#__PURE__*/React.createElement("span", {
    className: "num"
  }, dateDisplay), open && /*#__PURE__*/React.createElement("div", {
    className: "date-pop",
    onClick: e => e.stopPropagation()
  }, /*#__PURE__*/React.createElement("h4", null, "Seleccionar fecha"), /*#__PURE__*/React.createElement("input", {
    type: "date",
    value: val,
    onChange: e => setVal(e.target.value)
  }), /*#__PURE__*/React.createElement("div", {
    className: "hint"
  }, "Ingres\xE1 la fecha a consultar."), /*#__PURE__*/React.createElement("button", {
    className: "go",
    onClick: () => {
      onPickDate(val);
      setOpen(false);
    }
  }, "Ver fecha"), /*#__PURE__*/React.createElement("button", {
    className: "clr",
    onClick: () => {
      onClearDate();
      setOpen(false);
    }
  }, "Volver al d\xEDa actual"))), /*#__PURE__*/React.createElement("div", {
    className: "freshness"
  }, "MSPA en ", /*#__PURE__*/React.createElement("b", {
    className: "num"
  }, freshM, "s"), /*#__PURE__*/React.createElement("br", null), "Reactor en ", /*#__PURE__*/React.createElement("b", {
    className: "num"
  }, freshR, "min")), /*#__PURE__*/React.createElement("div", {
    className: "live"
  }, /*#__PURE__*/React.createElement("div", {
    className: "dot"
  }), "LIVE"), /*#__PURE__*/React.createElement("button", {
    className: "mode-btn",
    onClick: onToggleDark,
    title: dark ? 'Modo claro' : 'Modo oscuro'
  }, /*#__PURE__*/React.createElement(Icon, {
    name: dark ? 'sun' : 'moon'
  }))));
}

/* ── Delta (color only on state) ──────────────────────────────────────── */
function Delta({
  curr,
  prev
}) {
  if (!prev || !curr) return null;
  const p = (curr - prev) / prev * 100;
  const up = p >= 0;
  return /*#__PURE__*/React.createElement("div", {
    className: 'delta ' + (up ? 'up' : 'down')
  }, /*#__PURE__*/React.createElement(Icon, {
    name: up ? 'arrowUp' : 'arrowDown',
    cls: "ico-sm"
  }), Math.abs(p).toFixed(1).replace('.', ','), "% ", /*#__PURE__*/React.createElement("span", {
    style: {
      color: 'var(--text-3)',
      fontWeight: 400
    }
  }, "vs. comp."));
}

/* ── HERO: Plan (dominant) + two headline stats ───────────────────────── */
function Hero({
  d
}) {
  const plan = d.plan;
  const onTrack = plan.pct >= plan.pace;
  const done = plan.pct >= 100;
  const fillColor = done ? 'var(--green)' : onTrack ? 'var(--wurth-red)' : 'var(--amber)';
  const stateCls = done || onTrack ? 'state-ok' : 'state-warn';
  const stateIco = done || onTrack ? 'checkCircle' : 'trendingDown';
  const stateTxt = done ? 'Plan cumplido' : onTrack ? 'En ritmo' : 'Por debajo del ritmo';
  return /*#__PURE__*/React.createElement("div", {
    className: "hero"
  }, /*#__PURE__*/React.createElement("div", {
    className: "hero-main"
  }, /*#__PURE__*/React.createElement("div", {
    className: "hero-eyebrow"
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "target"
  }), " Plan de Ventas \xB7 Facturaci\xF3n acumulada del mes"), /*#__PURE__*/React.createElement("div", {
    className: "hero-figs"
  }, /*#__PURE__*/React.createElement("span", {
    className: "hero-curr"
  }, fmtK(plan.fact_acum)), /*#__PURE__*/React.createElement("span", {
    className: "hero-total"
  }, "/ ", fmtK(plan.plan_total))), /*#__PURE__*/React.createElement("div", {
    className: "hero-pct-line"
  }, /*#__PURE__*/React.createElement("span", {
    className: "hero-pct",
    style: {
      color: fillColor
    }
  }, fmtN(plan.pct, 1), "%"), /*#__PURE__*/React.createElement("div", {
    className: "plan-bar-bg"
  }, /*#__PURE__*/React.createElement("div", {
    className: "plan-bar-fill",
    style: {
      width: Math.min(plan.pct, 100) + '%',
      background: fillColor
    }
  }), /*#__PURE__*/React.createElement("div", {
    className: "plan-bar-pace",
    style: {
      left: plan.pace + '%'
    }
  })), /*#__PURE__*/React.createElement("span", {
    className: 'state-tag ' + stateCls
  }, /*#__PURE__*/React.createElement(Icon, {
    name: stateIco,
    cls: "ico-sm"
  }), " ", stateTxt)), /*#__PURE__*/React.createElement("div", {
    className: "hero-foot"
  }, /*#__PURE__*/React.createElement("span", null, "Ritmo esperado a hoy: ", /*#__PURE__*/React.createElement("b", {
    className: "num"
  }, plan.pace, "%")), /*#__PURE__*/React.createElement("span", null, "Restante: ", /*#__PURE__*/React.createElement("b", {
    className: "num"
  }, fmtK(plan.plan_total - plan.fact_acum))))), /*#__PURE__*/React.createElement("div", {
    className: "hero-side"
  }, /*#__PURE__*/React.createElement("div", {
    className: "hero-stat"
  }, /*#__PURE__*/React.createElement("div", {
    className: "l"
  }, "Venta del D\xEDa \xB7 MSPA"), /*#__PURE__*/React.createElement("div", {
    className: "v"
  }, fmtK(d.valor)), /*#__PURE__*/React.createElement("div", {
    className: "d"
  }, /*#__PURE__*/React.createElement(Delta, {
    curr: d.valor,
    prev: d.comp.valor
  }))), /*#__PURE__*/React.createElement("div", {
    className: "hsep"
  }), /*#__PURE__*/React.createElement("div", {
    className: "hero-stat"
  }, /*#__PURE__*/React.createElement("div", {
    className: "l"
  }, "Pedidos Informados"), /*#__PURE__*/React.createElement("div", {
    className: "v"
  }, fmtN(d.pedidos)), /*#__PURE__*/React.createElement("div", {
    className: "d"
  }, /*#__PURE__*/React.createElement(Delta, {
    curr: d.pedidos,
    prev: d.comp.pedidos
  })))));
}

/* ── KPI strip (secondary, neutral) ───────────────────────────────────── */
function Kpi({
  label,
  value,
  sub,
  delta
}) {
  return /*#__PURE__*/React.createElement("div", {
    className: "kpi"
  }, /*#__PURE__*/React.createElement("div", {
    className: "kpi-lbl"
  }, label), /*#__PURE__*/React.createElement("div", {
    className: "kpi-val"
  }, value), delta, sub && /*#__PURE__*/React.createElement("div", {
    className: "kpi-sub"
  }, sub));
}
function KpiStrip({
  d
}) {
  return /*#__PURE__*/React.createElement("div", {
    className: "sec"
  }, /*#__PURE__*/React.createElement("div", {
    className: "sec-lbl"
  }, "Indicadores del d\xEDa"), /*#__PURE__*/React.createElement("div", {
    className: "kpi-grid"
  }, /*#__PURE__*/React.createElement(Kpi, {
    label: "Vendedores activos",
    value: fmtN(d.vendedores),
    sub: `${fmtN(d.lineas)} líneas totales`
  }), /*#__PURE__*/React.createElement(Kpi, {
    label: "Pedidos / Vendedor",
    value: fmtN(d.avg_ped_vend, 1),
    delta: /*#__PURE__*/React.createElement(Delta, {
      curr: d.avg_ped_vend,
      prev: d.comp.avg_ped_vend
    })
  }), /*#__PURE__*/React.createElement(Kpi, {
    label: "Promedio L\xEDneas / Pedido",
    value: fmtN(d.avg_lineas, 1),
    delta: /*#__PURE__*/React.createElement(Delta, {
      curr: d.avg_lineas,
      prev: d.comp.avg_lineas
    })
  }), /*#__PURE__*/React.createElement(Kpi, {
    label: "Ticket promedio",
    value: fmtK(d.valor / d.pedidos),
    sub: "valor / pedido informado"
  })));
}

/* ── Flow bar (neutral numbers, color only on the tick) ───────────────── */
function FlowSeg({
  tick,
  label,
  val,
  sub
}) {
  return /*#__PURE__*/React.createElement("div", {
    className: "flow-cell"
  }, /*#__PURE__*/React.createElement("div", {
    className: "flow-dot"
  }, /*#__PURE__*/React.createElement("span", {
    className: 'flow-tick ' + tick
  }), /*#__PURE__*/React.createElement("span", {
    className: "flow-label"
  }, label)), /*#__PURE__*/React.createElement("div", {
    className: "flow-val"
  }, val), /*#__PURE__*/React.createElement("div", {
    className: "flow-sub"
  }, sub));
}
function Arrow() {
  return /*#__PURE__*/React.createElement("div", {
    className: "flow-arrow"
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "arrowRight"
  }));
}
function FlowBar({
  flow
}) {
  return /*#__PURE__*/React.createElement("div", {
    className: "sec"
  }, /*#__PURE__*/React.createElement("div", {
    className: "sec-lbl"
  }, "Flujo del d\xEDa \xB7 informado \u2192 facturado"), /*#__PURE__*/React.createElement("div", {
    className: "flow-bar"
  }, /*#__PURE__*/React.createElement(FlowSeg, {
    tick: "tk-blue",
    label: "Informado",
    val: fmtN(flow.informado.v),
    sub: fmtK(flow.informado.val)
  }), /*#__PURE__*/React.createElement(Arrow, null), /*#__PURE__*/React.createElement(FlowSeg, {
    tick: "tk-amber",
    label: "Retenido",
    val: fmtN(flow.retenido.v),
    sub: fmtN(flow.retenido.pct, 1) + '%'
  }), /*#__PURE__*/React.createElement(Arrow, null), /*#__PURE__*/React.createElement(FlowSeg, {
    tick: "tk-red",
    label: "Anulado",
    val: fmtN(flow.anulado.v),
    sub: fmtN(flow.anulado.pct, 1) + '%'
  }), /*#__PURE__*/React.createElement(Arrow, null), /*#__PURE__*/React.createElement(FlowSeg, {
    tick: "tk-green",
    label: "Facturado",
    val: fmtN(flow.facturado.v),
    sub: fmtN(flow.facturado.pct, 1) + '%'
  })));
}

/* ── MSPA panel (line icons per row) ──────────────────────────────────── */
const MSPA_ICONS = {
  'Backorders (Plazos viejos)': 'clock',
  'Bloqueados por Límite Crédito': 'creditCard',
  'Bloqueados (Status < -1)': 'lock',
  'Pedidos Abiertos (Futuros)': 'fileText',
  'Producción Abierta': 'factory',
  'Remitos / Facturas Abiertas': 'truck',
  'Venta del Día': 'banknote'
};
function MspaPanel({
  rows
}) {
  return /*#__PURE__*/React.createElement("div", {
    className: "card"
  }, /*#__PURE__*/React.createElement("div", {
    className: "card-head"
  }, /*#__PURE__*/React.createElement("div", {
    className: "sec-lbl"
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "layers"
  }), " MSPA \xB7 Estado actual"), /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: '10px',
      color: 'var(--text-3)'
    }
  }, "refresca 60s")), rows.map((r, i) => /*#__PURE__*/React.createElement("div", {
    key: i,
    className: 'mspa-row' + (r.venta ? ' venta' : r.hi ? ' hi' : '')
  }, /*#__PURE__*/React.createElement("span", {
    className: "mspa-l"
  }, /*#__PURE__*/React.createElement(Icon, {
    name: MSPA_ICONS[r.k] || 'fileText'
  }), /*#__PURE__*/React.createElement("span", {
    className: "mspa-lbl"
  }, r.k)), /*#__PURE__*/React.createElement("span", {
    className: "mspa-val"
  }, fmtK(r.val), /*#__PURE__*/React.createElement("div", {
    className: "s-sub"
  }, fmtN(r.ords), " ord \xB7 ", fmtN(r.pos), " pos")))));
}

/* ── Sellers ──────────────────────────────────────────────────────────── */
function SellerTable({
  rows,
  unit
}) {
  return /*#__PURE__*/React.createElement("table", {
    className: "seller-tbl"
  }, /*#__PURE__*/React.createElement("thead", null, /*#__PURE__*/React.createElement("tr", null, /*#__PURE__*/React.createElement("th", null), /*#__PURE__*/React.createElement("th", null, "Vendedor"), /*#__PURE__*/React.createElement("th", {
    style: {
      textAlign: 'right'
    }
  }, unit))), /*#__PURE__*/React.createElement("tbody", null, rows.map((s, i) => /*#__PURE__*/React.createElement("tr", {
    key: i
  }, /*#__PURE__*/React.createElement("td", {
    className: "s-rank"
  }, i + 1), /*#__PURE__*/React.createElement("td", null, /*#__PURE__*/React.createElement("div", {
    className: "s-name"
  }, s.nombre), /*#__PURE__*/React.createElement("div", {
    className: "s-sub"
  }, fmtN(s.cnt), " ", unit === 'Valor' ? 'pedidos' : unit.toLowerCase())), /*#__PURE__*/React.createElement("td", {
    className: "s-val"
  }, fmtK(s.val))))));
}
function SellerPanels({
  d
}) {
  return /*#__PURE__*/React.createElement("div", {
    className: "sec"
  }, /*#__PURE__*/React.createElement("div", {
    className: "sec-lbl"
  }, "Ranking de vendedores"), /*#__PURE__*/React.createElement("div", {
    className: "sellers-wrap"
  }, /*#__PURE__*/React.createElement("div", {
    className: "card"
  }, /*#__PURE__*/React.createElement("div", {
    className: "card-head"
  }, /*#__PURE__*/React.createElement("div", {
    className: "head-ico"
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "trophy",
    cls: "ico ic-fact"
  }), /*#__PURE__*/React.createElement("span", {
    className: "sec-lbl",
    style: {
      letterSpacing: '.6px'
    }
  }, "Top facturaci\xF3n"))), /*#__PURE__*/React.createElement(SellerTable, {
    rows: d.sellers_fact,
    unit: "Valor"
  })), /*#__PURE__*/React.createElement("div", {
    className: "card"
  }, /*#__PURE__*/React.createElement("div", {
    className: "card-head"
  }, /*#__PURE__*/React.createElement("div", {
    className: "head-ico"
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "pauseCircle",
    cls: "ico ic-ret"
  }), /*#__PURE__*/React.createElement("span", {
    className: "sec-lbl",
    style: {
      letterSpacing: '.6px'
    }
  }, "M\xE1s retenidos"))), /*#__PURE__*/React.createElement(SellerTable, {
    rows: d.sellers_ret,
    unit: "Retenidos"
  })), /*#__PURE__*/React.createElement("div", {
    className: "card"
  }, /*#__PURE__*/React.createElement("div", {
    className: "card-head"
  }, /*#__PURE__*/React.createElement("div", {
    className: "head-ico"
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "ban",
    cls: "ico ic-an"
  }), /*#__PURE__*/React.createElement("span", {
    className: "sec-lbl",
    style: {
      letterSpacing: '.6px'
    }
  }, "M\xE1s anulados"))), /*#__PURE__*/React.createElement(SellerTable, {
    rows: d.sellers_an,
    unit: "Anulados"
  }))));
}

/* ── Trend chart ──────────────────────────────────────────────────────── */
function TrendChart({
  dark
}) {
  const ref = useRef(null);
  const chart = useRef(null);
  useEffect(() => {
    const labels = TREND.map(t => {
      const [y, m] = t.mes.split('-');
      return MONTHS[+m - 1] + ' ' + y.slice(2);
    });
    const bar = TREND.map(t => +(t.pedidos / t.dias_hab).toFixed(1));
    const line = TREND.map(t => +(t.valor / 1e6 / t.dias_hab).toFixed(2));
    const tick = dark ? '#64748b' : '#94a3b8';
    const grid = dark ? '#1e293b' : '#f1f5f9';
    if (chart.current) chart.current.destroy();
    chart.current = new Chart(ref.current.getContext('2d'), {
      data: {
        labels,
        datasets: [{
          type: 'bar',
          label: 'Pedidos / día hábil',
          data: bar,
          backgroundColor: dark ? 'rgba(148,163,184,.35)' : 'rgba(203,213,225,.8)',
          borderColor: dark ? '#475569' : '#cbd5e1',
          borderWidth: 1,
          yAxisID: 'y1',
          order: 2
        }, {
          type: 'line',
          label: 'M$ / día hábil',
          data: line,
          borderColor: '#cc0000',
          backgroundColor: 'rgba(204,0,0,.06)',
          borderWidth: 2.5,
          pointRadius: 2.5,
          pointBackgroundColor: '#cc0000',
          tension: .35,
          yAxisID: 'y2',
          order: 1,
          fill: true
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: 'index',
          intersect: false
        },
        plugins: {
          legend: {
            labels: {
              color: dark ? '#cbd5e1' : '#475569',
              font: {
                size: 11
              },
              boxWidth: 12,
              padding: 16,
              usePointStyle: true
            }
          }
        },
        scales: {
          x: {
            ticks: {
              color: tick,
              font: {
                size: 9
              }
            },
            grid: {
              display: false
            }
          },
          y1: {
            type: 'linear',
            position: 'left',
            title: {
              display: true,
              text: 'pedidos/día',
              color: tick,
              font: {
                size: 9
              }
            },
            ticks: {
              color: tick,
              font: {
                size: 9
              }
            },
            grid: {
              color: grid
            }
          },
          y2: {
            type: 'linear',
            position: 'right',
            title: {
              display: true,
              text: 'M$/día',
              color: tick,
              font: {
                size: 9
              }
            },
            ticks: {
              color: '#cc0000',
              font: {
                size: 9
              },
              callback: v => v.toFixed(1).replace('.', ',')
            },
            grid: {
              drawOnChartArea: false
            }
          }
        }
      }
    });
    return () => chart.current && chart.current.destroy();
  }, [dark]);
  return /*#__PURE__*/React.createElement("div", {
    className: "card"
  }, /*#__PURE__*/React.createElement("div", {
    className: "card-head"
  }, /*#__PURE__*/React.createElement("div", {
    className: "sec-lbl"
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "trendingUp"
  }), " Tendencia mensual \xB7 por d\xEDa h\xE1bil")), /*#__PURE__*/React.createElement("div", {
    className: "chart-wrap"
  }, /*#__PURE__*/React.createElement("canvas", {
    ref: ref
  })));
}
Object.assign(window, {
  Header,
  Hero,
  KpiStrip,
  FlowBar,
  MspaPanel,
  SellerPanels,
  TrendChart
});
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/operations-dashboard-v2/components.jsx", error: String((e && e.message) || e) }); }

// ui_kits/operations-dashboard-v2/data.js
try { (() => {
/* Fake-but-realistic data for the Würth Operations Dashboard kit.
   Mirrors the shape produced by dashboard.py (reactor + mspa).
   Two days are provided so the date picker can switch context. */
(function () {
  // ── number / currency formatting (es-AR) ──
  window.fmtN = (n, d = 0) => Number(n || 0).toLocaleString('es-AR', {
    minimumFractionDigits: d,
    maximumFractionDigits: d
  });
  window.fmtK = n => {
    n = Number(n) || 0;
    if (n >= 1e9) return '$' + (n / 1e9).toFixed(1).replace('.', ',') + 'B';
    if (n >= 1e6) return '$' + (n / 1e6).toFixed(1).replace('.', ',') + 'M';
    if (n >= 1e3) return '$' + Math.round(n / 1e3) + 'K';
    return '$' + window.fmtN(n, 0);
  };
  window.pct = (a, b) => b ? (a / b * 100).toFixed(1).replace('.', ',') + '%' : '—';
  const MONTHS = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'];
  const trend = [{
    mes: '2025-06',
    pedidos: 4120,
    valor: 38.2e6,
    dias_hab: 21
  }, {
    mes: '2025-07',
    pedidos: 4480,
    valor: 41.5e6,
    dias_hab: 23
  }, {
    mes: '2025-08',
    pedidos: 3990,
    valor: 36.8e6,
    dias_hab: 21
  }, {
    mes: '2025-09',
    pedidos: 4610,
    valor: 43.1e6,
    dias_hab: 22
  }, {
    mes: '2025-10',
    pedidos: 4820,
    valor: 45.9e6,
    dias_hab: 23
  }, {
    mes: '2025-11',
    pedidos: 4530,
    valor: 42.7e6,
    dias_hab: 20
  }, {
    mes: '2025-12',
    pedidos: 3870,
    valor: 39.4e6,
    dias_hab: 19
  }, {
    mes: '2026-01',
    pedidos: 4210,
    valor: 40.1e6,
    dias_hab: 22
  }, {
    mes: '2026-02',
    pedidos: 4350,
    valor: 41.0e6,
    dias_hab: 20
  }, {
    mes: '2026-03',
    pedidos: 4900,
    valor: 46.8e6,
    dias_hab: 22
  }, {
    mes: '2026-04',
    pedidos: 4720,
    valor: 44.2e6,
    dias_hab: 21
  }, {
    mes: '2026-05',
    pedidos: 4980,
    valor: 47.6e6,
    dias_hab: 21
  }];
  const sellers = [['García, M.', '204'], ['Rossi, L.', '118'], ['Pérez, A.', '077'], ['Lombardi, S.', '156'], ['Núñez, D.', '231'], ['Ferraro, J.', '092'], ['Sosa, P.', '188'], ['Ibáñez, R.', '143']];
  const mk = arr => arr.map(([i, c, v]) => ({
    nombre: `${sellers[i][0]} (${sellers[i][1]})`,
    cnt: c,
    val: v
  }));
  window.DASH_DATA = {
    '2026-05-28': {
      date_display: '28/05/2026',
      pedidos: 1284,
      vendedores: 86,
      valor: 3402190,
      lineas: 7820,
      avg_lineas: 6.1,
      avg_ped_vend: 14.9,
      comp: {
        pedidos: 1142,
        valor: 3010400,
        avg_lineas: 5.8,
        avg_ped_vend: 13.4
      },
      flow: {
        informado: {
          v: 1284,
          val: 5.1e6
        },
        retenido: {
          v: 312,
          pct: 24.3
        },
        anulado: {
          v: 48,
          pct: 3.7
        },
        facturado: {
          v: 924,
          pct: 71.9
        }
      },
      plan: {
        plan_total: 42.0e6,
        fact_acum: 28.4e6,
        pct: 67.6,
        pace: 72
      },
      meta: {
        curr_month: '2026-05',
        last_month: '2026-04',
        curr: 4980,
        last: 4720,
        pace: 78,
        dias_elapsed: 16,
        curr_wd: 21
      },
      mspa: [{
        k: 'Backorders (Plazos viejos)',
        val: 1245800,
        ords: 142,
        pos: 318
      }, {
        k: 'Bloqueados por Límite Crédito',
        val: 842300,
        ords: 64,
        pos: 121,
        hi: true
      }, {
        k: 'Bloqueados (Status < -1)',
        val: 318900,
        ords: 22,
        pos: 47
      }, {
        k: 'Pedidos Abiertos (Futuros)',
        val: 8420110,
        ords: 388,
        pos: 902
      }, {
        k: 'Producción Abierta',
        val: 3110450,
        ords: 95,
        pos: 240
      }, {
        k: 'Remitos / Facturas Abiertas',
        val: 2204600,
        ords: 156,
        pos: 410
      }, {
        k: 'Venta del Día',
        val: 3402190,
        ords: 57,
        pos: 188,
        venta: true
      }],
      sellers_fact: mk([[0, 3, 1.1e6], [1, 5, 842000], [2, 2, 610000], [3, 4, 488000], [4, 3, 402000]]),
      sellers_ret: mk([[5, 9, 412000], [3, 7, 388000], [6, 6, 270000], [1, 5, 198000], [7, 4, 142000]]),
      sellers_an: mk([[7, 4, 88000], [2, 3, 64000], [5, 2, 41000], [0, 2, 38000], [4, 1, 22000]])
    },
    '2026-05-27': {
      date_display: '27/05/2026',
      pedidos: 1198,
      vendedores: 84,
      valor: 3115600,
      lineas: 6980,
      avg_lineas: 5.8,
      avg_ped_vend: 14.3,
      comp: {
        pedidos: 1210,
        valor: 3240800,
        avg_lineas: 6.0,
        avg_ped_vend: 14.6
      },
      flow: {
        informado: {
          v: 1198,
          val: 4.7e6
        },
        retenido: {
          v: 268,
          pct: 22.4
        },
        anulado: {
          v: 39,
          pct: 3.3
        },
        facturado: {
          v: 891,
          pct: 74.4
        }
      },
      plan: {
        plan_total: 42.0e6,
        fact_acum: 25.0e6,
        pct: 59.5,
        pace: 67
      },
      meta: {
        curr_month: '2026-05',
        last_month: '2026-04',
        curr: 4982,
        last: 4720,
        pace: 74,
        dias_elapsed: 15,
        curr_wd: 21
      },
      mspa: [{
        k: 'Backorders (Plazos viejos)',
        val: 1198400,
        ords: 138,
        pos: 302
      }, {
        k: 'Bloqueados por Límite Crédito',
        val: 911200,
        ords: 71,
        pos: 134,
        hi: true
      }, {
        k: 'Bloqueados (Status < -1)',
        val: 290100,
        ords: 19,
        pos: 41
      }, {
        k: 'Pedidos Abiertos (Futuros)',
        val: 8190050,
        ords: 372,
        pos: 870
      }, {
        k: 'Producción Abierta',
        val: 2980300,
        ords: 91,
        pos: 228
      }, {
        k: 'Remitos / Facturas Abiertas',
        val: 2110800,
        ords: 149,
        pos: 392
      }, {
        k: 'Venta del Día',
        val: 3115600,
        ords: 52,
        pos: 171,
        venta: true
      }],
      sellers_fact: mk([[1, 4, 980000], [0, 3, 720000], [3, 5, 540000], [2, 2, 430000], [6, 3, 360000]]),
      sellers_ret: mk([[3, 8, 360000], [5, 6, 310000], [1, 5, 240000], [7, 4, 160000], [6, 3, 120000]]),
      sellers_an: mk([[2, 3, 72000], [7, 3, 58000], [0, 2, 36000], [5, 1, 24000], [4, 1, 18000]])
    }
  };
  window.TREND = trend;
  window.MONTHS = MONTHS;
})();
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/operations-dashboard-v2/data.js", error: String((e && e.message) || e) }); }

// ui_kits/operations-dashboard-v2/icons.jsx
try { (() => {
/* Minimal Lucide icon set (paths copied from lucide.dev, ISC license).
   Rendered as inline SVG React components so they survive re-renders. */
function Icon({
  name,
  cls = 'ico'
}) {
  const p = ICONS[name] || '';
  return /*#__PURE__*/React.createElement("svg", {
    className: cls,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: "2",
    strokeLinecap: "round",
    strokeLinejoin: "round",
    dangerouslySetInnerHTML: {
      __html: p
    }
  });
}
const ICONS = {
  calendar: '<rect width="18" height="18" x="3" y="4" rx="2"/><path d="M3 10h18M8 2v4M16 2v4"/>',
  moon: '<path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/>',
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/>',
  target: '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>',
  trendingUp: '<path d="M16 7h6v6"/><path d="m22 7-8.5 8.5-5-5L2 17"/>',
  trendingDown: '<path d="M16 17h6v-6"/><path d="m22 17-8.5-8.5-5 5L2 7"/>',
  arrowUp: '<path d="m5 12 7-7 7 7M12 19V5"/>',
  arrowDown: '<path d="M12 5v14M5 12l7 7 7-7"/>',
  arrowRight: '<path d="M5 12h14M12 5l7 7-7 7"/>',
  fileText: '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4M10 9H8M16 13H8M16 17H8"/>',
  pauseCircle: '<circle cx="12" cy="12" r="10"/><path d="M10 15V9M14 15V9"/>',
  xCircle: '<circle cx="12" cy="12" r="10"/><path d="m15 9-6 6M9 9l6 6"/>',
  checkCircle: '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><path d="m9 11 3 3L22 4"/>',
  trophy: '<path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6M18 9h1.5a2.5 2.5 0 0 0 0-5H18M4 22h16M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22M18 2H6v7a6 6 0 0 0 12 0V2Z"/>',
  ban: '<circle cx="12" cy="12" r="10"/><path d="m4.9 4.9 14.2 14.2"/>',
  layers: '<path d="m12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83l8.58 3.91a2 2 0 0 0 1.66 0l8.58-3.9a1 1 0 0 0 0-1.83Z"/><path d="m22 17.65-9.17 4.16a2 2 0 0 1-1.66 0L2 17.65M22 12.65l-9.17 4.16a2 2 0 0 1-1.66 0L2 12.65"/>',
  factory: '<path d="M2 20a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V8l-7 5V8l-7 5V4a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2Z"/><path d="M17 18h1M12 18h1M7 18h1"/>',
  truck: '<path d="M14 18V6a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2v11a1 1 0 0 0 1 1h2"/><path d="M15 18H9M19 18h2a1 1 0 0 0 1-1v-3.65a1 1 0 0 0-.22-.62l-3.48-4.35A1 1 0 0 0 17.52 8H14"/><circle cx="17" cy="18" r="2"/><circle cx="7" cy="18" r="2"/>',
  lock: '<rect width="18" height="11" x="3" y="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>',
  creditCard: '<rect width="20" height="14" x="2" y="5" rx="2"/><path d="M2 10h20"/>',
  clock: '<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>',
  receipt: '<path d="M4 2v20l2-1 2 1 2-1 2 1 2-1 2 1 2-1 2 1V2l-2 1-2-1-2 1-2-1-2 1-2-1-2 1Z"/><path d="M8 7h8M8 11h8M8 15h5"/>',
  banknote: '<rect width="20" height="12" x="2" y="6" rx="2"/><circle cx="12" cy="12" r="2"/><path d="M6 12h.01M18 12h.01"/>'
};
window.Icon = Icon;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/operations-dashboard-v2/icons.jsx", error: String((e && e.message) || e) }); }

// ui_kits/operations-dashboard-v3/app.jsx
try { (() => {
/* App shell v3 — dark mode, TV mode, export, date switch, skeleton on load */
const {
  useState: useS,
  useEffect: useE
} = React;
function App() {
  const [dark, setDark] = useS(false);
  const [tv, setTv] = useS(false);
  const [dateKey, setDateKey] = useS('2026-05-28');
  const [loading, setLoading] = useS(true);
  useE(() => {
    document.body.classList.toggle('dark', dark);
  }, [dark]);
  useE(() => {
    document.body.classList.toggle('tv', tv);
  }, [tv]);
  // simulate initial data fetch → skeleton, then content
  useE(() => {
    const t = setTimeout(() => setLoading(false), 900);
    return () => clearTimeout(t);
  }, []);
  // brief skeleton when switching date too
  const switchDate = k => {
    setLoading(true);
    setDateKey(k);
    setTimeout(() => setLoading(false), 600);
  };
  const d = window.DASH_DATA[dateKey] || window.DASH_DATA['2026-05-28'];
  return /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement(Header, {
    d: d,
    dark: dark,
    tv: tv,
    onToggleDark: () => setDark(v => !v),
    onToggleTV: () => setTv(v => !v),
    onExport: () => window.print(),
    onPickDate: v => switchDate(window.DASH_DATA[v] ? v : '2026-05-27'),
    onClearDate: () => switchDate('2026-05-28')
  }), /*#__PURE__*/React.createElement("div", {
    className: 'main' + (loading ? ' is-loading' : '')
  }, /*#__PURE__*/React.createElement(AlertBanner, {
    d: d
  }), /*#__PURE__*/React.createElement(Hero, {
    d: d
  }), /*#__PURE__*/React.createElement(KpiStrip, {
    d: d
  }), /*#__PURE__*/React.createElement(FlowBar, {
    flow: d.flow
  }), /*#__PURE__*/React.createElement("div", {
    className: "bottom"
  }, /*#__PURE__*/React.createElement(TrendChart, {
    dark: dark,
    stamp: d.datos_al.reactor
  }), /*#__PURE__*/React.createElement(MspaPanel, {
    rows: d.mspa,
    stamp: d.datos_al.mspa
  })), /*#__PURE__*/React.createElement(SellerPanels, {
    d: d
  })));
}
ReactDOM.createRoot(document.getElementById('root')).render(/*#__PURE__*/React.createElement(App, null));
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/operations-dashboard-v3/app.jsx", error: String((e && e.message) || e) }); }

// ui_kits/operations-dashboard-v3/components.jsx
try { (() => {
/* Würth Operations Dashboard v3 — components */
const {
  useState,
  useRef,
  useEffect
} = React;

/* ── Sparkline (SVG puro, sin librerías) ──────────────────────────────── */
function Sparkline({
  data,
  color = 'var(--text-3)',
  w = 74,
  h = 30
}) {
  if (!data || data.length < 2) return null;
  const min = Math.min(...data),
    max = Math.max(...data);
  const range = max - min || 1;
  const pad = 2;
  const step = (w - pad * 2) / (data.length - 1);
  const pts = data.map((v, i) => [pad + i * step, h - pad - (v - min) / range * (h - pad * 2)]);
  const d = pts.map((p, i) => (i ? 'L' : 'M') + p[0].toFixed(1) + ' ' + p[1].toFixed(1)).join(' ');
  const area = d + ` L${pts[pts.length - 1][0].toFixed(1)} ${h} L${pts[0][0].toFixed(1)} ${h} Z`;
  const up = data[data.length - 1] >= data[0];
  const c = color === 'auto' ? up ? 'var(--green)' : 'var(--red)' : color;
  const gid = 'sg' + Math.random().toString(36).slice(2, 7);
  return /*#__PURE__*/React.createElement("svg", {
    className: "spark",
    viewBox: `0 0 ${w} ${h}`,
    preserveAspectRatio: "none"
  }, /*#__PURE__*/React.createElement("defs", null, /*#__PURE__*/React.createElement("linearGradient", {
    id: gid,
    x1: "0",
    y1: "0",
    x2: "0",
    y2: "1"
  }, /*#__PURE__*/React.createElement("stop", {
    offset: "0%",
    stopColor: c,
    stopOpacity: "0.18"
  }), /*#__PURE__*/React.createElement("stop", {
    offset: "100%",
    stopColor: c,
    stopOpacity: "0"
  }))), /*#__PURE__*/React.createElement("path", {
    d: area,
    fill: `url(#${gid})`
  }), /*#__PURE__*/React.createElement("path", {
    d: d,
    fill: "none",
    stroke: c,
    strokeWidth: "1.6",
    strokeLinecap: "round",
    strokeLinejoin: "round"
  }), /*#__PURE__*/React.createElement("circle", {
    cx: pts[pts.length - 1][0],
    cy: pts[pts.length - 1][1],
    r: "2",
    fill: c
  }));
}

/* ── Header (con estado de conexión + datos al + export + TV) ─────────── */
function Header({
  d,
  dark,
  tv,
  onToggleDark,
  onToggleTV,
  onExport,
  onPickDate,
  onClearDate
}) {
  const [open, setOpen] = useState(false);
  const [val, setVal] = useState('2026-05-27');
  const connTxt = {
    ok: 'OK',
    slow: 'lento',
    down: 'sin conexión'
  };
  return /*#__PURE__*/React.createElement("div", {
    className: "hdr"
  }, /*#__PURE__*/React.createElement("div", {
    className: "hdr-left"
  }, /*#__PURE__*/React.createElement("img", {
    className: "hdr-logo",
    src: "wurth-logo.png",
    alt: "W\xFCrth"
  }), /*#__PURE__*/React.createElement("div", {
    className: "div-v"
  }), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    className: "hdr-title"
  }, "Operations Dashboard"), /*#__PURE__*/React.createElement("div", {
    className: "hdr-sub"
  }, "Reactor \xB7 MSPA \xB7 Tiempo Real"))), /*#__PURE__*/React.createElement("div", {
    className: "hdr-right"
  }, /*#__PURE__*/React.createElement("div", {
    className: "conn"
  }, /*#__PURE__*/React.createElement("span", {
    className: "conn-row"
  }, /*#__PURE__*/React.createElement("span", {
    className: 'conn-dot ' + d.conn.mspa
  }), "MSPA ", connTxt[d.conn.mspa], " \xB7 datos al ", /*#__PURE__*/React.createElement("b", null, d.datos_al.mspa)), /*#__PURE__*/React.createElement("span", {
    className: "conn-row"
  }, /*#__PURE__*/React.createElement("span", {
    className: 'conn-dot ' + d.conn.reactor
  }), "Reactor ", connTxt[d.conn.reactor], " \xB7 ", /*#__PURE__*/React.createElement("b", null, d.datos_al.reactor))), /*#__PURE__*/React.createElement("div", {
    className: "date-badge",
    onClick: () => setOpen(o => !o)
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "calendar"
  }), " ", /*#__PURE__*/React.createElement("span", {
    className: "num"
  }, d.date_display), open && /*#__PURE__*/React.createElement("div", {
    className: "date-pop",
    onClick: e => e.stopPropagation()
  }, /*#__PURE__*/React.createElement("h4", null, "Seleccionar fecha"), /*#__PURE__*/React.createElement("input", {
    type: "date",
    value: val,
    onChange: e => setVal(e.target.value)
  }), /*#__PURE__*/React.createElement("div", {
    className: "hint"
  }, "Ingres\xE1 la fecha a consultar."), /*#__PURE__*/React.createElement("button", {
    className: "go",
    onClick: () => {
      onPickDate(val);
      setOpen(false);
    }
  }, "Ver fecha"), /*#__PURE__*/React.createElement("button", {
    className: "clr",
    onClick: () => {
      onClearDate();
      setOpen(false);
    }
  }, "Volver al d\xEDa actual"))), /*#__PURE__*/React.createElement("button", {
    className: "icon-btn",
    onClick: onExport,
    title: "Exportar / Imprimir"
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "download"
  })), /*#__PURE__*/React.createElement("button", {
    className: 'icon-btn' + (tv ? ' on' : ''),
    onClick: onToggleTV,
    title: "Modo pantalla (TV)"
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "tv"
  })), /*#__PURE__*/React.createElement("button", {
    className: "icon-btn",
    onClick: onToggleDark,
    title: dark ? 'Modo claro' : 'Modo oscuro'
  }, /*#__PURE__*/React.createElement(Icon, {
    name: dark ? 'sun' : 'moon'
  }))));
}

/* ── Banda de ALERTAS (sólo aparece si hay excepciones) ───────────────── */
function buildAlerts(d) {
  const out = [];
  if (d.flow.retenido.pct >= 20) out.push({
    sev: d.flow.retenido.pct >= 30 ? 'danger' : 'warn',
    ico: 'pauseCircle',
    msg: /*#__PURE__*/React.createElement("span", null, /*#__PURE__*/React.createElement("b", null, "Retenidos en ", fmtN(d.flow.retenido.pct, 1), "%"), " \u2014 por encima del objetivo de 20% (", fmtN(d.flow.retenido.v), " pedidos)"),
    act: 'Ver retenidos →'
  });
  if (d.plan.pct < d.plan.pace) out.push({
    sev: 'warn',
    ico: 'trendingDown',
    msg: /*#__PURE__*/React.createElement("span", null, "Plan de ventas ", /*#__PURE__*/React.createElement("b", null, fmtN(d.plan.pace - d.plan.pct, 1), " pts por debajo del ritmo"), " esperado (", fmtN(d.plan.pct, 1), "% vs ", d.plan.pace, "%)"),
    act: 'Ver plan →'
  });
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
function AlertBanner({
  d
}) {
  const alerts = buildAlerts(d);
  if (!alerts.length) return null;
  return /*#__PURE__*/React.createElement("div", {
    className: "alerts"
  }, alerts.map((a, i) => /*#__PURE__*/React.createElement("div", {
    key: i,
    className: 'alert ' + a.sev
  }, /*#__PURE__*/React.createElement(Icon, {
    name: a.ico
  }), a.msg, /*#__PURE__*/React.createElement("a", {
    className: "a-act",
    href: "#"
  }, a.act))));
}

/* ── Delta ────────────────────────────────────────────────────────────── */
function Delta({
  curr,
  prev,
  label
}) {
  if (!prev || !curr) return null;
  const p = (curr - prev) / prev * 100;
  const up = p >= 0;
  return /*#__PURE__*/React.createElement("span", {
    className: 'delta ' + (up ? 'up' : 'down')
  }, /*#__PURE__*/React.createElement(Icon, {
    name: up ? 'arrowUp' : 'arrowDown',
    cls: "ico-sm"
  }), Math.abs(p).toFixed(1).replace('.', ','), "%", label && /*#__PURE__*/React.createElement("span", {
    style: {
      color: 'var(--text-3)',
      fontWeight: 400
    }
  }, "\xA0", label));
}

/* ── HERO ─────────────────────────────────────────────────────────────── */
function Hero({
  d
}) {
  const plan = d.plan,
    onTrack = plan.pct >= plan.pace,
    done = plan.pct >= 100;
  const fillColor = done ? 'var(--green)' : onTrack ? 'var(--wurth-red)' : 'var(--amber)';
  const stateCls = done || onTrack ? 'state-ok' : 'state-warn';
  const stateIco = done || onTrack ? 'checkCircle' : 'trendingDown';
  const stateTxt = done ? 'Plan cumplido' : onTrack ? 'En ritmo' : 'Por debajo del ritmo';
  return /*#__PURE__*/React.createElement("div", {
    className: "hero"
  }, /*#__PURE__*/React.createElement("div", {
    className: "hero-main"
  }, /*#__PURE__*/React.createElement("div", {
    className: "hero-eyebrow"
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "target"
  }), " Plan de Ventas \xB7 Facturaci\xF3n acumulada del mes"), /*#__PURE__*/React.createElement("div", {
    className: "hero-figs"
  }, /*#__PURE__*/React.createElement("span", {
    className: "hero-curr"
  }, fmtK(plan.fact_acum)), /*#__PURE__*/React.createElement("span", {
    className: "hero-total"
  }, "/ ", fmtK(plan.plan_total))), /*#__PURE__*/React.createElement("div", {
    className: "hero-pct-line"
  }, /*#__PURE__*/React.createElement("span", {
    className: "hero-pct",
    style: {
      color: fillColor
    }
  }, fmtN(plan.pct, 1), "%"), /*#__PURE__*/React.createElement("div", {
    className: "plan-bar-bg"
  }, /*#__PURE__*/React.createElement("div", {
    className: "plan-bar-fill",
    style: {
      width: Math.min(plan.pct, 100) + '%',
      background: fillColor
    }
  }), /*#__PURE__*/React.createElement("div", {
    className: "plan-bar-pace",
    style: {
      left: plan.pace + '%'
    }
  })), /*#__PURE__*/React.createElement("span", {
    className: 'state-tag ' + stateCls
  }, /*#__PURE__*/React.createElement(Icon, {
    name: stateIco,
    cls: "ico-sm"
  }), " ", stateTxt)), /*#__PURE__*/React.createElement("div", {
    className: "hero-foot"
  }, /*#__PURE__*/React.createElement("span", null, "Ritmo esperado a hoy: ", /*#__PURE__*/React.createElement("b", {
    className: "num"
  }, plan.pace, "%")), /*#__PURE__*/React.createElement("span", null, "Restante: ", /*#__PURE__*/React.createElement("b", {
    className: "num"
  }, fmtK(plan.plan_total - plan.fact_acum))))), /*#__PURE__*/React.createElement("div", {
    className: "hero-side"
  }, /*#__PURE__*/React.createElement("div", {
    className: "hero-stat"
  }, /*#__PURE__*/React.createElement("div", {
    className: "l"
  }, "Venta del D\xEDa \xB7 MSPA"), /*#__PURE__*/React.createElement("div", {
    className: "v"
  }, fmtK(d.valor)), /*#__PURE__*/React.createElement("div", {
    className: "d"
  }, /*#__PURE__*/React.createElement(Delta, {
    curr: d.valor,
    prev: d.comp.valor,
    label: 'vs. ' + d.comp.label
  }))), /*#__PURE__*/React.createElement("div", {
    className: "hsep"
  }), /*#__PURE__*/React.createElement("div", {
    className: "hero-stat"
  }, /*#__PURE__*/React.createElement("div", {
    className: "l"
  }, "Pedidos Informados"), /*#__PURE__*/React.createElement("div", {
    className: "v"
  }, fmtN(d.pedidos)), /*#__PURE__*/React.createElement("div", {
    className: "d"
  }, /*#__PURE__*/React.createElement(Delta, {
    curr: d.pedidos,
    prev: d.comp.pedidos,
    label: 'vs. ' + d.comp.label
  })))));
}

/* ── KPI con sparkline + meta ─────────────────────────────────────────── */
function Kpi({
  label,
  value,
  spark,
  sparkColor,
  delta,
  sub,
  meta
}) {
  return /*#__PURE__*/React.createElement("div", {
    className: "kpi"
  }, /*#__PURE__*/React.createElement("div", {
    className: "kpi-lbl"
  }, label), /*#__PURE__*/React.createElement("div", {
    className: "kpi-top"
  }, /*#__PURE__*/React.createElement("div", {
    className: "kpi-val"
  }, value), spark && /*#__PURE__*/React.createElement(Sparkline, {
    data: spark,
    color: sparkColor || 'auto'
  })), /*#__PURE__*/React.createElement("div", {
    className: "kpi-foot"
  }, delta, meta, sub && /*#__PURE__*/React.createElement("span", {
    className: "kpi-sub"
  }, sub)));
}
function MetaChip({
  curr,
  target,
  unit
}) {
  if (!target) return null;
  const ok = curr >= target;
  return /*#__PURE__*/React.createElement("span", {
    className: "meta-chip"
  }, /*#__PURE__*/React.createElement("span", {
    className: 'dot ' + (ok ? 'ok' : 'warn')
  }), "meta ", unit ? unit(target) : fmtN(target));
}
function KpiStrip({
  d
}) {
  const sp = d.spark;
  return /*#__PURE__*/React.createElement("div", {
    className: "sec"
  }, /*#__PURE__*/React.createElement("div", {
    className: "sec-lbl"
  }, "Indicadores del d\xEDa \xB7 \xFAltimos 14 d\xEDas h\xE1biles"), /*#__PURE__*/React.createElement("div", {
    className: "kpi-grid"
  }, /*#__PURE__*/React.createElement(Kpi, {
    label: "Pedidos Informados",
    value: fmtN(d.pedidos),
    spark: sp.pedidos,
    delta: /*#__PURE__*/React.createElement(Delta, {
      curr: d.pedidos,
      prev: d.comp.pedidos
    }),
    meta: /*#__PURE__*/React.createElement(MetaChip, {
      curr: d.pedidos,
      target: d.meta_pedidos
    })
  }), /*#__PURE__*/React.createElement(Kpi, {
    label: "Venta del D\xEDa",
    value: fmtK(d.valor),
    spark: sp.valor,
    delta: /*#__PURE__*/React.createElement(Delta, {
      curr: d.valor,
      prev: d.comp.valor
    }),
    meta: /*#__PURE__*/React.createElement(MetaChip, {
      curr: d.valor,
      target: d.meta_valor,
      unit: fmtK
    })
  }), /*#__PURE__*/React.createElement(Kpi, {
    label: "Pedidos / Vendedor",
    value: fmtN(d.avg_ped_vend, 1),
    spark: sp.ped_vend,
    delta: /*#__PURE__*/React.createElement(Delta, {
      curr: d.avg_ped_vend,
      prev: d.comp.avg_ped_vend
    }),
    sub: `${fmtN(d.vendedores)} activos`
  }), /*#__PURE__*/React.createElement(Kpi, {
    label: "L\xEDneas / Pedido",
    value: fmtN(d.avg_lineas, 1),
    spark: sp.lineas,
    delta: /*#__PURE__*/React.createElement(Delta, {
      curr: d.avg_lineas,
      prev: d.comp.avg_lineas
    }),
    sub: `${fmtN(d.lineas)} líneas`
  })));
}

/* ── FLOW ─────────────────────────────────────────────────────────────── */
function FlowSeg({
  tick,
  label,
  val,
  sub
}) {
  return /*#__PURE__*/React.createElement("div", {
    className: "flow-cell"
  }, /*#__PURE__*/React.createElement("div", {
    className: "flow-dot"
  }, /*#__PURE__*/React.createElement("span", {
    className: 'flow-tick ' + tick
  }), /*#__PURE__*/React.createElement("span", {
    className: "flow-label"
  }, label)), /*#__PURE__*/React.createElement("div", {
    className: "flow-val"
  }, val), /*#__PURE__*/React.createElement("div", {
    className: "flow-sub"
  }, sub));
}
function FlowBar({
  flow
}) {
  return /*#__PURE__*/React.createElement("div", {
    className: "sec"
  }, /*#__PURE__*/React.createElement("div", {
    className: "sec-lbl"
  }, "Flujo del d\xEDa \xB7 informado \u2192 facturado"), /*#__PURE__*/React.createElement("div", {
    className: "flow-bar"
  }, /*#__PURE__*/React.createElement(FlowSeg, {
    tick: "tk-blue",
    label: "Informado",
    val: fmtN(flow.informado.v),
    sub: fmtK(flow.informado.val)
  }), /*#__PURE__*/React.createElement(FlowSeg, {
    tick: "tk-amber",
    label: "Retenido",
    val: fmtN(flow.retenido.v),
    sub: fmtN(flow.retenido.pct, 1) + '%'
  }), /*#__PURE__*/React.createElement(FlowSeg, {
    tick: "tk-red",
    label: "Anulado",
    val: fmtN(flow.anulado.v),
    sub: fmtN(flow.anulado.pct, 1) + '%'
  }), /*#__PURE__*/React.createElement(FlowSeg, {
    tick: "tk-green",
    label: "Facturado",
    val: fmtN(flow.facturado.v),
    sub: fmtN(flow.facturado.pct, 1) + '%'
  })));
}

/* ── MSPA con semáforos + "datos al" ──────────────────────────────────── */
const MSPA_SEM = sev => 'mspa-sem' + (sev && sev !== 'ok' ? ' ' + sev : '');
function MspaPanel({
  rows,
  stamp
}) {
  return /*#__PURE__*/React.createElement("div", {
    className: "card"
  }, /*#__PURE__*/React.createElement("div", {
    className: "card-head"
  }, /*#__PURE__*/React.createElement("div", {
    className: "sec-lbl"
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "layers"
  }), " MSPA \xB7 Estado actual"), /*#__PURE__*/React.createElement("span", {
    className: "stamp"
  }, "datos al ", stamp)), rows.map((r, i) => /*#__PURE__*/React.createElement("div", {
    key: i,
    className: 'mspa-row' + (r.venta ? ' venta' : '')
  }, /*#__PURE__*/React.createElement("span", {
    className: "mspa-l"
  }, /*#__PURE__*/React.createElement("span", {
    className: MSPA_SEM(r.venta ? 'ok' : r.sev)
  }), /*#__PURE__*/React.createElement("span", {
    className: "mspa-lbl"
  }, r.k)), /*#__PURE__*/React.createElement("span", {
    className: "mspa-val"
  }, fmtK(r.val), /*#__PURE__*/React.createElement("div", {
    className: "s-sub"
  }, fmtN(r.ords), " ord \xB7 ", fmtN(r.pos), " pos")))));
}

/* ── Sellers ──────────────────────────────────────────────────────────── */
function SellerTable({
  rows,
  unit
}) {
  return /*#__PURE__*/React.createElement("table", {
    className: "seller-tbl"
  }, /*#__PURE__*/React.createElement("thead", null, /*#__PURE__*/React.createElement("tr", null, /*#__PURE__*/React.createElement("th", null), /*#__PURE__*/React.createElement("th", null, "Vendedor"), /*#__PURE__*/React.createElement("th", {
    style: {
      textAlign: 'right'
    }
  }, unit))), /*#__PURE__*/React.createElement("tbody", null, rows.map((s, i) => /*#__PURE__*/React.createElement("tr", {
    key: i
  }, /*#__PURE__*/React.createElement("td", {
    className: "s-rank"
  }, i + 1), /*#__PURE__*/React.createElement("td", null, /*#__PURE__*/React.createElement("div", {
    className: "s-name"
  }, s.nombre), /*#__PURE__*/React.createElement("div", {
    className: "s-sub"
  }, fmtN(s.cnt), " ", unit === 'Valor' ? 'pedidos' : unit.toLowerCase())), /*#__PURE__*/React.createElement("td", {
    className: "s-val"
  }, fmtK(s.val))))));
}
function SellerPanels({
  d
}) {
  return /*#__PURE__*/React.createElement("div", {
    className: "sec"
  }, /*#__PURE__*/React.createElement("div", {
    className: "sec-lbl"
  }, "Ranking de vendedores"), /*#__PURE__*/React.createElement("div", {
    className: "sellers-wrap"
  }, /*#__PURE__*/React.createElement("div", {
    className: "card"
  }, /*#__PURE__*/React.createElement("div", {
    className: "card-head"
  }, /*#__PURE__*/React.createElement("div", {
    className: "head-ico"
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "trophy",
    cls: "ico ic-fact"
  }), /*#__PURE__*/React.createElement("span", {
    className: "sec-lbl",
    style: {
      letterSpacing: '.6px'
    }
  }, "Top facturaci\xF3n"))), /*#__PURE__*/React.createElement(SellerTable, {
    rows: d.sellers_fact,
    unit: "Valor"
  })), /*#__PURE__*/React.createElement("div", {
    className: "card"
  }, /*#__PURE__*/React.createElement("div", {
    className: "card-head"
  }, /*#__PURE__*/React.createElement("div", {
    className: "head-ico"
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "pauseCircle",
    cls: "ico ic-ret"
  }), /*#__PURE__*/React.createElement("span", {
    className: "sec-lbl",
    style: {
      letterSpacing: '.6px'
    }
  }, "M\xE1s retenidos"))), /*#__PURE__*/React.createElement(SellerTable, {
    rows: d.sellers_ret,
    unit: "Retenidos"
  })), /*#__PURE__*/React.createElement("div", {
    className: "card"
  }, /*#__PURE__*/React.createElement("div", {
    className: "card-head"
  }, /*#__PURE__*/React.createElement("div", {
    className: "head-ico"
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "ban",
    cls: "ico ic-an"
  }), /*#__PURE__*/React.createElement("span", {
    className: "sec-lbl",
    style: {
      letterSpacing: '.6px'
    }
  }, "M\xE1s anulados"))), /*#__PURE__*/React.createElement(SellerTable, {
    rows: d.sellers_an,
    unit: "Anulados"
  }))));
}

/* ── Trend chart ──────────────────────────────────────────────────────── */
function TrendChart({
  dark,
  stamp
}) {
  const ref = useRef(null),
    chart = useRef(null);
  useEffect(() => {
    const labels = TREND.map(t => {
      const [y, m] = t.mes.split('-');
      return MONTHS[+m - 1] + ' ' + y.slice(2);
    });
    const bar = TREND.map(t => +(t.pedidos / t.dias_hab).toFixed(1));
    const line = TREND.map(t => +(t.valor / 1e6 / t.dias_hab).toFixed(2));
    const tick = dark ? '#64748b' : '#94a3b8',
      grid = dark ? '#1e293b' : '#f1f5f9';
    if (chart.current) chart.current.destroy();
    chart.current = new Chart(ref.current.getContext('2d'), {
      data: {
        labels,
        datasets: [{
          type: 'bar',
          label: 'Pedidos / día hábil',
          data: bar,
          backgroundColor: dark ? 'rgba(148,163,184,.35)' : 'rgba(203,213,225,.8)',
          borderColor: dark ? '#475569' : '#cbd5e1',
          borderWidth: 1,
          yAxisID: 'y1',
          order: 2
        }, {
          type: 'line',
          label: 'M$ / día hábil',
          data: line,
          borderColor: '#cc0000',
          backgroundColor: 'rgba(204,0,0,.06)',
          borderWidth: 2.5,
          pointRadius: 2.5,
          pointBackgroundColor: '#cc0000',
          tension: .35,
          yAxisID: 'y2',
          order: 1,
          fill: true
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: 'index',
          intersect: false
        },
        plugins: {
          legend: {
            labels: {
              color: dark ? '#cbd5e1' : '#475569',
              font: {
                size: 11
              },
              boxWidth: 12,
              padding: 16,
              usePointStyle: true
            }
          }
        },
        scales: {
          x: {
            ticks: {
              color: tick,
              font: {
                size: 9
              }
            },
            grid: {
              display: false
            }
          },
          y1: {
            type: 'linear',
            position: 'left',
            title: {
              display: true,
              text: 'pedidos/día',
              color: tick,
              font: {
                size: 9
              }
            },
            ticks: {
              color: tick,
              font: {
                size: 9
              }
            },
            grid: {
              color: grid
            }
          },
          y2: {
            type: 'linear',
            position: 'right',
            title: {
              display: true,
              text: 'M$/día',
              color: tick,
              font: {
                size: 9
              }
            },
            ticks: {
              color: '#cc0000',
              font: {
                size: 9
              },
              callback: v => v.toFixed(1).replace('.', ',')
            },
            grid: {
              drawOnChartArea: false
            }
          }
        }
      }
    });
    return () => chart.current && chart.current.destroy();
  }, [dark]);
  return /*#__PURE__*/React.createElement("div", {
    className: "card"
  }, /*#__PURE__*/React.createElement("div", {
    className: "card-head"
  }, /*#__PURE__*/React.createElement("div", {
    className: "sec-lbl"
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "trendingUp"
  }), " Tendencia mensual \xB7 por d\xEDa h\xE1bil"), /*#__PURE__*/React.createElement("span", {
    className: "stamp"
  }, "datos al ", stamp)), /*#__PURE__*/React.createElement("div", {
    className: "chart-wrap"
  }, /*#__PURE__*/React.createElement("canvas", {
    ref: ref
  })));
}
Object.assign(window, {
  Header,
  AlertBanner,
  Hero,
  KpiStrip,
  FlowBar,
  MspaPanel,
  SellerPanels,
  TrendChart,
  Sparkline
});
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/operations-dashboard-v3/components.jsx", error: String((e && e.message) || e) }); }

// ui_kits/operations-dashboard-v3/data.js
try { (() => {
/* Data for Dashboard v3 — extends v2 with sparkline series, targets,
   alert thresholds and connection state. Still fake/static. */
(function () {
  window.fmtN = (n, d = 0) => Number(n || 0).toLocaleString('es-AR', {
    minimumFractionDigits: d,
    maximumFractionDigits: d
  });
  window.fmtK = n => {
    n = Number(n) || 0;
    const neg = n < 0;
    n = Math.abs(n);
    let s;
    if (n >= 1e9) s = '$' + (n / 1e9).toFixed(1).replace('.', ',') + 'B';else if (n >= 1e6) s = '$' + (n / 1e6).toFixed(1).replace('.', ',') + 'M';else if (n >= 1e3) s = '$' + Math.round(n / 1e3) + 'K';else s = '$' + window.fmtN(n, 0);
    return (neg ? '−' : '') + s;
  };
  window.pct = (a, b) => b ? (a / b * 100).toFixed(1).replace('.', ',') + '%' : '—';
  const MONTHS = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'];
  const trend = [{
    mes: '2025-06',
    pedidos: 4120,
    valor: 38.2e6,
    dias_hab: 21
  }, {
    mes: '2025-07',
    pedidos: 4480,
    valor: 41.5e6,
    dias_hab: 23
  }, {
    mes: '2025-08',
    pedidos: 3990,
    valor: 36.8e6,
    dias_hab: 21
  }, {
    mes: '2025-09',
    pedidos: 4610,
    valor: 43.1e6,
    dias_hab: 22
  }, {
    mes: '2025-10',
    pedidos: 4820,
    valor: 45.9e6,
    dias_hab: 23
  }, {
    mes: '2025-11',
    pedidos: 4530,
    valor: 42.7e6,
    dias_hab: 20
  }, {
    mes: '2025-12',
    pedidos: 3870,
    valor: 39.4e6,
    dias_hab: 19
  }, {
    mes: '2026-01',
    pedidos: 4210,
    valor: 40.1e6,
    dias_hab: 22
  }, {
    mes: '2026-02',
    pedidos: 4350,
    valor: 41.0e6,
    dias_hab: 20
  }, {
    mes: '2026-03',
    pedidos: 4900,
    valor: 46.8e6,
    dias_hab: 22
  }, {
    mes: '2026-04',
    pedidos: 4720,
    valor: 44.2e6,
    dias_hab: 21
  }, {
    mes: '2026-05',
    pedidos: 4980,
    valor: 47.6e6,
    dias_hab: 21
  }];
  const sellers = [['García, M.', '204'], ['Rossi, L.', '118'], ['Pérez, A.', '077'], ['Lombardi, S.', '156'], ['Núñez, D.', '231'], ['Ferraro, J.', '092'], ['Sosa, P.', '188'], ['Ibáñez, R.', '143']];
  const mk = arr => arr.map(([i, c, v]) => ({
    nombre: `${sellers[i][0]} (${sellers[i][1]})`,
    cnt: c,
    val: v
  }));
  window.DASH_DATA = {
    '2026-05-28': {
      date_display: '28/05/2026',
      datos_al: {
        mspa: '14:32:07',
        reactor: '14:25:00'
      },
      conn: {
        mspa: 'ok',
        reactor: 'ok'
      },
      // ok | slow | down
      pedidos: 1284,
      vendedores: 86,
      valor: 3402190,
      lineas: 7820,
      avg_lineas: 6.1,
      avg_ped_vend: 14.9,
      comp: {
        pedidos: 1142,
        valor: 3010400,
        avg_lineas: 5.8,
        avg_ped_vend: 13.4,
        label: 'mismo día hábil mes anterior'
      },
      // metas (targets) por KPI
      meta_pedidos: 1350,
      meta_valor: 3600000,
      // sparklines: últimos 14 días hábiles
      spark: {
        pedidos: [1190, 1210, 1255, 1180, 1230, 1290, 1240, 1198, 1260, 1275, 1220, 1284, 1250, 1284],
        valor: [2.9, 3.0, 3.2, 2.8, 3.1, 3.3, 3.15, 2.95, 3.25, 3.3, 3.05, 3.4, 3.2, 3.4],
        ped_vend: [13.4, 13.8, 14.1, 13.6, 14.0, 14.6, 14.2, 13.9, 14.4, 14.7, 14.2, 14.9, 14.5, 14.9],
        lineas: [5.8, 5.9, 6.0, 5.7, 6.1, 6.2, 6.0, 5.9, 6.1, 6.3, 6.0, 6.1, 6.2, 6.1]
      },
      flow: {
        informado: {
          v: 1284,
          val: 5.1e6
        },
        retenido: {
          v: 312,
          pct: 24.3
        },
        anulado: {
          v: 48,
          pct: 3.7
        },
        facturado: {
          v: 924,
          pct: 71.9
        }
      },
      plan: {
        plan_total: 42.0e6,
        fact_acum: 28.4e6,
        pct: 67.6,
        pace: 72
      },
      mspa: [{
        k: 'Backorders (Plazos viejos)',
        val: 1245800,
        ords: 142,
        pos: 318,
        sev: 'ok'
      }, {
        k: 'Bloqueados por Límite Crédito',
        val: 842300,
        ords: 64,
        pos: 121,
        sev: 'warn'
      }, {
        k: 'Bloqueados (Status < -1)',
        val: 318900,
        ords: 22,
        pos: 47,
        sev: 'ok'
      }, {
        k: 'Pedidos Abiertos (Futuros)',
        val: 8420110,
        ords: 388,
        pos: 902,
        sev: 'ok'
      }, {
        k: 'Producción Abierta',
        val: 3110450,
        ords: 95,
        pos: 240,
        sev: 'ok'
      }, {
        k: 'Remitos / Facturas Abiertas',
        val: 2204600,
        ords: 156,
        pos: 410,
        sev: 'ok'
      }, {
        k: 'Venta del Día',
        val: 3402190,
        ords: 57,
        pos: 188,
        venta: true
      }],
      sellers_fact: mk([[0, 3, 1.1e6], [1, 5, 842000], [2, 2, 610000], [3, 4, 488000], [4, 3, 402000]]),
      sellers_ret: mk([[5, 9, 412000], [3, 7, 388000], [6, 6, 270000], [1, 5, 198000], [7, 4, 142000]]),
      sellers_an: mk([[7, 4, 88000], [2, 3, 64000], [5, 2, 41000], [0, 2, 38000], [4, 1, 22000]]),
      sin_facturar: 3 // vendedores activos sin facturar aún
    },
    '2026-05-27': {
      date_display: '27/05/2026',
      datos_al: {
        mspa: '17:58:40',
        reactor: '17:50:00'
      },
      conn: {
        mspa: 'ok',
        reactor: 'slow'
      },
      pedidos: 1198,
      vendedores: 84,
      valor: 3115600,
      lineas: 6980,
      avg_lineas: 5.8,
      avg_ped_vend: 14.3,
      comp: {
        pedidos: 1210,
        valor: 3240800,
        avg_lineas: 6.0,
        avg_ped_vend: 14.6,
        label: 'mismo día hábil mes anterior'
      },
      meta_pedidos: 1350,
      meta_valor: 3600000,
      spark: {
        pedidos: [1240, 1180, 1220, 1260, 1190, 1230, 1280, 1200, 1250, 1270, 1210, 1240, 1198, 1198],
        valor: [3.2, 2.9, 3.1, 3.3, 2.95, 3.1, 3.35, 3.0, 3.2, 3.3, 3.05, 3.2, 3.12, 3.12],
        ped_vend: [14.0, 13.5, 13.9, 14.3, 13.7, 14.0, 14.5, 13.8, 14.2, 14.5, 14.0, 14.3, 14.3, 14.3],
        lineas: [6.0, 5.7, 5.9, 6.1, 5.8, 6.0, 6.2, 5.9, 6.1, 6.2, 5.9, 6.0, 5.8, 5.8]
      },
      flow: {
        informado: {
          v: 1198,
          val: 4.7e6
        },
        retenido: {
          v: 268,
          pct: 22.4
        },
        anulado: {
          v: 39,
          pct: 3.3
        },
        facturado: {
          v: 891,
          pct: 74.4
        }
      },
      plan: {
        plan_total: 42.0e6,
        fact_acum: 25.0e6,
        pct: 59.5,
        pace: 67
      },
      mspa: [{
        k: 'Backorders (Plazos viejos)',
        val: 1198400,
        ords: 138,
        pos: 302,
        sev: 'ok'
      }, {
        k: 'Bloqueados por Límite Crédito',
        val: 911200,
        ords: 71,
        pos: 134,
        sev: 'danger'
      }, {
        k: 'Bloqueados (Status < -1)',
        val: 290100,
        ords: 19,
        pos: 41,
        sev: 'ok'
      }, {
        k: 'Pedidos Abiertos (Futuros)',
        val: 8190050,
        ords: 372,
        pos: 870,
        sev: 'ok'
      }, {
        k: 'Producción Abierta',
        val: 2980300,
        ords: 91,
        pos: 228,
        sev: 'ok'
      }, {
        k: 'Remitos / Facturas Abiertas',
        val: 2110800,
        ords: 149,
        pos: 392,
        sev: 'ok'
      }, {
        k: 'Venta del Día',
        val: 3115600,
        ords: 52,
        pos: 171,
        venta: true
      }],
      sellers_fact: mk([[1, 4, 980000], [0, 3, 720000], [3, 5, 540000], [2, 2, 430000], [6, 3, 360000]]),
      sellers_ret: mk([[3, 8, 360000], [5, 6, 310000], [1, 5, 240000], [7, 4, 160000], [6, 3, 120000]]),
      sellers_an: mk([[2, 3, 72000], [7, 3, 58000], [0, 2, 36000], [5, 1, 24000], [4, 1, 18000]]),
      sin_facturar: 5
    }
  };
  window.TREND = trend;
  window.MONTHS = MONTHS;
})();
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/operations-dashboard-v3/data.js", error: String((e && e.message) || e) }); }

// ui_kits/operations-dashboard-v3/icons.jsx
try { (() => {
/* Minimal Lucide icon set (paths copied from lucide.dev, ISC license).
   Rendered as inline SVG React components so they survive re-renders. */
function Icon({
  name,
  cls = 'ico'
}) {
  const p = ICONS[name] || '';
  return /*#__PURE__*/React.createElement("svg", {
    className: cls,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: "2",
    strokeLinecap: "round",
    strokeLinejoin: "round",
    dangerouslySetInnerHTML: {
      __html: p
    }
  });
}
const ICONS = {
  calendar: '<rect width="18" height="18" x="3" y="4" rx="2"/><path d="M3 10h18M8 2v4M16 2v4"/>',
  moon: '<path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/>',
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/>',
  target: '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>',
  trendingUp: '<path d="M16 7h6v6"/><path d="m22 7-8.5 8.5-5-5L2 17"/>',
  trendingDown: '<path d="M16 17h6v-6"/><path d="m22 17-8.5-8.5-5 5L2 7"/>',
  arrowUp: '<path d="m5 12 7-7 7 7M12 19V5"/>',
  arrowDown: '<path d="M12 5v14M5 12l7 7 7-7"/>',
  arrowRight: '<path d="M5 12h14M12 5l7 7-7 7"/>',
  fileText: '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4M10 9H8M16 13H8M16 17H8"/>',
  pauseCircle: '<circle cx="12" cy="12" r="10"/><path d="M10 15V9M14 15V9"/>',
  xCircle: '<circle cx="12" cy="12" r="10"/><path d="m15 9-6 6M9 9l6 6"/>',
  checkCircle: '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><path d="m9 11 3 3L22 4"/>',
  trophy: '<path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6M18 9h1.5a2.5 2.5 0 0 0 0-5H18M4 22h16M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22M18 2H6v7a6 6 0 0 0 12 0V2Z"/>',
  ban: '<circle cx="12" cy="12" r="10"/><path d="m4.9 4.9 14.2 14.2"/>',
  layers: '<path d="m12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83l8.58 3.91a2 2 0 0 0 1.66 0l8.58-3.9a1 1 0 0 0 0-1.83Z"/><path d="m22 17.65-9.17 4.16a2 2 0 0 1-1.66 0L2 17.65M22 12.65l-9.17 4.16a2 2 0 0 1-1.66 0L2 12.65"/>',
  factory: '<path d="M2 20a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V8l-7 5V8l-7 5V4a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2Z"/><path d="M17 18h1M12 18h1M7 18h1"/>',
  truck: '<path d="M14 18V6a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2v11a1 1 0 0 0 1 1h2"/><path d="M15 18H9M19 18h2a1 1 0 0 0 1-1v-3.65a1 1 0 0 0-.22-.62l-3.48-4.35A1 1 0 0 0 17.52 8H14"/><circle cx="17" cy="18" r="2"/><circle cx="7" cy="18" r="2"/>',
  lock: '<rect width="18" height="11" x="3" y="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>',
  creditCard: '<rect width="20" height="14" x="2" y="5" rx="2"/><path d="M2 10h20"/>',
  clock: '<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>',
  receipt: '<path d="M4 2v20l2-1 2 1 2-1 2 1 2-1 2 1 2-1 2 1V2l-2 1-2-1-2 1-2-1-2 1-2-1-2 1Z"/><path d="M8 7h8M8 11h8M8 15h5"/>',
  banknote: '<rect width="20" height="12" x="2" y="6" rx="2"/><circle cx="12" cy="12" r="2"/><path d="M6 12h.01M18 12h.01"/>',
  download: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="M7 10l5 5 5-5M12 15V3"/>',
  tv: '<rect width="20" height="15" x="2" y="3" rx="2"/><path d="M7 21h10M12 18v3"/>',
  userX: '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="m17 8 5 5M22 8l-5 5"/>',
  activity: '<path d="M22 12h-4l-3 9L9 3l-3 9H2"/>'
};
window.Icon = Icon;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/operations-dashboard-v3/icons.jsx", error: String((e && e.message) || e) }); }

// ui_kits/operations-dashboard/app.jsx
try { (() => {
/* App shell — wires components, dark mode, date switching, live countdown */
const {
  useState: useS,
  useEffect: useE
} = React;
function App() {
  const [dark, setDark] = useS(false);
  const [dateKey, setDateKey] = useS('2026-05-28');
  const [freshM, setFreshM] = useS(45);
  const [freshR, setFreshR] = useS(8);
  useE(() => {
    document.body.classList.toggle('dark', dark);
  }, [dark]);
  useE(() => {
    const t = setInterval(() => setFreshM(s => s <= 1 ? 60 : s - 1), 1000);
    return () => clearInterval(t);
  }, []);
  const d = window.DASH_DATA[dateKey] || window.DASH_DATA['2026-05-28'];
  return /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement(Header, {
    dateDisplay: d.date_display,
    dark: dark,
    onToggleDark: () => setDark(v => !v),
    onPickDate: v => setDateKey(window.DASH_DATA[v] ? v : '2026-05-27'),
    onClearDate: () => setDateKey('2026-05-28'),
    freshM: freshM,
    freshR: freshR
  }), /*#__PURE__*/React.createElement("div", {
    className: "main"
  }, /*#__PURE__*/React.createElement(KpiGrid, {
    d: d
  }), /*#__PURE__*/React.createElement(FlowBar, {
    flow: d.flow
  }), /*#__PURE__*/React.createElement(PlanBar, {
    plan: d.plan
  }), /*#__PURE__*/React.createElement(MetaBar, {
    meta: d.meta
  }), /*#__PURE__*/React.createElement("div", {
    className: "bottom"
  }, /*#__PURE__*/React.createElement(TrendChart, {
    dark: dark
  }), /*#__PURE__*/React.createElement(MspaPanel, {
    rows: d.mspa
  })), /*#__PURE__*/React.createElement(SellerPanels, {
    d: d
  })));
}
ReactDOM.createRoot(document.getElementById('root')).render(/*#__PURE__*/React.createElement(App, null));
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/operations-dashboard/app.jsx", error: String((e && e.message) || e) }); }

// ui_kits/operations-dashboard/components.jsx
try { (() => {
/* Würth Operations Dashboard — UI components (cosmetic recreation) */
const {
  useState,
  useRef,
  useEffect
} = React;

/* ── Header ───────────────────────────────────────────────────────────── */
function Header({
  dateDisplay,
  dark,
  onToggleDark,
  onPickDate,
  onClearDate,
  freshM,
  freshR
}) {
  const [open, setOpen] = useState(false);
  const [val, setVal] = useState('2026-05-27');
  return /*#__PURE__*/React.createElement("div", {
    className: "hdr"
  }, /*#__PURE__*/React.createElement("div", {
    className: "hdr-left"
  }, /*#__PURE__*/React.createElement("img", {
    className: "hdr-logo",
    src: "wurth-logo.png",
    alt: "W\xFCrth"
  }), /*#__PURE__*/React.createElement("div", {
    className: "div-v"
  }), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    className: "hdr-title"
  }, "Operations Dashboard"), /*#__PURE__*/React.createElement("div", {
    className: "hdr-sub"
  }, "Reactor \xB7 MSPA \xB7 Tiempo Real"))), /*#__PURE__*/React.createElement("div", {
    className: "hdr-right"
  }, /*#__PURE__*/React.createElement("div", {
    className: "date-badge",
    onClick: () => setOpen(o => !o)
  }, dateDisplay, " \uD83D\uDCC5", open && /*#__PURE__*/React.createElement("div", {
    className: "date-pop",
    onClick: e => e.stopPropagation()
  }, /*#__PURE__*/React.createElement("h4", null, "Seleccionar fecha"), /*#__PURE__*/React.createElement("input", {
    type: "date",
    value: val,
    onChange: e => setVal(e.target.value)
  }), /*#__PURE__*/React.createElement("div", {
    className: "hint"
  }, "Ingres\xE1 la fecha a consultar."), /*#__PURE__*/React.createElement("button", {
    className: "go",
    onClick: () => {
      onPickDate(val);
      setOpen(false);
    }
  }, "Ver fecha"), /*#__PURE__*/React.createElement("button", {
    className: "clr",
    onClick: () => {
      onClearDate();
      setOpen(false);
    }
  }, "Volver al d\xEDa actual"))), /*#__PURE__*/React.createElement("div", {
    className: "freshness"
  }, "MSPA actualiza en ", /*#__PURE__*/React.createElement("b", {
    className: "fresh-g"
  }, freshM, "s"), /*#__PURE__*/React.createElement("br", null), "Reactor actualiza en ", /*#__PURE__*/React.createElement("b", {
    className: "fresh-g"
  }, freshR, "min")), /*#__PURE__*/React.createElement("div", {
    className: "live"
  }, /*#__PURE__*/React.createElement("div", {
    className: "dot"
  }), "LIVE"), /*#__PURE__*/React.createElement("button", {
    className: "mode-btn",
    onClick: onToggleDark
  }, dark ? '☀️ Claro' : '🌙 Oscuro')));
}

/* ── KPI cards ────────────────────────────────────────────────────────── */
function Delta({
  curr,
  prev
}) {
  if (!prev || !curr) return null;
  const p = (curr - prev) / prev * 100;
  const up = p > 0;
  return /*#__PURE__*/React.createElement("div", {
    className: 'delta ' + (up ? 'up' : 'down')
  }, up ? '▲' : '▼', " ", Math.abs(p).toFixed(1).replace('.', ','), "%");
}
function Kpi({
  cls,
  label,
  value,
  sub,
  delta
}) {
  return /*#__PURE__*/React.createElement("div", {
    className: 'kpi ' + cls
  }, /*#__PURE__*/React.createElement("div", {
    className: "kpi-lbl"
  }, label), /*#__PURE__*/React.createElement("div", {
    className: "kpi-val"
  }, value), delta, sub && /*#__PURE__*/React.createElement("div", {
    className: "kpi-sub"
  }, sub));
}
function KpiGrid({
  d
}) {
  const retWarn = d.flow.retenido.pct >= 20;
  return /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    className: "sec-lbl"
  }, "Pedidos Informados \xB7 ", d.date_display), /*#__PURE__*/React.createElement("div", {
    className: "kpi-grid"
  }, /*#__PURE__*/React.createElement(Kpi, {
    cls: "c-blue",
    label: "Pedidos Informados",
    value: fmtN(d.pedidos),
    delta: /*#__PURE__*/React.createElement(Delta, {
      curr: d.pedidos,
      prev: d.comp.pedidos
    })
  }), /*#__PURE__*/React.createElement(Kpi, {
    cls: "c-cyan",
    label: "Pedidos / Vendedor",
    value: fmtN(d.avg_ped_vend, 1),
    sub: `${d.vendedores} vendedores activos`,
    delta: /*#__PURE__*/React.createElement(Delta, {
      curr: d.avg_ped_vend,
      prev: d.comp.avg_ped_vend
    })
  }), /*#__PURE__*/React.createElement(Kpi, {
    cls: "c-orange",
    label: "Promedio L\xEDneas / Pedido",
    value: fmtN(d.avg_lineas, 1),
    sub: `${fmtN(d.lineas)} líneas`,
    delta: /*#__PURE__*/React.createElement(Delta, {
      curr: d.avg_lineas,
      prev: d.comp.avg_lineas
    })
  }), /*#__PURE__*/React.createElement(Kpi, {
    cls: "c-green",
    label: "Venta del D\xEDa \xB7 MSPA",
    value: fmtK(d.valor),
    sub: `vs. ${fmtK(d.comp.valor)} día comparable`
  })));
}

/* ── Flow bar ─────────────────────────────────────────────────────────── */
function FlowBar({
  flow
}) {
  const retDanger = flow.retenido.pct >= 35,
    retWarn = flow.retenido.pct >= 20;
  return /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    className: "sec-lbl"
  }, "Flujo del D\xEDa \u2014 Pedidos Informados \u2192 Facturaci\xF3n"), /*#__PURE__*/React.createElement("div", {
    className: "flow-bar"
  }, /*#__PURE__*/React.createElement("div", {
    className: "flow-cell fl-inf"
  }, /*#__PURE__*/React.createElement("div", {
    className: "flow-label"
  }, "Informado"), /*#__PURE__*/React.createElement("div", {
    className: "flow-val"
  }, fmtN(flow.informado.v)), /*#__PURE__*/React.createElement("div", {
    className: "flow-sub"
  }, fmtK(flow.informado.val))), /*#__PURE__*/React.createElement("div", {
    className: 'flow-cell fl-ret' + (retWarn ? ' pulse' : '')
  }, /*#__PURE__*/React.createElement("div", {
    className: "flow-label"
  }, "Retenido"), /*#__PURE__*/React.createElement("div", {
    className: "flow-val"
  }, fmtN(flow.retenido.v)), /*#__PURE__*/React.createElement("div", {
    className: "flow-pct"
  }, fmtN(flow.retenido.pct, 1), "%")), /*#__PURE__*/React.createElement("div", {
    className: "flow-cell fl-an"
  }, /*#__PURE__*/React.createElement("div", {
    className: "flow-label"
  }, "Anulado"), /*#__PURE__*/React.createElement("div", {
    className: "flow-val"
  }, fmtN(flow.anulado.v)), /*#__PURE__*/React.createElement("div", {
    className: "flow-pct"
  }, fmtN(flow.anulado.pct, 1), "%")), /*#__PURE__*/React.createElement("div", {
    className: "flow-cell fl-fact"
  }, /*#__PURE__*/React.createElement("div", {
    className: "flow-label"
  }, "Facturado"), /*#__PURE__*/React.createElement("div", {
    className: "flow-val"
  }, fmtN(flow.facturado.v)), /*#__PURE__*/React.createElement("div", {
    className: "flow-pct"
  }, fmtN(flow.facturado.pct, 1), "%"))));
}

/* ── Plan de ventas ───────────────────────────────────────────────────── */
function PlanBar({
  plan
}) {
  const onTrack = plan.pct >= plan.pace;
  const color = plan.pct >= 100 ? 'var(--green)' : onTrack ? 'var(--wurth-red)' : 'var(--amber)';
  const tagCls = plan.pct >= 100 ? 'tag-ok' : onTrack ? 'tag-ok' : 'tag-warn';
  return /*#__PURE__*/React.createElement("div", {
    className: "meta-card"
  }, /*#__PURE__*/React.createElement("div", {
    className: "sec-lbl",
    style: {
      color: 'var(--wurth-red)'
    }
  }, "\uD83D\uDCCA Plan de Ventas \u2014 Facturaci\xF3n Acumulada del Mes vs. Plan"), /*#__PURE__*/React.createElement("div", {
    className: "meta-row"
  }, /*#__PURE__*/React.createElement("div", {
    className: "meta-nums"
  }, /*#__PURE__*/React.createElement("span", {
    className: "plan-curr"
  }, fmtK(plan.fact_acum)), /*#__PURE__*/React.createElement("span", {
    className: "plan-total"
  }, "/ ", fmtK(plan.plan_total))), /*#__PURE__*/React.createElement("div", {
    className: "plan-bar-bg"
  }, /*#__PURE__*/React.createElement("div", {
    className: "plan-bar-fill",
    style: {
      width: Math.min(plan.pct, 100) + '%',
      background: color
    }
  }, fmtN(plan.pct, 1), "%"), /*#__PURE__*/React.createElement("div", {
    className: "plan-bar-pace",
    style: {
      left: plan.pace + '%'
    }
  })), /*#__PURE__*/React.createElement("span", {
    className: 'meta-tag ' + tagCls
  }, onTrack ? 'En ritmo' : 'Por debajo del ritmo')));
}

/* ── Ritmo mensual ────────────────────────────────────────────────────── */
function MetaBar({
  meta
}) {
  const progPct = Math.min(meta.curr / meta.last * 100, 120);
  const paceTarget = meta.pace / 100 * meta.last;
  const onTrack = meta.curr >= paceTarget;
  const tagCls = onTrack ? 'tag-ok' : 'tag-warn';
  const diff = Math.round(meta.curr - paceTarget);
  return /*#__PURE__*/React.createElement("div", {
    className: "meta-card"
  }, /*#__PURE__*/React.createElement("div", {
    className: "sec-lbl"
  }, "Ritmo Mensual \u2014 Pedidos vs. Mes Anterior"), /*#__PURE__*/React.createElement("div", {
    className: "meta-row"
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: '11px',
      color: 'var(--text-2)',
      whiteSpace: 'nowrap'
    }
  }, meta.curr_month, " vs ", meta.last_month), /*#__PURE__*/React.createElement("div", {
    className: "meta-nums"
  }, /*#__PURE__*/React.createElement("span", {
    className: "meta-curr"
  }, fmtN(meta.curr)), /*#__PURE__*/React.createElement("span", {
    className: "meta-sep"
  }, "de"), /*#__PURE__*/React.createElement("span", {
    className: "meta-last"
  }, fmtN(meta.last), " pedidos")), /*#__PURE__*/React.createElement("div", {
    className: "meta-bar-wrap"
  }, /*#__PURE__*/React.createElement("div", {
    className: "meta-bar-bg"
  }, /*#__PURE__*/React.createElement("div", {
    className: "meta-bar-fill",
    style: {
      width: Math.min(progPct, 100) + '%',
      background: progPct > 100 ? 'var(--green)' : onTrack ? 'var(--blue)' : 'var(--amber)'
    }
  }), /*#__PURE__*/React.createElement("div", {
    className: "meta-bar-pace",
    style: {
      left: meta.pace + '%'
    }
  })), /*#__PURE__*/React.createElement("div", {
    className: "meta-bar-labels"
  }, /*#__PURE__*/React.createElement("span", null, progPct.toFixed(0), "% del mes anterior"))), /*#__PURE__*/React.createElement("span", {
    className: 'meta-tag ' + tagCls
  }, onTrack ? `+${diff} sobre ritmo` : `${Math.abs(diff)} por debajo del ritmo`)));
}

/* ── MSPA panel ───────────────────────────────────────────────────────── */
function MspaPanel({
  rows
}) {
  return /*#__PURE__*/React.createElement("div", {
    className: "card"
  }, /*#__PURE__*/React.createElement("div", {
    className: "sec-lbl"
  }, "MSPA \u2014 Estado Actual ", /*#__PURE__*/React.createElement("small", {
    style: {
      fontSize: '9px',
      color: 'var(--text-3)'
    }
  }, "(refresca cada 60s)")), rows.map((r, i) => /*#__PURE__*/React.createElement("div", {
    key: i,
    className: 'mspa-row' + (r.venta ? ' venta' : r.hi ? ' hi' : '')
  }, /*#__PURE__*/React.createElement("span", {
    className: "mspa-lbl"
  }, r.k), /*#__PURE__*/React.createElement("span", {
    className: "mspa-val"
  }, fmtK(r.val), /*#__PURE__*/React.createElement("div", {
    className: "s-sub",
    style: {
      textAlign: 'right'
    }
  }, fmtN(r.ords), " ord \xB7 ", fmtN(r.pos), " pos")))));
}

/* ── Seller leaderboards ──────────────────────────────────────────────── */
function SellerTable({
  rows,
  valCls,
  unit
}) {
  return /*#__PURE__*/React.createElement("table", {
    className: "seller-tbl"
  }, /*#__PURE__*/React.createElement("thead", null, /*#__PURE__*/React.createElement("tr", null, /*#__PURE__*/React.createElement("th", null), /*#__PURE__*/React.createElement("th", null, "Vendedor"), /*#__PURE__*/React.createElement("th", {
    style: {
      textAlign: 'right'
    }
  }, unit))), /*#__PURE__*/React.createElement("tbody", null, rows.map((s, i) => /*#__PURE__*/React.createElement("tr", {
    key: i
  }, /*#__PURE__*/React.createElement("td", {
    className: 's-rank ' + (i < 3 ? 'med-' + (i + 1) : '')
  }, i + 1), /*#__PURE__*/React.createElement("td", null, /*#__PURE__*/React.createElement("div", {
    className: "s-name"
  }, s.nombre), /*#__PURE__*/React.createElement("div", {
    className: "s-sub"
  }, fmtN(s.cnt), " ", unit === 'Valor' ? 'pedidos' : unit.toLowerCase())), /*#__PURE__*/React.createElement("td", {
    className: 's-val ' + valCls
  }, fmtK(s.val))))));
}
function SellerPanels({
  d
}) {
  return /*#__PURE__*/React.createElement("div", {
    className: "sellers-wrap"
  }, /*#__PURE__*/React.createElement("div", {
    className: "card"
  }, /*#__PURE__*/React.createElement("div", {
    className: "sec-lbl lbl-fact"
  }, "\uD83C\uDFC6 Top 5 Facturaci\xF3n del D\xEDa"), /*#__PURE__*/React.createElement(SellerTable, {
    rows: d.sellers_fact,
    valCls: "fact-val",
    unit: "Valor"
  })), /*#__PURE__*/React.createElement("div", {
    className: "card"
  }, /*#__PURE__*/React.createElement("div", {
    className: "sec-lbl lbl-ret"
  }, "\u23F8 Top 5 con M\xE1s Retenidos"), /*#__PURE__*/React.createElement(SellerTable, {
    rows: d.sellers_ret,
    valCls: "ret-val",
    unit: "Retenidos"
  })), /*#__PURE__*/React.createElement("div", {
    className: "card"
  }, /*#__PURE__*/React.createElement("div", {
    className: "sec-lbl lbl-an"
  }, "\u2715 Top 5 con M\xE1s Anulados"), /*#__PURE__*/React.createElement(SellerTable, {
    rows: d.sellers_an,
    valCls: "an-val",
    unit: "Anulados"
  })));
}

/* ── Trend chart (Chart.js) ───────────────────────────────────────────── */
function TrendChart({
  dark
}) {
  const ref = useRef(null);
  const chart = useRef(null);
  useEffect(() => {
    const labels = TREND.map(t => {
      const [y, m] = t.mes.split('-');
      return MONTHS[+m - 1] + ' ' + y.slice(2);
    });
    const bar = TREND.map(t => +(t.pedidos / t.dias_hab).toFixed(1));
    const line = TREND.map(t => +(t.valor / 1e6 / t.dias_hab).toFixed(2));
    const tick = dark ? '#64748b' : '#94a3b8';
    const grid = dark ? '#1e293b' : '#f1f5f9';
    if (chart.current) chart.current.destroy();
    chart.current = new Chart(ref.current.getContext('2d'), {
      data: {
        labels,
        datasets: [{
          type: 'bar',
          label: 'Ped/día hábil',
          data: bar,
          backgroundColor: 'rgba(37,99,235,.7)',
          borderColor: '#2563eb',
          borderWidth: 1,
          yAxisID: 'y1',
          order: 2
        }, {
          type: 'line',
          label: 'M$/día hábil',
          data: line,
          borderColor: '#059669',
          backgroundColor: 'rgba(5,150,105,.07)',
          borderWidth: 2.5,
          pointRadius: 3,
          pointBackgroundColor: '#059669',
          tension: .35,
          yAxisID: 'y2',
          order: 1,
          fill: true
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: 'index',
          intersect: false
        },
        plugins: {
          legend: {
            labels: {
              color: dark ? '#cbd5e1' : '#475569',
              font: {
                size: 11
              },
              boxWidth: 12,
              padding: 14
            }
          }
        },
        scales: {
          x: {
            ticks: {
              color: tick,
              font: {
                size: 9
              }
            },
            grid: {
              color: grid
            }
          },
          y1: {
            type: 'linear',
            position: 'left',
            ticks: {
              color: '#2563eb',
              font: {
                size: 9
              }
            },
            grid: {
              color: grid
            }
          },
          y2: {
            type: 'linear',
            position: 'right',
            ticks: {
              color: '#059669',
              font: {
                size: 9
              },
              callback: v => v.toFixed(1) + 'M'
            },
            grid: {
              drawOnChartArea: false
            }
          }
        }
      }
    });
    return () => chart.current && chart.current.destroy();
  }, [dark]);
  return /*#__PURE__*/React.createElement("div", {
    className: "card"
  }, /*#__PURE__*/React.createElement("div", {
    className: "sec-lbl"
  }, "Tendencia Mensual \u2014 Pedidos & Valor por D\xEDa H\xE1bil"), /*#__PURE__*/React.createElement("div", {
    className: "chart-wrap"
  }, /*#__PURE__*/React.createElement("canvas", {
    ref: ref
  })));
}
Object.assign(window, {
  Header,
  KpiGrid,
  FlowBar,
  PlanBar,
  MetaBar,
  MspaPanel,
  SellerPanels,
  TrendChart
});
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/operations-dashboard/components.jsx", error: String((e && e.message) || e) }); }

// ui_kits/operations-dashboard/data.js
try { (() => {
/* Fake-but-realistic data for the Würth Operations Dashboard kit.
   Mirrors the shape produced by dashboard.py (reactor + mspa).
   Two days are provided so the date picker can switch context. */
(function () {
  // ── number / currency formatting (es-AR) ──
  window.fmtN = (n, d = 0) => Number(n || 0).toLocaleString('es-AR', {
    minimumFractionDigits: d,
    maximumFractionDigits: d
  });
  window.fmtK = n => {
    n = Number(n) || 0;
    if (n >= 1e9) return '$' + (n / 1e9).toFixed(1).replace('.', ',') + 'B';
    if (n >= 1e6) return '$' + (n / 1e6).toFixed(1).replace('.', ',') + 'M';
    if (n >= 1e3) return '$' + Math.round(n / 1e3) + 'K';
    return '$' + window.fmtN(n, 0);
  };
  window.pct = (a, b) => b ? (a / b * 100).toFixed(1).replace('.', ',') + '%' : '—';
  const MONTHS = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'];
  const trend = [{
    mes: '2025-06',
    pedidos: 4120,
    valor: 38.2e6,
    dias_hab: 21
  }, {
    mes: '2025-07',
    pedidos: 4480,
    valor: 41.5e6,
    dias_hab: 23
  }, {
    mes: '2025-08',
    pedidos: 3990,
    valor: 36.8e6,
    dias_hab: 21
  }, {
    mes: '2025-09',
    pedidos: 4610,
    valor: 43.1e6,
    dias_hab: 22
  }, {
    mes: '2025-10',
    pedidos: 4820,
    valor: 45.9e6,
    dias_hab: 23
  }, {
    mes: '2025-11',
    pedidos: 4530,
    valor: 42.7e6,
    dias_hab: 20
  }, {
    mes: '2025-12',
    pedidos: 3870,
    valor: 39.4e6,
    dias_hab: 19
  }, {
    mes: '2026-01',
    pedidos: 4210,
    valor: 40.1e6,
    dias_hab: 22
  }, {
    mes: '2026-02',
    pedidos: 4350,
    valor: 41.0e6,
    dias_hab: 20
  }, {
    mes: '2026-03',
    pedidos: 4900,
    valor: 46.8e6,
    dias_hab: 22
  }, {
    mes: '2026-04',
    pedidos: 4720,
    valor: 44.2e6,
    dias_hab: 21
  }, {
    mes: '2026-05',
    pedidos: 4980,
    valor: 47.6e6,
    dias_hab: 21
  }];
  const sellers = [['García, M.', '204'], ['Rossi, L.', '118'], ['Pérez, A.', '077'], ['Lombardi, S.', '156'], ['Núñez, D.', '231'], ['Ferraro, J.', '092'], ['Sosa, P.', '188'], ['Ibáñez, R.', '143']];
  const mk = arr => arr.map(([i, c, v]) => ({
    nombre: `${sellers[i][0]} (${sellers[i][1]})`,
    cnt: c,
    val: v
  }));
  window.DASH_DATA = {
    '2026-05-28': {
      date_display: '28/05/2026',
      pedidos: 1284,
      vendedores: 86,
      valor: 3402190,
      lineas: 7820,
      avg_lineas: 6.1,
      avg_ped_vend: 14.9,
      comp: {
        pedidos: 1142,
        valor: 3010400,
        avg_lineas: 5.8,
        avg_ped_vend: 13.4
      },
      flow: {
        informado: {
          v: 1284,
          val: 5.1e6
        },
        retenido: {
          v: 312,
          pct: 24.3
        },
        anulado: {
          v: 48,
          pct: 3.7
        },
        facturado: {
          v: 924,
          pct: 71.9
        }
      },
      plan: {
        plan_total: 42.0e6,
        fact_acum: 28.4e6,
        pct: 67.6,
        pace: 72
      },
      meta: {
        curr_month: '2026-05',
        last_month: '2026-04',
        curr: 4980,
        last: 4720,
        pace: 78,
        dias_elapsed: 16,
        curr_wd: 21
      },
      mspa: [{
        k: 'Backorders (Plazos viejos)',
        val: 1245800,
        ords: 142,
        pos: 318
      }, {
        k: 'Bloqueados por Límite Crédito',
        val: 842300,
        ords: 64,
        pos: 121,
        hi: true
      }, {
        k: 'Bloqueados (Status < -1)',
        val: 318900,
        ords: 22,
        pos: 47
      }, {
        k: 'Pedidos Abiertos (Futuros)',
        val: 8420110,
        ords: 388,
        pos: 902
      }, {
        k: 'Producción Abierta',
        val: 3110450,
        ords: 95,
        pos: 240
      }, {
        k: 'Remitos / Facturas Abiertas',
        val: 2204600,
        ords: 156,
        pos: 410
      }, {
        k: 'Venta del Día',
        val: 3402190,
        ords: 57,
        pos: 188,
        venta: true
      }],
      sellers_fact: mk([[0, 3, 1.1e6], [1, 5, 842000], [2, 2, 610000], [3, 4, 488000], [4, 3, 402000]]),
      sellers_ret: mk([[5, 9, 412000], [3, 7, 388000], [6, 6, 270000], [1, 5, 198000], [7, 4, 142000]]),
      sellers_an: mk([[7, 4, 88000], [2, 3, 64000], [5, 2, 41000], [0, 2, 38000], [4, 1, 22000]])
    },
    '2026-05-27': {
      date_display: '27/05/2026',
      pedidos: 1198,
      vendedores: 84,
      valor: 3115600,
      lineas: 6980,
      avg_lineas: 5.8,
      avg_ped_vend: 14.3,
      comp: {
        pedidos: 1210,
        valor: 3240800,
        avg_lineas: 6.0,
        avg_ped_vend: 14.6
      },
      flow: {
        informado: {
          v: 1198,
          val: 4.7e6
        },
        retenido: {
          v: 268,
          pct: 22.4
        },
        anulado: {
          v: 39,
          pct: 3.3
        },
        facturado: {
          v: 891,
          pct: 74.4
        }
      },
      plan: {
        plan_total: 42.0e6,
        fact_acum: 25.0e6,
        pct: 59.5,
        pace: 67
      },
      meta: {
        curr_month: '2026-05',
        last_month: '2026-04',
        curr: 4982,
        last: 4720,
        pace: 74,
        dias_elapsed: 15,
        curr_wd: 21
      },
      mspa: [{
        k: 'Backorders (Plazos viejos)',
        val: 1198400,
        ords: 138,
        pos: 302
      }, {
        k: 'Bloqueados por Límite Crédito',
        val: 911200,
        ords: 71,
        pos: 134,
        hi: true
      }, {
        k: 'Bloqueados (Status < -1)',
        val: 290100,
        ords: 19,
        pos: 41
      }, {
        k: 'Pedidos Abiertos (Futuros)',
        val: 8190050,
        ords: 372,
        pos: 870
      }, {
        k: 'Producción Abierta',
        val: 2980300,
        ords: 91,
        pos: 228
      }, {
        k: 'Remitos / Facturas Abiertas',
        val: 2110800,
        ords: 149,
        pos: 392
      }, {
        k: 'Venta del Día',
        val: 3115600,
        ords: 52,
        pos: 171,
        venta: true
      }],
      sellers_fact: mk([[1, 4, 980000], [0, 3, 720000], [3, 5, 540000], [2, 2, 430000], [6, 3, 360000]]),
      sellers_ret: mk([[3, 8, 360000], [5, 6, 310000], [1, 5, 240000], [7, 4, 160000], [6, 3, 120000]]),
      sellers_an: mk([[2, 3, 72000], [7, 3, 58000], [0, 2, 36000], [5, 1, 24000], [4, 1, 18000]])
    }
  };
  window.TREND = trend;
  window.MONTHS = MONTHS;
})();
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/operations-dashboard/data.js", error: String((e && e.message) || e) }); }

// ui_kits/taginfo-terminal/app.jsx
try { (() => {
/* DAILY INFO 2 SALES — terminal recreation (cosmetic, fake data) */
const {
  useState,
  useEffect,
  useRef
} = React;
const fmtVal = n => Number(n || 0).toLocaleString('es-AR', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2
});
const fmtNum = n => Number(n || 0).toLocaleString('es-AR');

// Base rows mirror taginfo_web.py's 7 metrics.
const BASE = [{
  label: 'Backorders (Plazos viejos)',
  val: 1245800,
  ords: 142,
  pos: 318
}, {
  label: 'Bloqueados por Limite credito',
  val: 842300,
  ords: 64,
  pos: 121
}, {
  label: 'Bloqueado (Status< -1)',
  val: 318900,
  ords: 22,
  pos: 47
}, {
  label: 'Pedidos Abiertos (Plazos futuros)',
  val: 8420110,
  ords: 388,
  pos: 902
}, {
  label: 'Ordenes de produccion abiertas',
  val: 3110450,
  ords: 95,
  pos: 240
}, {
  label: 'Remitos/Facturas abiertas',
  val: 2204600,
  ords: 156,
  pos: 410
}, {
  label: 'Venta diaria',
  val: 3402190,
  ords: 57,
  pos: 188
}];

// jitter the live "venta diaria" row a touch on each refresh
function snapshot() {
  const rows = BASE.map(r => ({
    ...r
  }));
  const v = rows[6];
  v.val += Math.round((Math.random() - 0.3) * 60000);
  v.ords += Math.floor(Math.random() * 3);
  v.pos += Math.floor(Math.random() * 6);
  return rows;
}
const RULE = '='.repeat(100);
function TitleBars() {
  return /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("div", {
    className: "title-bar"
  }, "taginfo2-1:\xA0\xA01.Anzeige\xA0\xA02.Taginfo EK\xA0\xA03.Taginfo Kunde\xA0\xA0Hecho"), /*#__PURE__*/React.createElement("div", {
    className: "title-bar plain"
  }, "Anzeige Tagesinformation"));
}
function DataTable({
  rows
}) {
  return /*#__PURE__*/React.createElement("table", null, /*#__PURE__*/React.createElement("thead", null, /*#__PURE__*/React.createElement("tr", null, /*#__PURE__*/React.createElement("th", {
    className: "left",
    style: {
      width: '46%'
    }
  }), /*#__PURE__*/React.createElement("th", {
    style: {
      width: '4%'
    }
  }), /*#__PURE__*/React.createElement("th", {
    style: {
      width: '24%'
    }
  }, "Value"), /*#__PURE__*/React.createElement("th", {
    style: {
      width: '13%'
    }
  }, "Number", /*#__PURE__*/React.createElement("br", null), "Order"), /*#__PURE__*/React.createElement("th", {
    style: {
      width: '13%'
    }
  }, "Number", /*#__PURE__*/React.createElement("br", null), "Pos"))), /*#__PURE__*/React.createElement("tbody", null, rows.map((r, i) => /*#__PURE__*/React.createElement("tr", {
    key: i
  }, /*#__PURE__*/React.createElement("td", {
    className: "label"
  }, r.label), /*#__PURE__*/React.createElement("td", {
    className: "colon"
  }, ":"), /*#__PURE__*/React.createElement("td", {
    className: "val"
  }, fmtVal(r.val)), /*#__PURE__*/React.createElement("td", {
    className: "num"
  }, fmtNum(r.ords)), /*#__PURE__*/React.createElement("td", {
    className: "num"
  }, fmtNum(r.pos))))));
}
function Footer({
  ts,
  countdown
}) {
  return /*#__PURE__*/React.createElement("div", {
    className: "footer"
  }, "\xDAltima actualizaci\xF3n: ", /*#__PURE__*/React.createElement("b", null, ts), "\xA0|\xA0 Pr\xF3xima en ", /*#__PURE__*/React.createElement("b", null, countdown), "s \xA0|\xA0 ", /*#__PURE__*/React.createElement("span", {
    className: "dot"
  }, "\u25CF"), " LIVE");
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
      if (cd.current <= 0) {
        setRows(snapshot());
        setTs(new Date());
        cd.current = REFRESH;
      }
      setCountdown(cd.current);
    }, 1000);
    return () => clearInterval(t);
  }, []);
  const fecha = ts.toLocaleDateString('es-AR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric'
  }).replace(/\//g, '.');
  const tsStr = ts.toISOString().slice(0, 19).replace('T', ' ');
  return /*#__PURE__*/React.createElement("div", {
    className: "screen"
  }, /*#__PURE__*/React.createElement(TitleBars, null), /*#__PURE__*/React.createElement("div", {
    className: "sep"
  }, RULE), /*#__PURE__*/React.createElement("div", {
    className: "center"
  }, "DAILY INFO 2 SALES"), /*#__PURE__*/React.createElement("div", {
    className: "sep"
  }, RULE), /*#__PURE__*/React.createElement("div", {
    className: "meta"
  }, /*#__PURE__*/React.createElement("span", null, "Fecha : ", /*#__PURE__*/React.createElement("b", {
    style: {
      color: 'var(--term-fg)'
    }
  }, fecha), /*#__PURE__*/React.createElement("span", {
    className: "cursor"
  }, "_"))), /*#__PURE__*/React.createElement(DataTable, {
    rows: rows
  }), /*#__PURE__*/React.createElement(Footer, {
    ts: tsStr,
    countdown: countdown
  }), /*#__PURE__*/React.createElement("div", {
    className: "hint"
  }, "Solo lectura \xB7 refresco autom\xE1tico cada 60s \xB7 fuente: MSPA (Informix)"));
}
ReactDOM.createRoot(document.getElementById('root')).render(/*#__PURE__*/React.createElement(Terminal, null));
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/taginfo-terminal/app.jsx", error: String((e && e.message) || e) }); }

})();

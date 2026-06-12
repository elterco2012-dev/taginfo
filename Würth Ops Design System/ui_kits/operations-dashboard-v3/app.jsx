/* App shell v3 — dark mode, TV mode, export, date switch, skeleton on load */
const { useState: useS, useEffect: useE } = React;

function App() {
  const [dark, setDark] = useS(false);
  const [tv, setTv] = useS(false);
  const [dateKey, setDateKey] = useS('2026-05-28');
  const [loading, setLoading] = useS(true);

  useE(() => { document.body.classList.toggle('dark', dark); }, [dark]);
  useE(() => { document.body.classList.toggle('tv', tv); }, [tv]);
  // simulate initial data fetch → skeleton, then content
  useE(() => { const t = setTimeout(() => setLoading(false), 900); return () => clearTimeout(t); }, []);
  // brief skeleton when switching date too
  const switchDate = (k) => { setLoading(true); setDateKey(k); setTimeout(() => setLoading(false), 600); };

  const d = window.DASH_DATA[dateKey] || window.DASH_DATA['2026-05-28'];

  return (
    <React.Fragment>
      <Header
        d={d} dark={dark} tv={tv}
        onToggleDark={() => setDark(v => !v)}
        onToggleTV={() => setTv(v => !v)}
        onExport={() => window.print()}
        onPickDate={(v) => switchDate(window.DASH_DATA[v] ? v : '2026-05-27')}
        onClearDate={() => switchDate('2026-05-28')}
      />
      <div className={'main' + (loading ? ' is-loading' : '')}>
        <AlertBanner d={d} />
        <Hero d={d} />
        <KpiStrip d={d} />
        <FlowBar flow={d.flow} />
        <div className="bottom">
          <TrendChart dark={dark} stamp={d.datos_al.reactor} />
          <MspaPanel rows={d.mspa} stamp={d.datos_al.mspa} />
        </div>
        <SellerPanels d={d} />
      </div>
    </React.Fragment>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />);

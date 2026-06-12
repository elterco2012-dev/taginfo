/* App shell — wires components, dark mode, date switching, live countdown */
const { useState: useS, useEffect: useE } = React;

function App() {
  const [dark, setDark] = useS(false);
  const [dateKey, setDateKey] = useS('2026-05-28');
  const [freshM, setFreshM] = useS(45);
  const [freshR, setFreshR] = useS(8);

  useE(() => { document.body.classList.toggle('dark', dark); }, [dark]);
  useE(() => {
    const t = setInterval(() => setFreshM(s => (s <= 1 ? 60 : s - 1)), 1000);
    return () => clearInterval(t);
  }, []);

  const d = window.DASH_DATA[dateKey] || window.DASH_DATA['2026-05-28'];

  return (
    <React.Fragment>
      <Header
        dateDisplay={d.date_display}
        dark={dark}
        onToggleDark={() => setDark(v => !v)}
        onPickDate={(v) => setDateKey(window.DASH_DATA[v] ? v : '2026-05-27')}
        onClearDate={() => setDateKey('2026-05-28')}
        freshM={freshM}
        freshR={freshR}
      />
      <div className="main">
        <KpiGrid d={d} />
        <FlowBar flow={d.flow} />
        <PlanBar plan={d.plan} />
        <MetaBar meta={d.meta} />
        <div className="bottom">
          <TrendChart dark={dark} />
          <MspaPanel rows={d.mspa} />
        </div>
        <SellerPanels d={d} />
      </div>
    </React.Fragment>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />);

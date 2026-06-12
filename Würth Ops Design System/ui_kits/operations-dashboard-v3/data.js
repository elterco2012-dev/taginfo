/* Data for Dashboard v3 — extends v2 with sparkline series, targets,
   alert thresholds and connection state. Still fake/static. */
(function () {
  window.fmtN = (n, d = 0) => Number(n || 0).toLocaleString('es-AR', { minimumFractionDigits: d, maximumFractionDigits: d });
  window.fmtK = (n) => {
    n = Number(n) || 0;
    const neg = n < 0; n = Math.abs(n);
    let s;
    if (n >= 1e9) s = '$' + (n / 1e9).toFixed(1).replace('.', ',') + 'B';
    else if (n >= 1e6) s = '$' + (n / 1e6).toFixed(1).replace('.', ',') + 'M';
    else if (n >= 1e3) s = '$' + Math.round(n / 1e3) + 'K';
    else s = '$' + window.fmtN(n, 0);
    return (neg ? '−' : '') + s;
  };
  window.pct = (a, b) => (b ? ((a / b) * 100).toFixed(1).replace('.', ',') + '%' : '—');

  const MONTHS = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'];
  const trend = [
    { mes: '2025-06', pedidos: 4120, valor: 38.2e6, dias_hab: 21 },
    { mes: '2025-07', pedidos: 4480, valor: 41.5e6, dias_hab: 23 },
    { mes: '2025-08', pedidos: 3990, valor: 36.8e6, dias_hab: 21 },
    { mes: '2025-09', pedidos: 4610, valor: 43.1e6, dias_hab: 22 },
    { mes: '2025-10', pedidos: 4820, valor: 45.9e6, dias_hab: 23 },
    { mes: '2025-11', pedidos: 4530, valor: 42.7e6, dias_hab: 20 },
    { mes: '2025-12', pedidos: 3870, valor: 39.4e6, dias_hab: 19 },
    { mes: '2026-01', pedidos: 4210, valor: 40.1e6, dias_hab: 22 },
    { mes: '2026-02', pedidos: 4350, valor: 41.0e6, dias_hab: 20 },
    { mes: '2026-03', pedidos: 4900, valor: 46.8e6, dias_hab: 22 },
    { mes: '2026-04', pedidos: 4720, valor: 44.2e6, dias_hab: 21 },
    { mes: '2026-05', pedidos: 4980, valor: 47.6e6, dias_hab: 21 },
  ];

  const sellers = [
    ['García, M.', '204'], ['Rossi, L.', '118'], ['Pérez, A.', '077'],
    ['Lombardi, S.', '156'], ['Núñez, D.', '231'], ['Ferraro, J.', '092'],
    ['Sosa, P.', '188'], ['Ibáñez, R.', '143'],
  ];
  const mk = (arr) => arr.map(([i, c, v]) => ({ nombre: `${sellers[i][0]} (${sellers[i][1]})`, cnt: c, val: v }));

  window.DASH_DATA = {
    '2026-05-28': {
      date_display: '28/05/2026',
      datos_al: { mspa: '14:32:07', reactor: '14:25:00' },
      conn: { mspa: 'ok', reactor: 'ok' },          // ok | slow | down
      pedidos: 1284, vendedores: 86, valor: 3402190, lineas: 7820,
      avg_lineas: 6.1, avg_ped_vend: 14.9,
      comp: { pedidos: 1142, valor: 3010400, avg_lineas: 5.8, avg_ped_vend: 13.4, label: 'mismo día hábil mes anterior' },
      // metas (targets) por KPI
      meta_pedidos: 1350, meta_valor: 3600000,
      // sparklines: últimos 14 días hábiles
      spark: {
        pedidos: [1190, 1210, 1255, 1180, 1230, 1290, 1240, 1198, 1260, 1275, 1220, 1284, 1250, 1284],
        valor: [2.9, 3.0, 3.2, 2.8, 3.1, 3.3, 3.15, 2.95, 3.25, 3.3, 3.05, 3.4, 3.2, 3.4],
        ped_vend: [13.4, 13.8, 14.1, 13.6, 14.0, 14.6, 14.2, 13.9, 14.4, 14.7, 14.2, 14.9, 14.5, 14.9],
        lineas: [5.8, 5.9, 6.0, 5.7, 6.1, 6.2, 6.0, 5.9, 6.1, 6.3, 6.0, 6.1, 6.2, 6.1],
      },
      flow: { informado: { v: 1284, val: 5.1e6 }, retenido: { v: 312, pct: 24.3 }, anulado: { v: 48, pct: 3.7 }, facturado: { v: 924, pct: 71.9 } },
      plan: { plan_total: 42.0e6, fact_acum: 28.4e6, pct: 67.6, pace: 72 },
      mspa: [
        { k: 'Backorders (Plazos viejos)', val: 1245800, ords: 142, pos: 318, sev: 'ok' },
        { k: 'Bloqueados por Límite Crédito', val: 842300, ords: 64, pos: 121, sev: 'warn' },
        { k: 'Bloqueados (Status < -1)', val: 318900, ords: 22, pos: 47, sev: 'ok' },
        { k: 'Pedidos Abiertos (Futuros)', val: 8420110, ords: 388, pos: 902, sev: 'ok' },
        { k: 'Producción Abierta', val: 3110450, ords: 95, pos: 240, sev: 'ok' },
        { k: 'Remitos / Facturas Abiertas', val: 2204600, ords: 156, pos: 410, sev: 'ok' },
        { k: 'Venta del Día', val: 3402190, ords: 57, pos: 188, venta: true },
      ],
      sellers_fact: mk([[0, 3, 1.1e6], [1, 5, 842000], [2, 2, 610000], [3, 4, 488000], [4, 3, 402000]]),
      sellers_ret: mk([[5, 9, 412000], [3, 7, 388000], [6, 6, 270000], [1, 5, 198000], [7, 4, 142000]]),
      sellers_an: mk([[7, 4, 88000], [2, 3, 64000], [5, 2, 41000], [0, 2, 38000], [4, 1, 22000]]),
      sin_facturar: 3,   // vendedores activos sin facturar aún
    },
    '2026-05-27': {
      date_display: '27/05/2026',
      datos_al: { mspa: '17:58:40', reactor: '17:50:00' },
      conn: { mspa: 'ok', reactor: 'slow' },
      pedidos: 1198, vendedores: 84, valor: 3115600, lineas: 6980,
      avg_lineas: 5.8, avg_ped_vend: 14.3,
      comp: { pedidos: 1210, valor: 3240800, avg_lineas: 6.0, avg_ped_vend: 14.6, label: 'mismo día hábil mes anterior' },
      meta_pedidos: 1350, meta_valor: 3600000,
      spark: {
        pedidos: [1240, 1180, 1220, 1260, 1190, 1230, 1280, 1200, 1250, 1270, 1210, 1240, 1198, 1198],
        valor: [3.2, 2.9, 3.1, 3.3, 2.95, 3.1, 3.35, 3.0, 3.2, 3.3, 3.05, 3.2, 3.12, 3.12],
        ped_vend: [14.0, 13.5, 13.9, 14.3, 13.7, 14.0, 14.5, 13.8, 14.2, 14.5, 14.0, 14.3, 14.3, 14.3],
        lineas: [6.0, 5.7, 5.9, 6.1, 5.8, 6.0, 6.2, 5.9, 6.1, 6.2, 5.9, 6.0, 5.8, 5.8],
      },
      flow: { informado: { v: 1198, val: 4.7e6 }, retenido: { v: 268, pct: 22.4 }, anulado: { v: 39, pct: 3.3 }, facturado: { v: 891, pct: 74.4 } },
      plan: { plan_total: 42.0e6, fact_acum: 25.0e6, pct: 59.5, pace: 67 },
      mspa: [
        { k: 'Backorders (Plazos viejos)', val: 1198400, ords: 138, pos: 302, sev: 'ok' },
        { k: 'Bloqueados por Límite Crédito', val: 911200, ords: 71, pos: 134, sev: 'danger' },
        { k: 'Bloqueados (Status < -1)', val: 290100, ords: 19, pos: 41, sev: 'ok' },
        { k: 'Pedidos Abiertos (Futuros)', val: 8190050, ords: 372, pos: 870, sev: 'ok' },
        { k: 'Producción Abierta', val: 2980300, ords: 91, pos: 228, sev: 'ok' },
        { k: 'Remitos / Facturas Abiertas', val: 2110800, ords: 149, pos: 392, sev: 'ok' },
        { k: 'Venta del Día', val: 3115600, ords: 52, pos: 171, venta: true },
      ],
      sellers_fact: mk([[1, 4, 980000], [0, 3, 720000], [3, 5, 540000], [2, 2, 430000], [6, 3, 360000]]),
      sellers_ret: mk([[3, 8, 360000], [5, 6, 310000], [1, 5, 240000], [7, 4, 160000], [6, 3, 120000]]),
      sellers_an: mk([[2, 3, 72000], [7, 3, 58000], [0, 2, 36000], [5, 1, 24000], [4, 1, 18000]]),
      sin_facturar: 5,
    },
  };
  window.TREND = trend;
  window.MONTHS = MONTHS;
})();

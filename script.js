
function fetchADV(symbol) {
  const toDate = new Date().toISOString().split('T')[0];
  const fromDate = new Date(Date.now() - 10 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];
  const url = `https://api.polygon.io/v2/aggs/ticker/${symbol}/range/1/day/${fromDate}/${toDate}?adjusted=true&sort=desc&limit=10&apiKey=${apiKey}`;

  return fetch(url)
    .then(res => res.json())
    .then(data => {
      if (!data.results || data.results.length === 0) return null;
      const volumes = data.results.map(d => d.v);
      const avg = volumes.reduce((sum, v) => sum + v, 0) / volumes.length;
      return { symbol, adv: Math.round(avg) };
    })
    .catch(() => null);
}

function updateTable() {
  const tbody = document.getElementById("table-body");
  tbody.innerHTML = "";

  const now = new Date().toLocaleTimeString();

  Promise.all(tickers.map(fetchADV)).then(results => {
    results.forEach(item => {
      if (!item) return;
      const row = document.createElement("tr");
      row.innerHTML = `
        <td>${item.symbol}</td>
        <td>${item.adv.toLocaleString()}</td>
        <td>${now}</td>
      `;
      tbody.appendChild(row);
    });
  });
}

updateTable();
setInterval(updateTable, 20000);

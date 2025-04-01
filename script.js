
async function fetchADV(symbol) {
  const toDate = new Date().toISOString().split('T')[0];
  const fromDate = new Date(Date.now() - 10 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];
  const url = `https://api.polygon.io/v2/aggs/ticker/${symbol}/range/1/day/${fromDate}/${toDate}?adjusted=true&sort=desc&limit=10&apiKey=${apiKey}`;

  try {
    const res = await fetch(url);
    const data = await res.json();
    if (!data.results || data.results.length === 0) return null;
    const volumes = data.results.map(d => d.v);
    const adv = volumes.reduce((sum, v) => sum + v, 0) / volumes.length;
    return Math.round(adv);
  } catch {
    return null;
  }
}

async function fetchSnapshot(symbol) {
  const url = `https://api.polygon.io/v2/snapshot/locale/us/markets/stocks/tickers/${symbol}?apiKey=${apiKey}`;
  try {
    const res = await fetch(url);
    const data = await res.json();
    if (!data.ticker) return null;
    return {
      volume: data.ticker.day.v,
      change: data.ticker.todaysChangePerc,
      bid: data.ticker.lastQuote.p,
      ask: data.ticker.lastQuote.ap
    };
  } catch {
    return null;
  }
}

async function updateTable() {
  const tbody = document.getElementById("table-body");
  tbody.innerHTML = "";
  const now = new Date().toLocaleTimeString();

  for (const symbol of tickers) {
    const [adv, snapshot] = await Promise.all([
      fetchADV(symbol),
      fetchSnapshot(symbol)
    ]);

    if (!adv || !snapshot) continue;

    const row = document.createElement("tr");
    const colorClass = snapshot.change > 0 ? "green" : snapshot.change < 0 ? "red" : "";

    row.innerHTML = `
      <td>${symbol}</td>
      <td>${adv.toLocaleString()}</td>
      <td>${snapshot.volume.toLocaleString()}</td>
      <td class="${colorClass}">${snapshot.change.toFixed(2)}%</td>
      <td>${snapshot.bid}</td>
      <td>${snapshot.ask}</td>
      <td>${now}</td>
    `;
    tbody.appendChild(row);
  }
}

function sortTable(n) {
  const table = document.getElementById("stock-table");
  let switching = true;
  let dir = "asc";
  let switchCount = 0;

  while (switching) {
    switching = false;
    const rows = table.rows;
    for (let i = 1; i < rows.length - 1; i++) {
      let shouldSwitch = false;
      const x = rows[i].getElementsByTagName("TD")[n];
      const y = rows[i + 1].getElementsByTagName("TD")[n];
      const xVal = isNaN(x.innerText.replace(/[%,$]/g, "")) ? x.innerText : parseFloat(x.innerText.replace(/[%,$]/g, ""));
      const yVal = isNaN(y.innerText.replace(/[%,$]/g, "")) ? y.innerText : parseFloat(y.innerText.replace(/[%,$]/g, ""));

      if ((dir === "asc" && xVal > yVal) || (dir === "desc" && xVal < yVal)) {
        shouldSwitch = true;
        break;
      }
    }

    if (shouldSwitch) {
      rows[i].parentNode.insertBefore(rows[i + 1], rows[i]);
      switching = true;
      switchCount++;
    } else {
      if (switchCount === 0 && dir === "asc") {
        dir = "desc";
        switching = true;
      }
    }
  }
}

// автооновлення кожні 100 секунд
updateTable();
setInterval(updateTable, 100000);

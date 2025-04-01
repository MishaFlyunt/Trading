
let sortColumn = localStorage.getItem("sortColumn") || 0;
let sortDirection = localStorage.getItem("sortDirection") || "asc";

function applyTheme() {
  const theme = localStorage.getItem("theme") || "light";
  document.body.classList.toggle("dark", theme === "dark");
}

function toggleTheme() {
  const isDark = document.body.classList.toggle("dark");
  localStorage.setItem("theme", isDark ? "dark" : "light");
}

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

  let rows = [];
  for (const symbol of tickers) {
    const [adv, snapshot] = await Promise.all([
      fetchADV(symbol),
      fetchSnapshot(symbol)
    ]);

    if (!adv || !snapshot) continue;

    const colorClass = snapshot.change > 0 ? "green" : snapshot.change < 0 ? "red" : "";
    rows.push([
      symbol,
      adv,
      snapshot.volume,
      `<span class="${colorClass}">${snapshot.change.toFixed(2)}%</span>`,
      snapshot.bid,
      snapshot.ask,
      now
    ]);
  }

  sortAndRender(rows);
}

function sortAndRender(data) {
  data.sort((a, b) => {
    const valA = isNaN(a[sortColumn]) ? a[sortColumn] : parseFloat(a[sortColumn]);
    const valB = isNaN(b[sortColumn]) ? b[sortColumn] : parseFloat(b[sortColumn]);
    return sortDirection === "asc" ? valA - valB : valB - valA;
  });

  const tbody = document.getElementById("table-body");
  tbody.innerHTML = "";
  data.forEach(row => {
    const tr = document.createElement("tr");
    tr.innerHTML = row.map(cell => `<td>${cell}</td>`).join("");
    tbody.appendChild(tr);
  });
}

function sortTable(n) {
  if (sortColumn == n) {
    sortDirection = sortDirection === "asc" ? "desc" : "asc";
  } else {
    sortColumn = n;
    sortDirection = "asc";
  }
  localStorage.setItem("sortColumn", sortColumn);
  localStorage.setItem("sortDirection", sortDirection);
  updateTable();
}

applyTheme();
updateTable();
setInterval(updateTable, 100000);

function filterTable() {
  const input = document.getElementById("searchInput").value.toUpperCase();
  const table = document.getElementById("stock-table");
  const trs = table.getElementsByTagName("tr");

  for (let i = 1; i < trs.length; i++) {
    const td = trs[i].getElementsByTagName("td")[0];
    if (td) {
      trs[i].style.display = td.innerText.toUpperCase().indexOf(input) > -1 ? "" : "none";
    }
  }
}


function applyTheme() {
  const theme = localStorage.getItem("theme") || "light";
  document.body.classList.toggle("dark", theme === "dark");
}
function toggleTheme() {
  const isDark = document.body.classList.toggle("dark");
  localStorage.setItem("theme", isDark ? "dark" : "light");
}

function clearSortIndicators(tableId) {
  document.querySelectorAll(`#${tableId} th`).forEach(th => {
    th.classList.remove("sorted-asc", "sorted-desc");
    const span = th.querySelector(".arrow");
    if (span) th.removeChild(span);
  });
}

function addSortIndicator(th, isAsc) {
  const arrow = document.createElement("span");
  arrow.className = "arrow";
  arrow.innerText = isAsc ? " ▲" : " ▼";
  th.appendChild(arrow);
  th.classList.add(isAsc ? "sorted-asc" : "sorted-desc");
}

function sortTable(tableId, colIndex) {
  const table = document.getElementById(tableId);
  const tbody = table.tBodies[0];
  let rows = Array.from(tbody.rows);

  const headers = table.tHead.rows[0].cells;
  clearSortIndicators(tableId);

  let isAsc = table.getAttribute("data-sort-dir") !== "asc";
  table.setAttribute("data-sort-dir", isAsc ? "asc" : "desc");

  rows.sort((a, b) => {
    const aText = a.cells[colIndex].innerText.replace(/[%,$]/g, '');
    const bText = b.cells[colIndex].innerText.replace(/[%,$]/g, '');
    const aVal = isNaN(aText) ? aText.toLowerCase() : parseFloat(aText);
    const bVal = isNaN(bText) ? bText.toLowerCase() : parseFloat(bText);
    return isAsc ? (aVal > bVal ? 1 : -1) : (aVal < bVal ? 1 : -1);
  });

  addSortIndicator(headers[colIndex], isAsc);
  rows.forEach(row => tbody.appendChild(row));
}

async function updateTable() {
  const now = new Date().toLocaleTimeString();
  const posBody = document.getElementById("pos-body");
  const negBody = document.getElementById("neg-body");
  posBody.innerHTML = "";
  negBody.innerHTML = "";

  const data = [
    { symbol: "AAPL", imbalance: 120000, matched: 130000, side: "buy" },
    { symbol: "TSLA", imbalance: -100000, matched: 110000, side: "sell" },
    { symbol: "MSFT", imbalance: 85000, matched: 100000, side: "buy" },
    { symbol: "NVDA", imbalance: -95000, matched: 100000, side: "sell" },
    { symbol: "META", imbalance: 175000, matched: 180000, side: "buy" },
    { symbol: "T", imbalance: -200000, matched: 190000, side: "sell" },
    { symbol: "GOOG", imbalance: 70000, matched: 100000, side: "buy" },
    { symbol: "BABA", imbalance: -160000, matched: 170000, side: "sell" },
    { symbol: "AMZN", imbalance: 100000, matched: 120000, side: "buy" },
    { symbol: "ORCL", imbalance: -120000, matched: 130000, side: "sell" },
  ];

  data.forEach(d => {
    const percent = Math.abs(d.imbalance) / d.matched * 100;
    if (percent < 70) return;

    const row = document.createElement("tr");
    const color = d.imbalance > 0 ? "green" : "red";
    row.innerHTML = `
      <td>${now}</td>
      <td>${d.symbol}</td>
      <td class="${color}">${d.imbalance.toLocaleString()}</td>
      <td>${d.matched.toLocaleString()}</td>
      <td>${percent.toFixed(2)}%</td>
    `;

    if (d.imbalance > 0) {
      posBody.appendChild(row);
    } else {
      negBody.appendChild(row);
    }
  });
}

applyTheme();
updateTable();
setInterval(updateTable, 30000);

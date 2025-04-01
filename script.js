
const tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 'BRK.B', 'UNH', 'JPM', 'V', 'XOM', 'PG', 'JNJ', 'MA', 'HD', 'CVX', 'LLY', 'MRK', 'ABBV', 'PEP', 'KO', 'AVGO', 'ADBE', 'TMO', 'CSCO', 'MCD', 'WMT', 'BAC', 'NFLX', 'ORCL', 'ABT', 'NKE', 'COST', 'DHR', 'QCOM', 'INTC', 'TXN', 'LIN', 'AMGN', 'PM', 'NEE', 'UNP', 'UPS', 'HON', 'IBM', 'MS', 'RTX', 'CAT', 'BA'];

const apiUrl = "https://query1.finance.yahoo.com/v7/finance/quote?symbols=";

function formatNumber(n) {
  return n ? n.toLocaleString("en-US") : "N/A";
}

function fetchYahooFinanceData() {
  const tbody = document.getElementById("table-body");
  tbody.innerHTML = "";
  const now = new Date().toLocaleTimeString();

  const chunks = [];
  for (let i = 0; i < tickers.length; i += 10) {
    chunks.push(tickers.slice(i, i + 10));
  }

  chunks.forEach(group => {
    fetch(apiUrl + group.join(","))
      .then(res => res.json())
      .then(data => {
        if (data.quoteResponse && data.quoteResponse.result) {
          data.quoteResponse.result.forEach(stock => {
            const price = stock.regularMarketPrice;
            const change = stock.regularMarketChange;
            const changePercent = stock.regularMarketChangePercent;
            const volume = stock.regularMarketVolume;
            const adv = stock.averageDailyVolume3Month;
            const imbalance = (volume && adv) ? volume - adv : null;

            const row = document.createElement("tr");
            row.innerHTML = `
              <td>${now}</td>
              <td>${stock.symbol}</td>
              <td>$${price?.toFixed(2) || "N/A"}</td>
              <td>${change?.toFixed(2) || "N/A"}</td>
              <td>${changePercent?.toFixed(2) || "N/A"}%</td>
              <td>${formatNumber(adv)}</td>
              <td style="color:${imbalance > 0 ? 'green' : imbalance < 0 ? 'red' : 'black'}">
                ${imbalance !== null ? (imbalance > 0 ? "+" : "") + formatNumber(imbalance) : "N/A"}
              </td>
            `;
            tbody.appendChild(row);
          });
        } else {
          const row = document.createElement("tr");
          row.innerHTML = `<td colspan='7'>Error fetching data or no results.</td>`;
          tbody.appendChild(row);
        }
      })
      .catch(err => {
        console.error("Yahoo fetch error:", err);
        const row = document.createElement("tr");
        row.innerHTML = `<td colspan='7'>Error loading data.</td>`;
        tbody.appendChild(row);
      });
  });
}

fetchYahooFinanceData();
setInterval(fetchYahooFinanceData, 20000);

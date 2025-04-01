
const tickers = [
  "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META", "BRK-B", "UNH", "JPM",
  "V", "XOM", "PG", "JNJ", "MA", "HD", "CVX", "LLY", "MRK", "ABBV",
  "PEP", "KO", "AVGO", "ADBE", "TMO", "CSCO", "MCD", "WMT", "BAC", "NFLX",
  "ORCL", "ABT", "NKE", "COST", "DHR", "QCOM", "INTC", "TXN", "LIN", "AMGN",
  "PM", "NEE", "UNP", "UPS", "HON", "IBM", "MS", "RTX", "CAT", "BA"
];

const apiUrl = "https://query1.finance.yahoo.com/v7/finance/quote?symbols=";

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
            const row = document.createElement("tr");
            row.innerHTML = `
              <td>${now}</td>
              <td>${stock.symbol}</td>
              <td>$${stock.regularMarketPrice?.toFixed(2) || "N/A"}</td>
              <td>${stock.regularMarketChange?.toFixed(2) || "N/A"}</td>
              <td>${stock.regularMarketChangePercent?.toFixed(2) || "N/A"}%</td>
            `;
            tbody.appendChild(row);
          });
        }
      })
      .catch(err => console.error("Yahoo fetch error:", err));
  });
}

fetchYahooFinanceData();
setInterval(fetchYahooFinanceData, 20000);

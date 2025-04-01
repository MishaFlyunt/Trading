
function fetchStockData() {
  const tbody = document.getElementById("table-body");
  tbody.innerHTML = "";
  const now = new Date().toLocaleTimeString();

  tickers.forEach(symbol => {
    fetch(`https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=${symbol}&apikey=${apiKey}`)
      .then(res => res.json())
      .then(data => {
        const quote = data["Global Quote"];
        if (quote && quote["05. price"]) {
          const row = document.createElement("tr");
          row.innerHTML = `
            <td>${now}</td>
            <td>${symbol}</td>
            <td>$${parseFloat(quote["05. price"]).toFixed(2)}</td>
            <td>${quote["10. change percent"]}</td>
            <td>${quote["06. volume"]}</td>
          `;
          tbody.appendChild(row);
        }
      })
      .catch(err => console.error("Error loading data for", symbol));
  });
}

// Initial load and refresh every 20 seconds
fetchStockData();
setInterval(fetchStockData, 20000);

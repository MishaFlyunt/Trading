
function fetchAlphaData() {
  const tbody = document.getElementById("table-body");
  tbody.innerHTML = "";
  const now = new Date().toLocaleTimeString();

  tickers.forEach((symbol) => {
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
            <td>${parseFloat(quote["09. change"]).toFixed(2)}</td>
            <td>${quote["10. change percent"]}</td>
            <td>${quote["06. volume"]}</td>
          `;
          tbody.appendChild(row);
        } else {
          const row = document.createElement("tr");
          row.innerHTML = `<td colspan='6'>No data for ${symbol}</td>`;
          tbody.appendChild(row);
        }
      })
      .catch(err => {
        const row = document.createElement("tr");
        row.innerHTML = `<td colspan='6'>Error loading ${symbol}</td>`;
        tbody.appendChild(row);
      });
  });
}

fetchAlphaData();
setInterval(fetchAlphaData, 60000); // оновлення раз в 60 сек

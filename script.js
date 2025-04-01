const apiKey = "TGV1HSYMU113MUCR";

function getStock() {
  const symbol = document.getElementById("symbol").value.toUpperCase().trim();
  const resultDiv = document.getElementById("result");
  resultDiv.textContent = "Loading...";

  if (!symbol) {
    resultDiv.textContent = "Please enter a stock symbol.";
    return;
  }

  const url = `https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=${symbol}&apikey=${apiKey}`;

  fetch(url)
    .then((response) => response.json())
    .then((data) => {
      const quote = data["Global Quote"];
      if (quote && quote["05. price"]) {
        resultDiv.innerHTML = `
          <strong>${symbol}</strong><br/>
          Price: <strong>$${parseFloat(quote["05. price"]).toFixed(2)}</strong><br/>
          Change: ${quote["10. change percent"]}
        `;
      } else {
        resultDiv.textContent = "No data found. Check the symbol.";
      }
    })
    .catch((error) => {
      resultDiv.textContent = "Error fetching data.";
      console.error(error);
    });
}

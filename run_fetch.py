from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import json
import time

options = Options()
options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")

driver = webdriver.Chrome(service=Service(), options=options)

try:
    print("🌐 Підключено до відкритого Chrome. Переходимо на сторінку...")
    driver.get("http://www.amerxmocs.com/Default.aspx?index=")
    time.sleep(10)

    html = driver.page_source
    with open("debug_page.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("✅ Збережено debug_page.html")

    soup = BeautifulSoup(html, "lxml")

    def extract_table(table_id):
        table = soup.find("table", id=table_id)
        if not table:
            return []

        rows = table.find_all("tr")
        data = []
        for row in rows:
            cols = row.find_all(["td", "th"])
            data.append([col.get_text(strip=True) for col in cols if col.get_text(strip=True)])
        return data

    buy_data = extract_table("MainContent_BuyTable")
    sell_data = extract_table("MainContent_SellTable")

    with open("buy_data.json", "w", encoding="utf-8") as f:
        json.dump(buy_data, f, ensure_ascii=False, indent=2)
    with open("sell_data.json", "w", encoding="utf-8") as f:
        json.dump(sell_data, f, ensure_ascii=False, indent=2)

    print(f"✅ Збережено: {len(buy_data)} рядків Buy / {len(sell_data)} рядків Sell")

finally:
    input("🧹 Натисни Enter, щоб завершити...")
    driver.quit()
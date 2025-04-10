from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import json
import time

options = Options()
options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")

driver = webdriver.Chrome(service=Service(), options=options)

try:
    print("🌐 Підключено до відкритого Chrome. Переходимо на сторінку...")
    driver.get("http://www.amerxmocs.com/Default.aspx?index=")
    time.sleep(15)

    driver.save_screenshot("4_table_loaded.png")

    html = driver.page_source
    with open("debug_page.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("✅ Збережено debug_page.html")

    soup = BeautifulSoup(html, "lxml")
    tables = soup.find_all("table")
    print(f"📊 Знайдено таблиць: {len(tables)}")

    if len(tables) >= 2:
        def parse_table(table):
            return [
                [td.get_text(strip=True) for td in tr.find_all(["th", "td"])]
                for tr in table.find_all("tr")
                if tr.find_all(["th", "td"])
            ]

        buy_data = parse_table(tables[0])
        sell_data = parse_table(tables[1])

        with open("buy_data.json", "w", encoding="utf-8") as f:
            json.dump(buy_data, f, ensure_ascii=False, indent=2)
        with open("sell_data.json", "w", encoding="utf-8") as f:
            json.dump(sell_data, f, ensure_ascii=False, indent=2)

        print(f"✅ Дані збережено: {len(buy_data)} buy / {len(sell_data)} sell")
    else:
        print("⚠️ Таблиці не знайдено.")

finally:
    input("🧹 Натисни Enter, щоб завершити...")
    driver.quit()
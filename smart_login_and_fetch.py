import os
import time
import json
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import subprocess
import requests
from datetime import datetime

load_dotenv()
USERNAME = os.getenv("LOGIN")
PASSWORD = os.getenv("PASSWORD")

chrome_options = Options()
chrome_options.add_argument("--remote-debugging-port=9222")
chrome_options.add_argument(f"--user-data-dir={os.path.expanduser('~')}/chrome-selenium")
chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")

def git_commit_and_push():
    try:
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", "🔄 Автооновлення imbalance даних"], check=True)
        subprocess.run(["git", "push"], check=True)
        print("✅ Зміни запушено на GitHub.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Змін нема або Git помилка: {e}")

def extract_table(table, imbalance_type):
    headers = ["Update Time", "Symbol", "Imbalance","Paired", "ADV", "% ImbADV"]
    rows = [headers]
    if table:
        header_row = [th.get_text(strip=True) for th in table.find_all("tr")[0].find_all("th")]
        try:
            time_idx = header_row.index("Update Time")
            symbol_idx = header_row.index("Symbol")
            imbalance_idx = header_row.index(f"{imbalance_type} Imbalance")
            paired_idx = header_row.index("Paired")
        except ValueError:
            return rows
        for row in table.find_all("tr")[1:]:
            cells = [td.get_text(strip=True) for td in row.find_all("td")]
            if not cells or "TOTAL" in cells or len(cells) <= imbalance_idx:
                continue
            symbol = cells[symbol_idx]
            paired = cells[paired_idx]
            imbalance = cells[imbalance_idx].replace(",", "")
            update_time = cells[time_idx]
            rows.append([update_time, symbol, imbalance, paired, "", ""])
    return rows

# Завантаження Finviz
def get_adv_from_finviz(symbol, cache):
    if symbol in cache:
        return cache[symbol]
    try:
        url = f"https://finviz.com/quote.ashx?t={symbol}&p=d"  
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        table = soup.find("table", class_="snapshot-table2")
        for row in table.find_all("tr"):
            cells = row.find_all("td")
            for i in range(len(cells)):
                if cells[i].text.strip() == "Volume":
                    volume_str = cells[i+1].text.strip().replace(",", "")
                    if volume_str.endswith("M"):
                        adv = int(float(volume_str[:-1]) * 1_000_000)
                    elif volume_str.endswith("K"):
                        adv = int(float(volume_str[:-1]) * 1_000)
                    else:
                        adv = int(volume_str)
                    cache[symbol] = adv
                    return adv
    except Exception as e:
        print(f"⚠️ Не вдалося отримати ADV для {symbol}: {e}")
    cache[symbol] = 0
    return 0

try:
    driver = webdriver.Chrome(service=Service(), options=chrome_options)
    print("🔐 Перевіряємо статус сесії...")
    driver.get("http://www.amerxmocs.com/Default.aspx?index=")
    time.sleep(3)

    if "Account/Login.aspx" in driver.current_url:
        print("🔓 Сесія неактивна. Виконуємо логін...")
        driver.get("http://www.amerxmocs.com/Account/Login.aspx")
        time.sleep(2)
        driver.find_element(By.ID, "MainContent_UserName").send_keys(USERNAME)
        driver.find_element(By.ID, "MainContent_Password").send_keys(PASSWORD)
        driver.find_element(By.ID, "MainContent_LoginButton").click()
        time.sleep(3)
        if "Account/Login.aspx" in driver.current_url:
            print("❌ Логін не вдалось виконати.")
            exit(1)
    else:
        print("✅ Вже залогінені.")
except Exception as e:
    print(f"❌ Помилка: {e}")
    exit(1)

while True:
    html = driver.page_source
    with open("debug_page.html", "w", encoding="utf-8") as f:
        f.write(html)

    soup = BeautifulSoup(html, "html.parser")
    buy_table = soup.find("table", {"id": "MainContent_BuyTable"})
    sell_table = soup.find("table", {"id": "MainContent_SellTable"})

    buy_data = extract_table(buy_table, "Buy")
    sell_data = extract_table(sell_table, "Sell")

    # Завантаження кешу
    adv_cache = {}
    if os.path.exists("adv_cache.json"):
        with open("adv_cache.json") as f:
            adv_cache = json.load(f)

    # Обчислення %ImbADV
    def enrich_data(data):
        for i in range(1, len(data)):
            symbol = data[i][1]
            imbalance = float(data[i][2]) if data[i][2] else 0
            adv = get_adv_from_finviz(symbol, adv_cache)
            data[i][3] = str(adv)
            data[i][4] = f"{(imbalance / adv * 100):.1f}" if adv else "0"
        return data

    buy_data = enrich_data(buy_data)
    sell_data = enrich_data(sell_data)

    # Зберігаємо кеш
    with open("adv_cache.json", "w") as f:
        json.dump(adv_cache, f, indent=2)

    # Запис результатів
    with open("buy_data.json", "w") as f:
        json.dump(buy_data, f, indent=2)
    with open("sell_data.json", "w") as f:
        json.dump(sell_data, f, indent=2)

    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ✅ Скрипт завершено. Buy: {len(buy_data)-1}, Sell: {len(sell_data)-1}")
    git_commit_and_push()
    time.sleep(300)
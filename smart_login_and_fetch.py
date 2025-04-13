import os
import time
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import subprocess
import json

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
        print(f"❌ Змін нема: {e}")

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

def extract_table(table, imbalance_type):
    rows = []
    if not table:
        return rows

    header_cells = table.find_all("tr")[0].find_all("td")
    raw_headers = [cell.get_text(strip=True) for cell in header_cells]
    included_indices = [i for i, h in enumerate(raw_headers) if "#" not in h]

    rows.append(["Update Time", "Symbol", "Buy Imbalance", "Sell Imbalance", "ADV", "% ImbADV"])

    for row in table.find_all("tr")[1:]:
        cols = [td.get_text(strip=True) for td in row.find_all("td")]

        if not cols or len(cols) < 3:
            continue

        # Пропустити рядки, де перша колонка починається з #
        if cols[0].strip().startswith("#"):
            continue

        # Пропустити рядки, де символ у другій колонці — TOTAL
        if len(cols) > 1 and cols[1].strip().upper() == "TOTAL":
            continue

        filtered = [cols[i] for i in included_indices if i < len(cols)]

        update_time = filtered[0] if len(filtered) > 0 else ""
        symbol = filtered[1].split()[0] if len(filtered) > 1 else ""
        imbalance = filtered[2] if len(filtered) > 2 else ""

        if imbalance_type == "Buy":
            rows.append([update_time, symbol, imbalance, "", "", ""])
        else:
            rows.append([update_time, symbol, "", imbalance, "", ""])

    return rows

while True:
    html = driver.page_source
    with open("debug_page.html", "w", encoding="utf-8") as f:
        f.write(html)

    soup = BeautifulSoup(html, "html.parser")
    buy_table = soup.find("table", {"id": "MainContent_BuyTable"})
    sell_table = soup.find("table", {"id": "MainContent_SellTable"})

    buy_data = extract_table(buy_table, "Buy")
    sell_data = extract_table(sell_table, "Sell")

    with open("buy_data.json", "w") as f:
        json.dump(buy_data, f, indent=2)
    with open("sell_data.json", "w") as f:
        json.dump(sell_data, f, indent=2)

    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Скрипт запущено успішно. Buy: {len(buy_data)}, Sell: {len(sell_data)}")

    git_commit_and_push()

    time.sleep(300)

import os
import time
from datetime import datetime
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
        print(f"❌ Змін нема або Git помилка: {e}")

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

def parse_table(table):
    rows = [["Time", "Symbol", "Imbalance", "ADV", "% ImbADV"]]
    now = datetime.now().strftime("%H:%M")
    if table:
        for row in table.find_all("tr")[1:]:
            cols = row.find_all("td")
            text_cols = [td.get_text(strip=True) for td in cols]
            if not text_cols or text_cols[0].startswith("#"):
                continue
            try:
                symbol = cols[2].get_text(strip=True).split()[0]
                imbalance = cols[6].get_text(strip=True)
                rows.append([now, symbol, imbalance, "", ""])
            except Exception:
                continue
    return rows

while True:
    html = driver.page_source
    with open("debug_page.html", "w", encoding="utf-8") as f:
        f.write(html)

    soup = BeautifulSoup(html, "html.parser")
    buy_table = soup.find("table", {"id": "MainContent_BuyTable"})
    sell_table = soup.find("table", {"id": "MainContent_SellTable"})

    buy_data = parse_table(buy_table)
    sell_data = parse_table(sell_table)

    with open("buy_data.json", "w") as f:
        json.dump(buy_data, f, indent=2)
    with open("sell_data.json", "w") as f:
        json.dump(sell_data, f, indent=2)

    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Скрипт запущено успішно. Buy: {len(buy_data)-1}, Sell: {len(sell_data)-1}")
    git_commit_and_push()
    time.sleep(300)
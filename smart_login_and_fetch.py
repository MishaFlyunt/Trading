import os
import time
import json
import pytz
import subprocess
from datetime import datetime, time as dtime
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

manual_run = os.getenv("MANUAL_RUN", "false").lower() == "true"

if not os.path.exists(".env"):
    print("❌ Файл .env не знайдено. Завершення.")
    exit(1)

load_dotenv()

GITHUB_USERNAME = os.getenv("GITHUB_USERNAME")
GITHUB_REPO = os.getenv("GITHUB_REPO")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REMOTE = f"https://{GITHUB_USERNAME}:{GITHUB_TOKEN}@github.com/{GITHUB_USERNAME}/{GITHUB_REPO}.git"

NY_TZ = pytz.timezone("America/New_York")
now = datetime.now(NY_TZ)
start_time = dtime(13, 30)
end_time = dtime(16, 0)

if not manual_run and not (start_time <= now.time() <= end_time):
    print(f"🌙 Зараз {now.time().strftime('%H:%M:%S')} NY — поза годинами автооновлення. Завершення.")
    exit(0)

chrome_options = Options()
chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")

logged_in = False
driver = None

def save_log(buy, sell):
    with open("last_run.log", "w") as f:
        line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Скрипт запущено успішно. Buy: {len(buy)}, Sell: {len(sell)}"
        print(line)
        f.write(line + "\n")

def git_commit_and_push():
    subprocess.run(["git", "fetch", "origin"])
    subprocess.run(["git", "reset", "--hard", "origin/main"])
    subprocess.run(["git", "add", "buy_data.json", "sell_data.json", "last_run.log"], check=True)
    subprocess.run(["git", "commit", "-m", "🔄 Автооновлення imbalance даних"], check=False)
    subprocess.run(["git", "push", GITHUB_REMOTE], check=True)

def parse_table(soup, table_id):
    data = []
    table = soup.find("table", {"id": table_id})
    if not table:
        return data
    rows = table.find_all("tr")[1:]
    for row in rows:
        cells = [td.text.strip() for td in row.find_all("td")]
        if len(cells) >= 7 and cells[0] != "#":
            data.append({
                "time": cells[1],
                "symbol": cells[2],
                "imbalance": cells[3],
                "paired": cells[4],
                "value": cells[5],
                "adv": cells[6]
            })
    return data

try:
    print("🔐 Перевіряємо статус сесії...")
    driver = webdriver.Chrome(service=Service(), options=chrome_options)
    driver.get("http://www.amerxmocs.com/Default.aspx?index=")
    time.sleep(3)
    if "Welcome" not in driver.page_source:
        print("🔓 Сесія неактивна. Виконуємо логін...")
        driver.get("http://www.amerxmocs.com/Account/Login.aspx")
        time.sleep(2)
        driver.find_element(By.ID, "MainContent_UserName").send_keys("mkotsko")
        driver.find_element(By.ID, "MainContent_Password").send_keys("Xzw184hcL!")
        driver.find_element(By.ID, "MainContent_LoginButton").click()
        time.sleep(3)
        logged_in = True
    else:
        print("✅ Сесія активна.")
        logged_in = True

    print("📄 Завантажуємо таблиці...")
    time.sleep(3)
    with open("debug_page.html", "w", encoding="utf-8") as f:
        f.write(driver.page_source)
    print("✅ Збережено debug_page.html")

    soup = BeautifulSoup(driver.page_source, "lxml")
    buy_data = parse_table(soup, "MainContent_BuyTable")
    sell_data = parse_table(soup, "MainContent_SellTable")

    with open("buy_data.json", "w") as f:
        json.dump(buy_data, f, indent=2)
    with open("sell_data.json", "w") as f:
        json.dump(sell_data, f, indent=2)

    save_log(buy_data, sell_data)
    print("\n🚀 Пушимо зміни на GitHub...")
    git_commit_and_push()

finally:
    if not logged_in:
        if driver:
            driver.quit()
    else:
        print("⚠️ Ви увійшли у сесію. Chrome НЕ буде закрито, щоб уникнути втрати сесії.")

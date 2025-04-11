import os
import time
import subprocess
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from pytz import timezone
from datetime import datetime
import json

def is_ny_time_active():
    ny = timezone("America/New_York")
    now = datetime.now(ny)
    start = now.replace(hour=13, minute=30, second=0, microsecond=0)
    end = now.replace(hour=16, minute=0, microsecond=0)
    return start <= now <= end

def wait_for_chrome():
    for _ in range(30):
        try:
            r = requests.get("http://localhost:9222/json/version")
            if r.status_code == 200:
                return True
        except:
            pass
        time.sleep(1)
    return False

def git_commit_and_push():
    remote_url = os.getenv("GIT_REMOTE_URL")
    if not remote_url:
        print("❌ Не задано GIT_REMOTE_URL в .env")
        return
    subprocess.run(["git", "add", "."], check=True)
    subprocess.run(["git", "commit", "-m", "🔄 Автооновлення imbalance даних"], check=False)
    subprocess.run(["git", "pull", "--rebase"], check=False)
    subprocess.run(["git", "push", remote_url], check=False)

def try_login(driver):
    driver.get("http://www.amerxmocs.com/Account/Login.aspx")
    time.sleep(2)
    if "Log Out" in driver.page_source:
        print("✅ Уже залогінено.")
        return True
    try:
        driver.find_element(By.ID, "MainContent_UserName").send_keys(os.getenv("LOGIN"))
        driver.find_element(By.ID, "MainContent_Password").send_keys(os.getenv("PASSWORD"))
        driver.find_element(By.ID, "MainContent_LoginButton").click()
        time.sleep(2)
        if "Welcome" in driver.page_source:
            print("✅ Логін успішний.")
            return True
    except Exception as e:
        print("❌ Логін не вдалось виконати:", e)
    return False

print("🔐 Перевіряємо статус сесії...")

if not wait_for_chrome():
    print("❌ Chrome не запущено з --remote-debugging-port=9222")
    exit(1)

options = Options()
options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
driver = webdriver.Chrome(service=Service(), options=options)

if not try_login(driver):
    print("❌ Логін не пройдено. Завершення.")
    driver.quit()
    exit(1)

print("📄 Завантажуємо таблиці...")
driver.get("http://www.amerxmocs.com/Default.aspx?index=")
time.sleep(2)
html = driver.page_source

with open("debug_page.html", "w", encoding="utf-8") as f:
    f.write(html)
print("✅ Збережено debug_page.html")

soup = BeautifulSoup(html, "lxml")

def extract_table(table):
    rows = []
    for tr in table.find_all("tr"):
        cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
        if cells and cells[0] != "#":
            rows.append(cells)
    return rows

buy_table = soup.find("table", id="MainContent_BuyTable")
sell_table = soup.find("table", id="MainContent_SellTable")

buy_data = extract_table(buy_table) if buy_table else []
sell_data = extract_table(sell_table) if sell_table else []

with open("buy_data.json", "w") as f:
    json.dump(buy_data, f, indent=2)
with open("sell_data.json", "w") as f:
    json.dump(sell_data, f, indent=2)

log_line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Скрипт запущено успішно. Buy: {len(buy_data)}, Sell: {len(sell_data)}\n"
print(log_line.strip())
with open("last_run.log", "a") as f:
    f.write(log_line)

if os.getenv("MANUAL_RUN") == "true" or is_ny_time_active():
    print("🚀 Пушимо зміни на GitHub...")
    git_commit_and_push()

if os.getenv("MANUAL_RUN") != "true":
    driver.quit()
    print("🧹 Завершено. Chrome закрито.")
else:
    print("⚠️ Ви увійшли у сесію. Chrome НЕ буде закрито, щоб уникнути втрати сесії.")
    input("🧹 Натисни Enter, щоб завершити...")
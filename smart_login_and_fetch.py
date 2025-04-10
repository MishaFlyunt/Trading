import os
import time
import json
import subprocess
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
from dotenv import load_dotenv

from pytz import timezone

env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path=env_path)

def is_logged_in(driver):
    driver.get("http://www.amerxmocs.com/Default.aspx?index=")
    time.sleep(3)
    return "Welcome" in driver.page_source

def perform_login(driver):
    driver.get("http://www.amerxmocs.com/Account/Login.aspx")
    time.sleep(2)
    driver.find_element(By.ID, "MainContent_UserName").send_keys("mkotsko")
    driver.find_element(By.ID, "MainContent_Password").send_keys("Xzw184hcL!")
    driver.find_element(By.ID, "MainContent_LoginButton").click()
    time.sleep(5)

def extract_table(soup, table_id):
    table = soup.find("table", id=table_id)
    if not table:
        return []
    rows = table.find_all("tr")
    data = []
    for row in rows:
        cols = row.find_all(["td", "th"])
        clean_row = [col.get_text(strip=True) for col in cols if col.get_text(strip=True) != "#"]
        if clean_row:
            data.append(clean_row)
    return data

def git_commit_and_push():
    repo = os.getenv("GITHUB_REPO")
    username = os.getenv("GITHUB_USERNAME")
    token = os.getenv("GITHUB_TOKEN")
    remote_url = f"https://{username}:{token}@github.com/{username}/{repo}.git"

    subprocess.run(["git", "config", "--global", "user.email", "bot@example.com"])
    subprocess.run(["git", "config", "--global", "user.name", "AutoBot"])
    subprocess.run(["git", "add", "-A"])
    subprocess.run(["git", "commit", "-m", "🔄 Автооновлення imbalance даних"])
    subprocess.run(["git", "pull", "--rebase"])
    subprocess.run(["git", "push", remote_url], check=True)

options = Options()
options.add_argument("--start-maximized")
driver = webdriver.Chrome(service=Service(), options=options)

logged_in = False

try:
    print("🔐 Перевіряємо статус сесії...")
    if not is_logged_in(driver):
        print("🔓 Сесія неактивна. Виконуємо логін...")
        perform_login(driver)
        logged_in = True
    else:
        print("✅ Сесія активна. Переходимо до таблиць...")

    driver.get("http://www.amerxmocs.com/Default.aspx?index=")
    print("📄 Завантажуємо таблиці...")
    time.sleep(8)

    html = driver.page_source
    with open("debug_page.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("✅ Збережено debug_page.html")

    soup = BeautifulSoup(html, "lxml")
    buy_data = extract_table(soup, "MainContent_BuyTable")
    sell_data = extract_table(soup, "MainContent_SellTable")

    with open("buy_data.json", "w", encoding="utf-8") as f:
        json.dump(buy_data, f, ensure_ascii=False, indent=2)
    with open("sell_data.json", "w", encoding="utf-8") as f:
        json.dump(sell_data, f, ensure_ascii=False, indent=2)

    log_line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Скрипт запущено успішно. Buy: {len(buy_data)}, Sell: {len(sell_data)}\n"
    print(log_line)
    with open("last_run.log", "a", encoding="utf-8") as log_file:
        log_file.write(log_line)

    print("🚀 Пушимо зміни на GitHub...")
    git_commit_and_push()
    print("✅ Успішно запушено в GitHub!")

    # Автоматичний log out о 23:00 Київського часу
    kyiv_time = datetime.now(timezone('Europe/Kyiv'))
    if kyiv_time.hour == 23:
        try:
            print("🚪 Вихід із системи (Log Out)...")
            logout_link = driver.find_element(By.ID, "MainContent_LogOut")
            logout_link.click()
            time.sleep(2)
        except Exception as e:
            print("⚠️ Не вдалося натиснути Log Out:", e)

finally:
    if logged_in:
        print("⚠️ Ви увійшли у сесію. Chrome НЕ буде закрито, щоб уникнути втрати сесії.")
    else:
        print("🧹 Завершуємо через 3 секунди...")
        time.sleep(3)
        driver.quit()
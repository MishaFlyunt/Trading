
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
from collections import defaultdict

load_dotenv()
USERNAME = os.getenv("LOGIN")
PASSWORD = os.getenv("PASSWORD")

chrome_options = Options()
chrome_options.add_argument("--remote-debugging-port=9222")
chrome_options.add_argument(
    f"--user-data-dir={os.path.expanduser('~')}/chrome-selenium")
chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")


def git_commit_and_push():
    try:
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(
            ["git", "commit", "-m", "🔄 Автооновлення imbalance даних"], check=True)
        subprocess.run(["git", "push"], check=True)
        print("✅ Зміни запушено на GitHub.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Змін нема або Git помилка: {e}")


def parse_message_table(soup):
    table = soup.find("table", id="MainContent_MessageTable")
    if not table:
        print("❌ Таблиця MessageTable не знайдена")
        return {"main": [], "archive": {}}

    rows = table.find_all("tr")
    archive = defaultdict(lambda: [["Update Time", "Imbalance", "Paired"]])
    main = [["Update Time", "Symbol", "Imbalance", "Paired", "ADV", "% ImbADV"]]
    latest_seen = {}

    for row in rows[1:]:
        cells = [td.text.strip() for td in row.find_all("td")]
        if len(cells) < 5:
            continue
        time_val, symbol, side, imbalance, paired = cells
        imbalance = int(imbalance.replace(",", "") or 0)
        paired = int(paired.replace(",", "") or 0)

        archive[symbol].append([time_val, imbalance, paired])
        if symbol not in latest_seen:
            latest_seen[symbol] = (time_val, imbalance, paired)

    for symbol, (t, imb, paired) in latest_seen.items():
        main.append([t, symbol, imb, paired, "", ""])

    return {"main": main, "archive": dict(archive)}


def get_adv_from_finviz(symbol, cache):
    if symbol in cache:
        return cache[symbol]
    try:
        url = f"https://finviz.com/quote.ashx?t={symbol}&p=d"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        table = soup.find("table", class_="snapshot-table2")
        if not table:
            raise ValueError("Snapshot table not found")

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
    print("✅ Вже залогінені або логін виконано успішно.")

    html = driver.page_source
    with open("debug_page.html", "w", encoding="utf-8") as f:
        f.write(html)

    soup = BeautifulSoup(html, "html.parser")

    # Парсимо дані
    full_data = parse_message_table(soup)

    # Завантаження кешу
    adv_cache = {}
    if os.path.exists("adv_cache.json"):
        try:
            with open("adv_cache.json") as f:
                adv_cache = json.load(f)
            if not isinstance(adv_cache, dict):
                print("⚠️ Файл кешу не є словником. Створено новий пустий кеш.")
                adv_cache = {}
        except Exception as e:
            print(f"⚠️ Не вдалося завантажити кеш: {e}")
            adv_cache = {}

    # Обчислення ADV і %ImbADV
    for i in range(1, len(full_data["main"])):
        row = full_data["main"][i]
        symbol = row[1]
        imbalance = float(row[2])
        adv = get_adv_from_finviz(symbol, adv_cache)
        row[4] = str(adv)
        row[5] = f"{(imbalance / adv * 100):.1f}" if adv else "0"

    # Зберігаємо кеш
    with open("adv_cache.json", "w") as f:
        json.dump(adv_cache, f, indent=2)

    # Розділяємо buy/sell
    buy_main = [full_data["main"][0]]
    sell_main = [full_data["main"][0]]
    for row in full_data["main"][1:]:
        symbol = row[1]
        if symbol in full_data["archive"]:
            last_archive = full_data["archive"][symbol]
            if any("Sell" in str(val) for val in row):
                sell_main.append(row)
            else:
                buy_main.append(row)

    # Запис результатів
    with open("buy_data.json", "w") as f:
        json.dump(
            {"main": buy_main, "archive": full_data["archive"]}, f, indent=2)
    with open("sell_data.json", "w") as f:
        json.dump(
            {"main": sell_main, "archive": full_data["archive"]}, f, indent=2)

    print("✅ Дані збережено у buy_data.json та sell_data.json")
    git_commit_and_push()

except Exception as e:
    print(f"❌ Помилка при виконанні: {e}")

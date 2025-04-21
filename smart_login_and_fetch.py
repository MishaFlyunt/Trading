import os
import time
import json
import requests
import math
import psutil
import sys
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import subprocess
import telegram
import asyncio
from collections import defaultdict
from datetime import datetime

load_dotenv()

def is_chrome_running_with_debugging():
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if 'Google Chrome' in proc.info['name'] and '--remote-debugging-port=9222' in ' '.join(proc.info['cmdline']):
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return False

USERNAME = os.getenv("LOGIN")
PASSWORD = os.getenv("PASSWORD")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

bot = telegram.Bot(token=TELEGRAM_TOKEN)

if not is_chrome_running_with_debugging():
    print("🧭 Chrome не запущено з remote-debugging. Запускаємо...")
    chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    user_data_dir = os.path.expanduser("~/chrome-selenium")
    target_url = "http://www.amerxmocs.com/Default.aspx?index="

    subprocess.Popen([
        chrome_path,
        "--remote-debugging-port=9222",
        f"--user-data-dir={user_data_dir}",
        "--new-window",
        target_url
    ])
    time.sleep(5)  # зачекати, поки вкладка відкриється
else:
    print("🟢 Chrome вже працює з remote-debugging.")

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


def get_adv_from_finviz(symbol, cache):
    if symbol in cache:
        return cache[symbol]
    try:
        url = f"https://finviz.com/quote.ashx?t={symbol}&p=d"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Accept-Language": "en-US,en;q=0.9",
        }
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            print(f"⚠️ Finviz статус {response.status_code} для {symbol}")
            cache[symbol] = 0
            return 0
        soup = BeautifulSoup(response.text, "html.parser")
        table = soup.find("table", class_="snapshot-table2")
        if not table:
            print(f"⚠️ Таблиця не знайдена для {symbol}")
            cache[symbol] = 0
            return 0
        for row in table.find_all("tr"):
            cells = row.find_all("td")
            for i in range(len(cells)):
                if cells[i].text.strip() == "Avg Volume":
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


def parse_table_from_message_table(soup):
    table = soup.find("table", id="MainContent_MessageTable")
    if not table:
        print("❌ Таблиця MessageTable не знайдена. Можливо, сесія неактивна або логін не пройшов.")
        sys.exit(1)

    rows = table.find_all("tr")
    archive_buy = defaultdict(lambda: [["Update Time", "Imbalance", "Paired"]])
    archive_sell = defaultdict(
        lambda: [["Update Time", "Imbalance", "Paired"]])
    main_buy = [["Update Time", "Symbol",
                 "Imbalance", "Paired", "ADV", "% ImbADV"]]
    main_sell = [["Update Time", "Symbol",
                  "Imbalance", "Paired", "ADV", "% ImbADV"]]
    latest_buy = {}
    latest_sell = {}

    latest_buy.clear()
    latest_sell.clear()

    for row in rows[1:]:
        cells = row.find_all("td")
        if len(cells) < 5:
            continue

        time_val = cells[0].text.strip()
        symbol_tag = cells[1].find("a")
        symbol = symbol_tag.text.strip(
        ) if symbol_tag else cells[1].text.strip()
        side = cells[2].text.strip()
        imbalance = int(cells[3].text.strip().replace(
            ",", "")) if cells[3].text.strip() else 0
        paired = int(cells[4].text.strip().replace(
            ",", "")) if cells[4].text.strip() else 0

        target_latest = latest_buy if side == "B" else latest_sell
        target_archive = archive_buy if side == "B" else archive_sell

        target_archive[symbol].append([time_val, imbalance, paired])
        target_latest[symbol] = (time_val, imbalance, paired)

    for symbol, (t, imb, paired) in latest_buy.items():
        main_buy.append([t, symbol, imb, paired, "", ""])
    for symbol, (t, imb, paired) in latest_sell.items():
        main_sell.append([t, symbol, imb, paired, "", ""])

    return {
        "buy": {"main": main_buy, "archive": dict(archive_buy)},
        "sell": {"main": main_sell, "archive": dict(archive_sell)},
    }


async def send_telegram_message(message):
    try:
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        print("📨 Надіслано сповіщення у Telegram")
    except Exception as e:
        print(f"❌ Помилка надсилання в Telegram: {e}")

        # ✅ ТЕСТОВЕ ПОВІДОМЛЕННЯ
# if __name__ == "__main__":
#     asyncio.run(send_telegram_message(
#         "🔔 Тестове повідомлення: перевірка Telegram бота"))


async def main():
    try:
        driver = webdriver.Chrome(service=Service(), options=chrome_options)
        print("🔐 Перевіряємо статус сесії...")
        driver.get("http://www.amerxmocs.com/Default.aspx?index=")
        time.sleep(3)
        if "Account/Login.aspx" in driver.current_url:
            print("🔓 Сесія неактивна. Виконуємо логін...")
            driver.get("http://www.amerxmocs.com/Account/Login.aspx")
            time.sleep(2)
            driver.find_element(
                By.ID, "MainContent_UserName").send_keys(USERNAME)
            driver.find_element(
                By.ID, "MainContent_Password").send_keys(PASSWORD)
            driver.find_element(By.ID, "MainContent_LoginButton").click()
            time.sleep(3)
    except Exception as e:
        print(f"❌ Помилка: {e}")
        return

    while True:
        html = driver.page_source
        with open("debug_page.html", "w", encoding="utf-8") as f:
            f.write(html)

        soup = BeautifulSoup(html, "html.parser")
        parsed = parse_table_from_message_table(soup)

        adv_cache = {}
        try:
            if os.path.exists("adv_cache.json"):
                with open("adv_cache.json") as f:
                    adv_cache = json.load(f)
                if not isinstance(adv_cache, dict):
                    print("⚠️ Файл кешу не є словником. Створено новий пустий кеш.")
                    adv_cache = {}
        except Exception as e:
            print(f"⚠️ Не вдалося завантажити кеш: {e}")
            adv_cache = {}

        for kind in ("buy", "sell"):
            data = parsed[kind]
            for i in range(1, len(data["main"])):
                row = data["main"][i]
                symbol = row[1]
                imbalance = float(row[2])
                adv = get_adv_from_finviz(symbol, adv_cache)
                row[4] = str(adv)
                row[5] = str(math.ceil(imbalance / adv * 100)) if adv else "0"

            with open(f"{kind}_data.json", "w") as f:
                json.dump(data, f, indent=2)

            prev_file = f"prev_{kind}.json"
            # prev_symbols = {}
            # if os.path.exists(prev_file):
            #     try:
            #         with open(prev_file) as f:
            #             prev_data = json.load(f)
            #             prev_symbols = {row[1]: True for row in prev_data.get("main", [])[
            #                 1:]}
            #     except Exception:
            #         prev_symbols = {}

            for row in data["main"][1:]:
                symbol = row[1]
                imbalance = int(row[2])
                adv = int(row[4])
                percent = int(row[5])

                if percent > 95:
                    side = "BUY" if kind == "buy" else "SELL"
                    msg = f"🔥 {side} | {symbol}\nImbalance: {imbalance:,}\nADV: {adv:,}\n% ImbADV: {percent}%"
                    await send_telegram_message(msg)

                opposite_kind = "sell" if kind == "buy" else "buy"
                opposite_prev_file = f"prev_{opposite_kind}.json"
                opposite_prev_symbols = {}
                if os.path.exists(opposite_prev_file):
                    try:
                        with open(opposite_prev_file) as f:
                            opp_data = json.load(f)
                            opposite_prev_symbols = {row[1]: True for row in opp_data.get("main", [])[
                                1:]}
                    except Exception:
                        opposite_prev_symbols = {}

                if percent > 90 and symbol in opposite_prev_symbols:
                    direction = "BUY → SELL" if kind == "sell" else "SELL → BUY"
                    msg = f"🔄 {direction} | {symbol}\nImbalance: {imbalance:,}\nADV: {adv:,}\n% ImbADV: {percent}%"
                    await send_telegram_message(msg)

            with open(prev_file, "w") as f:
                json.dump(data, f, indent=2)

        with open("adv_cache.json", "w") as f:
            json.dump(adv_cache, f, indent=2)

        print("✅ Дані збережено у buy_data.json та sell_data.json")
        git_commit_and_push()

        now = datetime.now()
        if now.hour == 23:
            print("🛑 Завершення скрипта о 23:00")
        # 🔧 Викликаємо reset_data.sh через subprocess
            reset_script = "/Users/mihajloflunt/Desktop/Home/Навчання/GOIT/Trading/reset_data.sh"
            if os.path.exists(reset_script):
                try:
                    print("🚀 Запускаємо reset_data.sh...")
                    subprocess.run(["/bin/bash", reset_script], check=True)
                    print("✅ reset_data.sh виконано успішно.")
                except subprocess.CalledProcessError as e:
                    print(f"❌ Помилка виконання reset_data.sh: {e}")
            else:
                print("❌ Файл reset_data.sh не знайдено!")

            break
        time.sleep(40)

if __name__ == "__main__":
    asyncio.run(main())

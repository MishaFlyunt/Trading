import os
import time
import json
import requests
import math
import psutil
import random
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
from datetime import datetime, timedelta

# -----Функція перевірки коли були зміни по ADV------
def is_adv_outdated(date_str, max_age_days=10):
    try:
        adv_date = datetime.strptime(date_str, "%Y-%m-%d")
        return datetime.now() - adv_date > timedelta(days=max_age_days)
    except Exception:
        return True

load_dotenv()

# ----------Автозапуск ГуглХром--------
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
    # Додаємо перевірку протягом 20 секунд
    for _ in range(20):
        if is_chrome_running_with_debugging():
            break
        time.sleep(1)
    else:
        print("❌ Chrome не стартував вчасно!")
        exit(1)
else:
    print("🟢 Chrome вже працює з remote-debugging.")

chrome_options = Options()
chrome_options.add_argument("--remote-debugging-port=9222")
chrome_options.add_argument(f"--user-data-dir={os.path.expanduser('~')}/chrome-selenium")
chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")


# --------GIT PUSH---------
def git_commit_and_push():
    try:
        subprocess.run(["git", "add", "."], check=True)

        # Перевіряємо чи є що комітити
        result = subprocess.run(["git", "diff", "--cached", "--quiet"])
        if result.returncode == 0:
            print("ℹ️ Немає змін для коміту.")
            return

        subprocess.run(
            ["git", "commit", "-m", "🔄 Автооновлення imbalance даних"], check=True)
        subprocess.run(["git", "push"], check=True)
        print("✅ Зміни запушено на GitHub.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Git помилка: {e}")


# -----------Finviz--------
def get_adv_from_finviz(symbol, cache):
    if any(char in symbol for char in ['.', '-', ' ']):
        # print(f"⚠️ Символ {symbol} містить недопустимі символи. ADV = 0")
        cache[symbol] = {
            "adv": 0,
            "date": datetime.now().strftime("%Y-%m-%d")
        }
        return 0

    cache_entry = cache.get(symbol)
    if cache_entry and isinstance(cache_entry, dict):
        if not is_adv_outdated(cache_entry.get("date", ""), 10) and cache_entry.get("adv", 0) > 0:
            return cache_entry["adv"]

    # Інакше — парсимо Finviz
    try:
        url = f"https://finviz.com/quote.ashx?t={symbol}&p=d"
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept-Language": "en-US,en;q=0.9",
        }
        response = requests.get(url, headers=headers, timeout=15)
        time.sleep(random.uniform(1.5, 3.5))

        if response.status_code == 429:
            print(f"🚫 Finviz заблокував: 429 для {symbol}")
            return cache_entry["adv"] if cache_entry else 0

        if response.status_code != 200:
            print(f"⚠️ Finviz статус {response.status_code} для {symbol}")
            return 0

        soup = BeautifulSoup(response.text, "html.parser")
        table = soup.find("table", class_="snapshot-table2")
        if not table:
            print(f"⚠️ Таблиця не знайдена для {symbol}")
            return 0

        for row in table.find_all("tr"):
            cells = row.find_all("td")
            for i in range(len(cells)):
                if cells[i].text.strip() == "Avg Volume":
                   volume_str = cells[i+1].text.strip().replace(",", "")
                   try:
                       if volume_str.endswith("M"):
                           adv = int(float(volume_str[:-1]) * 1_000_000)
                       elif volume_str.endswith("K"):
                           adv = int(float(volume_str[:-1]) * 1_000)
                       else:
                           adv = int(volume_str)

                       cache[symbol] = {
                           "adv": adv,
                           "date": datetime.now().strftime("%Y-%m-%d")
                       }
                       return adv
                   except ValueError:
                       print(f"⚠️ Неможливо розпарсити обсяг для {symbol}: '{volume_str}'")
                       return 0
    except Exception as e:
        print(f"⚠️ Не вдалося отримати ADV для {symbol}: {e}")

    return 0

# -----------Парс сторінки---------


def parse_table_from_message_table(soup, driver):
    while True:
        table = soup.find("table", id="MainContent_MessageTable")
        if table:
            break
        print("🕒 Таблиця ще не доступна, повторна перевірка через 60 сек...")
        time.sleep(60)
        soup = BeautifulSoup(driver.page_source, "html.parser")

    rows = table.find_all("tr")
    archive_buy = defaultdict(lambda: [["Update Time", "Imbalance", "Paired"]])
    archive_sell = defaultdict(
        lambda: [["Update Time", "Imbalance", "Paired"]])
    latest_buy = {}
    latest_sell = {}

    active_symbols_buy = set()
    active_symbols_sell = set()

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

        # Додаємо до архіву завжди
        target_archive = archive_buy if side == "B" else archive_sell
        target_archive[symbol].append([time_val, imbalance, paired])

        # Запам'ятовуємо активні символи
        if side == "B":
            active_symbols_buy.add(symbol)
            # Зберігаємо лише найновіший запис
            if symbol not in latest_buy or time_val > latest_buy[symbol][0]:
                latest_buy[symbol] = (time_val, imbalance, paired)
        else:
            active_symbols_sell.add(symbol)
            if symbol not in latest_sell or time_val > latest_sell[symbol][0]:
                latest_sell[symbol] = (time_val, imbalance, paired)

    # 📚 Сортуємо архіви за часом для кожного символу
    for archive in (archive_buy, archive_sell):
        for symbol, records in archive.items():
            if len(records) > 1:
                header, *data_rows = records
                # сортуємо за часом
                sorted_rows = sorted(data_rows, key=lambda r: r[0])
                archive[symbol] = [header] + sorted_rows

    # Формуємо основні таблиці лише для символів, які є зараз на сторінці
    main_buy = [["Update Time", "Symbol",
                 "Imbalance", "Paired", "ADV", "% ImbADV"]]
    for symbol in active_symbols_buy:
        t, imb, paired = latest_buy[symbol]
        main_buy.append([t, symbol, imb, paired, "", ""])

    main_sell = [["Update Time", "Symbol",
                  "Imbalance", "Paired", "ADV", "% ImbADV"]]
    for symbol in active_symbols_sell:
        t, imb, paired = latest_sell[symbol]
        main_sell.append([t, symbol, imb, paired, "", ""])

    return {
        "buy": {"main": main_buy, "archive": dict(archive_buy)},
        "sell": {"main": main_sell, "archive": dict(archive_sell)}
    }
# ----------Телеграм повідомлення----------
async def send_telegram_message(message):
    try:
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        print("📨 Надіслано сповіщення у Telegram")
    except Exception as e:
        print(f"❌ Помилка надсилання в Telegram: {e}")


# ---------Перевірка чи логін не втрачений підчас сесії---------
def is_logged_in(driver):
    return "Account/Login.aspx" not in driver.current_url

async def perform_login(driver):
    print("🔓 Сесія неактивна. Виконуємо логін...")
    driver.get("http://www.amerxmocs.com/Account/Login.aspx")

    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    for attempt in range(20):
        try:
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.ID, "MainContent_UserName"))
            )
            driver.find_element(By.ID, "MainContent_UserName").clear()
            driver.find_element(
                By.ID, "MainContent_UserName").send_keys(USERNAME)
            driver.find_element(By.ID, "MainContent_Password").clear()
            driver.find_element(
                By.ID, "MainContent_Password").send_keys(PASSWORD)
            driver.find_element(By.ID, "MainContent_LoginButton").click()
            await asyncio.sleep(3)
            print("✅ Логін виконано або обробляється...")
            break
        except Exception:
            print(
                f"⏳ Логін ще недоступний ({attempt+1}/20). Повтор через 60 сек...")
            await asyncio.sleep(60)
    else:
        print("❌ Не вдалося залогінитись після 20 спроб. Вихід.")
        return False
    return True

# ---------Хром драйвер----------
async def start_driver_with_retry(max_retries=3):
    for attempt in range(1, max_retries + 1):
        try:
            driver = webdriver.Chrome(
                service=Service(), options=chrome_options)
            # Обмеження на завантаження сторінки
            driver.set_page_load_timeout(60)
            print(f"🟢 Драйвер успішно підключено на спробі {attempt}.")
            return driver
        except Exception as e:
            print(f"⚠️ Помилка підключення драйвера на спробі {attempt}: {e}")
            if attempt < max_retries:
                print("🔄 Повторна спроба через 10 секунд...")
                await asyncio.sleep(10)
            else:
                print("❌ Всі спроби вичерпані. Завершення скрипта.")
                raise e

# ---------Логін на сайті www.amerxmocs.com----------
async def main():
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    try:
        driver = await start_driver_with_retry()
        print("🔐 Перевіряємо статус сесії...")
        driver.get("http://www.amerxmocs.com/Default.aspx?index=")
        await asyncio.sleep(3)

        if "Account/Login.aspx" in driver.current_url:
            print("🔓 Сесія неактивна. Виконуємо логін...")
            driver.get("http://www.amerxmocs.com/Account/Login.aspx")

            for attempt in range(20):
                try:
                    WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located(
                            (By.ID, "MainContent_UserName"))
                    )
                    driver.find_element(By.ID, "MainContent_UserName").clear()
                    driver.find_element(
                        By.ID, "MainContent_UserName").send_keys(USERNAME)
                    driver.find_element(By.ID, "MainContent_Password").clear()
                    driver.find_element(
                        By.ID, "MainContent_Password").send_keys(PASSWORD)
                    driver.find_element(
                        By.ID, "MainContent_LoginButton").click()
                    await asyncio.sleep(3)
                    print("✅ Логін виконано або обробляється...")
                    break
                except Exception:
                    print(
                        f"⏳ Логін ще недоступний ({attempt+1}/20). Повтор через 60 сек...")
                    await asyncio.sleep(60)
            else:
                print("❌ Не вдалося залогінитись після 20 спроб. Вихід.")
                return
    except Exception as e:
        print(f"❌ Помилка ініціалізації драйвера або логіну: {e}")
        return

    while True:
        if not is_logged_in(driver):
             print("ℹ️ Перевірка сесії...")
             success = await perform_login(driver)
             if not success:
                 break
        html = driver.page_source
        with open("debug_page.html", "w", encoding="utf-8") as f:
            f.write(html)

        soup = BeautifulSoup(html, "html.parser")
        parsed = parse_table_from_message_table(soup, driver)

        adv_cache = {}
        if os.path.exists("adv_cache.json"):
            try:
                with open("adv_cache.json") as f:
                    adv_cache = json.load(f)
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
            last_sent_map = {}

            if os.path.exists(prev_file):
               try:
                   with open(prev_file) as f:
                       prev_data = json.load(f)
                       for prev_row in prev_data.get("main", [])[1:]:
                           symbol = prev_row[1]
                           val = prev_row[5]
                           if isinstance(val, int):
                               sent_percent = val
                           elif isinstance(val, str) and val.isdigit():
                               sent_percent = int(val)
                           else:
                               sent_percent = 0
                           last_sent_map[symbol] = sent_percent
               except Exception as e:
                    print(f"⚠️ Не вдалося зчитати {prev_file}: {e}")

            for row in data["main"][1:]:
                symbol = row[1]
                imbalance = int(row[2])
                paired = int(row[3]) if isinstance(row[3], str) and row[3].isdigit() else int(row[3]) if isinstance(row[3], int) else 0
                adv = int(row[4]) if row[4].isdigit() else 0
                percent = int(row[5]) if row[5].isdigit() else 0

                last_sent = last_sent_map.get(symbol, 0)
                if percent >= 95 and (last_sent == 0 or percent >= last_sent + 10):
                    print(f"{symbol}: now={percent}%, last={last_sent} → відправляємо")
                    if kind == "buy":
                        arrow = "🟢⬆️"
                        side = "Buy"
                    else:
                        arrow = "🔴⬇️"
                        side = "Sell"
                    msg = f"{arrow} {side}  |  {symbol}\nImbalance: {imbalance:,}\nPaired: {paired:,}\nADV: {adv:,}\n% ImbADV: {percent}%"

                    if last_sent > 0:
                        diff = percent - last_sent
                        msg += f" (+{diff}%)"
                    await send_telegram_message(msg)
                    last_sent_map[symbol] = percent

                opposite_kind = "sell" if kind == "buy" else "buy"
                opposite_prev_file = f"prev_{opposite_kind}.json"
                opposite_prev_symbols = {}
                if os.path.exists(opposite_prev_file):
                    try:
                        with open(opposite_prev_file) as f:
                            opp_data = json.load(f)
                            opposite_prev_symbols = {
                                r[1]: True for r in opp_data.get("main", [])[1:]
                            }
                    except Exception:
                        opposite_prev_symbols = {}

                # Aкції з ДЕФІСОМ
                dash_file = f"dash_notified_{kind}.json"
                notified_dash_symbols = set()
                if os.path.exists(dash_file):
                    try:
                        with open(dash_file) as f:
                            notified_dash_symbols = set(json.load(f))
                    except Exception as e:
                        print(f"⚠️ Не вдалося зчитати {dash_file}: {e}")
                
                if "-" in symbol and symbol not in notified_dash_symbols:
                    if kind == "buy":
                        arrow = "🟢⬆️"
                        side = "Buy"
                    else:
                        arrow = "🔴⬇️"
                        side = "Sell"
                    msg = f"{arrow} {side} ⚠️ДЕФІС  |  {symbol}\nImbalance: {imbalance:,}\nPaired: {paired:,}"
                    await send_telegram_message(msg)
                    notified_dash_symbols.add(symbol)

                with open(dash_file, "w") as f:
                     json.dump(list(notified_dash_symbols), f, indent=2)

                # Зміна сторони BUY ↔ SELL з унікальністю
                flip_file = f"flip_notified_{kind}.json"
                flip_notified = {}
                if os.path.exists(flip_file):
                    try:
                        with open(flip_file) as f:
                            flip_notified = json.load(f)
                    except Exception:
                        flip_notified = {}

                if percent > 80 and symbol in opposite_prev_symbols:
                    if not flip_notified.get(symbol):
                        direction = "🟢BUY → 🔴SELL" if kind == "sell" else "🔴SELL → 🟢BUY"
                        msg = f"🔄 Зміна сторони {direction}  |  {symbol}\nImbalance: {imbalance:,}\nPaired: {paired:,}\nADV: {adv:,}\n% ImbADV: {percent}%"
                        await send_telegram_message(msg)
                        flip_notified[symbol] = True

                with open(flip_file, "w") as f:
                   json.dump(flip_notified, f, indent=2)

            # 🔥 Формуємо нові prev_* тільки зі зміненими або актуальними акціями
            new_prev_main = [["Update Time", "Symbol","Imbalance", "Paired", "ADV", "% ImbADV"]]

            for row in data["main"][1:]:
                symbol = row[1]
                imbalance = int(row[2])
                paired = int(row[3]) if isinstance(row[3], str) and row[3].isdigit() else int(row[3]) if isinstance(row[3], int) else 0
                adv = int(row[4]) if isinstance(row[4], str) and row[4].isdigit() else int(
                row[4]) if isinstance(row[4], int) else 0
                percent = last_sent_map.get(symbol, 0)

                new_prev_main.append([row[0], symbol, imbalance, paired, adv, percent])

            prev_data = {
                 "main": new_prev_main,
                 "archive": {}
            }

            with open(prev_file, "w") as f:
                json.dump(prev_data, f, indent=2)

        with open("adv_cache.json", "w") as f:
            json.dump(adv_cache, f, indent=2)

        # 👉 Git Push в кінці скрипту
        print("✅ Дані збережено у buy_data.json та sell_data.json")
        git_commit_and_push()

        now = datetime.now()
        if now.hour == 23:
            print("🛑 Завершення скрипта о 23:00")

            # 👉 Розлогінення перед завершенням
            try:
                logout_btn = driver.find_element(By.ID, "MainContent_LogOut")
                logout_btn.click()
                print("🚪 Успішно розлогінено з сайту.")
            except Exception as e:
                print(f"⚠️ Не вдалося розлогінитися: {e}")

            # 👉 Запуск reset_data
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

        await asyncio.sleep(30)

if __name__ == "__main__":
    asyncio.run(main())
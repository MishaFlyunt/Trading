# v3: improved Google Finance parser with exact label check for Avg volume
import re
import os
import time
import json
import requests
import math
try:
    import psutil  # type: ignore
except Exception:
    psutil = None
import random
import socket
from bs4 import BeautifulSoup
from dotenv import load_dotenv

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    SELENIUM_AVAILABLE = True
except Exception:
    webdriver = None
    By = None
    Options = None
    Service = None
    SELENIUM_AVAILABLE = False

try:
    import telegram  # type: ignore
    TELEGRAM_AVAILABLE = True
except Exception:
    telegram = None
    TELEGRAM_AVAILABLE = False

import subprocess
import asyncio
from collections import defaultdict
from datetime import datetime, timedelta


def is_adv_outdated(date_str, max_age_days=10):
    try:
        adv_date = datetime.strptime(date_str, "%Y-%m-%d")
        return datetime.now() - adv_date > timedelta(days=max_age_days)
    except Exception:
        return True


load_dotenv()


def normalize_symbol(symbol):
    symbol = symbol.strip().upper()
    if " PR" in symbol:
        parts = symbol.split()
        if len(parts) == 2 and parts[1].startswith("PR") and len(parts[1]) == 3:
            base = parts[0]
            suffix = parts[1][-1]
            return f"{base}-{suffix}", True
    symbol = re.sub(r"\s*\(PR\)$", "", symbol)
    return symbol, False


def extract_cache_key(symbol):
    return re.sub(r"[-\s]*\(?PR\)?\s*$", "", symbol.strip())


def _is_port_open(host: str, port: int, timeout: float = 0.3) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False


def is_chrome_running_with_debugging():
    if _is_port_open("127.0.0.1", 9222):
        return True
    if psutil is not None:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                name = (proc.info.get('name') or '').lower()
                cmdline = ' '.join(proc.info.get('cmdline') or [])
                if ('chrome' in name or 'google chrome' in name) and '--remote-debugging-port=9222' in cmdline:
                    return True
            except Exception:
                continue
    return False


USERNAME = os.getenv("LOGIN")
PASSWORD = os.getenv("PASSWORD")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if TELEGRAM_AVAILABLE and TELEGRAM_TOKEN:
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
else:
    bot = None

if not SELENIUM_AVAILABLE:
    print("ℹ️ Selenium не знайдено. Браузерні функції пропущено. ADV-тести працюватимуть.")

if SELENIUM_AVAILABLE and not is_chrome_running_with_debugging():
    print("🧭 Chrome не запущено з remote-debugging. Запускаємо...")
    chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    user_data_dir = os.path.expanduser("~/chrome-selenium")
    target_url = "http://www.amerxmocs.com/Default.aspx?index="
    try:
        subprocess.Popen([
            chrome_path,
            "--remote-debugging-port=9222",
            f"--user-data-dir={user_data_dir}",
            "--new-window",
            target_url
        ])
        for _ in range(20):
            if is_chrome_running_with_debugging():
                break
            time.sleep(1)
        else:
            print("❌ Chrome не стартував вчасно!")
    except Exception as e:
        print(f"❌ Не вдалося запустити Chrome: {e}")
elif SELENIUM_AVAILABLE:
    print("🟢 Chrome вже працює з remote-debugging.")

if SELENIUM_AVAILABLE:
    chrome_options = Options()
    chrome_options.add_argument("--remote-debugging-port=9222")
    chrome_options.add_argument(
        f"--user-data-dir={os.path.expanduser('~')}/chrome-selenium")
    chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")

LAST_PUSH_FILE = "last_push_time.txt"


def can_push_now(min_interval_seconds=80):
    if os.path.exists(LAST_PUSH_FILE):
        with open(LAST_PUSH_FILE, "r") as f:
            last_push_time = float(f.read().strip())
        if time.time() - last_push_time < min_interval_seconds:
            print(
                f"⏳ Пуш відкладено. Минуло менше {min_interval_seconds} секунд.")
            return False
    return True


def update_last_push_time():
    with open(LAST_PUSH_FILE, "w") as f:
        f.write(str(time.time()))


def git_commit_and_push():
    try:
        subprocess.run(["git", "stash"], check=False,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["git", "pull", "--rebase"], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["git", "stash", "pop"], check=False,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["git", "add", "."], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        result = subprocess.run(["git", "diff", "--cached", "--quiet"])
        if result.returncode == 0:
            print("ℹ️ Немає змін для коміту. Пуш не потрібен.")
            return
        if not can_push_now(80):
            return
        subprocess.run(["git", "commit", "-m", "🔄 Автооновлення imbalance даних"],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["git", "push"], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        update_last_push_time()
        print("✅ Зміни запушено на GitHub.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Git помилка: {e}")


def _parse_human_number_to_int(text: str) -> int:
    if not text:
        return 0
    s = text.strip().replace(',', '')
    try:
        if s.endswith(('M', 'm')):
            return int(float(s[:-1]) * 1_000_000)
        if s.endswith(('K', 'k')):
            return int(float(s[:-1]) * 1_000)
        if s.endswith(('B', 'b')):
            return int(float(s[:-1]) * 1_000_000_000)
        return int(float(s))
    except Exception:
        return 0
    

def _selenium_get_html(url: str, wait_css: str = "div[role='region']") -> str:
    """Повертає повністю відрендерений HTML через Selenium (якщо доступний)."""
    if not SELENIUM_AVAILABLE:
        return ""
    try:
        # якщо вже є chrome_options (з твого коду) — використаємо його; інакше створимо мінімальний
        opts = Options() if 'Options' in globals() and Options else None
        if opts:
            # підключення до існуючого дебаг-порту, якщо він є
            opts.add_argument("--remote-debugging-port=9222")
            opts.add_argument(
                f"--user-data-dir={os.path.expanduser('~')}/chrome-selenium")
            opts.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
        driver = webdriver.Chrome(
            service=Service(), options=opts) if opts else webdriver.Chrome()

        driver.set_page_load_timeout(30)
        driver.get(url)

        # м’яке очікування рендеру секції з ключовими статами
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "div[role='region']"))
        )
        html = driver.page_source
        driver.quit()
        return html
    except Exception:
        try:
            driver.quit()
        except Exception:
            pass
        return ""


def _extract_avg_volume_from_soup_strict(soup: BeautifulSoup) -> int:
    """Шукає 'Avg volume'/'Average volume' та число поряд:
       1) у контейнері 'gyFHrc' з міткою,
       2) піднімаючись вгору від мітки,
       3) по найближчих сусідах.
    """
    def _clean(s: str) -> str:
        return re.sub(r"\s+", " ", (s or "").replace("\xa0", " ").strip()).lower()

    LABELS = {"avg volume", "average volume"}

    # (1) Контейнери gyFHrc
    for block in soup.find_all("div", class_="gyFHrc"):
        text = _clean(block.get_text(" ", strip=True))
        if any(lbl in text for lbl in LABELS):
            # у цьому ж блоці шукаємо div.P6K39c або просто перше адекватне число
            num = block.find("div", class_="P6K39c")
            if num:
                v = _parse_human_number_to_int(num.get_text(" ", strip=True))
                if v:
                    return v
            # запасний варіант: будь-яке число у межах блоку
            m = re.search(r"\b(\d[\d,\.]*\s*[KMB]?)\b", text, flags=re.I)
            if m:
                v = _parse_human_number_to_int(m.group(1))
                if v:
                    return v

    # (2) Від мітки вгору/вниз
    label_nodes = [n for n in soup.find_all(
        string=True) if _clean(str(n)) in LABELS]
    for node in label_nodes:
        # вгору до 5 рівнів шукаємо P6K39c
        parent = node.parent
        for _ in range(5):
            if not parent:
                break
            for c in parent.find_all("div", class_="P6K39c"):
                v = _parse_human_number_to_int(c.get_text(" ", strip=True))
                if v:
                    return v
            parent = parent.parent

        # по сусідах до 20 кроків
        sib = node.parent.find_next() if hasattr(node, "parent") else None
        for _ in range(20):
            if sib is None:
                break
            if getattr(sib, "name", None) == "div" and "P6K39c" in (sib.get("class") or []):
                v = _parse_human_number_to_int(sib.get_text(" ", strip=True))
                if v:
                    return v
            inner = sib.find("div", class_="P6K39c") if hasattr(
                sib, "find") else None
            if inner:
                v = _parse_human_number_to_int(inner.get_text(" ", strip=True))
                if v:
                    return v
            sib = sib.find_next() if hasattr(sib, "find_next") else None

    return 0


def _get_adv_from_google(symbol: str, cache: dict) -> int:
    """Google Finance fallback: суворо прив’язуємося до 'Avg volume'/'Average volume'.
       Біржа: лише NYSE. Якщо в сирому HTML нічого — пробуємо Selenium-рендерінг.
    """
    url = f"https://www.google.com/finance/quote/{symbol}:NYSE?hl=en"
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": "https://www.google.com/",
    }

    # 1) Спочатку пробуємо requests (швидко)
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        time.sleep(random.uniform(1.1, 1.9))
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            val = _extract_avg_volume_from_soup_strict(soup)
            if val:
                cache[symbol] = {"adv": val,
                                 "date": datetime.now().strftime("%Y-%m-%d")}
                print(
                    f"✅ Google Finance ADV для {symbol} (NYSE, requests): {val} | {url}")
                return val
    except Exception as e:
        print(f"⚠️ Google Finance (requests) помилка для {symbol}: {e}")

    # 2) Якщо не вдалось — Selenium (рендерений DOM)
    html = _selenium_get_html(url)
    if html:
        soup = BeautifulSoup(html, "html.parser")
        val = _extract_avg_volume_from_soup_strict(soup)
        if val:
            cache[symbol] = {"adv": val,
                             "date": datetime.now().strftime("%Y-%m-%d")}
            print(
                f"✅ Google Finance ADV для {symbol} (NYSE, selenium): {val} | {url}")
            return val

    print(f"⚠️ Google Finance не знайдено ADV для {symbol} на NYSE")
    return 0

def get_adv_from_finviz(symbol, cache):
    clean_symbol, _ = normalize_symbol(symbol)
    symbol = clean_symbol

    cache_entry = cache.get(symbol)
    if cache_entry and isinstance(cache_entry, dict):
        if not is_adv_outdated(cache_entry.get("date", ""), 9):
            return cache_entry["adv"]

    try:
        normalized = symbol.replace(" ", "-").replace(".", "-")
        url = f"https://finviz.com/quote.ashx?t={normalized}&p=d"
        print(f"🔎 Запит до Finviz → {url}")
        headers = {"User-Agent": "Mozilla/5.0",
                   "Accept-Language": "en-US,en;q=0.9"}
        response = requests.get(url, headers=headers, timeout=15)
        time.sleep(random.uniform(1.4, 2.3))

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            table = soup.find("table", class_="snapshot-table2")
            if table:
                for row in table.find_all("tr"):
                    cells = row.find_all("td")
                    for i in range(len(cells)):
                        if cells[i].text.strip() == "Avg Volume":
                            volume_str = cells[i+1].text.strip()
                            adv = _parse_human_number_to_int(volume_str)
                            if adv:
                                cache[symbol] = {
                                    "adv": adv, "date": datetime.now().strftime("%Y-%m-%d")}
                                return adv
        else:
            print(f"⚠️ Finviz статус {response.status_code} для {symbol}")
        print(f"⚠️ Finviz не надав дані для {symbol}, пробуємо Google Finance")
    except Exception as e:
        print(f"⚠️ Помилка Finviz для {symbol}: {e}. Пробуємо Google Finance")

    val = _get_adv_from_google(symbol, cache)
    if val:
        return val

    cache[symbol] = {"adv": 0, "date": datetime.now().strftime("%Y-%m-%d")}
    return 0


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Fetch ADV via Finviz with Google Finance fallback")
    parser.add_argument(
        "--symbol", "-s", help="Single symbol to fetch (e.g., MS-O)")
    args = parser.parse_args()

    test_symbols = [
        "MS-O",
        "T-C",
        "VNO-O",
        "NOAH",
    ]

    extra_tests = [
     
    ]

    adv_cache = {}

    def run_one(sym: str):
        try:
            clean, _ = normalize_symbol(sym)
            print(f"--- SYMBOL: '{sym}' -> clean '{clean}' ---")
            val = get_adv_from_finviz(clean, adv_cache)
            print(f"ADV[{clean}] = {val:,}")
        except Exception as e:
            print(f"❌ Error for {sym}: {e}")

    print("\n🚀 QUICK TEST: get_adv_from_finviz with Google fallback\n")

    if args.symbol:
        run_one(args.symbol)

    for s in test_symbols:
        run_one(s)

    for s in extra_tests:
        run_one(s)

    print("\n📦 adv_cache snapshot:")
    try:
        print(json.dumps(adv_cache, indent=2))
    except Exception:
        print(str(adv_cache))

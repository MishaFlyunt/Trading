from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup
import json
import time

# Налаштування браузера
options = Options()
options.add_argument("--start-maximized")

driver = webdriver.Chrome(service=Service(), options=options)

try:
    print("🌐 Відкриваємо сайт...")
    driver.get("http://www.amerxmocs.com/Account/Login.aspx")
    time.sleep(2)

    # Вводимо логін
    username = driver.find_element(By.ID, "MainContent_UserName")
    password = driver.find_element(By.ID, "MainContent_Password")
    login_btn = driver.find_element(By.ID, "MainContent_LoginButton")

    username.send_keys("mkotsko")
    password.send_keys("Xzw184hcL!")
    login_btn.click()

    print("🔐 Логін виконується...")
    time.sleep(5)

    driver.get("http://www.amerxmocs.com/Default.aspx?index=")
    print("📄 Завантажуємо сторінку з таблицями...")
    time.sleep(10)

    html = driver.page_source
    with open("debug_page.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("✅ Збережено debug_page.html")

    soup = BeautifulSoup(html, "lxml")

    def extract_table(table_id):
        table = soup.find("table", id=table_id)
        if not table:
            return []
        rows = table.find_all("tr")
        data = []
        for row in rows:
            cols = row.find_all(["td", "th"])
            data.append([col.get_text(strip=True) for col in cols if col.get_text(strip=True)])
        return data

    buy_data = extract_table("MainContent_BuyTable")
    sell_data = extract_table("MainContent_SellTable")

    with open("buy_data.json", "w", encoding="utf-8") as f:
        json.dump(buy_data, f, ensure_ascii=False, indent=2)
    with open("sell_data.json", "w", encoding="utf-8") as f:
        json.dump(sell_data, f, ensure_ascii=False, indent=2)

    print(f"✅ Дані збережено: {len(buy_data)} рядків Buy / {len(sell_data)} рядків Sell")

finally:
    input("🧹 Натисни Enter, щоб завершити...")
    driver.quit()
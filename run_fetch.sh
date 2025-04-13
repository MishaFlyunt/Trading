#!/bin/bash

# Завантажити змінні середовища з .env
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

# Лог файл
LOGFILE="last_run.log"

# Перевірити чи Chrome вже запущений з remote-debugging-port
if ! lsof -i :9222 | grep -q LISTEN; then
  echo "🚀 Запускаємо Chrome з remote-debugging-port..."
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
    --remote-debugging-port=9222 \
    --user-data-dir="$HOME/chrome-selenium" &
  sleep 5
else
  echo "🟢 Chrome вже запущений з remote-debugging-port"
fi

# Запуск Python-скрипта
echo "▶️ Запускаємо smart_login_and_fetch.py..."
python3 smart_login_and_fetch.py

# Записати дату запуску
echo "[`date '+%Y-%m-%d %H:%M:%S'`] ✅ Скрипт завершено" >> "$LOGFILE"

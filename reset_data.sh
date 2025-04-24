#!/bin/bash

# Розширити PATH для cron, особливо на Mac M1
export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

# Каталог скрипта
SCRIPT_DIR="/Users/mihajloflunt/Desktop/Home/Навчання/GOIT/Trading"
cd "$SCRIPT_DIR" || exit 1

# Файли для очищення
FILES=("buy_data.json" "sell_data.json" "prev_buy.json" "prev_sell.json" "flip_notified_buy.json" "flip_notified_sell.json" "dash_notified_buy.json" "dash_notified_sell.json")

# Лог-файл
LOGFILE="$SCRIPT_DIR/reset_log.txt"
{
  echo ""
  echo "🧹 Reset запущено: $(date)"

  for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
      > "$file"
      echo "✅ Очищено файл: $file"
    else
      echo "⚠️ Файл не знайдено: $file"
    fi
  done

  git add .
  git commit -m "🧹 Автоочищення JSON файлів о 23:00 за Києвом"
  git push
  echo "✅ Git push виконано"
} >> "$LOGFILE" 2>&1
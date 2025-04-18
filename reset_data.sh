#!/bin/bash

# Файли, які потрібно очистити
FILES=("buy_data.json" "sell_data.json" "adv_cache.json" "prev_buy.json" "prev_sell.json")

# Каталог скрипта
SCRIPT_DIR="/Users/mihajloflunt/Desktop/Home/Навчання/GOIT/Trading"

# Перехід у каталог
cd "$SCRIPT_DIR" || exit 1

# Створити лог-файл
LOGFILE="$SCRIPT_DIR/reset_log.txt"
{
  echo ""
  echo "🧹 Reset запущено: $(date '+%Y-%m-%d %H:%M:%S')"

  # Очистити файли
  for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
      > "$file"
      echo "✅ Очищено файл: $file"
    else
      echo "⚠️ Файл не знайдено: $file"
    fi
  done

  # Git-операції
  git add .
  git commit -m "🧹 Автоочищення JSON файлів о 23:00 за Києвом"
  git push
  echo "✅ Git push виконано"
} >> "$LOGFILE" 2>&1
#!/bin/bash

# Каталог скрипта
SCRIPT_DIR="/Users/mihajloflunt/Desktop/Home/Навчання/GOIT/Trading"
cd "$SCRIPT_DIR" || exit 1

# Файли, які потрібно очистити
FILES=("buy_data.json" "sell_data.json" "adv_cache.json" "prev_buy.json" "prev_sell.json")

# Шлях до git (перевірити через `which git`)
GIT_CMD="/usr/bin/git"

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
  $GIT_CMD add .
  $GIT_CMD commit -m "🧹 Автоочищення JSON файлів о 23:00 за Києвом" || echo "ℹ️ Немає змін для коміту"
  $GIT_CMD push && echo "✅ Git push виконано" || echo "❌ Git push не вдалось"
} >> "$LOGFILE" 2>&1
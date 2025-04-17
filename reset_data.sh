#!/bin/bash

# Очищення файлів
echo "{}" > adv_cache.json
echo '{"main": [], "archive": {}}' > buy_data.json
echo '{"main": [], "archive": {}}' > sell_data.json

# Коміт і пуш
git add adv_cache.json buy_data.json sell_data.json
git commit -m "🧹 Автоочищення JSON файлів о 23:00 за Києвом"
git push

echo "✅ Файли очищено та запушено на GitHub"


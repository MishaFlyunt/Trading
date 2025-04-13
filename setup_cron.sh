# Додати автозапуск кожні 5 хв з 20:00 до 22:55 і о 23:30 (за Києвом)
(crontab -l 2>/dev/null; echo "*/5 20-22 * * * /Users/mihajloflunt/Desktop/Home/Навчання/GOIT/Trading/run_fetch.sh") | crontab -
(crontab -l 2>/dev/null; echo "30 23 * * * /Users/mihajloflunt/Desktop/Home/Навчання/GOIT/Trading/run_fetch.sh") | crontab -
echo "✅ Cron job додано! Скрипт буде запускатися з 13:30 до 16:00 за Нью-Йорком (20:30–23:00 Київ)."

f"{imbalance_type}  imbalance_type
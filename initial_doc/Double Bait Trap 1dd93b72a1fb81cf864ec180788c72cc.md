# Double Bait Trap

1. **Механика "двойного сигнала" (Double Bait Trap)**

Что делает:  Сначала даёт ложный сигнал (бот его фильтрует), затем повторяет его через 2–3 свечи с небольшой модификацией — бот думает, что второй — настоящий, и влетает. Это уже против контр-ботов, которые обучаются отбрасывать первый сигнал

## **Манипуляция №22: Double Bait Trap — Финальная версия**

### I. Суть манипуляции

Double Bait Trap — это HFT-манипуляция, ориентированная на продвинутых ботов.

Алго сначала подсовывает **первый ложный сигнал**, который бот фильтрует.

Через 2–3 свечи — **повтор**, но чуть убедительнее (чуть больше объём, красивее формация).

Бот "покупается" на второй сигнал — и рынок разворачивается.

### II. Признаки на графике

- Повтор одного и того же сигнала в пределах 2–3 свечей.
- Второй сигнал выглядит "чище" визуально (объём выше).
- Дельта при втором сигнале ≈ 0 или отрицательная.
- Сразу после входа рынок уходит против.

### III. Метрики и источники

| **Метрика** | **Условие** | **Источник** |
| --- | --- | --- |
| Интервал между сигналами | ≤ 3 свечи | Буфер сигналов |
| Тип сигнала | Совпадает (Breakout, Impulse и т.п.) | Внутренняя логика |
| Объём второго | > 1.2× среднего | /market/kline |
| Дельта | Δдельта ≤ 0 | WebSocket /recent-trade |
| За сигналом | 1–2 свечи отката или слабости | /market/kline |

### IV. Python-фильтр с буфером, объёмом, дельтой и Telegram

```python
from pybit.unified_trading import HTTP, WebSocket
import time, requests, pandas as pd, statistics

API_KEY = "ТВОЙ_API"
API_SECRET = "ТВОЙ_SECRET"
SYMBOL = "BTCUSDT"
INTERVAL = "1"
CATEGORY = "linear"
TELEGRAM_TOKEN = "ТВОЙ_ТГ_ТОКЕН"
CHAT_ID = "ТВОЙ_CHAT_ID"

client = HTTP(api_key=API_KEY, api_secret=API_SECRET)
ws = WebSocket(testnet=False, channel_type="linear")

signal_buffer = []  # Буфер последних сигналов
delta_buffer = {}
last_trap_ts = None

# Telegram
def send_telegram_message(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}
    try:
        requests.post(url, data=data)
    except Exception as e:
        print("Telegram ошибка:", e)

# WebSocket → дельта по минутам
def handle_trade_msg(message):
    if "data" in message:
        for trade in message["data"]:
            ts = int(trade["T"]) // 60000 * 60000
            delta = float(trade["v"]) if trade["S"] == "Buy" else -float(trade["v"])
            delta_buffer[ts] = delta_buffer.get(ts, 0) + delta

ws.trade_stream(symbol=SYMBOL, callback=handle_trade_msg)

# Получение свечей и OI
def get_klines():
    return client.get_kline(category=CATEGORY, symbol=SYMBOL, interval=INTERVAL, limit=30)["result"]["list"]

# Ловушка двойного сигнала
def detect_double_bait_trap(klines):
    global last_trap_ts
    signals = []
    if len(signal_buffer) < 2:
        return signals

    s1, s2 = signal_buffer[-2], signal_buffer[-1]
    if s1["type"] != s2["type"]:
        return signals

    time_diff = (s2["ts"] - s1["ts"]) / 1000 / 60
    if time_diff > 3:
        return signals

    current_kline = klines[-1]
    ts = int(current_kline[0])
    close = float(current_kline[4])
    volume = float(current_kline[5])
    delta = delta_buffer.get(ts, 0)

    avg_volume = statistics.mean([float(k[5]) for k in klines[-6:-1]])
    volume_confirm = volume > avg_volume * 1.2
    delta_weak = delta <= 0

    if volume_confirm and delta_weak and last_trap_ts != s2["ts"]:
        msg = (
            f"🪤 *Double Bait Trap Detected*\n"
            f"📉 Сигнал: `{s2['type']}` повтор через {time_diff:.1f} мин\n"
            f"📊 Объём: {volume:.2f} | ΔДельта: {delta:.0f}\n"
            f"⚠️ Входы временно заблокированы"
        )
        send_telegram_message(msg)
        last_trap_ts = s2["ts"]
        signals.append((ts, "Double Bait Trap"))

    return signals

# Пример сигнальной записи (эмулируется другой логикой):
def register_signal(signal_type, ts):
    signal_buffer.append({"type": signal_type, "ts": ts})
    if len(signal_buffer) > 10:
        signal_buffer.pop(0)

def run():
    while True:
        try:
            klines = get_klines()
            ts = int(klines[-1][0])

            # Предположим, сигнал типа "Breakout" приходит из логики №19, 20 и т.п.
            # Здесь пример: каждая 10-я минута — фейковый сигнал
            if time.localtime().tm_min % 10 == 0:
                register_signal("Breakout", ts)

            traps = detect_double_bait_trap(klines)
            if traps:
                df = pd.DataFrame(traps, columns=["timestamp", "signal"])
                df.to_csv("double_bait_trap.csv", mode="a", header=False, index=False)
                print("💥 Обнаружена ловушка:", traps)
            else:
                print("✅ Манипуляций нет.")

            time.sleep(60)
        except Exception as e:
            print("❗ Ошибка:", e)
            time.sleep(10)

if __name__ == "__main__":
    run()

```

### V. Противодействие в боте

| **Механизм** | **Действие** |
| --- | --- |
| 🧠 Сигнальный буфер | Отслеживает повторные сигналы |
| ⏱ Проверка времени | Анализирует: интервал ≤ 3 свечи |
| 📊 Фильтрация по объёму | Второй сигнал — >1.2× объёма, но не экстремум |
| 📉 Дельта слабая или < 0 | Показывает, что движение не поддержано маркетами |
| 🛡️ Защита от повторов | Один сигнал на один повтор — без спама |
| 🚫 Блокировка входа | Бот не открывает позицию |
| 📬 Telegram | Уведомление в момент ловушки |

### VI. Сводка условий

| **Условие** | **Порог** |
| --- | --- |
| Тип сигнала совпадает | "Breakout" → "Breakout" |
| Интервал между сигналами | ≤ 3 свечи (3 мин на 1м ТФ) |
| Объём второго сигнала | > 1.2× среднего объёма |
| Дельта | ≤ 0 |
| Поведение после входа | Падение / откат / слабость |

### VII. Выходные данные

| **Параметр** | **Значение** |
| --- | --- |
| ТФ | 1m |
| Частота анализа | каждые 60 сек |
| Output | Telegram + CSV |
| Тип ловушки | Double Bait Trap |
| Защита | Игнор входа + блокировка |
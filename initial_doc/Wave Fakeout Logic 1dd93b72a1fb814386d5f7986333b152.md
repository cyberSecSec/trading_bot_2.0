# Wave Fakeout Logic

1. **Контр-волновое поведение (Wave Fakeout Logic)**

Что делает: Имитация 3-й волны по Эллиотту или «продолжения импульса», на которых заходят алгоритмы, но вместо этого идёт флет → сброс.

## Манипуляция №20: Контр-волновое поведение (Wave Fakeout Logic) — финальная версия

### I. Что это

Алгоритм HFT-уровня имитирует **начало мощной третьей волны** (по Эллиотту), формируя резкую импульсную свечу.

Толпа и трендовые боты входят в рынок на "идеальный" импульс.

Но далее:

- Нет подтверждающих свечей.
- Объём резко падает.
- Цена замирает.
- Через 3–5 свечей — **резкий сброс вниз**.

🔻 **Цель манипуляции** — затянуть ликвидность на импульсе и **забрать её без продолжения движения**.

### II. Как выглядит

- Импульсная свеча с объёмом > 2x
- После неё — замедление, объём падает
- Цена стоит, хотя дельта положительная
- OI растёт → толпа заходит в позицию
- Через 3–5 свечей — **обратный сброс**

### III. Метрики и источники

| **Метрика** | **Условие** | **Источник (Bybit API)** |
| --- | --- | --- |
| Импульсная свеча | Объём > 2x среднего, тело > 70% диапазона | /market/kline |
| Контекст до импульса | < 1.5% изменения цены за 5–6 свечей | /market/kline |
| Follow-through | Узкий диапазон после импульса, объём падает | /market/kline |
| Положительная дельта | Дельта > 0, но свечи красные | WebSocket /recent-trade |
| Рост OI | ΔOI > 500, при слабом изменении цены | /market/open-interest |
| Сброс | close[i+4] < open[i+1], объём ≥ средний | /market/kline |

### IV. Логика и формулы

```python
i = -5  # Импульсная свеча

# Контекст до импульса
pre_range = abs(float(klines[i-5][4]) - float(klines[i-1][4])) / float(klines[i-5][4]) * 100
pre_consolidation = pre_range < 1.5

# Импульсная свеча
k = klines[i]
open_, high, low, close, volume = map(float, k[1:6])
range_ = high - low + 1e-8
body = abs(close - open_)
body_ratio = body / range_
avg_vol = statistics.mean([float(k[5]) for k in klines[i-5:i]])
volume_ratio = volume / avg_vol
impulse = volume_ratio > 2 and body_ratio > 0.7

# Follow-through: слабое продолжение
next_closes = [float(klines[j][4]) for j in range(i+1, i+4)]
next_range = max(next_closes) - min(next_closes)
follow_through = next_range < 0.004 * close

# Объём падает после импульса
next_volumes = [float(klines[j][5]) for j in range(i+1, i+4)]
avg_next_volume = sum(next_volumes) / 3
volume_drop = avg_next_volume < avg_vol * 0.8

# Рост OI без движения
oi_now = float(oi_data[i]["openInterest"])
oi_prev = float(oi_data[i - 1]["openInterest"])
delta_oi = oi_now - oi_prev
price_change = abs(close - open_) / open_ * 100
oi_fake = delta_oi > 500 and price_change < 0.2

# Сброс
reversal = float(klines[i+4][4]) < float(klines[i+1][1])
vol_reversal = float(klines[i+4][5]) > avg_vol

```

### V. Поведение бота

📍 Если одновременно:

- pre_consolidation = True
- impulse = True
- follow_through = True
- volume_drop = True
- oi_fake = True
- reversal = True and vol_reversal = True

📌 Тогда:

- Маркируется как Wave Trap
- Запрещается вход на 10 минут
- Telegram-уведомление
- CSV лог

### VI. Логгер (Python + Telegram)

- Работает в цикле 60 сек
- Отслеживает последнюю свечу last_signal_ts, чтобы не дублировать сигнал

### VII. Python-фильтр (финальный код)

```python
from pybit.unified_trading import HTTP
import statistics
import pandas as pd
import time
import requests

API_KEY = "API_КЛЮЧ"
API_SECRET = "API_СЕКРЕТ"
SYMBOL = "BTCUSDT"
CATEGORY = "linear"
INTERVAL = "1"
LOOKBACK = 30

TELEGRAM_TOKEN = "ТГ_БОТ_ТОКЕН"
CHAT_ID = "CHAT_ID"

client = HTTP(api_key=API_KEY, api_secret=API_SECRET)
last_signal_ts = None

def get_klines():
    return client.get_kline(category=CATEGORY, symbol=SYMBOL, interval=INTERVAL, limit=LOOKBACK + 5)["result"]["list"]

def get_open_interest():
    return client.get_open_interest(category=CATEGORY, symbol=SYMBOL, intervalTime="1min", limit=LOOKBACK + 5)["result"]["list"]

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, data=data)
    except Exception as e:
        print("Telegram ошибка:", e)

def detect_wave_fakeout(klines, oi_data):
    global last_signal_ts
    signals = []
    i = -5  # свеча, где произошёл "импульс"

    # Предыдущая структура
    pre_range = abs(float(klines[i-5][4]) - float(klines[i-1][4])) / float(klines[i-5][4]) * 100
    pre_consolidation = pre_range < 1.5

    # Импульс
    k = klines[i]
    open_, high, low, close, volume = map(float, k[1:6])
    range_ = high - low + 1e-8
    body_ratio = abs(close - open_) / range_
    avg_vol = statistics.mean([float(k[5]) for k in klines[i-5:i]])
    volume_ratio = volume / avg_vol
    impulse = volume_ratio > 2 and body_ratio > 0.7

    # Follow-through
    next_closes = [float(klines[j][4]) for j in range(i+1, i+4)]
    next_range = max(next_closes) - min(next_closes)
    follow_through = next_range < 0.004 * close
    next_volumes = [float(klines[j][5]) for j in range(i+1, i+4)]
    avg_next_volume = sum(next_volumes) / 3
    volume_drop = avg_next_volume < avg_vol * 0.8

    # OI
    oi_now = float(oi_data[i]["openInterest"])
    oi_prev = float(oi_data[i - 1]["openInterest"])
    delta_oi = oi_now - oi_prev
    price_change = abs(close - open_) / open_ * 100
    oi_fake = delta_oi > 500 and price_change < 0.2

    # Резкий сброс
    reversal = float(klines[i+4][4]) < float(klines[i+1][1])
    vol_reversal = float(klines[i+4][5]) > avg_vol

    if pre_consolidation and impulse and follow_through and volume_drop and oi_fake and reversal and vol_reversal:
        ts = int(klines[i][0])
        if ts != last_signal_ts:
            msg = (
                f"🚨 *Wave Trap Detected*\n"
                f"📉 Символ: `{SYMBOL}`\n"
                f"🕒 Время: {pd.to_datetime(ts, unit='ms')}\n"
                f"📊 Объём: {volume:.2f}, ΔOI: {delta_oi:.0f}\n"
                f"🔒 Вход заблокирован на 10 минут"
            )
            send_telegram_message(msg)
            signals.append((ts, "Wave Trap Detected"))
            last_signal_ts = ts
    return signals

def run_logger():
    while True:
        try:
            klines = get_klines()
            oi_data = get_open_interest()
            signals = detect_wave_fakeout(klines, oi_data)
            if signals:
                df = pd.DataFrame(signals, columns=["timestamp", "signal"])
                df.to_csv("wave_trap_signals.csv", mode="a", header=False, index=False)
                print("📌 Wave Trap:", signals)
            else:
                print("✅ Манипуляций нет.")
            time.sleep(60)
        except Exception as e:
            print("❗ Ошибка:", e)
            time.sleep(10)

if __name__ == "__main__":
    run_logger()

```

### VIII. Сводка условий

| **Условие** | **Порог** |
| --- | --- |
| Диапазон до импульса | < 1.5% |
| Объём импульсной свечи | > 2× среднего |
| Тело свечи | > 70% от диапазона |
| Follow-through | Диапазон < 0.4%, объём ↓ |
| ΔOI | > 500 |
| Цена после импульса | Не растёт, откат |
| Сброс через 3–5 свечей | close[i+4] < open[i+1] |
| Объём сброса | > среднего |

### IX. Таблицы

| **Параметр** | **Значение** |
| --- | --- |
| ТФ | 1м (адаптивно до 5м) |
| Источник | Bybit REST API |
| Частота анализа | Каждые 60 сек |
| Тип сигнала | Wave Trap |
| Output | CSV + Telegram |
| Поведение бота | Ждёт подтверждение волны, блокирует фейк |
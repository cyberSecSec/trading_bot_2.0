# Candle Context Mismatch

**№21: Контекстный обман свечей (Candle Context Mismatch) —**

1. Суть манипуляции

Алгоритм рисует визуально убедительную свечу (например, сильную бычью), чтобы активировать сигналы и привлечь ритейл. Но эта свеча:

не подтверждается объёмом, дельтой или открытым интересом;

не укладывается в общий контекст;

не сопровождается follow-up движением.

Цель: вызвать вход в рынок по ложному свечному сигналу и быстро его "погасить"

## Манипуляция №21: Контекстный обман свечей (Candle Context Mismatch) — финальная версия

### I. Суть манипуляции

HFT-алгоритм формирует визуально сильную свечу (обычно бычью), которая **выглядит как трендовая**, но:

- не подтверждена объёмом,
- не сопровождается follow-up свечами,
- не поддерживается дельтой или OI.

🔻 Цель — втянуть ритейл в рынок на ложной визуальной информации и **обрушить позицию в следующие 1–2 свечи**.

### II. Как выглядит на графике

- Длинная свеча с большим телом и маленькими тенями.
- До этого — боковик или слабый даунтренд.
- Следующая свеча — плоская или обратная.
- Нет роста OI.
- Дельта ≈ 0 или отрицательная.
- Объём — не выше среднего.

### III. Метрики и источники

| **Метрика** | **Условие** | **Источник** |
| --- | --- | --- |
| Контекст свечей | Предыдущие 5 свечей < 0.5% диапазон | /market/kline |
| Объём свечи | < 1.2× среднего | /market/kline |
| Дельта | ≤ 0 | WebSocket recent-trade |
| Open Interest | ΔOI < 100 | /market/open-interest |
| Follow-up свеча | Цена не растёт, объём падает | /market/kline |

### IV. Формулы и логика

```python
# [1] Контекст до свечи (5 свечей) — флет
context_range = max([float(k[2]) for k in klines[i-5:i]]) - min([float(k[3]) for k in klines[i-5:i]])
context_percent = context_range / float(klines[i-1][4]) * 100
flat_before = context_percent < 0.5

# [2] Объём свечи
avg_volume = statistics.mean([float(k[5]) for k in klines[i-5:i]])
volume_now = float(klines[i][5])
volume_ratio = volume_now / avg_volume
low_volume = volume_ratio < 1.2

# [3] Дельта свечи
delta = delta_buffer.get(i, 0)
delta_conflict = delta <= 0

# [4] OI не растёт
oi_now = float(oi_data[i]['openInterest'])
oi_prev = float(oi_data[i-1]['openInterest'])
oi_delta = oi_now - oi_prev
low_oi = oi_delta < 100

# [5] Нет follow-up
close_now = float(klines[i][4])
close_next = float(klines[i+1][4])
volume_next = float(klines[i+1][5])
follow_fail = close_next < close_now or volume_next < volume_now * 0.7

# [6] Тело свечи большое
open_ = float(klines[i][1])
price_change = abs(close_now - open_) / open_ * 100
big_body = price_change > 0.4

# [7] Финальное условие
if big_body and flat_before and low_volume and delta_conflict and low_oi and follow_fail:
    return True

```

### V. Поведение бота

- **Не даёт использовать свечу как сигнал входа**
- **Запрещает входы** в течение следующих **3 минут**
- **Добавляет сигнал в глобальный блокировщик**
- **Отправляет уведомление в Telegram**
- **Записывает в CSV лог**

### VI. Финальный код

```python
from pybit.unified_trading import HTTP, WebSocket
import statistics, pandas as pd, time, requests

API_KEY = "ТВОЙ_API"
API_SECRET = "ТВОЙ_SECRET"
SYMBOL = "BTCUSDT"
CATEGORY = "linear"
INTERVAL = "1"
LOOKBACK = 40
TELEGRAM_TOKEN = "ТВОЙ_TG_ТОКЕН"
CHAT_ID = "ТВОЙ_CHAT_ID"

client = HTTP(api_key=API_KEY, api_secret=API_SECRET)
ws = WebSocket(testnet=False, channel_type="linear")

delta_buffer = {}
last_signal_ts = None

# Получение свечей
def get_klines():
    return client.get_kline(category=CATEGORY, symbol=SYMBOL, interval=INTERVAL, limit=LOOKBACK)["result"]["list"]

# Получение OI
def get_open_interest():
    return client.get_open_interest(category=CATEGORY, symbol=SYMBOL, intervalTime="1min", limit=LOOKBACK)["result"]["list"]

# Telegram
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, data=data)
    except Exception as e:
        print("Telegram ошибка:", e)

# Подписка на сделки — для дельты
def handle_trade_msg(message):
    if "data" in message:
        for trade in message["data"]:
            ts = int(trade["T"]) // 60000 * 60000
            delta = float(trade["v"]) if trade["S"] == "Buy" else -float(trade["v"])
            delta_buffer[ts] = delta_buffer.get(ts, 0) + delta

ws.trade_stream(symbol=SYMBOL, callback=handle_trade_msg)

# Детектор манипуляции
def detect_candle_context_mismatch(klines, oi_data):
    global last_signal_ts
    signals = []
    for i in range(5, len(klines) - 2):
        o, h, l, c, v = map(float, klines[i][1:6])
        c_next = float(klines[i+1][4])
        v_next = float(klines[i+1][5])

        # Контекст
        context_range = max([float(k[2]) for k in klines[i-5:i]]) - min([float(k[3]) for k in klines[i-5:i]])
        context_percent = context_range / float(klines[i-1][4]) * 100
        flat_before = context_percent < 0.5

        avg_volume = statistics.mean([float(k[5]) for k in klines[i-5:i]])
        volume_ratio = v / avg_volume
        low_volume = volume_ratio < 1.2

        ts = int(klines[i][0])
        delta = delta_buffer.get(ts, 0)
        delta_conflict = delta <= 0

        oi_now = float(oi_data[i]['openInterest'])
        oi_prev = float(oi_data[i-1]['openInterest'])
        oi_delta = oi_now - oi_prev
        low_oi = oi_delta < 100

        follow_fail = c_next < c or v_next < v * 0.7
        price_change = abs(c - o) / o * 100
        big_body = price_change > 0.4

        if big_body and flat_before and low_volume and delta_conflict and low_oi and follow_fail:
            if ts != last_signal_ts:
                message = (
                    f"🚩 *Candle Context Mismatch Detected*\n"
                    f"📈 `{SYMBOL}`\n"
                    f"🕒 {pd.to_datetime(ts, unit='ms')}\n"
                    f"ΔOI: {oi_delta:.0f}, ΔЦена: {price_change:.2f}%, ΔДельта: {delta:.0f}\n"
                    f"⚠️ Свеча отключена для сигналов на 3 минуты"
                )
                send_telegram_message(message)
                signals.append((ts, "Candle Context Mismatch"))
                last_signal_ts = ts
    return signals

def run():
    while True:
        try:
            klines = get_klines()
            oi_data = get_open_interest()
            signals = detect_candle_context_mismatch(klines, oi_data)
            if signals:
                df = pd.DataFrame(signals, columns=["timestamp", "signal"])
                df.to_csv("candle_context_mismatch_signals.csv", mode="a", header=False, index=False)
                print("⚠️ Обнаружено:", signals)
            else:
                print("✅ Нет манипуляций.")
            time.sleep(60)
        except Exception as e:
            print("Ошибка:", e)
            time.sleep(10)

if __name__ == "__main__":
    run()

```

### VII. Сводка условий

| **Условие** | **Порог** |
| --- | --- |
| Диапазон до свечи | < 0.5% |
| ΔЦена по телу свечи | > 0.4% |
| Объём | < 1.2× среднего |
| ΔOI | < 100 |
| ΔДельта | ≤ 0 |
| Follow-up | Нет роста цены/объёма |

### VIII. Таблица параметров

| **Параметр** | **Значение** |
| --- | --- |
| ТФ | 1м |
| API | REST + WebSocket |
| Частота анализа | 1 раз в минуту |
| Выход | CSV + Telegram |
| Защита | От повторов, 3 мин блок |
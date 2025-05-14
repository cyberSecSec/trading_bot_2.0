# Volume Injection

1. **Подмена объема (Volume Injection)**
- Вброс объема без истинного интереса
- Алго просто качает цифры, чтобы создать иллюзию интереса к уровню
- Трейдер видит «взрыв» и входит → его ловят

**Манипуляция №5: Толкающий объём (Momentum Trap / Volume Injection / Absorption)**

### **1. Идентификация манипуляции: как работает и что искать**

**Что это:**

Алгоритм вбрасывает крупные объёмы агрессивных рыночных ордеров в одну сторону, создавая видимость пробоя или сильного импульса. Однако цель — не продолжить движение, а **втянуть толпу в ловушку**, поглотить их заявки лимитами (absorption), и после фиксации ликвидности **развернуть цену в противоположную сторону**.

**Типичные варианты:**

1. **Momentum Trap** — искусственный маркет-импульс, затем разворот
2. **Absorption** — лимитки удерживают уровень, без фейкового импульса
3. **Volume Injection** — всплеск объёма, отсутствует продолжение, рынок зависает или откатывает

**Сценарий:**

1. В ленте фиксируется всплеск маркет-покупок (или продаж)
2. Свеча не закрывается выше, несмотря на объём
3. На уровне находятся лимитные заявки, которые поглощают агрессию
4. Open Interest растёт, но цена не движется
5. Следующие свечи показывают отсутствие follow-through
6. Происходит разворот или вялый флэт

### **2. Методы идентификации и метрики**

| **Признак** | **Что отслеживаем** | **Где брать** |
| --- | --- | --- |
| Всплеск агрессивного объёма (дельта) | taker buy volume ↑ / sell volume ↑ | /market/recent-trade, считаем delta |
| Свеча не подтверждает движение | Цена не закрепляется, тело маленькое | /market/kline |
| OI растёт, но цена не идёт | Рост открытого интереса, но цена стагнирует | /market/open-interest |
| Отсутствие follow-through | 1–3 свечи после сигнала слабые | kline |
| Поглощение лимитками | Маркет-объём упирается в лимитные заявки | WebSocket /orderbook.25/.200 |
| Длинные тени | Верхние/нижние тени у свечей на фоне объёма | OHLC анализ |
| Ratio агрессии к ликвидности (absorption ratio) | market volume vs resting liquidity на уровне | стакан + лента |
| Order Flow Disbalance | Где именно концентрируются маркет-сделки внутри свечи | кластерный delta-анализ (опц.) |

### **3. Формулы и логика обработки**

1. **Агрессивная дельта + отсутствие движения**

```python
delta = taker_buy_volume - taker_sell_volume
if delta > avg_delta * 2 and price_change < 0.3:
    volume_spike = True
```

1. **Поведение свечи: короткое тело + тень**

```python
body_size = abs(close - open)
candle_range = high - low
wick_ratio = (high - close) / candle_range if close > open else (open - low) / candle_range
if body_size < candle_range * 0.3 and wick_ratio > 0.6:
    weak_close = True
```

1. **OI и отсутствие движения**

```python
delta_oi = OI_now - OI_prev
price_change = abs(close - open) / open * 100
if delta_oi > 500 and price_change < 0.3:
    trap_signal = True
```

1. **Follow-through слабый**

```python
if avg(volume[i+1:i+3]) < volume[i] * 0.6:
    no_follow = True
```

1. **Поглощение лимитками**

```python
wall_volume = sum(order['size'] for order in orderbook if order['price'] == key_level)
absorption_ratio = market_volume_at_level / wall_volume
if wall_volume > 1_000_000 and 0.8 < absorption_ratio < 1.2:
    absorption_detected = True

```

1. **Серия свечей с высоким объёмом и маленьким телом**

```python
for candle in last_3_candles:
    if candle['volume'] > avg_volume * 1.5 and abs(candle['close'] - candle['open']) < candle['range'] * 0.3:
        weak_body_candles += 1
if weak_body_candles >= 2:
    momentum_fade = True

```

### **4. Логгер (обновлённая версия)**

```python
from pybit.unified_trading import HTTP
import statistics
import time

symbol = "BTCUSDT"
interval = "1"
lookback = 20

client = HTTP(testnet=False, api_key="API", api_secret="SECRET")

def get_klines():
    k = client.get_kline(category="linear", symbol=symbol, interval=interval, limit=lookback + 3)
    return k["result"]["list"]

def get_oi():
    oi = client.get_open_interest(category="linear", symbol=symbol, intervalTime="1min", limit=lookback + 3)
    return oi["result"]["list"]

def detect_volume_injection(klines, oi_data):
    candle = klines[-2]
    o, h, l, c, v = map(float, candle[1:6])
    wick = h - c
    rng = h - l
    wick_ratio = wick / rng if rng > 0 else 0
    price_change = abs(c - o) / o * 100
    volumes = [float(k[5]) for k in klines[:-2]]
    avg_vol = statistics.mean(volumes)

    oi_now = float(oi_data[-1]['openInterest'])
    oi_prev = float(oi_data[-2]['openInterest'])
    delta_oi = oi_now - oi_prev

    if v > avg_vol * 2 and price_change < 0.3 and wick_ratio > 0.6 and delta_oi > 500:
        return True, {
            "wick_ratio": round(wick_ratio, 2),
            "volume_spike": round(v / avg_vol, 2),
            "price_change": round(price_change, 2),
            "delta_oi": delta_oi
        }
    else:
        return False, {}

while True:
    try:
        klines = get_klines()
        oi_data = get_oi()
        is_fake, metrics = detect_volume_injection(klines, oi_data)
        if is_fake:
            print(f"Volume Injection Detected: {metrics}")
        else:
            print("No signal. Monitoring...")
        time.sleep(30)
    except Exception as e:
        print(f"Error: {e}")
        time.sleep(10)

```

### **5. Сводка — признаки манипуляции Volume Injection**

| **Метрика** | **Значение** |
| --- | --- |
| Объём свечи | > 2× среднего |
| Цена не ушла | price_change < 0.3% |
| Длинная тень | wick_ratio > 0.6 |
| Open Interest | delta_OI > 500 |
| Нет follow-up | объём следующих свечей < 60% от текущей |
| Дельта агрессивная | delta > avg_delta * 2 |
| Свеча не закрывается выше | close внутри тела предыдущей свечи |
| Серия свечей с узким телом | ≥2 подряд |
| Поглощение в стакане | wall > 1M, absorption_ratio ≈ 1, цена не проходит |
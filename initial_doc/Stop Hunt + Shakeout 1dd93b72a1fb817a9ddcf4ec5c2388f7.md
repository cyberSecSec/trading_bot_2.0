# Stop Hunt + Shakeout

1. **Сброс ликвидности перед настоящим движением (Stop Hunt + Shakeout)**
- Алго пробивает уровень, выносит всех (лонги, шорты), и **лишь потом** запускает настоящее движение
- Особенно перед новостями или на малых объемах

## **Манипуляция №2: Сброс ликвидности перед настоящим движением (Stop Hunt + Shakeout)**

### I. Идентификация манипуляции: как работает и что искать

**Что это:**

Алгоритм искусственно инициирует пробой уровня (вверх или вниз), чтобы:

- ликвидировать позиции толпы (лонги/шорты),
- собрать стопы,
- очистить путь для последующего настоящего движения.

**Когда применяется:**

- перед важными новостями,
- в условиях узкого боковика,
- на низкой волатильности и падающем объёме.

**Этапы манипуляции:**

1. **Перед сбросом:**
    - Формируется боковик, рынок «замирает», позиции накапливаются.
    - OI растёт, объёмы падают — это подготовка ловушки.
2. **Во время сброса:**
    - Резкое движение с выбросом объёма.
    - Длинная тень, ликвидации в моменте, свеча не закрепляется.
    - Нет продолжения движения.
3. **После сброса:**
    - Алгоритм делает паузу.
    - Затем запускает реальное движение без сопротивления.
    - Часто в ту же сторону, куда был сброс.

### II. Методы идентификации и метрики

| **Этап** | **Признак** | **Что отслеживаем** | **Источник данных** |
| --- | --- | --- | --- |
| До | Узкий диапазон (флэт) | Цена в диапазоне, ATR падает | /market/kline |
|  | Сжатие ATR | Волатильность падает | Расчёт по свечам |
|  | Объём падает | Отсутствие интереса | Volume из /market/kline |
|  | OI растёт | Позиции набираются, но рынок стоит | /market/open-interest |
|  | Ликвидаций нет | Толпа «жива» → можно выносить | WebSocket /all-liquidation |
| Во время | Объёмный выброс | Всплеск объёма | Volume из kline |
|  | Длинная тень | Wick > 60% тела свечи | high, low, close, open |
|  | Ликвидации | В моменте — >1 млн USDT | WebSocket /all-liquidation |
|  | Нет закрепления | Закрытие внутри диапазона | close < breakout_level |
|  | Нет follow-up | После свечи объёмы падают | Volume[i+1:i+3] |
| После | Возврат в диапазон | Цена снова внутри | close из kline |
|  | Резкое падение объёма | Интерес выжат | Volume падает |
|  | Отсутствие новых ликвидаций | Рынок успокоился | WebSocket /all-liquidation |
|  | Движение начинается позже | Через 3–5 свечей, с объёмом и OI | volume, open-interest |

| Во время | Кластер ликвидаций | Сильный выброс ликвидаций > $1 млн на одной свече | WebSocket /v5/public/all-liquidation |
| --- | --- | --- | --- |
| После | Продолжение движения | Пробой high/low свечи shakeout через 3–5 баров | kline + breakout confirm |
| После | Ложное закрепление | Закрытие выше уровня → откат под него | close[i], close[i+1] |

### III. Формулы и логика обработки данных

1. **Узкий диапазон и сжатие:**

```python
range = max(high_N) - min(low_N)
avg_body = avg(high - low)
```

Условия:
range < 1.5 * avg_body
range < 0.5% от текущей цены

1. **Падение объёма:**

```python
volume_now / avg_volume_N < 0.6
```

1. **Рост OI без движения:**

```python
delta_OI = OI_now - OI_prev
price_change = abs(close - open) / open * 100

Условия:
delta_OI > 300 контрактов
price_change < 0.2%
```

1. **Всплеск объёма + длинная тень:**

```python
wick = high - max(open, close)
range = high - low
wick_ratio = wick / range

Условия:
wick_ratio > 0.6
volume_now > avg_volume * 1.8
ликвидации > 1 млн USDT за 10 сек
```

1. **Нет follow-up объёма:**

```python
avg(volume[i+1:i+3]) < volume[i] * 0.7
```

1. **Возврат внутрь диапазона:**

```python
close < breakout_level (если пробой вверх)
close > breakout_level (если пробой вниз)
```

1. **Поздний старт движения:**

```python
close[i+5] > high[i] (или < low[i])
avg(volume[i+3:i+5]) > avg(volume[i-5:i])
```

1. **Ложное закрепление:**

```python
if close[i] > breakout_level and close[i+1] < breakout_level:
    # ложное закрепление — это shakeout
```

1. **Продолжение после сброса:**

```python
if close[i+5] > high[i] and volume[i+5] > avg(volume[i-5:i]):
    # подтверждение: был сброс ликвидности
```

### IV. Логгер (пример)

```python
import time
import pandas as pd
from pybit.unified_trading import HTTP
import statistics

API_KEY = 'ТВОЙ_API_КЛЮЧ'
API_SECRET = 'ТВОЙ_API_СЕКРЕТ'
SYMBOL = 'BTCUSDT'
INTERVAL = '1'
CATEGORY = 'linear'
LOOKBACK = 20

session = HTTP(
    testnet=False,
    api_key=API_KEY,
    api_secret=API_SECRET
)

def get_ohlc():
    response = session.get_kline(
        category=CATEGORY,
        symbol=SYMBOL,
        interval=INTERVAL,
        limit=LOOKBACK + 1
    )
    return response['result']['list']

def get_open_interest():
    response = session.get_open_interest(
        category=CATEGORY,
        symbol=SYMBOL,
        intervalTime='1min',
        limit=LOOKBACK + 1
    )
    return response['result']['list']

def analyze_manipulation(ohlc_data, oi_data):
    signals = []

    for i in range(1, len(ohlc_data)):
        ohlc = ohlc_data[i]
        ohlc_prev = ohlc_data[i - 1]
        oi = oi_data[i]
        oi_prev = oi_data[i - 1]

        open_price = float(ohlc[1])
        high_price = float(ohlc[2])
        low_price = float(ohlc[3])
        close_price = float(ohlc[4])
        volume = float(ohlc[5])

        open_interest = float(oi['openInterest'])
        open_interest_prev = float(oi_prev['openInterest'])

        body = abs(close_price - open_price)
        wick = high_price - max(close_price, open_price)
        range_total = high_price - low_price
        wick_ratio = wick / range_total if range_total > 0 else 0
        volume_ratio = volume / statistics.mean([float(candle[5]) for candle in ohlc_data[i - LOOKBACK:i]])
        oi_delta = open_interest - open_interest_prev
        price_change = abs(close_price - open_price) / open_price * 100

        if wick_ratio > 0.6 and volume_ratio > 1.8:
            signals.append({
                'timestamp': ohlc[0],
                'signal': 'Сброс ликвидности (вверх)',
                'wick_ratio': round(wick_ratio, 2),
                'volume_ratio': round(volume_ratio, 2),
                'oi_delta': int(oi_delta),
                'price_change': round(price_change, 3)
            })

        if oi_delta > 1000 and price_change < 0.2:
            signals.append({
                'timestamp': ohlc[0],
                'signal': 'Рост OI без движения — ловушка',
                'wick_ratio': round(wick_ratio, 2),
                'volume_ratio': round(volume_ratio, 2),
                'oi_delta': int(oi_delta),
                'price_change': round(price_change, 3)
            })

    return signals

def log_data():
    while True:
        try:
            ohlc_data = get_ohlc()
            oi_data = get_open_interest()
            signals = analyze_manipulation(ohlc_data, oi_data)

            if signals:
                df = pd.DataFrame(signals)
                df.to_csv('shakeout_log.csv', mode='a', header=False, index=False)
                print(f"Обнаружены сигналы: {signals}")

            time.sleep(60)

        except Exception as e:
            print(f"Ошибка: {e}")
            time.sleep(10)

if __name__ == "__main__":
    log_data()

```
# Intentional Range Traps

1. **Алгоритмический флэт (Intentional Range Traps)**
- Рисуется боковик с красивыми уровнями
- Все ждут пробоя
- Но алго запускает серию **фейковых выходов вверх/вниз**, с диким откатом

## Манипуляция №11: Алгоритмический флэт (Intentional Range Traps)

### I. Что это и как работает

**Суть манипуляции:**

1. Алгоритм **искусственно формирует узкий визуальный флэт**, где:
    - границы чёткие (по High/Low),
    - внутри — контролируемое движение,
    - создаётся **ощущение подготовки к пробою**.
2. При приближении к границе:
    - алго делает **резкий "вброс" объёма** и пробивает уровень,
    - **активируются стопы и ликвидации**,
    - цена мгновенно **откатывается обратно**.

📌 Поведение **повторяется циклично**: вверх → вниз → вверх → откат

Цель — **выманивание ликвидности**, запутывание паттернов и создание ложных ожиданий.

### II. Как выглядит на графике

- 10+ свечей в узком канале
- High и Low почти ровные
- 1–2 свечи выбивают диапазон и сразу возвращаются внутрь
- На пробоях: ликвидации, всплеск объёма
- Нет follow-up движения после выхода из диапазона
- Поведение повторяется 2 и более раз

### III. Метрики и источники

| **Метрика** | **Что отслеживаем** | **Где брать** |
| --- | --- | --- |
| Узкий диапазон | High/Low за 20 свечей | /market/kline |
| Пробой + возврат | High > границы, но close < них | high[i], close[i] |
| Повторяемость фейков | ≥ 2 возврата в диапазон | фиксация по свечам |
| Ликвидации на пробоях | > 1M USDT | /all-liquidation |
| Отсутствие follow-through | Нет импульса после пробоя | объём, close[i+1] |

### IV. Формулы и логика распознавания

### 1. Диапазон за 20 свечей

```python
range_20 = max(high[-20:]) - min(low[-20:])
avg_body = statistics.mean([abs(c - o) for o, c in zip(open_list, close_list)])

if range_20 < avg_body * 2 and duration > 10:
    flag = "range trap forming"
```

### 2. Пробой и откат внутрь

```python
if high > range_top and close < range_top * 0.995:
    fake_breakout = True
```

### 3. Фейк повторяется

```python
fake_count += 1
if fake_count >= 2:
    flag = "intentional trap cycle"
```

### 4. Ликвидации + объём

```python
if volume_spike and liq_sum > 1_000_000 and close < range_top:
    mark = "range sweep with liquidation"
```

### V. Поведение бота

Если:

- Зафиксирован **визуально ровный диапазон** более 10 свечей
- Пробои вверх/вниз **не закрепляются** — цена возвращается
- На пробоях — **объём и ликвидации**
- Такое поведение **повторяется ≥ 2 раз**

**Тогда:**

- Бот ставит флаг range_trap_active = True
- **Запрещает вход по пробоям** диапазона
- Ожидает **реального выхода с follow-up**:
    - свеча с телом > 0.5%
    - объём > 2× среднего
    - нет возврата за 3 свечи

### VI. Python-блок (боевой логгер)

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
LOOKBACK = 25

session = HTTP(testnet=False, api_key=API_KEY, api_secret=API_SECRET)

def get_ohlc():
    response = session.get_kline(category=CATEGORY, symbol=SYMBOL, interval=INTERVAL, limit=LOOKBACK)
    return response['result']['list']

def get_oi():
    response = session.get_open_interest(category=CATEGORY, symbol=SYMBOL, intervalTime='1min', limit=LOOKBACK)
    return response['result']['list']

def get_mock_liquidations():
    return 1_500_000  # заглушка

def detect_range_trap(ohlc_data, oi_data):
    signals = []

    highs = [float(k[2]) for k in ohlc_data[:-1]]
    lows = [float(k[3]) for k in ohlc_data[:-1]]
    closes = [float(k[4]) for k in ohlc_data[:-1]]
    volumes = [float(k[5]) for k in ohlc_data[:-1]]
    avg_volume = statistics.mean(volumes)
    avg_body = statistics.mean([abs(float(k[4]) - float(k[1])) for k in ohlc_data[:-1]])

    range_top = max(highs)
    range_bottom = min(lows)
    range_size = range_top - range_bottom

    if range_size < avg_body * 2:
        last = ohlc_data[-1]
        ts = int(last[0])
        o, h, l, c, v = map(float, last[1:6])
        oi_now = float(oi_data[-1]['openInterest'])
        oi_prev = float(oi_data[-2]['openInterest'])
        delta_oi = oi_now - oi_prev
        liq_volume = get_mock_liquidations()

        wick_ratio = abs(h - max(o, c)) / (h - l + 1e-8)

        if h > range_top and c < range_top * 0.995 and liq_volume > 1_000_000 and wick_ratio > 0.5:
            signals.append((ts, 'Fake breakout UP', c, liq_volume, delta_oi))

        if l < range_bottom and c > range_bottom * 1.005 and liq_volume > 1_000_000 and wick_ratio > 0.5:
            signals.append((ts, 'Fake breakout DOWN', c, liq_volume, delta_oi))

    return signals

def log_range_trap():
    while True:
        try:
            ohlc = get_ohlc()
            oi = get_oi()
            signals = detect_range_trap(ohlc, oi)

            if signals:
                df = pd.DataFrame(signals, columns=['timestamp', 'event', 'close', 'liq_volume', 'oi_delta'])
                df.to_csv('range_trap_log.csv', mode='a', header=False, index=False)
                print(f"[ALERT] Обнаружено: {signals}")
            else:
                print("— Диапазон в норме, ловушек нет.")

            time.sleep(60)

        except Exception as e:
            print(f"[Ошибка]: {e}")
            time.sleep(15)

if __name__ == '__main__':
    log_range_trap()

```

### VII. Сводка по Intentional Range Trap

| **Метрика** | **Условие** |
| --- | --- |
| Диапазон по 20 свечам | < 2× средней свечи |
| Пробой и возврат | close < range_top (или > range_bottom) |
| Повторяемость | ≥ 2 фейка |
| Ликвидации и объём | > 1 млн USDT + wick_ratio > 0.5 |
| Нет follow-up | свеча без закрепления |
| Поведение бота | Вход запрещён, ждёт подтверждённый выход |

### 📌 Пояснение для программиста (по блоку логгера):

| **Компонент** | **Назначение** |
| --- | --- |
| detect_range_trap() | Проверяет диапазон, фиксирует фейки вверх и вниз |
| log_range_trap() | Пишет сигналы в range_trap_log.csv с метками времени и ликвидаций |
| range_top/bottom | Расчёт на основе High/Low за 20 свечей |
| wick_ratio | Показывает агрессивность ложного пробоя |
| delta_oi | Фиксирует вход/выход позиций на пробоях |
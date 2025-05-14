# Stair-Step Hunt)

1. **Стоповые «ступеньки» (Stair-Step Hunt)**

Суть манипуляции:

Алгоритм поэтапно двигает цену через локальные уровни, активируя кластеры стопов — на каждом уровне срабатывают новые триггеры толпы. Кажется, будто это восходящий тренд (или нисходящий), но на деле:

каждое движение вверх — это съём ликвидности,

на импульсах цена не закрепляется и переходит в новую ступень,

все входят поздно и по рынку, думая, что это тренд,

а затем рынок резко разворачивается**.**

## **Манипуляция №6: Стоповые «ступеньки» (Stair-Step Hunt)**

### I. Что это и как работает

**Суть манипуляции:**

Алгоритм поэтапно двигает цену через локальные уровни, активируя кластеры стопов — на каждом уровне срабатывают новые триггеры толпы. Визуально создаётся впечатление устойчивого тренда, но в реальности происходит:

- **импульсное срывание ликвидности на каждом уровне**,
- **отсутствие закреплений**,
- **втягивание толпы в поздние входы**,
- **накопление в диапазоне и разворот**.

**Фазовая структура:**

- **Фаза 1**: Серия импульсов вверх/вниз на объёме
- **Фаза 2**: Отсутствие закреплений, тени, рост OI
- **Фаза 3**: Пауза/накопление, резкий откат или разворот

### II. Как идентифицировать

**Визуально для трейдера:**

- График "шагает по ступенькам"
- Импульс → пауза → следующий импульс
- На каждой ступени:
    - всплеск объёма
    - рост Open Interest
    - слабое закрытие свечи (малая часть тела)
    - нет консолидации между движениями
    - серия ликвидаций в сторону "тренда"

**Типичные признаки:**

- Цена пробивает микроуровень → объёмный импульс
- Свеча с длинной тенью (не закрепление)
- Толпа входит по рынку (рост OI), но цена не идёт
- Через 2–3 ступени — рынок разворачивается или глохнет

### III. Методы и метрики

| **Метрика** | **Что отслеживаем** | **Где брать** |
| --- | --- | --- |
| Последовательные всплески объёма | Каждый импульс запускается объёмом | /market/kline |
| Рост OI при каждом всплеске | Толпа входит, думая что начался тренд | /market/open-interest |
| Цена не закрепляется | close < high (вверх) или close > low (вниз), wick_ratio > 0.6 | Kline OHLC |
| Нет консолидации | Снижение ATR или сжатие диапазона | Расчёт range/ATR |
| Ликвидации сериями | На каждом импульсе есть ликвидации — фиксация по WebSocket | /all-liquidation |
| Кол-во ступеней подряд | 3 и более — сигнал на накопление или ловушку | Kline + история сигналов |
| Пауза с падением объёма | Потеря инерции после серии | Kline |

### IV. Формулы и логика

**1. Всплеск объёма:**

```python
volume[i] > statistics.mean(volume[i-5:i-1]) * 1.8
```

**2. Рост OI при слабом движении:**

```python
delta_OI = OI_now - OI_prev
if delta_OI > 500 and price_change < 0.3:
    trap_positioning = True
```

**3. Неудачный пробой мини-уровня:**

```python
close[i] < high[i] * 0.998  # или close > low[i] * 1.002 для шортов
wick_ratio = (high[i] - close[i]) / (high[i] - low[i])
if wick_ratio > 0.6:
    no_confirmation = True

```

**4. Нет накопления:**

```python
range_N = max(high[i-N:i]) - min(low[i-N:i])
if range_N < atr_avg * 0.7:
    no_consolidation = True
```

**5. Повторяемость:**

```python
if len(step_impulse_signals[-10m]) >= 3:
    probable_trap = True
```

**6. Ликвидации:**

Фиксируем ≥ 3 ликвидации подряд на свечу в сторону импульса, но без продолжения движения. Данные с /all-liquidation.

### V. Поведение бота (анти-логика)

Если:

- за последние 10 минут было ≥3 импульса на объёме
- каждый сопровождался ростом OI ≥ 500
- свечи имели wick_ratio > 0.6
- ни одна не закрепилась за уровнем
- ликвидации присутствовали, но тренда нет

**Тогда:**

- бот **помечает участок как Stair-Step Hunt**
- **блокирует вход на пробой**
- **не открывает позицию в сторону ступеней**
- **ожидает структуру накопления и подтверждение объёмом**
- **при кульминационной свече против ступеней** (тело > 60%, OI падает) → **можен рассматривать вход в контртренд**

### VI. Python-логгер (обновлённая версия)

```python
from pybit.unified_trading import HTTP
import statistics, time

symbol = "BTCUSDT"
interval = "1"
lookback = 20

client = HTTP(api_key="API", api_secret="SECRET", testnet=False)

def get_klines():
    return client.get_kline(category="linear", symbol=symbol, interval=interval, limit=lookback + 3)["result"]["list"]

def get_oi():
    return client.get_open_interest(category="linear", symbol=symbol, intervalTime="1min", limit=lookback + 3)["result"]["list"]

def detect_stair_step(klines, oi_data):
    signals = []
    for i in range(1, len(klines) - 1):
        candle = klines[i]
        open_, high, low, close, volume = map(float, candle[1:6])
        prev_volumes = [float(c[5]) for c in klines[i-5:i]]
        avg_vol = statistics.mean(prev_volumes)
        wick_ratio = (high - close) / (high - low) if (high - low) > 0 else 0
        price_change = abs(close - open_) / open_ * 100
        oi_now = float(oi_data[i]['openInterest'])
        oi_prev = float(oi_data[i-1]['openInterest'])
        delta_oi = oi_now - oi_prev

        if volume > avg_vol * 1.8 and delta_oi > 500 and wick_ratio > 0.6 and price_change < 0.3:
            signals.append({
                'timestamp': int(candle[0]),
                'type': 'Stair-Step Impulse',
                'volume_ratio': round(volume / avg_vol, 2),
                'wick_ratio': round(wick_ratio, 2),
                'delta_oi': delta_oi
            })

    return signals

while True:
    try:
        klines = get_klines()
        oi_data = get_oi()
        signals = detect_stair_step(klines, oi_data)

        if signals:
            print(f"Ступенька зафиксирована: {signals[-1]}")
        else:
            print("Мониторинг продолжается...")

        time.sleep(30)

    except Exception as e:
        print(f"Ошибка: {e}")
        time.sleep(10)

```

### VII. Сводка по Stair-Step Hunt

| **Метрика** | **Условие** |
| --- | --- |
| Объём свечи | > 1.8× среднего за последние 5 свечей |
| Рост OI | > 500 контрактов |
| Закрытие свечи | close ≈ high/low, wick_ratio > 0.6 |
| Консолидация | отсутствует, range < ATR * 0.7 |
| Ликвидации | ≥ 3 на импульс, без follow-up |
| Повторяемость | ≥ 3 ступеней за 10 минут |
| Фаза 3 (пауза + кульминация) | падение объёма, тело в другую сторону, OI ↓ |
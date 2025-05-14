# Pattern Reversal Trap

1. **Алгоинверсии паттернов (Pattern Reversal Trap)**

Что делает:

Создает классический паттерн (например, двойное дно), но в последнюю секунду:

ломает его структуру,

разворачивает в противоположную,

часто втягивая бота в ложный пробой.

# **Финальная версия: Манипуляция №18 — Pattern Reversal Trap (v2.0)**

## I. Что это

**Pattern Reversal Trap** — манипуляция, при которой алгоритм:

1. Формирует узнаваемый паттерн (двойное дно, флаг, клин, голова-плечи).
2. Пробивает уровень как будто в сторону продолжения.
3. Демонстрирует всплеск объёма и положительную дельту.
4. Через 1–2 свечи происходит разворот и ликвидация вошедших.
5. Цена уходит в противоположную сторону, паттерн ломается.

📌 **Фазы ловушки**:

- До — узнаваемый паттерн, ожидание пробоя
- Во время — всплеск объёма, движение
- После — резкий разворот, возврат и снос позиций

## II. Как выглядит

- Визуально — классический паттерн (H&S, дно, треугольник)
- Резкий пробой на высокой дельте и объёме
- Через свечу — разворот
- OI не снижается (т.е. участники остались внутри)
- Часто свеча пробоя «зелёная», а следующая — «красная»

## III. Метрики и источники

| **Метрика** | **Что проверяем** | **Источник** |
| --- | --- | --- |
| Объём на пробое | > 1.8× среднего объёма последних 5–10 свечей | REST API: /kline |
| Дельта | Положительная дельта при красной свече | Расчёт: takerBuy - takerSell |
| Разворот свечи | close[i+1] < close[i] | Klines |
| OI | OI растёт, но цена не идёт | WebSocket или REST: /openInterest |
| Скорость движения | price_velocity > avg_velocity * 2 | Close[i] - Close[i-1] |

## IV. Формулы и логика

```python
volume_spike = v_now > avg_vol * 1.8  
# Всплеск объёма на пробое. Признак давления.

delta_divergence = (delta > 0 and close < open) or (delta < 0 and close > open)  
# Дельта и тело свечи не совпадают по направлению — ловушка.

price_reversal = close[i+1] < close[i]  
# После свечи пробоя — нет продолжения, начинается откат.

price_velocity = abs(close[i] - close[i-1])  
avg_velocity = mean(abs(close[n] - close[n-1]) for n in i-5 to i-1)  
velocity_spike = price_velocity > avg_velocity * 2  
# Алгоритм создаёт кратковременный импульс.

OI_rise = open_interest[i] - open_interest[i-1] > 500  
price_change = abs(close - open) / open < 0.2%  
# Рост открытого интереса, но цена не двигается = толпа попала в ловушку.

```

## V. Поведение бота

Бот должен:

- Проверить:
    - Есть ли объём на пробое > 1.8× среднего?
    - Есть ли свеча с быстрым разворотом после пробоя?
    - Есть ли расхождение между дельтой и телом свечи?
    - Увеличился ли OI без движения?
- Если совпало **2+ признака**:
    - ❌ **Не входит**
    - 📍 Помечает уровень как ловушечный
- Если совпало **3+ признака**:
    - 🛡 **Переходит в защитный режим на 3 свечи**

## VI. Логгер

```python
def log_pattern_trap(timestamp, price, flags):
    print(f"[{timestamp}] ⚠️ Pattern Reversal Trap Detected")
    print(f"↳ Price: {price}")
    print(f"↳ Flags: {', '.join(flags)}")
    print(f"↳ Phase: reversal after breakout")

```

## VII. Python-фильтр (боевой)

```python
def detect_pattern_reversal_trap(klines, oi_data, deltas):
    signals = []
    for i in range(5, len(klines) - 2):
        o, h, l, c, v = map(float, klines[i][1:6])
        c_next = float(klines[i + 1][4])
        avg_vol = sum([float(k[5]) for k in klines[i - 5:i]]) / 5

        volume_spike = v > avg_vol * 1.8
        delta = deltas[i] if i < len(deltas) else 0
        delta_div = (delta > 0 and c < o) or (delta < 0 and c > o)
        reversal = c_next < c

        oi_now = float(oi_data[i]['openInterest'])
        oi_prev = float(oi_data[i - 1]['openInterest'])
        oi_rise = oi_now - oi_prev > 500
        price_change = abs(c - o) / o * 100
        trapped = oi_rise and price_change < 0.2

        flags = []
        if volume_spike: flags.append("volume_spike")
        if delta_div: flags.append("delta_divergence")
        if reversal: flags.append("reversal_next_candle")
        if trapped: flags.append("oi_trap")

        if len(flags) >= 2:
            log_pattern_trap(klines[i][0], c, flags)
            signals.append((int(klines[i][0]), "Pattern Reversal Trap"))

    return signals

```

## VIII. Сводка условий

| **Признак** | **Порог** | **Фаза** |
| --- | --- | --- |
| Объём | > 1.8× среднего | Во время пробоя |
| Дельта ≠ Тело свечи | Дельта полож., свеча красная | Во время пробоя |
| Разворот после пробоя | close[i+1] < close[i] | После пробоя |
| Скорость цены | velocity > 2× средняя | Во время |
| OI без движения | ΔOI > 500 и price < 0.2% | После входа |
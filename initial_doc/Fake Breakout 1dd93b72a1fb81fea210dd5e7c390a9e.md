# Fake Breakout

1. **Ложные пробои (Fake Breakouts)**

**Как работает:**

- Пробивают хай/лоу диапазона
- Активируют стопы и лимитные входы «по учебнику»
- Моментально возвращаются обратно

**Цель:**

Собрать ликвидность, вскрыть стопы и заставить трейдера перевернуться

## **Манипуляция №1: Ложный пробой (Fake Breakout)**

### I. Как работает манипуляция. Идентификация

**Описание:**

Алгоритм делает пробой уровня (хай или лоу диапазона), создавая "по учебнику" сигнал для входа. Он сопровождает пробой всплеском объёма, визуальным паттерном или резким движением. Как только толпа входит — алго разворачивает рынок. Итог — пробой не подтверждается, все входящие вынуждены выходить или переворачиваться.

**Типичный сценарий:**

- Цена пробивает уровень.
- Происходит активация стопов или лимитных ордеров.
- Свеча закрывается ниже уровня пробоя.
- Объём есть, но дальнейшего движения нет.
- Следующие свечи разворачивают цену.
- Открытый интерес растёт, но цена не двигается.

### Как по-настоящему отличить ложный пробой от реального

Ниже приведены реальные признаки, выведенные из анализа поведения алгоритмов, HFT-логики и ордерфлоу.

1. **Асинхронность цены и объёма**
- При настоящем пробое цена растёт вместе с объёмом.
- При ложном — сначала идёт всплеск объёма, а цена не уходит дальше уровня.То есть: объём есть, а результата нет.Это называется «расходящийся пробой». Цена не подтверждает усилие.
1. **Импульсная тень и возврат под уровень**Если цена пробила хай, но свеча:
- закрылась ниже уровня,
- имеет длинную верхнюю тень,и особенно если следующая свеча уходит ниже — это не подтверждённый пробой.Алгоритм выманивает вход по рынку и возвращает цену обратно.

**3. Отсутствие продолжения объёма (follow-up)**

- Пробой начался, но дальше объём резко гаснет.
- Нет поддержки со стороны ленты или крупных участников.Это означает, что усилие было однократным — не для продолжения, а для сбора ликвидности.
1. **Мгновенный разворот через 1–2 свечи**
- Пробойная свеча выглядит как сигнал, но сразу за ней идёт резкий разворот.Это признак ложного движения. Алгоритм не даёт времени на реакцию.
1. **Поведение открытого интереса и дельты**(особенно важно на фьючерсах)
- Открытый интерес растёт, а цена не двигается — толпа входит в рынок, но не получает движения.
- Дельта положительная (преобладают покупки), а свеча красная — значит, покупают, но цену опускают.Это классический десинхрон и показатель ловушки.
1. **Пробой без логичного контекста**
- Нет накопления.
- Нет флэта или сжатия.
- Пробой начинается "из ниоткуда".Алгоритм моделирует поведение рынка без предварительной подготовки, чтобы вызвать эмоциональные входы.
1. **Кластерный анализ и стакан (если доступен)**
- В зоне пробоя наблюдаются крупные кластерные вбросы, но движение не продолжается.
- Цена касается зоны ликвидности и сразу отскакивает.
- Над уровнем нет лимитных ордеров — никто не поддерживает движение

### Ключ: не просто фильтровать сигналы, а переигрывать манипуляцию

**Анти-вход (Anti-Entry Logic)**Мы не входим на свечу пробоя, даже если:

- есть объём,
- есть визуальный паттерн,
- есть сильный импульс.

Вместо этого мы ждём pullback к уровню. И только после:

- если цена возвращается и отскакивает от уровня с поддержкой объёма — можно входить,
- если цена уходит ниже (или выше, при шорте) — это был ложный пробой.

Настоящий пробой проходит ретест уровня. Ложный — нет.

**Фильтр отрицательного сигнала (анти-сигнал)**Вводим запрет на вход, если свеча пробила уровень, но:

- закрылась внутри диапазона,
- объём резко упал,
- открытый интерес вырос, но цена не изменилась.

Бот помечает этот уровень как зону ложного сигнала и не торгует её минимум 15 минут.

**Дополнительное правило**

- Пробой вверх с ликвидациями лонгов — в 90% случаев это ложный пробой.
- Пробой вниз с ликвидациями шортов — чаще всего реальный.

Маркетмейкер не будет ликвидировать свою же сторону. Это даёт дополнительную точку в сторону оценки подлинности движения.)

### II. Методы идентификации и необходимые метрики

| **Признак манипуляции** | **Что отслеживаем** | **Источник данных (Bybit API/WebSocket)** |
| --- | --- | --- |
| Асинхронность объёма и цены | Всплеск объёма при минимальном движении цены | /v5/market/kline (OHLC, объём) |
| Длинная тень + закрытие ниже уровня | Свеча пробивает, но не закрепляется | /v5/market/kline |
| Отсутствие продолжения объёма (follow-up) | После пробоя объём падает | /v5/market/kline |
| Быстрый разворот (1–2 свечи) | Следующая свеча перекрывает пробойную | /v5/market/kline |
| Рост OI без движения | Открытый интерес растёт, цена стоит | /v5/market/open-interest |
| Дельта против движения | Покупки преобладают, а свеча падающая | /v5/market/recent-trade (через isBuyerMaker) |
| Отсутствие накопления / сжатия | Пробой "из ниоткуда", без флэта или диапазона | Свечи (kline) — расчёт ATR вручную |
| Ликвидации против движения | При пробое вверх — ликвидируются лонги | WebSocket: /v5/public/all-liquidation |
| Пустота в стакане / исчезновение заявок | Нет плотностей после пробоя, или лимитки снимаются | WebSocket: orderbook.25.{symbol} |
| Повторяемость фейков | Более 2 ложных пробоя за последние 10 свечей | Внутренний счётчик |
| Слабый ретест после пробоя | Возврат к уровню, но объём < 0.7× среднего или тень > 50% | /v5/market/kline |
| Пробой без накопления (расширено) | ATR текущей свечи > 1.5× средней за 5 предыдущих | /v5/market/kline (ручной расчёт) |

### III. Формулы и логика обработки данных

**1. Асинхронность объёма и цены**

- price_change = abs(close - open) / open * 100
- volume_ratio = volume / avg(volume_N)

Условия:

- volume_ratio > 1.8
- price_change < 0.3

**2. Импульсная тень и закрытие внутри уровня**

- wick_ratio = (high - close) / (high - low)
- close < breakout_level

Условия:

- wick_ratio > 0.6
- close не закрепляется выше уровня

**3. Нет follow-up объёма**

- avg_volume_next_3 = avg(volume[i+1], volume[i+2], volume[i+3])

Условие:

- avg_volume_next_3 < volume[i] * 0.7

**4. Мгновенный разворот**

- Пробой вверх → close[i+1] < low[i]
- Пробой вниз → close[i+1] > high[i]

**5. Рост OI без ценового движения**

- OI_change = OI[i] - OI[i-1]
- price_change < 0.2%

**6. Дельта против движения**

- delta = takerBuyVol - takerSellVol
- Если дельта положительная, а свеча красная — противоречие

**7. Отсутствие накопления**

- ATR_now = high - low
- avg_ATR = avg(ATR[i-N:i])

Условие:

- ATR_now > avg_ATR * 1.5

**8. Пустой стакан / снятие заявок**

- Определяется по резкому исчезновению крупных лимитных заявок в WebSocket orderbook
- Нет заявок после пробоя, или стенки исчезают — сигнал спуфинга
1. **Повторяемость ловушек (антиспам)**

```bash
fake_count = sum(fake_breakout_history[-10:])
if fake_count >= 2:
    observe_mode = 5  # свечей без входа
```

**10.Слабый ретест (фильтрация pullback)**

```yaml
if retest_volume < avg_volume * 0.7 or wick_ratio_retest > 0.5:
    skip_pullback_entry = True
```

1. **Логгер: fake_breakout_logger.py (финальная версия)**

```python
from pybit.unified_trading import HTTP
import pandas as pd
import time
import statistics
from datetime import datetime

# Конфигурация API
client = HTTP(
    testnet=False,
    api_key="ТВОЙ_API_КЛЮЧ",
    api_secret="ТВОЙ_API_СЕКРЕТ"
)

# Настройки символа и таймфрейма
symbol = "BTCUSDT"
interval = "1"  # 1m
lookback = 20

# История фейков и режим наблюдения
fake_breakout_history = []
fake_levels = []
observe_mode = 0

# Получение свечей
def get_klines():
    response = client.get_kline(
        category="linear",
        symbol=symbol,
        interval=interval,
        limit=lookback + 3
    )
    return response["result"]["list"]

# Запись фейкового пробоя в CSV
def log_fake_breakout(level, reason_dict):
    df = pd.DataFrame({
        "time": [datetime.utcnow()],
        "level": [level],
        "wick_ratio": [reason_dict.get("wick_ratio")],
        "volume_spike": [reason_dict.get("volume_spike")],
        "price_change": [reason_dict.get("price_change")],
        "from_range": [reason_dict.get("from_range", False)],
        "repeated": [reason_dict.get("repeated", False)]
    })
    df.to_csv("fake_breakouts_log.csv", mode="a", header=False, index=False)

# Фильтр ложного пробоя
def detect_fake_breakout(klines):
    global observe_mode

    candle = klines[-2]
    o, h, l, c, v = map(float, candle[1:6])
    prev_vols = [float(k[5]) for k in klines[-7:-2]]
    avg_vol = statistics.mean(prev_vols)

    atr_now = h - l
    avg_atr = statistics.mean([float(k[2]) - float(k[3]) for k in klines[-7:-2]])
    is_from_range = atr_now > avg_atr * 1.5

    price_change = abs(c - o) / o * 100
    volume_ratio = v / avg_vol
    wick = h - max(o, c)
    candle_range = h - l
    wick_ratio = wick / candle_range if candle_range > 0 else 0
    wick_heavy = wick_ratio > 0.6
    is_close_below_high = c < h * 0.995

    flags = [
        is_from_range,
        volume_ratio > 1.8,
        price_change < 0.3,
        wick_heavy,
        is_close_below_high
    ]

    if sum(flags) >= 3:
        fake_breakout_history.append(1)
        fake_levels.append(round(h, 2))
        if len(fake_breakout_history) > 10:
            fake_breakout_history.pop(0)

        if sum(fake_breakout_history[-10:]) >= 2:
            observe_mode = 5

        log_fake_breakout(level=round(h, 2), reason_dict={
            "wick_ratio": round(wick_ratio, 2),
            "volume_spike": round(volume_ratio, 2),
            "price_change": round(price_change, 2),
            "from_range": is_from_range,
            "repeated": True
        })

        return True, {
            "wick_ratio": round(wick_ratio, 2),
            "volume_spike": round(volume_ratio, 2),
            "price_change": round(price_change, 2)
        }
    else:
        fake_breakout_history.append(0)
        if len(fake_breakout_history) > 10:
            fake_breakout_history.pop(0)
        return False, {}

# Цикл с логированием и выводом
while True:
    try:
        klines = get_klines()
        is_fake, metrics = detect_fake_breakout(klines)

        if is_fake:
            print(f"[FAKE] Обнаружен ложный пробой: {metrics}")
        else:
            print("Нет признаков ложного пробоя")

        time.sleep(30)

    except Exception as e:
        print(f"Ошибка: {e}")
        time.sleep(10)

```

**Что включено:**

- Подключение к Bybit через pybit
- Вычисление wick_ratio, price_change, volume_ratio
- Расчёт ATR и проверка на пробой "из диапазона"
- Поведенческая память (фейков за 10 свечей)
- CSV-логгер с сохранением ключевых параметров
- Консольный вывод в реальном времени

### VI. Python-фильтр

```python
import statistics

fake_breakout_history = []
fake_levels = []
observe_mode = 0

def detect_fake_breakout(klines):
    global observe_mode

    candle = klines[-2]
    o, h, l, c, v = map(float, candle[1:6])
    prev_vols = [float(k[5]) for k in klines[-7:-2]]
    avg_vol = statistics.mean(prev_vols)

    atr_now = h - l
    avg_atr = statistics.mean([float(k[2]) - float(k[3]) for k in klines[-7:-2]])
    is_from_range = atr_now > avg_atr * 1.5

    price_change = abs(c - o) / o * 100
    volume_ratio = v / avg_vol
    wick = h - max(o, c)
    candle_range = h - l
    wick_ratio = wick / candle_range if candle_range > 0 else 0
    wick_heavy = wick_ratio > 0.6
    is_close_below_high = c < h * 0.995

    flags = [
        is_from_range,
        volume_ratio > 1.8,
        price_change < 0.3,
        wick_heavy,
        is_close_below_high
    ]

    if sum(flags) >= 3:
        fake_breakout_history.append(1)
        fake_levels.append(round(h, 2))
        if len(fake_breakout_history) > 10:
            fake_breakout_history.pop(0)

        if sum(fake_breakout_history[-10:]) >= 2:
            observe_mode = 5

        log_fake_breakout(level=round(h, 2), reason_dict={
            "wick_ratio": round(wick_ratio, 2),
            "volume_spike": round(volume_ratio, 2),
            "price_change": round(price_change, 2),
            "from_range": is_from_range,
            "repeated": True
        })

        return True
    else:
        fake_breakout_history.append(0)
        if len(fake_breakout_history) > 10:
            fake_breakout_history.pop(0)
        return False

def update_observe_mode():
    global observe_mode
    if observe_mode > 0:
        observe_mode -= 1

```
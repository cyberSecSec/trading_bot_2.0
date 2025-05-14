# Order Flow Splitting

1. **Разделение ленты (Order Flow Splitting)**
- Алго разбивает один крупный ордер на **100 мелких**, чтобы не было видно агрессии
- Или наоборот: **несколько мелких в одну сторону**, чтобы имитировать тренд

## Манипуляция №8: Разделение ленты (Order Flow Splitting)

### I. Что это и как работает

**Суть манипуляции:**

Алгоритм скрывает реальное намерение крупного участника, разбивая заявки на десятки или сотни мелких ордеров, чтобы:

1. Не показать агрессию в стакане или ленте
2. Избежать внимания трейдеров, ориентирующихся на объёмы
3. Имитировать устойчивое движение, создавая иллюзию тренда

**Поведенческие фазы:**

- **Фаза I — накопление:** алго заходит “шумом”, разбивая объёмы
- **Фаза II — маскированное давление:** направленный импульс без объёма
- **Фаза III — фиксация / выход:** свечи “глохнут”, начинается откат

**Примеры:**

- Вместо 1 ордера на 1 млн USDT → 150× ордеров по 6–9k
- В ленте — 50–100 сделок подряд одного направления
- Цена двигается, но объём не растёт

### II. Как выглядит на графике / в ленте

- В ленте: много мелких сделок (например, 0.01–0.3 BTC), почти подряд
- Объём свечи невелик, несмотря на высокую активность
- Направление сохраняется, но **дельта и OI ведут себя “глухо”**
- Все сделки — одинакового размера (например, 0.05 BTC 40 раз)
- Между сделками — минимальные интервалы (HFT-шум)

### III. Методы и метрики для распознавания

| **Метрика** | **Что отслеживаем** | **Где брать** |
| --- | --- | --- |
| Повторяющиеся однонаправленные сделки | Алго зашумляет Buy/Sell | /v5/market/recent-trade |
| Средний объём сделки падает | Общее кол-во сделок растёт | recent-trade + группировка |
| Все сделки — одинаковый размер | Признак алго-сплита | округлённые qty |
| Интервалы между сделками | < 200–250 мс | timestamp трейдов |
| Объём свечи не растёт | Несмотря на большое количество сделок | /market/kline |
| Однонаправленность | > 80% сделок одной стороны (buy/sell) | t['side'] из ленты |

### IV. Формулы и логика бота

1. **Средний объём сделки + плотность:**

```python
avg_trade_size = sum(volumes) / len(volumes)
if avg_trade_size < 0.08 and len(volumes) > 40:
    flag_split = True
```

1. **Повторяемость одного объёма:**

```python
from collections import Counter
rounded_volumes = [round(v, 3) for v in volumes]
most_common = Counter(rounded_volumes).most_common(1)[0]
if most_common[1] / len(volumes) > 0.6:
    signal_split_pattern = True
```

1. **Интервалы между сделками:**

```python
intervals = [timestamps[i] - timestamps[i-1] for i in range(1, len(timestamps))]
if all(i < 250 for i in intervals):
    micro_hft = True
```

1. **Stealth Volume (маскировка активности):**

```python
stealth_ratio = volume_candle / len(volumes)
if stealth_ratio < 0.002:
    stealth_flag = True
```

1. **Однонаправленный агрессор:**

```python
buy_ratio = sum(1 for t in trades if t['side'] == 'Buy') / len(trades)
if buy_ratio > 0.8 or buy_ratio < 0.2:
    directional_flow = True
```

### V. Поведение бота

Если одновременно наблюдаются:

- ≥ 40 сделок за 10 секунд
- средний объём сделки < 0.08 BTC
- 60% сделок одного размера
- интервалы между сделками < 250 мс
- однонаправленность > 80%
- объём свечи не растёт → **stealth**

**Тогда:**

- order_flow_split = True
- зона маркируется как **маскированное давление**
- бот **переходит в режим блокировки входа**
- **ожидает подтверждения объёма или дельты** (follow-up)
- если после split идёт объёмный импульс с пробоем → бот переключается в **режим наблюдения**

### VI. Python-функция детекции (обновлённая)

```python
from collections import Counter

def detect_order_flow_splitting(recent_trades, volume_candle):
    volumes = [float(t['qty']) for t in recent_trades]
    timestamps = [int(t['T']) for t in recent_trades]
    sides = [t['side'] for t in recent_trades]

    if len(volumes) < 10:
        return {"flow_split": False}

    avg_volume = sum(volumes) / len(volumes)
    rounded_volumes = [round(v, 3) for v in volumes]
    most_common = Counter(rounded_volumes).most_common(1)[0]
    intervals = [timestamps[i] - timestamps[i-1] for i in range(1, len(timestamps))]
    stealth_ratio = volume_candle / len(volumes)
    buy_ratio = sides.count("Buy") / len(sides)

    conditions = {
        "flow_split": False,
        "avg_volume": round(avg_volume, 3),
        "most_common_ratio": round(most_common[1] / len(volumes), 2),
        "interval_avg": sum(intervals) / len(intervals),
        "stealth_ratio": round(stealth_ratio, 5),
        "direction": "Buy" if buy_ratio > 0.8 else "Sell" if buy_ratio < 0.2 else "Mixed"
    }

    if (
        avg_volume < 0.08 and
        most_common[1] / len(volumes) > 0.6 and
        len(volumes) >= 30 and
        all(i < 250 for i in intervals) and
        stealth_ratio < 0.002
    ):
        conditions["flow_split"] = True

    return conditions

```

### VII. Сводка по Order Flow Splitting

| **Метрика** | **Условие** |
| --- | --- |
| Средний объём сделки | < 0.08 BTC |
| Кол-во сделок в серии | > 40 за 10 сек |
| Один объём повторяется | > 60% |
| Время между сделками | < 200–250 мс |
| Stealth объём свечи | < 0.002 BTC/сделку |
| Направленность | > 80% сделок одной стороны (buy/sell) |
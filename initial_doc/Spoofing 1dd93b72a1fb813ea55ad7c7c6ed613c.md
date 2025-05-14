# Spoofing

1. **Вброс объема в стакан (Spoofing)**
- Алгоритм ставит крупный ордер (например, на продажу) → все думают, что будет падение
- Люди начинают продавать → алго снимает ордер и **покупает по низу**

Это прямое манипулирование «психологией толпы»

## **🧨 Манипуляция №3: Вброс объёма в стакан (Spoofing)**

### **1. Что это**

**Spoofing** — манипуляция через выставление крупных лимитных заявок, которые не предполагается исполнять. Цель — спровоцировать других участников на реакцию (чаще розничных трейдеров), а затем отменить заявку, получив преимущество за счёт вызванного движения цены.

🧠 Поведение:

- Крупная заявка появляется близко к лучшей цене (bid/ask)
- Не исполняется, исчезает до касания
- Вызывает движение в свою сторону
- После отмены — разворот
- Повторяется сериями (≥3 за 2 мин)

### **2. Как выглядит**

- Заявка появляется на 2–5 тиков от best bid/ask
- Размер заявки ≥ 5–6x среднего объёма уровня
- Время жизни < 1.5–2 сек
- Нет реального исполнения на этом уровне
- После снятия заявки: цена разворачивается
- Поведение повторяется — бот должен видеть это как серию
- Часто сопровождается **зеркальной активностью** на противоположной стороне

### **3. Метрики и источники**

1. **Order Book**
- bid/ask стаканы (до 25 уровней)
- объёмы на уровнях
- динамика появления/исчезновения
- расчёт времени жизни quote'ов
- относительная глубина по сторонам

📡 orderbook.25.BTCUSDT (Bybit WebSocket)

1. **Лента сделок (Trade Flow)**
- агрессор
- объём вблизи spoof-уровня
- подтверждение реальных исполнений

📡 publicTrade.BTCUSDT

1. **Контекст**
- Реакция цены после исчезновения
- Наличие противоположной агрессии
- Объём реального исполнения на spoof-уровне
1. **Расширенные показатели**
- Quote Lifetime (время жизни ордера)
- Tick-to-tick Depth Delta
- Execution Discrepancy
- Cancel Speed (объём снятия / время)
- Spoof Intensity (взвешенная оценка)
- Spoof Per Minute (частота попыток)

### **4. Формулы и логика**

```python
# Проверка на крупный объём рядом с ценой
local_liquidity = sum(order['size'] for order in bids if abs(order['price'] - best_bid) < best_bid * 0.0015)
median_liquidity = median([order['size'] for order in bids])
if local_liquidity > median_liquidity * 6:
    potential_spoof = True

# Скорость отмены
cancel_speed = size_removed / time_window_ms  # tick/ms

# Повторяемость
spoof_events_last_2min = count_spoof_events(window=120)
if spoof_events_last_2min >= 3:
    spoof_mode = True

# Проверка отсутствия исполнения и скорости снятия
quote_lifetime = disappear_timestamp - appear_timestamp
if potential_spoof and quote_lifetime < 1500 and no_trades_at_price:
    spoof_confirmed = True

# Интенсивность spoof
intensity = (local_liquidity / quote_lifetime) * (1 + (1 / (abs(spoof_price - best_bid) + 1)))

# Разворот после spoof
if spoof_confirmed and price_moved_opposite > tick_size * 3:
    spoof_effect = True

```

### **5. Поведение бота**

1. Блокировка входа в сторону spoof-заявки при подтверждении манипуляции
2. При развороте после снятия заявки + встречной агрессии — возможен вход против spoof
3. При ≥3 spoof-сценариях за 2 минуты: включается **режим защиты**, усиливаются фильтры
4. При серии spoof + отсутствие реального исполнения + движение против манипуляции: сигнал считается приоритетным на вход в разворот
5. В рамках защиты: **анти-спуф-зона** создаётся вблизи spoof-уровня, где запрещён вход
6. Бот отслеживает **spoof-репетиции** на одном и том же уровне — наращивает агрессию в противоход при повторе

### **6. Логгер spoof-активности (Python)**

```python
spoof_log = {
    'timestamp': snapshot['timestamp'],
    'price': best_bid,
    'side': 'buy',
    'local_liquidity': sum(liquidity_window),
    'median_volume': median_volume,
    'lifetime': quote_lifetime,
    'executed': False,
    'price_reversal': price_moved_opposite,
    'spoof_intensity': intensity,
    'cancel_speed': cancel_speed,
    'spoof_per_minute': spoof_events_last_2min,
    'status': 'confirmed' if spoof_confirmed else 'suspected'
}
```

### **7. Python-фильтр**

```python
def detect_spoof(snapshot_history, trades, depth=25, lifetime_limit=1.5):
    spoof_events = []
    for i in range(1, len(snapshot_history)):
        prev = snapshot_history[i - 1]
        curr = snapshot_history[i]
        for p, s in prev['bids']:
            median_vol = median([x[1] for x in prev['bids']])
            is_gone = not any(cp == p and cs >= s*0.8 for cp, cs in curr['bids'])
            life = curr['timestamp'] - prev['timestamp']
            if s > median_vol * 6 and is_gone and life < lifetime_limit:
                spoof_events.append({
                    'side': 'buy',
                    'price': p,
                    'lifetime': life,
                    'volume': s,
                    'timestamp': curr['timestamp'],
                })
    return spoof_events

```

### **8. Сводка условий**

| **Метрика** | **Критерий** |
| --- | --- |
| Размер заявки | > 5–6× среднего уровня |
| Позиция | 2–5 тиков от best bid/ask |
| Время жизни | < 1.5–2 секунд |
| Частота повторений | ≥3 за 2 минуты |
| Исполнение по цене | Отсутствует |
| Движение после снятия | В противоположную сторону |
| Интенсивность spoof | > определённого порога |
| Cancel Speed | Выше средней по рынку |
| Spoof Per Minute | ≥ порогового значения |

## 🧨 **Манипуляция №3.1: Partial Execution Spoofing**

📌 Подтип манипуляции Spoofing — адаптирован для боевого режима HFT-бота

### **1. Что это**

**Partial Execution Spoofing** — это форма спуффинга, при которой лимитная заявка **частично исполняется**, а оставшийся объём **резко отменяется**, создавая видимость реального интереса. Алгоритм **маскирует манипуляцию**, добавляя «след в ленте», чтобы ввести в заблуждение участников, особенно HFT-системы, реагирующие на подтверждение объёма.

### **2. Как выглядит**

- В стакане появляется **крупная лимитная заявка** (на покупку или продажу)
- Часть этой заявки **исполняется** (обычно 5–40%)
- **Оставшийся объём снимается** очень быстро (в течение < 300–500 мс после исполнения)
- Цена **резко меняет направление** (обычно в противоположную сторону)
- В ленте появляется «подтверждение» объёма, но это **не соответствует полной заявке**
- Поведение повторяется **сериями** на одном или близких уровнях

### **3. Метрики и источники**

1. **Order Book (orderbook.25.BTCUSDT)**
- Размер лимитной заявки
- Время появления и снятия
- Остаток заявки после исполнения
- Глубина стакана по сторонам
1. **Лента сделок (publicTrade.BTCUSDT)**
- Объём исполнения по уровню spoof
- Время исполнения
- Агрессор (buyer/seller)
1. **Вспомогательные метрики**
- Execution Ratio = executed_qty / initial_qty
- Cancel After Execution Delay — задержка между исполнением и отменой
- Remaining Cancelled Size — сколько отменено после частичного исполнения
- Post-Cancel Price Reversal — насколько изменилась цена после снятия
- Spoof Intensity — комбинированный параметр

### **4. Формулы и логика**

```python
# Расчёт доли исполнения от заявки
execution_ratio = executed_qty / initial_qty

# Расчёт отменённого остатка
cancelled_qty = initial_qty - executed_qty

# Задержка между частичным исполнением и отменой
cancel_delay = cancel_timestamp - last_exec_timestamp

# Интенсивность манипуляции
intensity = (cancelled_qty / cancel_delay) * (1 + (1 / (abs(spoof_price - best_bid) + 1)))

# Условия фиксации Partial Spoof
if execution_ratio > 0.05 and execution_ratio < 0.4 \
   and cancel_delay < 500 \
   and cancelled_qty > initial_qty * 0.5 \
   and price_moved_opposite > tick_size * 3:
       partial_spoof_confirmed = True

```

### **5. Поведение бота**

1. 📛 **Не открывает позицию в сторону частично исполненной заявки**, если:
    - исполнено < 40%
    - остаток снят быстро
    - есть разворот после отмены
2. 📉 Если после отмены остатка происходит **обратное движение** цены — возможен **вход в противоход**
3. 🧠 Если ≥2 таких события за 1 минуту на близких уровнях — включается **анти-сигнал зона**
4. ⚠️ Если partial spoof идёт **на сильном уровне поддержки/сопротивления**, бот усиливает фильтрацию фейковых пробоев
5. 🔄 Поведение распознаётся **как переходное** между классическим spoof и trap

### **6. Логгер Partial Spoof (Python)**

```python
partial_spoof_log = {
    'timestamp': cancel_timestamp,
    'price': spoof_price,
    'side': 'buy',
    'initial_qty': initial_qty,
    'executed_qty': executed_qty,
    'cancelled_qty': cancelled_qty,
    'execution_ratio': execution_ratio,
    'cancel_delay_ms': cancel_delay,
    'intensity': intensity,
    'post_cancel_price_move': price_moved_opposite,
    'status': 'confirmed' if partial_spoof_confirmed else 'suspected'
}

```

### **7. Python-фильтр**

```python
def detect_partial_spoof(orderbook_snapshots, trades, tick_size):
    events = []
    for snapshot in orderbook_snapshots:
        for order in snapshot.get('tracked_orders', []):
            execution_ratio = order['executed_qty'] / order['initial_qty']
            cancel_delay = order['cancel_ts'] - order['last_exec_ts']
            cancelled_qty = order['initial_qty'] - order['executed_qty']
            price_movement = order['post_cancel_price_move']

            if 0.05 < execution_ratio < 0.4 and \
               cancel_delay < 500 and \
               cancelled_qty > order['initial_qty'] * 0.5 and \
               price_movement > tick_size * 3:
                events.append({
                    'price': order['price'],
                    'side': order['side'],
                    'execution_ratio': execution_ratio,
                    'cancel_delay': cancel_delay,
                    'cancelled_qty': cancelled_qty,
                    'post_cancel_move': price_movement,
                    'timestamp': order['cancel_ts'],
                    'status': 'confirmed'
                })
    return events

```

### **8. Сводка условий**

| **Условие** | **Порог/Критерий** |
| --- | --- |
| Доля исполнения (execution_ratio) | > 5% и < 40% |
| Отменённый остаток | > 50% от заявки |
| Время между исполнением и отменой | < 500 мс |
| Движение цены после отмены | > 3 тика в противоположную сторону |
| Интенсивность (intensity) | Выше среднего по выборке |
| Повторяемость | ≥2 за 1 минуту |
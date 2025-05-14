# Data Injection Trap

1. **🛠 Манипуляция №17: Агрессивная перерисовка объёма и дельты (Data Injection Trap)**

**📌 Полный боевой разбор: механика, признаки, метрики, логика бота, детектор, кодовые фрагменты.**

# **Манипуляция №17— Data Injection Trap**

### I. Что это

Data Injection Trap — ловушка, в которой HFT-алгоритм:

- искусственно создаёт всплеск дельты и объёма,
- не даёт цене подтверждения движения,
- ловит трейдера/бота, реагирующего на импульс,
- и разворачивает рынок после входа.

### II. Как выглядит

- Всплеск дельты и объёма, но свеча короткая
- Цена стоит, но buy/sell-дельта резко доминирует
- В стакане быстро появляются и исчезают заявки
- Перед этим: рынок был тихим

### III. Цель манипуляции

Запустить бота/алгоритм, торгующего на:

- импульс объёма + дельты
- buy/sell-доминирование
- всплеск стакана
- быстрый объёмный вход

### IV. Метрики и источники

| **Метрика** | **Что отслеживаем** | **Где брать** |
| --- | --- | --- |
| Объём свечи | Всплеск > 1.8× среднего | REST: GET /market/kline |
| Дельта (buy/sell) | Явная доминация одной стороны (buy или sell > 2×) | WebSocket: recent-trade |
| Общая дельта | taker_buy - taker_sell, и сравнение с медианой | WebSocket |
| Изменение цены | Меньше 0.2% при всплеске дельты | close[-1] - close[-2] |
| Диапазон свечи | Короткая свеча (range < 70% среднего) | high - low |
| Поведение стакана | ≥3 отмены заявок за < 0.3 сек | WebSocket: /orderbook.25 |
| Контекст до ловушки | 2–3 свечи — низкий объём и слабая дельта | История свечей и ленты |
| Частота ловушек | ≥2 в последних 10 свечах — включить observe | Внутренний счётчик |

### V. Логика фильтрации

Бот считает ситуацию ловушкой, если выполняются 3 и более признаков:

- ✅ volume_spike = current_vol > mean_vol * 1.8*(всплеск объёма относительно среднего)*
- ✅ delta_net = taker_buy - taker_sell*(нетто-доминирование одной стороны)*
- ✅ delta_spike = delta_net > median * 2*(дисбаланс дельты)*
- ✅ short_candle = candle_range < avg_range * 0.7*(короткая свеча — движение не подтверждено)*
- ✅ price_change = abs(close - open) / open < 0.2%*(цена почти не изменилась)*
- ✅ buy/sell_domination = max(buy, sell) / min(buy, sell) > 2*(одна сторона явно преобладает)*
- ✅ fast_cancels = count(cancel_time < 0.3s) ≥ 3*(быстрые отмены заявок — HFT-манипуляция)*
- ✅ flat_inside = high < prev_high and low > prev_low*(ловушка разворачивается в середине флета)*
- ✅ velocity_spike = volume / range > 3× среднее*(искусственно раздутый импульс)*

📌 **Доп. условие**: если за последние 10 свечей — 2 или больше ловушек,

бот включает observe_mode на 5 свечей (временная блокировка входов).

### VI. Код (Python, боевой блок v2.2)

```python
import statistics
import datetime

bot_status = {
    "observe_mode": 0,
    "trap_history": []
}

def log_trap_extended(price, reason_flags, trap_type="DataInjection", phase="during"):
    print(f"[{datetime.datetime.utcnow()}] ⚠️ Trap Detected ({trap_type})")
    print(f"↳ Price: {price}")
    print(f"↳ Phase: {phase}")
    print(f"↳ Flags: {', '.join(reason_flags)}")

def is_data_injection_trap(klines, delta_list, orderbook_snapshots):
    last_candle = klines[-1]
    o, h, l, c, v = map(float, last_candle[1:6])
    
    volumes = [float(k[5]) for k in klines[-11:-1]]
    avg_vol = statistics.mean(volumes)
    volume_spike = v > avg_vol * 1.8

    candle_range = h - l
    avg_range = statistics.mean([float(k[2]) - float(k[3]) for k in klines[-11:-1]])
    short_candle = candle_range < avg_range * 0.7

    velocity = v / candle_range if candle_range else 0
    avg_velocity = statistics.mean([float(k[5]) / (float(k[2]) - float(k[3]) + 1e-6) for k in klines[-11:-1]])
    velocity_spike = velocity > avg_velocity * 3

    buy_now, sell_now = delta_list[-1]
    delta_net = buy_now - sell_now
    delta_median = statistics.median([(b - s) for b, s in delta_list[-11:-1]])
    delta_spike = delta_net > delta_median * 2

    buy_dom = buy_now > sell_now * 2
    sell_dom = sell_now > buy_now * 2
    has_domination = buy_dom or sell_dom

    low_activity_before = all([
        volumes[i] < avg_vol * 0.8 and abs(delta_list[-4+i][0] - delta_list[-4+i][1]) < abs(delta_median * 0.8)
        for i in range(-3, 0)
    ])

    price_change = abs(c - o) / o * 100
    price_static = price_change < 0.2

    # Проверка на flat-trap
    prev_high = float(klines[-2][2])
    prev_low = float(klines[-2][3])
    flat_inside = h < prev_high and l > prev_low

    lifetimes = []
    for snapshot in orderbook_snapshots[-5:]:
        for level in snapshot.get("asks", [])[:5] + snapshot.get("bids", [])[:5]:
            created = level.get("timestamp")
            removed = level.get("cancellation_timestamp")
            if created and removed:
                lifetime = removed - created
                if lifetime < 0.3:
                    lifetimes.append(lifetime)
    fast_cancels = len(lifetimes) >= 3

    checks = {
        "volume_spike": volume_spike,
        "delta_spike": delta_spike,
        "short_candle": short_candle,
        "quiet_context": low_activity_before,
        "price_static": price_static,
        "fast_cancels": fast_cancels,
        "domination": has_domination,
        "flat_inside": flat_inside,
        "velocity_spike": velocity_spike
    }

    passed = [k for k, v in checks.items() if v]

    if len(passed) >= 3:
        log_trap_extended(price=c, reason_flags=passed, phase="during")
        bot_status["trap_history"].append(1)
        if len(bot_status["trap_history"]) > 10:
            bot_status["trap_history"].pop(0)
        if sum(bot_status["trap_history"][-10:]) >= 2:
            bot_status["observe_mode"] = 5
        return True
    else:
        bot_status["trap_history"].append(0)
        if len(bot_status["trap_history"]) > 10:
            bot_status["trap_history"].pop(0)
        return False

def update_bot_status():
    if bot_status["observe_mode"] > 0:
        bot_status["observe_mode"] -= 1

def recovery_check(klines, delta_list):
    recent_vols = [float(k[5]) for k in klines[-3:]]
    avg_vol = statistics.mean([float(k[5]) for k in klines[-11:-1]])
    recent_deltas = [abs(b - s) for b, s in delta_list[-3:]]
    avg_delta = statistics.mean([abs(b - s) for b, s in delta_list[-11:-1]])
    if all(v < avg_vol * 1.2 for v in recent_vols) and all(d < avg_delta * 1.2 for d in recent_deltas):
        bot_status["observe_mode"] = 0  # Выход из observe_mode

# Интеграция
def strategy_decision(klines, delta_list, orderbook_snapshots):
    update_bot_status()
    recovery_check(klines, delta_list)
    if bot_status["observe_mode"] > 0:
        return "wait"
    elif is_data_injection_trap(klines, delta_list, orderbook_snapshots):
        return "ignore_trap"
    else:
        return "evaluate_entry"

```

### VII. Сводка условий

| **Признак** | **Порог** | **Фаза рынка** |
| --- | --- | --- |
| Объём | > 1.8× среднего | во время |
| Дельта (net) | > 2× медианы | во время |
| Свеча короткая | < 70% от средней | во время |
| До ловушки | объём и дельта < 80% | до |
| Быстрые отмены | ≥3 заявок < 0.3 сек | во время |
| Buy/Sell-доминация | > 2× | во время |
| Частота ловушек | ≥2 за 10 свечей | после |
| Velocity свечи | > 3× среднего | уточнение сигнала |
| Flat Inside (ловушка) | внутри 2 предыдущих свечей | фильтр риска |

### VIII. Логгер (уже встроен в код)

```python
log_trap_extended()
```

Выводит фазу, цену, тип ловушки и все признаки.
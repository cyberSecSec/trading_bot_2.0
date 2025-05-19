# Задача: Реализация сервиса для данных о ликвидациях в Bybit

## Контекст
В рамках разработки модуля Trading APIs & Exchange необходимо реализовать поддержку для получения и обработки данных о ликвидациях на бирже Bybit. Этот функционал является частью второго этапа разработки модуля: "Реализация сервисов для рыночных данных", описанного в бэклоге проекта.

Ликвидации - это события, происходящие на фьючерсном рынке, когда торговая позиция трейдера принудительно закрывается биржей из-за недостаточного обеспечения для поддержания маржинальных требований. Информация о ликвидациях представляет высокую ценность для анализа рыночной динамики и выявления потенциальных точек резких движений цены.

Текущая кодовая база уже содержит:
1. Модель данных `LiquidationData` для представления информации о ликвидациях
2. Интерфейс `IMarketDataStreamProvider` с методами для работы с ликвидациями
3. Реализацию провайдера `BybitMarketDataStreamProvider` с заглушкой для метода получения ликвидаций

## Задача
Реализовать функциональность для получения данных о ликвидациях в реальном времени через WebSocket API Bybit, включая:

1. Полную реализацию метода `subscribe_to_liquidations` в классе `BybitMarketDataStreamProvider`:
   - Настройку подписки на канал ликвидаций Bybit
   - Обработку сообщений о ликвидациях
   - Нормализацию данных в формат `LiquidationData`
   - Передачу данных через callback-функцию

2. Создание обработчика сообщений о ликвидациях (`LiquidationMessageHandler`):
   - Парсинг WebSocket сообщений о ликвидациях
   - Выделение релевантной информации о ликвидированных позициях
   - Преобразование данных в унифицированный формат

3. Разработку системы для анализа ликвидаций:
   - Фильтрацию ликвидаций по размеру (определение крупных ликвидаций)
   - Обнаружение каскадных ликвидаций (множественные ликвидации за короткий промежуток времени)
   - Генерацию уведомлений о значительных ликвидационных событиях

4. Реализацию подхода к отказоустойчивости:
   - Обработку специфических ошибок WebSocket для канала ликвидаций
   - Механизмы восстановления подписки при сбоях соединения
   - Мониторинг активности канала ликвидаций

## Технические требования

### 1. Реализация подписки на данные о ликвидациях через WebSocket

```python
async def subscribe_to_liquidations(
    self, 
    symbol: str,
    callback: Callable[[LiquidationData], Awaitable[None]]
) -> str:
    """
    Подписывается на поток ликвидаций в реальном времени.
    
    Args:
        symbol: Торговый символ (например, "BTCUSDT").
        callback: Асинхронная функция обратного вызова, которая будет вызываться
                 при получении новых данных. Принимает объект LiquidationData.
        
    Returns:
        Идентификатор подписки, который может быть использован для отписки.
        
    Raises:
        VantaAPIError: При ошибке взаимодействия с API биржи.
        VantaWebSocketError: При ошибке WebSocket соединения.
    """
    # Реализация метода
```

### 2. Обработчик сообщений о ликвидациях

```python
class LiquidationMessageHandler:
    """
    Обработчик сообщений о ликвидациях от WebSocket API Bybit.
    
    Отвечает за парсинг сообщений о ликвидациях и их преобразование
    в унифицированный формат LiquidationData.
    """
    
    # Регулярное выражение для извлечения информации из темы канала
    TOPIC_PATTERN = re.compile(r'^liquidation\.([A-Za-z0-9]+)$')
    
    def __init__(self, callback: Callable[[LiquidationData], Awaitable[None]]):
        """
        Инициализирует обработчик сообщений о ликвидациях.
        
        Args:
            callback: Асинхронная функция обратного вызова, которая будет вызываться
                     при получении новых данных. Принимает объект LiquidationData.
        """
        self.callback = callback
    
    async def handle_message(self, message: Dict[str, Any]) -> bool:
        """
        Обрабатывает входящее сообщение WebSocket.
        
        Args:
            message: Полученное сообщение
            
        Returns:
            bool: True, если сообщение было обработано, иначе False
        """
        # Реализация метода
```

### 3. Анализатор ликвидаций

```python
class LiquidationAnalyzer:
    """
    Анализатор данных о ликвидациях.
    
    Предоставляет функционал для фильтрации, агрегирования и выявления
    значимых паттернов в потоке ликвидаций.
    """
    
    def __init__(self, 
                 large_liquidation_threshold: Decimal = Decimal('10.0'),
                 cascade_time_window_seconds: int = 60,
                 cascade_min_volume: Decimal = Decimal('50.0')):
        """
        Инициализирует анализатор ликвидаций.
        
        Args:
            large_liquidation_threshold: Пороговое значение объема для определения крупной ликвидации
            cascade_time_window_seconds: Временное окно для определения каскада ликвидаций (в секундах)
            cascade_min_volume: Минимальный суммарный объем для определения каскада ликвидаций
        """
        # Инициализация параметров
    
    def is_large_liquidation(self, liquidation: LiquidationData) -> bool:
        """
        Определяет, является ли ликвидация крупной.
        
        Args:
            liquidation: Данные о ликвидации
            
        Returns:
            bool: True, если ликвидация является крупной
        """
        # Реализация метода
    
    def analyze_liquidations(self, 
                             recent_liquidations: List[LiquidationData]) -> Dict[str, Any]:
        """
        Анализирует список недавних ликвидаций для выявления паттернов.
        
        Args:
            recent_liquidations: Список недавних ликвидаций
            
        Returns:
            Dict[str, Any]: Результаты анализа, включая информацию о каскадах и крупных ликвидациях
        """
        # Реализация метода
```

## Требования к реализации

1. **Подписка на данные:** Метод `subscribe_to_liquidations` должен корректно формировать название канала для Bybit API (формат "liquidation.{symbol}") и выполнять подписку на этот канал.

2. **Обработка сообщений:** `LiquidationMessageHandler` должен правильно парсить сообщения, учитывая формат данных Bybit:
   ```json
   {
       "topic": "liquidation.BTCUSDT",
       "data": [
           {
               "symbol": "BTCUSDT",
               "side": "Sell",
               "price": "48000.00",
               "qty": "2.5",
               "time": 1675942858664
           }
       ]
   }
   ```

3. **Анализ ликвидаций:** Система должна обнаруживать следующие паттерны:
   - Крупные ликвидации (объем выше порогового значения)
   - Каскадные ликвидации (серия ликвидаций одного направления в короткий промежуток времени)
   - Необычные всплески активности ликвидаций

4. **Обработка ошибок:** Реализация должна корректно обрабатывать:
   - Ошибки подписки на каналы
   - Потерю WebSocket соединения
   - Некорректные форматы данных
   - Отсутствие активности канала

5. **Оптимизация:** Код должен быть оптимизирован для эффективной работы с высокочастотными потоками данных:
   - Минимальное потребление памяти
   - Быстрая обработка сообщений
   - Асинхронная обработка событий

## Примеры использования

### Пример подписки на ликвидации

```python
from exchange_api.core.config import ClientConfig
from exchange_api.services.bybit.market_data_service import BybitMarketDataService
from models.market_data import LiquidationSide

# Создаем конфигурацию
config = ClientConfig(
    exchange_name="bybit",
    test_mode=True  # Используем тестовую сеть Bybit для разработки
)

# Создаем сервис для работы с рыночными данными
market_data_service = BybitMarketDataService(config)

# Обработчик для ликвидаций
async def liquidation_callback(liquidation):
    side_str = "Длинной" if liquidation.side == LiquidationSide.SELL else "Короткой"
    print(f"Ликвидация {side_str} позиции {liquidation.symbol}: "
          f"Цена: {liquidation.price}, Объем: {liquidation.quantity}")
    
    # Рассчитываем стоимость ликвидации
    value = liquidation.value()
    if value > 100000:  # Большая ликвидация (> $100k)
        print(f"⚠️ КРУПНАЯ ЛИКВИДАЦИЯ: ${value:,.2f}")

# Подписка на ликвидации по BTCUSDT
async def subscribe_to_liquidations_example():
    subscription_id = await market_data_service.subscribe_to_liquidations(
        symbol="BTCUSDT",
        callback=liquidation_callback
    )
    
    # ... используем подписку ...
    
    # Отписываемся от ликвидаций, когда они больше не нужны
    await market_data_service.unsubscribe_from_liquidations(subscription_id)
```

### Пример анализа ликвидаций

```python
from exchange_api.services.bybit.liquidation_analyzer import LiquidationAnalyzer
from decimal import Decimal

# Создаем анализатор ликвидаций
analyzer = LiquidationAnalyzer(
    large_liquidation_threshold=Decimal('5.0'),  # ≥ 5 BTC считается крупной ликвидацией
    cascade_time_window_seconds=30,              # Окно 30 секунд для определения каскада
    cascade_min_volume=Decimal('20.0')           # Суммарный объем ≥ 20 BTC для каскада
)

# Обработчик для ликвидаций с анализом
async def advanced_liquidation_callback(liquidation):
    # Регистрируем ликвидацию в анализаторе
    analyzer.register_liquidation(liquidation)
    
    # Проверяем, является ли эта ликвидация крупной
    if analyzer.is_large_liquidation(liquidation):
        print(f"📊 Обнаружена крупная ликвидация: {liquidation.symbol}, "
              f"Объем: {liquidation.quantity} BTC, "
              f"Стоимость: ${liquidation.value():,.2f}")
    
    # Периодически анализируем недавние ликвидации
    if analyzer.should_analyze():
        analysis = analyzer.analyze_liquidations(analyzer.get_recent_liquidations())
        
        if analysis["cascade_detected"]:
            print(f"🔥 ВНИМАНИЕ! Обнаружен каскад ликвидаций {liquidation.symbol}!")
            print(f"Суммарный объем: {analysis['total_volume']} BTC")
            print(f"Направление: {'Длинные позиции' if analysis['cascade_side'] == LiquidationSide.SELL else 'Короткие позиции'}")
```

## Тестирование

Для тестирования реализации ликвидаций необходимо разработать:

1. **Модульные тесты:**
   - Тест парсинга сообщений о ликвидациях
   - Тест корректной работы подписки и отписки
   - Тест анализатора ликвидаций (обнаружение крупных и каскадных ликвидаций)

2. **Интеграционные тесты:**
   - Тест полного цикла получения и обработки ликвидаций
   - Тест с использованием записанных реальных ликвидаций с биржи

3. **Тесты обработки ошибок:**
   - Проверка отказоустойчивости при потере соединения
   - Проверка корректной обработки некорректных форматов данных

## Критерии выполнения

Задача будет считаться выполненной, когда:

1. ✅ Реализована полная функциональность метода `subscribe_to_liquidations` в классе `BybitMarketDataStreamProvider`
2. ✅ Создан и протестирован обработчик `LiquidationMessageHandler`
3. ✅ Разработан и интегрирован анализатор ликвидаций
4. ✅ Реализована надежная обработка ошибок и восстановление после сбоев
5. ✅ Код соответствует стандартам проекта и имеет полную документацию
6. ✅ Успешно проходят все модульные и интеграционные тесты
7. ✅ Производительность соответствует требованиям работы с высокочастотными данными

## Примечания по реализации

- В Bybit ликвидации доступны только через WebSocket, нет REST API для исторических ликвидаций
- Ликвидации редкие события, поэтому рекомендуется создать заглушку для локального тестирования
- При обработке сообщений обратите внимание на правильную конвертацию временных меток
- Система анализа должна иметь низкую задержку, чтобы обеспечить быструю реакцию на рыночные события

## Ссылки на документацию

- [Bybit WebSocket API - Liquidation канал](https://bybit-exchange.github.io/docs/v5/websocket/public/liquidation)
- [LiquidationData модель](models/market_data/liquidation.py)
- [IMarketDataStreamProvider интерфейс](exchange_api/interfaces/market_data.py) 
# Задача: Реализация сервиса для доступа к данным о сделках в Bybit

## Контекст
В рамках разработки модуля Trading APIs & Exchange необходимо реализовать полноценную поддержку для получения и обработки данных о сделках (trades) на бирже Bybit. Этот функционал является частью второго этапа разработки модуля: "Реализация сервисов для рыночных данных", описанного в бэклоге проекта.

Текущая кодовая база уже содержит:
1. Модель данных `TradeData` для представления информации о сделках
2. Интерфейсы `IMarketDataRestProvider` и `IMarketDataStreamProvider` с методами для работы со сделками
3. Реализацию провайдеров `BybitMarketDataRestProvider` и `BybitMarketDataStreamProvider` с заглушками для методов получения сделок
4. Объединенный сервис `BybitMarketDataService`, который делегирует вызовы соответствующим провайдерам

## Задача
Необходимо реализовать полноценную поддержку для работы с данными о сделках, включая:

1. **REST API**:
   - Завершить реализацию метода `get_recent_trades` в `BybitMarketDataRestProvider` для получения последних сделок через REST API
   
2. **WebSocket API**:
   - Реализовать метод `subscribe_to_trades` в `BybitMarketDataStreamProvider` для подписки на обновления о новых сделках в реальном времени
   - Дополнить метод `_on_message` для обработки сообщений о сделках

3. **Проверка целостности данных**:
   - Реализовать алгоритм проверки последовательности ID сделок для обнаружения пропусков
   - Создать механизм для восстановления пропущенных данных при необходимости

4. **Обработчик WebSocket сообщений**:
   - Создать специализированный `TradeMessageHandler` для разбора сообщений о сделках из WebSocket

## Требования
1. Обеспечить надежное получение и обработку данных о сделках
2. Поддерживать эффективную работу даже при высокой частоте сделок
3. Обнаруживать и логировать пропущенные сделки
4. Использовать существующие модели данных и интерфейсы
5. Обеспечить правильную сортировку сделок по времени
6. Поддерживать функционал фильтрации сделок по различным параметрам

## Примечания
- Bybit API возвращает сделки в формате объектов с полями id, цена, объем, сторона (buyer/seller maker) и др.
- WebSocket-канал для сделок имеет формат `publicTrade.{symbol}`
- Последовательные ID сделок позволяют отслеживать пропуски данных
- Модель данных `TradeData` уже имеет методы для преобразования форматов данных биржи

## Ожидаемый результат
Полнофункциональный сервис для работы с данными о сделках, который позволяет:
1. Получать историю недавних сделок через REST API
2. Подписываться на обновления о новых сделках через WebSocket API
3. Отслеживать целостность данных и обнаруживать пропуски
4. Эффективно обрабатывать высокочастотные потоки сделок

## Структура изменений

### 1. Реализация метода `get_recent_trades` в BybitMarketDataRestProvider:

```python
async def get_recent_trades(self, symbol: str, limit: Optional[int] = None) -> List[TradeData]:
    """
    Получает список недавних сделок для указанного символа.
    
    Args:
        symbol: Торговый символ (например, "BTCUSDT").
        limit: Максимальное количество сделок для получения.
              Если None, используется значение по умолчанию API.
        
    Returns:
        Список объектов TradeData, отсортированных по времени (обычно от старых к новым).
        
    Raises:
        VantaAPIError: При ошибке взаимодействия с API биржи.
        VantaRateLimitError: При превышении лимита запросов к API биржи.
    """
    try:
        # Определяем категорию инструмента
        category = self._get_category_for_symbol(symbol)
        
        # Формируем параметры запроса
        params = {
            'category': category,
            'symbol': symbol
        }
        
        # Добавляем лимит, если указан
        if limit is not None:
            params['limit'] = limit
        
        # Выполняем запрос к API
        response = await self.connection.get(MarketDataEndpoints.RECENT_TRADES, params)
        
        # Проверяем успешность запроса
        if response.get('retCode') != 0:
            raise VantaAPIError(
                message=f"Ошибка при получении данных о сделках: {response.get('retMsg', 'Unknown error')}",
                code=response.get('retCode'),
                exchange=self.exchange_name
            )
        
        # Извлекаем данные из ответа
        trades_data = response.get('result', {}).get('list', [])
        
        # Преобразуем данные в объекты TradeData
        trades = []
        for trade_item in trades_data:
            trade = TradeData.from_bybit_rest(trade_item, symbol)
            trades.append(trade)
        
        # Сортируем сделки по времени (от старых к новым)
        trades.sort(key=lambda x: x.timestamp)
        
        return trades
        
    except VantaAPIError:
        # Пробрасываем ошибки API без изменений
        raise
    except Exception as e:
        # Преобразуем другие исключения в VantaAPIError
        raise VantaAPIError(
            message=f"Ошибка при получении данных о сделках: {str(e)}",
            exchange=self.exchange_name,
            original_exception=e
        ) from e
```

### 2. Создание TradeSequenceValidator для проверки последовательности сделок:

Новый файл: `exchange_api/services/bybit/trade_sequence_validator.py`

```python
"""
Валидатор последовательности сделок для биржи Bybit.

Отвечает за проверку целостности данных о сделках,
обнаружение пропусков и отслеживание статистики.
"""

from typing import Dict, Set, List, Optional
from datetime import datetime, timedelta

from models.market_data import TradeData
from exchange_api.utils.logger import Logger

# Получаем логгер
logger = Logger.get_logger()

class TradeSequenceValidator:
    """
    Валидатор для проверки последовательности сделок.
    
    Отслеживает ID сделок для обнаружения пропусков и ведет
    статистику по обработанным сделкам.
    """
    
    def __init__(self, symbol: str, window_size: int = 1000):
        """
        Инициализирует валидатор последовательности сделок.
        
        Args:
            symbol: Торговый символ (например, "BTCUSDT")
            window_size: Размер окна для отслеживания ID сделок
        """
        self.symbol = symbol
        self.window_size = window_size
        
        # Множество для хранения последних ID сделок
        self.trade_ids: Set[str] = set()
        
        # Словарь для хранения статистики
        self.stats = {
            'total_trades': 0,
            'duplicates': 0,
            'gaps_detected': 0,
            'last_timestamp': None
        }
        
        # Наибольший и наименьший ID сделки в текущем окне
        self.min_id: Optional[str] = None
        self.max_id: Optional[str] = None
        
        # Время последней проверки статистики
        self.last_stats_time = datetime.now()
    
    def validate_trade(self, trade: TradeData) -> bool:
        """
        Проверяет сделку на уникальность и последовательность.
        
        Args:
            trade: Объект TradeData для проверки
            
        Returns:
            bool: True, если сделка новая, False, если дубликат
        """
        # Обновляем статистику
        self.stats['total_trades'] += 1
        self.stats['last_timestamp'] = trade.timestamp
        
        # Проверяем, не дубликат ли это
        if trade.trade_id in self.trade_ids:
            self.stats['duplicates'] += 1
            return False
        
        # Добавляем ID в множество
        self.trade_ids.add(trade.trade_id)
        
        # Обновляем минимальный и максимальный ID
        if self.min_id is None or trade.trade_id < self.min_id:
            self.min_id = trade.trade_id
        
        if self.max_id is None or trade.trade_id > self.max_id:
            self.max_id = trade.trade_id
        
        # Если размер множества превышает окно, удаляем старые ID
        if len(self.trade_ids) > self.window_size:
            # Очищаем старые ID (простая реализация - полная очистка)
            # В реальном приложении нужно более сложное управление окном
            old_size = len(self.trade_ids)
            self.trade_ids = {id for id in self.trade_ids if id >= self.min_id}
            new_size = len(self.trade_ids)
            
            if old_size - new_size > 0:
                logger.debug(f"Удалено {old_size - new_size} старых ID сделок из валидатора для {self.symbol}")
        
        # Логируем статистику каждые 5 минут
        if datetime.now() - self.last_stats_time > timedelta(minutes=5):
            self.log_statistics()
            self.last_stats_time = datetime.now()
        
        return True
    
    def check_for_gaps(self, trade_ids: List[str]) -> List[str]:
        """
        Проверяет наличие пропусков в последовательности ID сделок.
        
        Args:
            trade_ids: Список ID сделок для проверки
            
        Returns:
            List[str]: Список диапазонов пропущенных ID
        """
        # Преобразуем строковые ID в числовые, если это возможно
        try:
            numeric_ids = [int(id) for id in trade_ids]
            numeric_ids.sort()
            
            # Ищем пропуски в последовательности
            gaps = []
            for i in range(1, len(numeric_ids)):
                if numeric_ids[i] - numeric_ids[i-1] > 1:
                    gap = f"{numeric_ids[i-1]+1}-{numeric_ids[i]-1}"
                    gaps.append(gap)
                    self.stats['gaps_detected'] += 1
            
            return gaps
            
        except ValueError:
            # Если ID не числовые, просто возвращаем пустой список
            logger.warning(f"Не удалось преобразовать ID сделок в числовые для {self.symbol}")
            return []
    
    def log_statistics(self):
        """
        Логирует статистику обработки сделок.
        """
        logger.info(f"Статистика сделок для {self.symbol}: "
                   f"Всего обработано: {self.stats['total_trades']}, "
                   f"Дубликатов: {self.stats['duplicates']}, "
                   f"Обнаружено пропусков: {self.stats['gaps_detected']}")
```

### 3. Создание TradeMessageHandler для WebSocket:

Новый файл: `exchange_api/exchanges/bybit/handlers/trade_handler.py`

```python
"""
Обработчик сообщений о сделках от WebSocket API Bybit.

Отвечает за разбор сообщений о сделках и их преобразование
в унифицированный формат TradeData.
"""

from typing import Dict, Any, Callable, Awaitable, List
import re

from models.market_data import TradeData
from exchange_api.utils.logger import Logger

# Получаем логгер
logger = Logger.get_logger()

class TradeMessageHandler:
    """
    Обработчик сообщений о сделках от WebSocket API Bybit.
    
    Парсит сообщения о сделках и передает их в коллбэк-функцию.
    """
    
    # Регулярное выражение для извлечения информации из темы канала
    TOPIC_PATTERN = re.compile(r'^publicTrade\.([A-Za-z0-9]+)$')
    
    def __init__(self, callback: Callable[[TradeData], Awaitable[None]]):
        """
        Инициализирует обработчик сообщений о сделках.
        
        Args:
            callback: Асинхронная функция обратного вызова, которая будет вызываться
                     при получении новых данных. Принимает объект TradeData.
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
        if 'topic' not in message:
            return False
        
        topic = message['topic']
        
        # Проверяем, относится ли сообщение к сделкам
        match = self.TOPIC_PATTERN.match(topic)
        if not match:
            return False
        
        # Извлекаем символ из темы
        symbol = match.group(1)
        
        try:
            # Извлекаем данные о сделках из сообщения
            trades_data = message.get('data', [])
            
            # Обрабатываем каждую сделку
            for trade_data in trades_data:
                # Преобразуем данные в TradeData
                trade = TradeData.from_bybit_ws(trade_data, symbol)
                
                # Вызываем коллбэк с преобразованными данными
                await self.callback(trade)
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при обработке сообщения о сделках: {str(e)}")
            return False
```

### 4. Реализация метода `subscribe_to_trades` в BybitMarketDataStreamProvider:

```python
async def subscribe_to_trades(self, symbol: str, 
                             callback: Callable[[TradeData], Awaitable[None]]) -> str:
    """
    Подписывается на поток сделок в реальном времени.
    
    Args:
        symbol: Торговый символ (например, "BTCUSDT").
        callback: Асинхронная функция обратного вызова, которая будет вызываться
                 при получении новых данных. Принимает объект TradeData.
        
    Returns:
        Идентификатор подписки, который может быть использован для отписки.
        
    Raises:
        VantaAPIError: При ошибке взаимодействия с API биржи.
        VantaWebSocketError: При ошибке WebSocket соединения.
    """
    try:
        # Формируем имя канала
        channel = format_public_channel(
            PublicWebSocketChannels.TRADE,
            symbol=symbol
        )
        
        # Создаем валидатор последовательности сделок
        sequence_validator = TradeSequenceValidator(symbol)
        
        # Определяем коллбэк-функцию, которая будет обрабатывать поступающие данные
        async def handle_trade_update(trade: TradeData):
            # Проверяем сделку на уникальность и последовательность
            is_new = sequence_validator.validate_trade(trade)
            
            # Если это новая сделка, вызываем пользовательский коллбэк
            if is_new:
                await callback(trade)
        
        # Подписываемся на канал
        return await self._subscribe_to_channel(
            channel=channel,
            callback=handle_trade_update,
            symbol=symbol,
            sequence_validator=sequence_validator
        )
        
    except Exception as e:
        # Преобразуем исключение
        raise VantaWebSocketError(
            message=f"Ошибка при подписке на поток сделок: {str(e)}",
            exchange=self.exchange_name,
            channel=f"publicTrade.{symbol}"
        ) from e
```

### 5. Дополнение метода `_on_message` в BybitMarketDataStreamProvider:

```python
async def _on_message(self, message: Dict[str, Any]) -> None:
    """
    Обрабатывает входящие сообщения от WebSocket API.
    
    Args:
        message: Полученное сообщение
    """
    try:
        # Проверяем, имеет ли сообщение тему (topic)
        if 'topic' not in message:
            return
        
        topic = message['topic']
        
        # Ищем подписки, соответствующие теме
        for subscription_id, subscription in self.subscriptions.items():
            if subscription['channel'] == topic:
                # Извлекаем параметры и колбэк из подписки
                callback = subscription['callback']
                symbol = subscription['symbol']
                
                # В зависимости от типа канала преобразуем данные
                if topic.startswith('kline.'):
                    # ... код для обработки OHLCV данных ...
                
                elif topic.startswith('orderbook.'):
                    # ... код для обработки стакана ордеров ...
                
                elif topic.startswith('publicTrade.'):
                    # Извлекаем данные о сделках из сообщения
                    trades_data = message.get('data', [])
                    
                    # Обрабатываем каждую сделку
                    for trade_data in trades_data:
                        # Преобразуем данные в TradeData
                        trade = TradeData.from_bybit_ws(trade_data, symbol)
                        
                        # Вызываем колбэк с преобразованными данными
                        await callback(trade)
                
                # Аналогично для других типов каналов...
    
    except Exception as e:
        logger.error(f"Ошибка при обработке WebSocket сообщения: {str(e)}")
```

## Полное описание реализации

Реализация сервиса для доступа к данным о сделках биржи Bybit должна обеспечивать:

1. **Получение исторических данных**: Через REST API можно получать историю недавних сделок с параметрами фильтрации
2. **Реальновременные обновления**: Через WebSocket можно подписываться на поток новых сделок в реальном времени
3. **Проверку целостности данных**: Алгоритм проверки последовательности ID сделок обнаруживает пропуски
4. **Статистику и мониторинг**: Логирование важной информации о потоке сделок для анализа и отладки

Дополнительные улучшения:

1. **Дедупликация**: Исключение дублирующихся сделок при комбинировании данных из разных источников
2. **Обработка высокой нагрузки**: Эффективная работа даже при высокой частоте сделок в периоды волатильности
3. **Гибкая фильтрация**: Возможность получать только нужные сделки по различным параметрам
4. **Аналитические функции**: Вычисление агрегированных метрик, таких как объем торгов, дельта (buy - sell) и др.

С реализацией этого функционала модуль Trading APIs & Exchange будет предоставлять полноценный доступ к данным о сделках, что является важным компонентом для анализа микроструктуры рынка, выявления паттернов торговли и построения торговых стратегий. 
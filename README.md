# Trading APIs & Exchange

Компонент системы VANTA, обеспечивающий унифицированный доступ к API криптовалютных бирж. Модуль абстрагирует специфику различных биржевых API и предоставляет единый интерфейс для работы с рыночными данными и выполнения торговых операций.

## Назначение

Trading APIs & Exchange выполняет следующие функции в архитектуре системы VANTA:

- Предоставляет унифицированный доступ к API бирж через четко определенные интерфейсы
- Служит как "тонкий" клиент-прокси для доступа к рыночным данным и торговым операциям
- Управляет соединениями с биржей и обеспечивает их надежность
- Нормализует данные, полученные от биржи, в стандартный формат

## Установка

### Из исходного кода

```bash
git clone https://github.com/cyberSecSec/trading_bot_2.0.git
cd exchange_api
pip install -e .
```

### Через pip

```bash
pip install vanta-exchange-api
```

## Основные компоненты

### Конфигурация

Модуль использует гибкую систему конфигурации, позволяющую настраивать параметры подключения к биржам:

```python
from exchange_api.core.config import ClientConfig

# Создание конфигурации из переменных окружения
config = ClientConfig.from_env("bybit")

# Создание конфигурации из JSON-файла
config = ClientConfig.from_json("config.json")

# Создание конфигурации с дефолтными значениями
config = ClientConfig.get_default("bybit")

# Сохранение конфигурации в файл (секретные данные маскируются)
config.to_json("saved_config.json")
```

### Конфигурация Bybit

Для работы с Bybit API реализована специализированная конфигурация, учитывающая особенности этой биржи:

```python
from exchange_api.exchanges.bybit import BybitClientConfig, BybitEnvironmentType

# Создание конфигурации Bybit из переменных окружения
config = BybitClientConfig.from_env()

# Создание конфигурации с дефолтными значениями (использует testnet)
config = BybitClientConfig.get_default()

# Сохранение конфигурации в файл
config.to_json("bybit_config.json")
```

#### Пример конфигурации для тестовой среды (Testnet)

```python
from exchange_api.exchanges.bybit import BybitClientConfig, BybitEnvironmentType
from exchange_api.core.config import ApiCredentials, ConnectionConfig, RateLimitConfig

# Создание тестовой конфигурации
test_config = BybitClientConfig(
    exchange_name="bybit",
    bybit_environment=BybitEnvironmentType.TESTNET,  # Указываем тестовую сеть
    credentials=ApiCredentials(
        api_key="тестовый_api_ключ",
        api_secret="тестовый_секретный_ключ"
    ),
    categories={"spot", "linear"},  # Категории инструментов для работы
    recv_window=5000,  # Окно приема для запросов (в миллисекундах)
    test_mode=True,   # Этот параметр будет установлен автоматически для testnet
    debug_mode=True   # Включаем расширенное логирование для тестирования
)

# URL-адреса API и WebSocket будут установлены автоматически на основе bybit_environment
print(f"Base URL: {test_config.connection.base_url}")  # https://api-testnet.bybit.com
print(f"WS URL: {test_config.connection.ws_url}")      # wss://stream-testnet.bybit.com
```

#### Пример конфигурации для продакшн-среды (Mainnet)

```python
from exchange_api.exchanges.bybit import BybitClientConfig, BybitEnvironmentType
from exchange_api.core.config import ApiCredentials, RateLimitConfig

# Создание продакшн-конфигурации
prod_config = BybitClientConfig(
    exchange_name="bybit",
    bybit_environment=BybitEnvironmentType.MAINNET,  # Указываем основную сеть
    credentials=ApiCredentials(
        api_key="боевой_api_ключ",
        api_secret="боевой_секретный_ключ"
    ),
    categories={"spot", "linear", "inverse"},  # Категории инструментов для работы
    recv_window=5000,  # Окно приема для запросов (в миллисекундах)
    rate_limit=RateLimitConfig(
        max_requests_per_second=10,  # Лимиты для боевого API
        max_requests_per_minute=600,
        max_connections=30
    ),
    test_mode=False,  # Боевой режим
    debug_mode=False  # Отключаем отладочный режим в продакшене
)

# URL-адреса API и WebSocket будут установлены автоматически
print(f"Base URL: {prod_config.connection.base_url}")  # https://api.bybit.com
print(f"WS URL: {prod_config.connection.ws_url}")      # wss://stream.bybit.com
```

### Адаптеры соединения

Модуль предоставляет адаптеры для работы с HTTP и WebSocket соединениями.

#### HTTP соединения

```python
import asyncio
from exchange_api.core.config import ClientConfig
from exchange_api.connection import ConnectionManager

async def example():
    # Инициализация конфигурации
    config = ClientConfig.get_default("bybit")
    
    # Создание менеджера соединений
    async with ConnectionManager(config) as conn:
        # Выполнение GET-запроса без аутентификации
        public_data = await conn.get("/v5/market/tickers", {"category": "spot"})
        print(f"Публичные данные: {public_data}")
        
        # Выполнение GET-запроса с аутентификацией
        private_data = await conn.get("/v5/account/wallet-balance", 
                                     {"accountType": "UNIFIED"},
                                     authenticate=True)
        print(f"Приватные данные: {private_data}")

# Запуск асинхронной функции
asyncio.run(example())
```

#### WebSocket соединения

```python
import asyncio
from exchange_api.core.config import ClientConfig
from exchange_api.connection import WebSocketManager

async def on_message(data):
    print(f"Получено сообщение: {data}")

async def example():
    # Инициализация конфигурации
    config = ClientConfig.get_default("bybit")
    
    # Создание менеджера WebSocket соединений
    ws_manager = WebSocketManager(
        config,
        on_message=on_message
    )
    
    # Подключение к WebSocket серверу
    await ws_manager.connect()
    
    # Подписка на каналы данных
    await ws_manager.subscribe("orderbook.50.BTCUSDT")
    await ws_manager.subscribe("tickers.ETHUSDT")
    
    # Ожидание и обработка сообщений
    await asyncio.sleep(30)
    
    # Отключение от WebSocket сервера
    await ws_manager.disconnect()

# Запуск асинхронной функции
asyncio.run(example())
```

#### Обработка переподключений

```python
import asyncio
from exchange_api.core.config import ClientConfig
from exchange_api.connection import ConnectionManager
from exchange_api.connection import ReconnectionHandler

# Декоратор для повторных попыток с экспоненциальной задержкой
@ReconnectionHandler.with_backoff(
    max_tries=5,
    base_delay=1.0,
    max_delay=30.0
)
async def fetch_data(conn, endpoint, params):
    return await conn.get(endpoint, params)

# Декоратор для обработки превышения лимитов запросов
@ReconnectionHandler.with_rate_limit_handling()
async def fetch_rate_limited_data(conn, endpoint, params):
    return await conn.get(endpoint, params)

async def example():
    config = ClientConfig.get_default("bybit")
    
    async with ConnectionManager(config) as conn:
        # Использование функции с автоматической обработкой переподключений
        try:
            data = await fetch_data(conn, "/v5/market/tickers", {"category": "spot"})
            print(f"Данные получены: {data}")
        except Exception as e:
            print(f"Ошибка после всех попыток: {e}")

# Запуск асинхронной функции
asyncio.run(example())
```

### Переменные окружения

Для работы с модулем через `ClientConfig.from_env()` необходимо настроить следующие переменные окружения:

```
# Базовые параметры подключения
VANTA_BYBIT_API_KEY=ваш_api_ключ
VANTA_BYBIT_API_SECRET=ваш_секретный_ключ

# Параметры окружения
VANTA_BYBIT_ENVIRONMENT=production  # или development, test
VANTA_BYBIT_TEST_MODE=false         # или true
VANTA_BYBIT_DEBUG_MODE=false        # или true
```

При использовании специализированного `BybitClientConfig.from_env()` можно настроить дополнительно:

```
# Специфичные для Bybit параметры
VANTA_BYBIT_ENVIRONMENT=mainnet      # или testnet
VANTA_BYBIT_CATEGORIES=spot,linear    # список категорий через запятую
VANTA_BYBIT_RECV_WINDOW=5000         # окно приема в миллисекундах

# Настройки лимитов запросов
VANTA_BYBIT_MAX_REQUESTS_PER_SECOND=20
VANTA_BYBIT_MAX_REQUESTS_PER_MINUTE=1200  
VANTA_BYBIT_MAX_CONNECTIONS=50
```

Также можно задать URL-адреса API и WebSocket напрямую:

```
VANTA_BYBIT_BASE_URL=https://api.bybit.com       # или https://api-testnet.bybit.com
VANTA_BYBIT_WS_URL=wss://stream.bybit.com        # или wss://stream-testnet.bybit.com
```

URL-адреса будут автоматически настроены в зависимости от выбранного окружения Bybit (mainnet или testnet).

### Логирование

Модуль включает встроенную систему логирования на базе библиотеки loguru:

```python
from exchange_api.utils.logger import Logger, LogConfig, LogLevel

# Настройка логирования с использованием конфигурации клиента
Logger.setup_from_client_config(config)

# Получение логгера
from exchange_api.utils.logger import log
log.info("Пример информационного сообщения")
log.debug("Отладочная информация")
log.error("Ошибка при выполнении операции")

# Логирование с контекстом
logger = Logger.with_context(exchange="bybit", symbol="BTCUSDT")
logger.info("Логирование с контекстным контекстом")
```

### Обработка ошибок

Модуль предоставляет расширенную иерархию исключений для обработки различных ситуаций:

```python
from exchange_api.exceptions import VantaTradingError, ConnectionError, RateLimitError

try:
    # Код, который может вызвать исключение
    pass
except RateLimitError as e:
    # Обработка превышения лимитов API
    print(f"Превышен лимит запросов. Повторите через {e.retry_after} секунд")
except ConnectionError as e:
    # Обработка проблем с соединением
    print(f"Ошибка соединения: {e}")
except VantaTradingError as e:
    # Обработка любых других ошибок модуля
    print(f"Произошла ошибка: {e}")
    
    # Получение детальной информации об ошибке в виде словаря
    error_info = e.to_dict()
    print(f"Детали ошибки: {error_info}")
```

## Базовый пример использования

### Получение рыночных данных с использованием BybitClientConfig

```python
import asyncio
from exchange_api.exchanges.bybit import BybitClientConfig

async def main():
    # Создание специализированной конфигурации для Bybit
    config = BybitClientConfig.get_default()  # Использует testnet по умолчанию
    
    # Здесь будет код для инициализации и использования клиента Bybit
    # Пример кода:
    print(f"Соединение с: {config.connection.base_url}")
    print(f"Режим тестирования: {'Включен' if config.test_mode else 'Выключен'}")
    print(f"Категории: {config.categories}")
    
    # В будущих реализациях провайдер будет использовать специальную конфигурацию
    # provider = BybitMarketDataRestProvider(config)
    # klines = await provider.get_klines(symbol="BTCUSDT", interval="1m", limit=100)

if __name__ == "__main__":
    asyncio.run(main())
```


### Использование базового клиента Bybit

Базовый клиент Bybit предоставляет унифицированный интерфейс для работы с API Bybit, включая получение рыночных данных и выполнение торговых операций.

```python
import asyncio
from decimal import Decimal
from exchange_api.exchanges.bybit import BybitClient, BybitClientConfig

async def main():
    # Создание конфигурации для Bybit
    config = BybitClientConfig.get_default()  # Использует testnet по умолчанию
    
    # Инициализация клиента
    async with BybitClient(config) as client:
        # Получение OHLCV данных
        klines = await client.get_klines(
            symbol="BTCUSDT",
            interval="1",  # 1 минута
            limit=10,
            category="spot"
        )
        
        print(f"Получено {len(klines)} свечей для BTCUSDT:")
        for kline in klines[:3]:  # Выводим первые 3 свечи
            print(f"Время: {kline['timestamp']}, Цена закрытия: {kline['close']}")
        
        # Получение стакана ордеров
        orderbook = await client.get_orderbook(
            symbol="BTCUSDT",
            limit=5,  # Получаем 5 лучших уровней
            category="spot"
        )
        
        print("\nСтакан ордеров BTCUSDT:")
        print(f"Лучшие предложения на покупку (bids):")
        for bid in orderbook["bids"][:3]:
            print(f"Цена: {bid[0]}, Объем: {bid[1]}")
        
        print(f"Лучшие предложения на продажу (asks):")
        for ask in orderbook["asks"][:3]:
            print(f"Цена: {ask[0]}, Объем: {ask[1]}")
        
        # Получение последних сделок
        trades = await client.get_recent_trades(
            symbol="BTCUSDT",
            limit=5,
            category="spot"
        )
        
        print("\nПоследние сделки BTCUSDT:")
        for trade in trades[:3]:
            side = "Покупка" if trade["side"] == "Buy" else "Продажа"
            print(f"{side}: Цена: {trade['price']}, Объем: {trade['quantity']}")

if __name__ == "__main__":
    asyncio.run(main())
```

### Работа с WebSocket API Bybit

Пример подписки на потоки данных в реальном времени через WebSocket API:

```python
import asyncio
import json
from exchange_api.exchanges.bybit import (
    BybitClientConfig, BybitWebSocketManager, 
    PublicWebSocketChannels, format_public_channel
)

async def message_handler(message):
    """Обработчик входящих сообщений WebSocket."""
    if 'topic' in message:
        topic = message['topic']
        
        # Обрабатываем разные типы сообщений
        if topic.startswith('orderbook.'):
            data = message.get('data', {})
            if data and 'a' in data and 'b' in data:
                print(f"Обновление стакана: {len(data['a'])} asks, {len(data['b'])} bids")
        
        elif topic.startswith('kline.'):
            data = message.get('data', [])
            if data:
                candle = data[0]
                print(f"Свеча: O:{candle[1]} H:{candle[2]} L:{candle[3]} C:{candle[4]}")
        
        elif topic.startswith('publicTrade.'):
            data = message.get('data', [])
            if data:
                trade = data[0]
                print(f"Сделка: {trade.get('S')} {trade.get('p')} x {trade.get('v')}")

async def main():
    # Создание конфигурации
    config = BybitClientConfig.get_default()
    
    # Создание WebSocket менеджера
    ws_manager = BybitWebSocketManager(
        config=config,
        on_message=message_handler
    )
    
    try:
        # Подключение к WebSocket серверу
        await ws_manager.connect()
        
        # Формируем имена каналов с помощью функции format_public_channel
        kline_channel = format_public_channel(
            PublicWebSocketChannels.KLINE,
            interval="1",
            symbol="BTCUSDT"
        )
        
        orderbook_channel = format_public_channel(
            PublicWebSocketChannels.ORDERBOOK,
            depth="50",
            symbol="BTCUSDT"
        )
        
        trade_channel = format_public_channel(
            PublicWebSocketChannels.TRADE,
            symbol="BTCUSDT"
        )
        
        # Подписываемся на каналы
        await ws_manager.subscribe(kline_channel)
        await ws_manager.subscribe(orderbook_channel)
        await ws_manager.subscribe(trade_channel)
        
        print("Подписки активированы, ожидаем сообщения в течение 30 секунд...")
        
        # Ожидаем и обрабатываем сообщения
        await asyncio.sleep(30)
        
    finally:
        # Отключаемся от WebSocket сервера
        await ws_manager.disconnect()
        print("WebSocket соединение закрыто")

if __name__ == "__main__":
    asyncio.run(main())
```

### Использование обработчиков WebSocket сообщений

Пример использования специализированных обработчиков WebSocket сообщений:

```python
import asyncio
from exchange_api.exchanges.bybit import (
    BybitClientConfig, BybitWebSocketManager,
    WebSocketMessageRouter, KlineMessageHandler, 
    OrderbookMessageHandler, TradeMessageHandler,
    PublicWebSocketChannels, format_public_channel
)

async def kline_callback(data):
    """Обработчик OHLCV данных."""
    if 'data' in data and data['data']:
        candle = data['data'][0]
        print(f"Новая свеча {data['symbol']}: Открытие: {candle['open']}, Закрытие: {candle['close']}")

async def orderbook_callback(data):
    """Обработчик стакана ордеров."""
    if 'bids' in data and 'asks' in data:
        print(f"Обновление стакана {data['symbol']}: {len(data['bids'])} bids, {len(data['asks'])} asks")
        if data['bids']:
            print(f"Лучшая цена покупки: {data['bids'][0][0]}")
        if data['asks']:
            print(f"Лучшая цена продажи: {data['asks'][0][0]}")

async def trade_callback(data):
    """Обработчик сделок."""
    if 'data' in data and data['data']:
        trade = data['data'][0]
        print(f"Новая сделка {data['symbol']}: {trade['side']} {trade['price']} x {trade['quantity']}")

async def handle_ws_message(message):
    """Основной обработчик сообщений."""
    await router.route_message(message)

async def main():
    # Создание конфигурации
    config = BybitClientConfig.get_default()
    
    # Создание WebSocket менеджера
    ws_manager = BybitWebSocketManager(
        config=config,
        on_message=handle_ws_message
    )
    
    # Создание маршрутизатора сообщений
    global router
    router = WebSocketMessageRouter("bybit")
    
    # Добавление обработчиков с колбэками
    router.add_handler(KlineMessageHandler(kline_callback))
    router.add_handler(OrderbookMessageHandler(orderbook_callback))
    router.add_handler(TradeMessageHandler(trade_callback))
    
    try:
        # Подключение к WebSocket серверу
        await ws_manager.connect()
        
        # Формируем каналы и подписываемся
        kline_channel = format_public_channel(
            PublicWebSocketChannels.KLINE,
            interval="1",
            symbol="BTCUSDT"
        )
        
        orderbook_channel = format_public_channel(
            PublicWebSocketChannels.ORDERBOOK,
            depth="50",
            symbol="BTCUSDT"
        )
        
        trade_channel = format_public_channel(
            PublicWebSocketChannels.TRADE,
            symbol="BTCUSDT"
        )
        
        # Подписываемся на каналы
        await ws_manager.subscribe(kline_channel)
        await ws_manager.subscribe(orderbook_channel)
        await ws_manager.subscribe(trade_channel)
        
        print("Подписки активированы, ожидаем сообщения в течение 30 секунд...")
        
        # Ожидаем и обрабатываем сообщения
        await asyncio.sleep(30)
        
    finally:
        # Отключаемся от WebSocket сервера
        await ws_manager.disconnect()
        print("WebSocket соединение закрыто")

if __name__ == "__main__":
    router = None  # Глобальная переменная для маршрутизатора
    asyncio.run(main())
```

## Документация

Подробная документация доступна [здесь](docs/index.md).

## Разработка

### Установка зависимостей для разработки

```bash
pip install -e ".[dev]"
```

### Запуск тестов

```bash
pytest
```

## Лицензия

MIT 
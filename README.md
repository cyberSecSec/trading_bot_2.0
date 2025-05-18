# Trading APIs & Exchange

Модуль Trading APIs & Exchange является ключевым компонентом системы VANTA, обеспечивающим унифицированный доступ к API криптовалютных бирж. Модуль абстрагирует специфику различных биржевых API и предоставляет единый интерфейс для работы с рыночными данными и выполнения торговых операций.

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

## Модели данных

Модуль предоставляет набор моделей данных для преобразования и нормализации информации, получаемой от API бирж в единый универсальный формат.

### Структура моделей

Модели данных организованы в иерархическую структуру:

```
models/
├── __init__.py           # Общие импорты
├── base.py               # Базовые абстрактные классы
├── market_data/          # Модели рыночных данных
│   ├── __init__.py
│   ├── kline.py          # OHLCV данные
│   ├── orderbook.py      # Стакан ордеров
│   ├── trade.py          # Сделки
│   ├── liquidation.py    # Ликвидации
│   └── open_interest.py  # Открытый интерес
├── trading/              # Модели торговых операций
│   ├── __init__.py
│   ├── order_params.py   # Параметры ордеров
│   ├── order_info.py     # Информация об ордерах
│   ├── execution_info.py # Исполнение ордеров
│   └── position_info.py  # Позиции
└── utils/                # Вспомогательные утилиты
    ├── __init__.py
    └── converters.py     # Конвертеры типов данных
```

### Базовые классы

Все модели данных наследуются от базовых абстрактных классов:

```python
from models.base import BaseDataModel, BaseMarketDataModel, BaseTradingModel

# BaseDataModel - общий базовый класс для всех моделей
# BaseMarketDataModel - для моделей рыночных данных
# BaseTradingModel - для моделей торговых операций
```

### Модели рыночных данных

#### OHLCV данные (Kline)

```python
from models.market_data import KlineData, KlineInterval
from datetime import datetime
from decimal import Decimal

# Создание объекта KlineData
kline = KlineData(
    timestamp=datetime.now(),
    symbol="BTCUSDT",
    exchange="bybit",
    interval=KlineInterval.MIN_1,
    open=Decimal("50000.0"),
    high=Decimal("51000.0"),
    low=Decimal("49800.0"),
    close=Decimal("50500.0"),
    volume=Decimal("10.5"),
    turnover=Decimal("525000.0")
)

# Создание из ответа REST API Bybit
bybit_rest_data = {
    "symbol": "BTCUSDT",
    "category": "linear",
    "list": [
        [
            "1625793600000",  # timestamp
            "33700",          # open
            "33982",          # high
            "33620",          # low
            "33917",          # close
            "11.887",         # volume
            "4030098.6308"    # turnover
        ]
    ]
}
kline_from_rest = KlineData.from_bybit_rest(bybit_rest_data["list"][0], bybit_rest_data["symbol"])

# Создание из сообщения WebSocket API Bybit
bybit_ws_data = {
    "topic": "kline.1.BTCUSDT",
    "data": [
        {
            "start": 1675942800000,
            "end": 1675942860000,
            "interval": "1",
            "open": "22711.5",
            "close": "22718",
            "high": "22718",
            "low": "22711.5",
            "volume": "5.456",
            "turnover": "123949.4305",
            "confirm": False,
            "timestamp": 1675942858664
        }
    ]
}
kline_from_ws = KlineData.from_bybit_ws(bybit_ws_data)

# Аналитические методы
price_change = kline.price_change()  # Изменение цены за период
percent_change = kline.percent_change()  # Процентное изменение
is_bullish = kline.is_bullish()  # Является ли свеча бычьей
```

#### Стакан ордеров (OrderBook)

```python
from models.market_data import OrderBookData, OrderBookLevel
from decimal import Decimal

# Создание уровней стакана
bids = [
    OrderBookLevel(price=Decimal("49800.0"), quantity=Decimal("1.2")),
    OrderBookLevel(price=Decimal("49750.0"), quantity=Decimal("0.8"))
]
asks = [
    OrderBookLevel(price=Decimal("50200.0"), quantity=Decimal("0.5")),
    OrderBookLevel(price=Decimal("50250.0"), quantity=Decimal("1.5"))
]

# Создание объекта OrderBookData
orderbook = OrderBookData(
    timestamp=datetime.now(),
    symbol="BTCUSDT",
    exchange="bybit",
    bids=bids,
    asks=asks
)

# Анализ стакана ордеров
spread = orderbook.get_spread()  # Спред между лучшими ценами
mid_price = orderbook.get_mid_price()  # Средняя цена
imbalance = orderbook.get_imbalance()  # Дисбаланс спроса/предложения
```

#### Сделки (Trades)

```python
from models.market_data import TradeData, TradeSide
from decimal import Decimal

# Создание объекта TradeData
trade = TradeData(
    timestamp=datetime.now(),
    symbol="BTCUSDT",
    exchange="bybit",
    trade_id="123456",
    price=Decimal("50100.0"),
    quantity=Decimal("0.12"),
    side=TradeSide.BUY,
    is_maker=False
)

# Создание списка сделок из ответа API
trades_data = [
    {
        "execId": "a1234",
        "symbol": "BTCUSDT",
        "price": "50100.5",
        "size": "0.01",
        "side": "Buy",
        "time": "1675942858664",
        "isMaker": False
    },
    {
        "execId": "b5678",
        "symbol": "BTCUSDT",
        "price": "50100.0",
        "size": "0.02",
        "side": "Sell",
        "time": "1675942859000",
        "isMaker": True
    }
]
trades_list = [TradeData.from_bybit_response(trade_data) for trade_data in trades_data]

# Анализ сделок
vwap = TradeData.calculate_vwap(trades_list)  # Средневзвешенная цена
buy_volume = TradeData.calculate_buy_volume(trades_list)  # Объем покупок
sell_volume = TradeData.calculate_sell_volume(trades_list)  # Объем продаж
delta = TradeData.calculate_delta(trades_list)  # Дельта (разница покупки/продажи)
```

#### Ликвидации (Liquidations)

```python
from models.market_data import LiquidationData, LiquidationSide
from decimal import Decimal

# Создание объекта LiquidationData
liquidation = LiquidationData(
    timestamp=datetime.now(),
    symbol="BTCUSDT",
    exchange="bybit",
    side=LiquidationSide.SELL,
    price=Decimal("48000.0"),
    quantity=Decimal("2.5")
)

# Обработка WebSocket сообщений о ликвидациях
ws_data = {
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
liq_from_ws = LiquidationData.from_bybit_ws(ws_data)
```

#### Открытый интерес (Open Interest)

```python
from models.market_data import OpenInterestData
from decimal import Decimal

# Создание объекта OpenInterestData
oi = OpenInterestData(
    timestamp=datetime.now(),
    symbol="BTCUSDT",
    exchange="bybit",
    open_interest=Decimal("1250.5"),
    open_interest_value=Decimal("62525000.0")
)

# Создание из ответа API
api_data = {
    "symbol": "BTCUSDT",
    "openInterest": "1250.5",
    "timestamp": "1675942858664"
}
oi_from_api = OpenInterestData.from_bybit_response(api_data)

# Вычисление изменения открытого интереса
prev_oi = OpenInterestData(
    timestamp=datetime.now(),
    symbol="BTCUSDT",
    exchange="bybit",
    open_interest=Decimal("1200.0"),
    open_interest_value=Decimal("60000000.0")
)
oi_change = oi.calculate_change(prev_oi)  # Изменение открытого интереса
oi_percent_change = oi.calculate_percent_change(prev_oi)  # Процентное изменение
```

### Модели торговых операций

#### Параметры ордеров (OrderParams)

```python
from models.trading import OrderParams, OrderSide, OrderType, TimeInForce
from decimal import Decimal

# Создание параметров для рыночного ордера
market_order_params = OrderParams.market_order(
    symbol="BTCUSDT",
    side=OrderSide.BUY,
    qty=Decimal("0.01")
)

# Создание параметров для лимитного ордера
limit_order_params = OrderParams.limit_order(
    symbol="BTCUSDT",
    side=OrderSide.SELL,
    qty=Decimal("0.02"),
    price=Decimal("50000.0"),
    time_in_force=TimeInForce.GTC
)

# Создание параметров для стоп-ордера
stop_order_params = OrderParams.stop_order(
    symbol="BTCUSDT",
    side=OrderSide.SELL,
    qty=Decimal("0.01"),
    trigger_price=Decimal("48000.0"),
    price=Decimal("47950.0")  # Лимитная цена для исполнения
)

# Преобразование в формат запроса к API Bybit
api_request_params = market_order_params.to_bybit_request()
```

#### Информация об ордерах (OrderInfo)

```python
from models.trading import OrderInfo, OrderStatus
from decimal import Decimal

# Создание объекта OrderInfo из ответа API
api_response = {
    "orderId": "12345",
    "symbol": "BTCUSDT",
    "side": "Buy",
    "orderType": "Limit",
    "price": "50000",
    "qty": "0.01",
    "status": "New",
    "createdTime": "1675942858664",
    "updatedTime": "1675942858664",
    "timeInForce": "GTC",
    "cumExecQty": "0",
    "cumExecValue": "0"
}
order_info = OrderInfo.from_bybit_response(api_response)

# Проверка статуса ордера
is_active = order_info.is_active()
is_filled = order_info.is_filled()
is_cancelled = order_info.is_cancelled()
fill_percent = order_info.fill_percent()  # Процент заполнения ордера
```

#### Исполнение ордеров (ExecutionInfo)

```python
from models.trading import ExecutionInfo, LiquidityType
from decimal import Decimal

# Создание объекта ExecutionInfo из ответа API
api_response = {
    "execId": "abcd1234",
    "orderId": "12345",
    "symbol": "BTCUSDT",
    "side": "Buy",
    "execPrice": "49950.5",
    "execQty": "0.01",
    "execTime": "1675942858664",
    "execFee": "0.0299703",
    "feeRate": "0.0006",
    "liquidity": "Taker",
    "feeCurrency": "USDT",
    "execValue": "499.505"
}
exec_info = ExecutionInfo.from_bybit_response(api_response)

# Расчет стоимости исполнения
value = exec_info.value()  # Стоимость сделки (цена * количество)
net_value = exec_info.net_value()  # Чистая стоимость с учетом комиссии

# Обработка списка исполнений
executions = [exec_info]
total_fees = ExecutionInfo.calculate_total_fee(executions)  # Суммарные комиссии
vwap = ExecutionInfo.calculate_vwap(executions)  # Средневзвешенная цена исполнения
```

#### Позиции (PositionInfo)

```python
from models.trading import PositionInfo, PositionStatus, MarginMode
from decimal import Decimal

# Создание объекта PositionInfo из ответа API
api_response = {
    "symbol": "BTCUSDT",
    "side": "Buy",
    "size": "0.01",
    "entryPrice": "50000",
    "leverage": "10",
    "positionValue": "500",
    "markPrice": "49500",
    "positionStatus": "Normal",
    "positionIdx": 0,
    "marginMode": "isolated",
    "positionMargin": "50",
    "unrealisedPnl": "-5",
    "liqPrice": "45000",
    "bustPrice": "44900",
    "createdTime": "1675942858664",
    "updatedTime": "1675943858664"
}
position = PositionInfo.from_bybit_response(api_response)

# Анализ позиции
is_long = position.is_long()  # Длинная позиция
is_short = position.is_short()  # Короткая позиция
is_in_profit = position.is_in_profit()  # Позиция в прибыли
is_in_loss = position.is_in_loss()  # Позиция в убытке
liquidation_distance = position.liquidation_price_change()  # Процентное расстояние до ликвидации
pnl_percent = position.pnl_percent()  # Процент прибыли/убытка
current_value = position.value()  # Текущая стоимость позиции
margin_ratio = position.margin_ratio()  # Отношение маржи к стоимости позиции
```

### Импортирование моделей

Для удобства использования все основные модели доступны через корневой импорт:

```python
from models import (
    # Базовые классы
    BaseDataModel, BaseMarketDataModel, BaseTradingModel,
    
    # Рыночные данные
    KlineData, KlineInterval, OrderBookData, OrderBookLevel,
    TradeData, TradeSide, LiquidationData, LiquidationSide,
    OpenInterestData,
    
    # Торговые операции
    OrderParams, OrderSide, OrderType, TimeInForce, TriggerBy, PositionIdx,
    OrderInfo, OrderStatus, ExecutionInfo, LiquidityType,
    PositionInfo, PositionStatus, MarginMode
)
```

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

## Интерфейсы модуля (API Contracts)

Модуль Trading APIs & Exchange предоставляет набор четко определенных интерфейсов для взаимодействия с другими компонентами системы VANTA. Эти интерфейсы абстрагируют детали конкретных бирж и предоставляют унифицированные методы для работы с рыночными данными и торговыми операциями.

### Интерфейсы рыночных данных

#### IMarketDataRestProvider

Интерфейс для получения рыночных данных через REST API. Предоставляет методы для запроса различных типов рыночных данных:

```python
async def get_klines(symbol, interval, limit, start_time, end_time) -> List[KlineData]
async def get_orderbook(symbol, depth) -> OrderBookData 
async def get_recent_trades(symbol, limit) -> List[TradeData]
async def get_open_interest(symbol) -> OpenInterestData
async def get_open_interest_history(symbol, period, limit) -> List[OpenInterestData]
```

#### IMarketDataStreamProvider

Интерфейс для подписки на потоковые рыночные данные через WebSocket. Позволяет получать обновления в реальном времени:

```python
async def subscribe_to_klines(symbol, interval, callback) -> str
async def unsubscribe_from_klines(subscription_id) -> bool

async def subscribe_to_orderbook(symbol, callback, depth) -> str
async def unsubscribe_from_orderbook(subscription_id) -> bool

async def subscribe_to_trades(symbol, callback) -> str
async def unsubscribe_from_trades(subscription_id) -> bool

async def subscribe_to_liquidations(symbol, callback) -> str
async def unsubscribe_from_liquidations(subscription_id) -> bool

async def subscribe_to_open_interest(symbol, callback) -> str
async def unsubscribe_from_open_interest(subscription_id) -> bool
```

#### IMarketDataProvider

Комбинированный интерфейс, объединяющий функциональность REST и WebSocket провайдеров рыночных данных:

```python
class IMarketDataProvider(IMarketDataRestProvider, IMarketDataStreamProvider):
    pass
```

### Интерфейсы торговых операций

#### ITradeRestExecutor

Интерфейс для выполнения торговых операций через REST API:

```python
async def create_order(order_params) -> OrderInfo
async def cancel_order(symbol, order_id) -> OrderInfo
async def cancel_all_orders(symbol) -> List[OrderInfo]
async def get_order(symbol, order_id) -> OrderInfo
async def get_active_orders(symbol) -> List[OrderInfo]
async def get_position(symbol) -> PositionInfo
async def get_all_positions() -> List[PositionInfo]
async def set_leverage(symbol, leverage) -> bool
async def set_margin_mode(symbol, margin_mode) -> bool
async def set_position_mode(hedge_mode) -> bool
```

#### ITradeStreamExecutor

Интерфейс для получения обновлений о торговых операциях через WebSocket:

```python
async def subscribe_to_order_updates(callback) -> str
async def unsubscribe_from_order_updates(subscription_id) -> bool

async def subscribe_to_execution_updates(callback) -> str
async def unsubscribe_from_execution_updates(subscription_id) -> bool

async def subscribe_to_position_updates(callback) -> str
async def unsubscribe_from_position_updates(subscription_id) -> bool

async def subscribe_to_balance_updates(callback) -> str
async def unsubscribe_from_balance_updates(subscription_id) -> bool
```

#### ITradeExecutor

Комбинированный интерфейс, объединяющий функциональность REST и WebSocket интерфейсов для торговых операций:

```python
class ITradeExecutor(ITradeRestExecutor, ITradeStreamExecutor):
    pass
```

### Использование интерфейсов

Интерфейсы предназначены для использования другими модулями системы VANTA, которым требуется доступ к рыночным данным или выполнение торговых операций. Пример использования:

```python
from exchange_api.interfaces import IMarketDataProvider, ITradeExecutor
from exchange_api.factory import ExchangeClientFactory
from models.market_data import KlineInterval

async def example_usage():
    # Создание клиента биржи с помощью фабрики
    exchange_client = await ExchangeClientFactory.create_client("bybit")
    
    # Получение рыночных данных
    market_data_provider = exchange_client.market_data  # Реализация IMarketDataProvider
    
    # Получение исторических данных свечей
    klines = await market_data_provider.get_klines(
        symbol="BTCUSDT",
        interval=KlineInterval.MIN_1,
        limit=100
    )
    
    # Подписка на обновления стакана в реальном времени
    async def orderbook_callback(orderbook):
        print(f"Получено обновление стакана: {orderbook}")
    
    subscription_id = await market_data_provider.subscribe_to_orderbook(
        symbol="BTCUSDT",
        callback=orderbook_callback,
        depth=10
    )
    
    # Выполнение торговых операций
    trade_executor = exchange_client.trade_executor  # Реализация ITradeExecutor
    
    # Получение открытых позиций
    positions = await trade_executor.get_all_positions()
    
    # Отписка от обновлений стакана
    await market_data_provider.unsubscribe_from_orderbook(subscription_id)
```

### Обработка ошибок

Все методы интерфейсов могут генерировать следующие исключения:

- `VantaAPIError`: Базовое исключение при ошибках взаимодействия с API биржи
- `VantaRateLimitError`: При превышении лимита запросов к API биржи
- `VantaOrderError`: При ошибках операций с ордерами
- `VantaPositionError`: При ошибках операций с позициями
- `VantaWebSocketError`: При ошибках WebSocket соединения

Примеры обработки ошибок:

```python
from exchange_api.exceptions import VantaAPIError, VantaRateLimitError, VantaOrderError

async def example_error_handling(market_data_provider, trade_executor):
    try:
        # Получение рыночных данных
        klines = await market_data_provider.get_klines("BTCUSDT", KlineInterval.MIN_1)
        
    except VantaRateLimitError as e:
        print(f"Превышен лимит запросов: {e}")
        # Логика для повторной попытки с экспоненциальной задержкой
        
    except VantaAPIError as e:
        print(f"Ошибка API: {e}")
        
    try:
        # Выполнение торговой операции
        order = await trade_executor.create_order(order_params)
        
    except VantaOrderError as e:
        print(f"Ошибка создания ордера: {e}")
        # Логика обработки ошибки создания ордера
``` 

## Реализация сервисов рыночных данных для OHLCV (Свечи)

В рамках развития модуля Trading APIs & Exchange были реализованы сервисы для доступа к рыночным данным биржи Bybit, с фокусом на OHLCV данные (свечи):

### Реализованные компоненты

1. **REST провайдер данных**: `BybitMarketDataRestProvider`
   - Полная реализация метода `get_klines` для получения исторических OHLCV данных
   - Преобразование форматов данных биржи в универсальные модели
   - Обработка ошибок и исключений

2. **WebSocket провайдер данных**: `BybitMarketDataStreamProvider`
   - Реализация методов `subscribe_to_klines` и `unsubscribe_from_klines`
   - Управление WebSocket соединениями и подписками
   - Асинхронная обработка потоковых данных через функции обратного вызова

3. **Объединенный сервис**: `BybitMarketDataService`
   - Объединяет функциональность REST и WebSocket провайдеров
   - Предоставляет унифицированный интерфейс для работы с данными
   - Реализует интерфейс `IMarketDataProvider`

### Пример использования

Полный пример получения и обработки OHLCV данных доступен в [examples/kline_data_example.py](examples/kline_data_example.py)

```python
# Краткий пример использования
import asyncio
from exchange_api.exchanges.bybit import BybitClientConfig, BybitEnvironmentType
from exchange_api.services.bybit import BybitMarketDataService
from models.market_data import KlineInterval

async def main():
    # Создание конфигурации
    config = BybitClientConfig(
        exchange_name="bybit",
        bybit_environment=BybitEnvironmentType.TESTNET,
        test_mode=True
    )

    # Использование сервиса через контекстный менеджер
    async with BybitMarketDataService(config) as service:
        # Получение исторических данных
        klines = await service.get_klines(
            symbol="BTCUSDT",
            interval=KlineInterval.MINUTE_1,
            limit=10
        )
        
        # Вывод результатов
        for kline in klines:
            print(f"Время: {kline.timestamp}, Цена: {kline.close}")
```

### Особенности реализации

- **Типизация данных**: Все методы имеют четкую типизацию для повышения надежности кода
- **Асинхронная обработка**: Использование asyncio для неблокирующих операций ввода-вывода
- **Контекстные менеджеры**: Встроенная поддержка контекстных менеджеров для управления ресурсами
- **Обработка ошибок**: Расширенная система исключений для индикации и обработки проблем

### Заглушки для будущего расширения

В сервисе предусмотрены заглушки для реализации методов получения других типов рыночных данных:
- Стакан ордеров (Order Book)
- Последние сделки (Recent Trades)
- Данные по ликвидациям (Liquidations)
- Открытый интерес (Open Interest) 

## Реализованная функциональность

### Сервис для работы со стаканом ордеров

Реализован сервис для доступа к данным стакана ордеров через REST API и WebSocket, с поддержкой различных уровней глубины. Сервис включает в себя:

1. **REST API для получения стакана ордеров**
   - Метод `get_orderbook` в классе `BybitMarketDataRestProvider`
   - Поддержка различных глубин стакана (1, 25, 50, 100, 200, 500)
   - Валидация параметров и обработка ошибок
   - Нормализация данных в формат `OrderBookData`

2. **WebSocket подписка на обновления стакана**
   - Метод `subscribe_to_orderbook` в классе `BybitMarketDataStreamProvider`
   - Поддержка различных глубин стакана через параметр `depth`
   - Обработка как полных снимков, так и инкрементальных обновлений
   - Проксирование данных подписчикам без их хранения на стороне сервиса

3. **Обработчик инкрементальных обновлений стакана**
   - Класс `OrderBookDeltaProcessor`
   - Поддержание актуального состояния стакана на стороне клиента
   - Определение типа обновления (снимок/дельта)
   - Обнаружение пропущенных обновлений и механизмы восстановления

## Примеры использования

В директории `examples/` размещены примеры использования реализованной функциональности:

- `orderbook_example.py` - пример работы со стаканом ордеров (REST API и WebSocket)

### Пример получения данных стакана через REST API

```python
from exchange_api.core.config import ClientConfig
from exchange_api.services.bybit.market_data_service import BybitMarketDataService

# Создаем конфигурацию
config = ClientConfig(
    exchange_name="bybit",
    base_url="https://api.bybit.com",
    websocket_url="wss://stream.bybit.com/v5/public"
)

# Создаем сервис для работы с рыночными данными
market_data_service = BybitMarketDataService(config)

# Получаем данные стакана ордеров
async def get_orderbook_example():
    orderbook = await market_data_service.get_orderbook(
        symbol="BTCUSDT",
        depth=25  # глубина стакана (количество уровней)
    )
    
    # Доступ к данным стакана
    best_bid = orderbook.best_bid()
    best_ask = orderbook.best_ask()
    spread = orderbook.spread()
    
    # Перебор уровней стакана
    for bid_level in orderbook.bids:
        bid_price = bid_level.price
        bid_quantity = bid_level.quantity
        print(f"Бид: {bid_price}, объем: {bid_quantity}")
```

### Пример подписки на обновления стакана через WebSocket

```python
from exchange_api.core.config import ClientConfig
from exchange_api.services.bybit.market_data_service import BybitMarketDataService

# Создаем конфигурацию
config = ClientConfig(
    exchange_name="bybit",
    base_url="https://api.bybit.com",
    websocket_url="wss://stream.bybit.com/v5/public"
)

# Создаем сервис для работы с рыночными данными
market_data_service = BybitMarketDataService(config)

# Обработчик обновлений стакана
async def orderbook_callback(orderbook):
    print(f"Получено обновление стакана для {orderbook.symbol}")
    print(f"Лучший бид: {orderbook.best_bid().price}")
    print(f"Лучший аск: {orderbook.best_ask().price}")

# Подписка на обновления стакана
async def subscribe_to_orderbook_example():
    subscription_id = await market_data_service.subscribe_to_orderbook(
        symbol="BTCUSDT",
        callback=orderbook_callback,
        depth=25  # глубина стакана (количество уровней)
    )
    
    # ... используем подписку ...
    
    # Отменяем подписку, когда она больше не нужна
    await market_data_service.unsubscribe_from_orderbook(subscription_id)
```

## Документация

Подробное описание компонентов:

- `BybitMarketDataRestProvider.get_orderbook` - метод для получения текущего стакана ордеров через REST API
- `BybitMarketDataStreamProvider.subscribe_to_orderbook` - метод для подписки на обновления стакана через WebSocket
- `OrderBookDeltaProcessor` - класс для обработки инкрементальных обновлений стакана

## Критерии выполнения

Реализованные компоненты соответствуют следующим критериям:

1. ✅ Поддержка различных глубин стакана ордеров
2. ✅ Корректная обработка и применение инкрементальных обновлений
3. ✅ Высокая производительность при большом количестве обновлений
4. ✅ Отсутствие хранения данных на стороне сервиса, только проксирование 
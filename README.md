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

### Получение рыночных данных

```python
import asyncio
from exchange_api.core.config import ClientConfig
from exchange_api.services.bybit import BybitMarketDataRestProvider

async def main():
    # Создание конфигурации
    config = ClientConfig.from_env("bybit")
    
    # Создание провайдера рыночных данных
    provider = BybitMarketDataRestProvider(config)
    
    # Инициализация провайдера
    await provider.initialize()
    
    try:
        # Получение OHLCV данных
        klines = await provider.get_klines(
            symbol="BTCUSDT",
            interval="1m",
            limit=100
        )
        
        print(f"Получено {len(klines)} свечей")
        print(f"Последняя свеча: {klines[-1]}")
        
    finally:
        # Освобождение ресурсов
        await provider.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
```

### Выполнение торговых операций

```python
import asyncio
from exchange_api.core.config import ClientConfig
from exchange_api.services.bybit import BybitTradeRestExecutor

async def main():
    # Создание конфигурации
    config = ClientConfig.from_env("bybit")
    
    # Создание исполнителя торговых операций
    executor = BybitTradeRestExecutor(config)
    
    # Инициализация исполнителя
    await executor.initialize()
    
    try:
        # Создание лимитного ордера
        order = await executor.create_order(
            symbol="BTCUSDT",
            side="Buy",
            order_type="Limit",
            qty=0.001,
            price=20000.0
        )
        
        print(f"Создан ордер: {order}")
        
    finally:
        # Освобождение ресурсов
        await executor.shutdown()

if __name__ == "__main__":
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
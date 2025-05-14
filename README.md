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

### Переменные окружения

Для работы с модулем через `ClientConfig.from_env()` необходимо настроить следующие переменные окружения:

```
VANTA_BYBIT_API_KEY=ваш_api_ключ
VANTA_BYBIT_API_SECRET=ваш_секретный_ключ
VANTA_BYBIT_BASE_URL=https://api.bybit.com
VANTA_BYBIT_WS_URL=wss://stream.bybit.com
```

Дополнительные опциональные параметры:
```
VANTA_BYBIT_ENVIRONMENT=production  # или development, test
VANTA_BYBIT_TEST_MODE=false         # или true
VANTA_BYBIT_DEBUG_MODE=false        # или true
```

## Лицензия

MIT 
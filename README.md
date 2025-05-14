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
git clone https://github.com/vanta/exchange_api.git
cd exchange_api
pip install -e .
```

### Через pip

```bash
pip install vanta-exchange-api
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

## Лицензия

MIT 
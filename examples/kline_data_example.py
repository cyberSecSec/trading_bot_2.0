"""
Пример использования сервиса для доступа к OHLCV данным биржи Bybit.

Этот пример демонстрирует получение исторических OHLCV данных через REST API
и подписку на обновления в реальном времени через WebSocket.
"""

import asyncio
from datetime import datetime, timedelta

from exchange_api.exchanges.bybit import BybitClientConfig, BybitEnvironmentType
from exchange_api.services.bybit import BybitMarketDataService
from models.market_data import KlineInterval


async def on_kline_update(kline):
    """Обработчик обновлений OHLCV данных."""
    print(f"Получено обновление свечи для {kline.symbol}:")
    print(f"Время: {kline.timestamp}")
    print(f"Интервал: {kline.interval}")
    print(f"O: {kline.open}, H: {kline.high}, L: {kline.low}, C: {kline.close}")
    print(f"Объем: {kline.volume}")
    print(f"Закрыта: {kline.is_closed}")
    print("-" * 50)


async def main():
    # Создаем тестовую конфигурацию для Bybit
    config = BybitClientConfig(
        exchange_name="bybit",
        bybit_environment=BybitEnvironmentType.TESTNET,
        categories={"spot", "linear"},
        test_mode=True,
        debug_mode=True
    )

    print(f"Подключение к {config.connection.base_url}")

    # Создаем сервис для доступа к рыночным данным
    async with BybitMarketDataService(config) as market_data_service:
        symbol = "BTCUSDT"
        interval = KlineInterval.MINUTE_1

        # 1. Получение исторических OHLCV данных через REST API
        print(f"\nПолучение исторических данных для {symbol}...")
        
        # Задаем временной диапазон (последние 1 час)
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=1)
        
        try:
            # Получаем исторические данные
            klines = await market_data_service.get_klines(
                symbol=symbol,
                interval=interval,
                start_time=start_time,
                end_time=end_time,
                limit=10  # Ограничиваем количество свечей для примера
            )
            
            print(f"Получено {len(klines)} свечей:")
            for i, kline in enumerate(klines[:5], 1):  # Выводим первые 5 свечей
                print(f"Свеча {i}:")
                print(f"  Время: {kline.timestamp}")
                print(f"  O: {kline.open}, H: {kline.high}, L: {kline.low}, C: {kline.close}")
                print(f"  Объем: {kline.volume}")
            
            if len(klines) > 5:
                print("...")
                
        except Exception as e:
            print(f"Ошибка при получении исторических данных: {e}")

        # 2. Подписка на обновления OHLCV данных в реальном времени через WebSocket
        print(f"\nПодписка на обновления OHLCV данных в реальном времени для {symbol}...")
        
        try:
            # Подписываемся на обновления
            subscription_id = await market_data_service.subscribe_to_klines(
                symbol=symbol,
                interval=interval,
                callback=on_kline_update
            )
            
            print(f"Подписка активирована с ID: {subscription_id}")
            print("Ожидание обновлений в течение 60 секунд...")
            
            # Ждем некоторое время для получения обновлений
            await asyncio.sleep(60)
            
            # Отписываемся от обновлений
            result = await market_data_service.unsubscribe_from_klines(subscription_id)
            print(f"Отписка от обновлений: {'успешно' if result else 'не удалось'}")
            
        except Exception as e:
            print(f"Ошибка при работе с WebSocket: {e}")


if __name__ == "__main__":
    # Запускаем асинхронный код
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nПрервано пользователем")
    except Exception as e:
        print(f"Необработанная ошибка: {e}") 
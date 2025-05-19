"""
Пример использования сервисов для работы с данными о сделках Bybit.

Демонстрирует получение последних сделок через REST API и 
подписку на поток сделок через WebSocket.
"""

import asyncio
import signal
from datetime import datetime, timedelta

from exchange_api.core.config import ClientConfig
from exchange_api.exchanges.bybit import BybitClientConfig, BybitEnvironmentType
from exchange_api.services.bybit import BybitMarketDataService

async def callback_trades(trade):
    """
    Callback-функция для обработки сделок в реальном времени.
    
    Args:
        trade: Объект TradeData с информацией о сделке
    """
    print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] "
          f"Новая сделка: "
          f"{trade.symbol} | "
          f"{'Покупка' if trade.is_buy() else 'Продажа'} | "
          f"Цена: {trade.price} | "
          f"Объем: {trade.quantity} | "
          f"ID: {trade.id}")

async def main():
    """Основная функция примера."""
    # Создаем конфигурацию для тестовой сети Bybit
    config = BybitClientConfig(
        exchange_name="bybit",
        bybit_environment=BybitEnvironmentType.TESTNET,
        test_mode=True,
        categories={"spot", "linear"}
    )
    
    # Создаем сервис для доступа к рыночным данным
    async with BybitMarketDataService(config) as service:
        # Символ для получения данных
        symbol = "BTCUSDT"
        
        # 1. Получение последних сделок через REST API
        print(f"\n1. Получение последних сделок для {symbol}\n")
        
        # Запрашиваем последние 5 сделок
        recent_trades = await service.get_recent_trades(symbol, limit=5)
        
        # Выводим информацию о полученных сделках
        for trade in recent_trades:
            print(f"Сделка: "
                  f"{trade.symbol} | "
                  f"{'Покупка' if trade.is_buy() else 'Продажа'} | "
                  f"Цена: {trade.price} | "
                  f"Объем: {trade.quantity} | "
                  f"ID: {trade.id} | "
                  f"Время: {trade.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 2. Подписка на поток сделок через WebSocket
        print(f"\n2. Подписка на поток сделок для {symbol} в реальном времени\n")
        print("Ожидание сделок... (Ctrl+C для выхода)")
        
        # Подписываемся на обновления сделок
        subscription_id = await service.subscribe_to_trades(symbol, callback_trades)
        
        # Имитируем обработку сделок в течение некоторого времени
        try:
            # Запускаем бесконечный цикл ожидания (до прерывания пользователем)
            while True:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            print("\nПолучен сигнал остановки")
        finally:
            # Отписываемся от обновлений и закрываем соединение
            await service.unsubscribe_from_trades(subscription_id)
            print("\nОтписка от обновлений выполнена")

if __name__ == "__main__":
    # Настраиваем обработку сигнала прерывания
    loop = asyncio.get_event_loop()
    main_task = loop.create_task(main())
    
    def signal_handler():
        main_task.cancel()
    
    loop.add_signal_handler(signal.SIGINT, signal_handler)
    
    try:
        loop.run_until_complete(main_task)
    except asyncio.CancelledError:
        pass
    finally:
        loop.close() 
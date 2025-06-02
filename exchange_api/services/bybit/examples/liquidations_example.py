"""
Пример использования сервиса для доступа к данным о ликвидациях Bybit.

Демонстрирует подписку на поток ликвидаций через WebSocket
и анализ получаемых данных.
"""

import asyncio
import signal
from datetime import datetime
from decimal import Decimal

from exchange_api.core.config import ClientConfig
from exchange_api.exchanges.bybit import BybitClientConfig, BybitEnvironmentType
from exchange_api.services.bybit import BybitMarketDataService
from models.market_data import LiquidationSide
from exchange_api.services.bybit.liquidation_analyzer import LiquidationAnalyzer

# Флаг для контроля выполнения основного цикла
running = True

# Обработчик сигнала для корректного завершения
def handle_sigint(sig, frame):
    global running
    print("\nПолучен сигнал завершения. Останавливаем работу...")
    running = False

# Обработчик ликвидаций
async def liquidation_callback(liquidation):
    # Определяем сторону ликвидации для вывода
    side_str = "длинной" if liquidation.is_long_liquidation() else "короткой"
    
    # Форматируем сообщение
    message = (
        f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] "
        f"Ликвидация {side_str} позиции {liquidation.symbol}: "
        f"Цена: {liquidation.price}, Объем: {liquidation.quantity}"
    )
    
    # Рассчитываем стоимость ликвидации
    value = liquidation.value()
    
    # Для крупных ликвидаций добавляем выделение в логе
    if value > Decimal('100000'):  # Более $100k считаем крупной ликвидацией
        message += f"\n⚠️ КРУПНАЯ ЛИКВИДАЦИЯ: ${value:,.2f}"
    
    print(message)

async def main():
    # Регистрируем обработчик сигнала SIGINT (Ctrl+C)
    signal.signal(signal.SIGINT, handle_sigint)
    
    try:
        # Создаем конфигурацию для тестовой сети Bybit
        config = BybitClientConfig(
            exchange_name="bybit",
            bybit_environment=BybitEnvironmentType.TESTNET,
            test_mode=True
        )
        
        print("Подключаемся к Bybit WebSocket API (testnet)...")
        print("Для завершения программы нажмите Ctrl+C")
        
        # Создаем сервис для работы с рыночными данными
        async with BybitMarketDataService(config) as service:
            # Инструменты, за которыми будем следить
            symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
            
            # Словарь для хранения идентификаторов подписок
            subscriptions = {}
            
            # Подписываемся на ликвидации по каждому инструменту
            print(f"Подписываемся на ликвидации для: {', '.join(symbols)}")
            for symbol in symbols:
                subscription_id = await service.subscribe_to_liquidations(
                    symbol=symbol,
                    callback=liquidation_callback
                )
                subscriptions[symbol] = subscription_id
                print(f"Подписка на {symbol} активирована")
            
            print("\nОжидаем ликвидации...\n")
            
            # Создаем собственный анализатор для агрегированного анализа
            liquidation_analyzer = LiquidationAnalyzer(
                large_liquidation_threshold=Decimal('5.0'),
                cascade_time_window_seconds=60,
                cascade_min_volume=Decimal('20.0')
            )
            
            # Основной цикл работы программы
            counter = 0
            while running:
                # Ждем 1 секунду
                await asyncio.sleep(1)
                counter += 1
                
                # Каждые 30 секунд выводим статистику
                if counter >= 30:
                    counter = 0
                    stats = liquidation_analyzer.get_statistics()
                    
                    print("\n--- Статистика ликвидаций ---")
                    print(f"Всего ликвидаций: {stats['total_count']}")
                    print(f"Длинные позиции: {stats['long_liquidations']} ({stats['long_ratio']:.1%})")
                    print(f"Короткие позиции: {stats['short_liquidations']} ({stats['short_ratio']:.1%})")
                    print(f"Общий объем: {stats['total_volume']:.2f}")
                    print(f"Крупных ликвидаций: {stats['large_liquidations']}")
                    print(f"Каскадных событий: {stats['cascade_events']}")
                    print(f"Отслеживаемые символы: {', '.join(stats['symbols'])}")
                    print("-----------------------------\n")
            
            # Отписываемся от всех инструментов
            print("Отключаемся от WebSocket API...")
            for symbol, subscription_id in subscriptions.items():
                await service.unsubscribe_from_liquidations(subscription_id)
                print(f"Отписка от {symbol} выполнена")
                
    except Exception as e:
        print(f"Произошла ошибка: {e}")

if __name__ == "__main__":
    # В Windows для корректной обработки Ctrl+C
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    # Запускаем асинхронную функцию
    asyncio.run(main()) 
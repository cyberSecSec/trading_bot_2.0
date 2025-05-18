#!/usr/bin/env python3
"""
Пример использования сервиса для работы со стаканом ордеров.

Демонстрирует получение данных стакана ордеров через REST API
и подписку на обновления через WebSocket.
"""

import asyncio
import logging
from datetime import datetime

from exchange_api.core.config import ClientConfig
from exchange_api.services.bybit.market_data_service import BybitMarketDataService
from models.market_data import OrderBookData

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Конфигурация клиента
config = ClientConfig(
    exchange_name="bybit",
    base_url="https://api.bybit.com",
    websocket_url="wss://stream.bybit.com/v5/public",
    api_key="YOUR_API_KEY",  # Не требуется для публичных данных
    api_secret="YOUR_API_SECRET",  # Не требуется для публичных данных
    categories={"spot", "linear"}
)

# Функции для анализа данных стакана
def analyze_orderbook(orderbook: OrderBookData) -> None:
    """Анализирует данные стакана и выводит основную информацию."""
    
    # Получаем лучшие бид и аск
    best_bid = orderbook.best_bid()
    best_ask = orderbook.best_ask()
    
    # Рассчитываем спред
    spread = orderbook.spread()
    spread_percentage = orderbook.spread_percentage()
    
    # Расчет суммарных объемов
    bid_volume = sum(level.quantity for level in orderbook.bids)
    ask_volume = sum(level.quantity for level in orderbook.asks)
    
    # Соотношение спроса и предложения
    imbalance = orderbook.imbalance()
    
    # Вывод информации
    logger.info(f"Символ: {orderbook.symbol}")
    logger.info(f"Timestamp: {orderbook.timestamp}")
    logger.info(f"Лучший бид: {best_bid.price if best_bid else None}")
    logger.info(f"Лучший аск: {best_ask.price if best_ask else None}")
    logger.info(f"Спред: {spread}")
    logger.info(f"Спред %: {spread_percentage}%")
    logger.info(f"Объем бидов: {bid_volume}")
    logger.info(f"Объем асков: {ask_volume}")
    logger.info(f"Дисбаланс: {imbalance}")
    logger.info(f"Количество уровней: {len(orderbook.bids)} бидов, {len(orderbook.asks)} асков")
    logger.info("-" * 50)

# Обработчик обновлений стакана через WebSocket
async def orderbook_callback(orderbook: OrderBookData) -> None:
    """Обработчик для обновлений стакана ордеров через WebSocket."""
    logger.info(f"Получено обновление стакана для {orderbook.symbol} в {orderbook.timestamp}")
    analyze_orderbook(orderbook)

# Основная функция
async def main() -> None:
    """Основная функция для демонстрации работы со стаканом ордеров."""
    
    # Создаем сервис для работы с рыночными данными
    market_data_service = BybitMarketDataService(config)
    
    try:
        # Символ, для которого будем получать данные
        symbol = "BTCUSDT"
        
        # 1. Получение данных стакана через REST API
        logger.info("Получение данных стакана через REST API")
        orderbook = await market_data_service.get_orderbook(symbol, depth=25)
        analyze_orderbook(orderbook)
        
        # 2. Подписка на обновления стакана через WebSocket
        logger.info(f"Подписка на обновления стакана для {symbol}")
        subscription_id = await market_data_service.subscribe_to_orderbook(
            symbol=symbol,
            callback=orderbook_callback,
            depth=25
        )
        
        # Ждем некоторое время, чтобы получить обновления
        logger.info("Ожидание обновлений стакана...")
        await asyncio.sleep(30)
        
        # Отмена подписки
        logger.info("Отмена подписки на обновления стакана")
        await market_data_service.unsubscribe_from_orderbook(subscription_id)
        
        # Пауза перед завершением
        await asyncio.sleep(1)
        
    except Exception as e:
        logger.error(f"Ошибка при работе со стаканом ордеров: {e}")
    finally:
        # Закрываем соединения
        await market_data_service.close()

# Запуск примера
if __name__ == "__main__":
    asyncio.run(main()) 
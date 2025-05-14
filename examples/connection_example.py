"""
Пример использования адаптеров соединения.

Демонстрирует базовое использование ConnectionManager, WebSocketManager и ReconnectionHandler.
"""
import asyncio
import json
from datetime import datetime
from typing import Dict, Any

from exchange_api.core.config import ClientConfig
from exchange_api.exchanges.bybit import BybitClientConfig, BybitEnvironmentType
from exchange_api.exchanges.bybit import BybitConnectionManager, BybitWebSocketManager
from exchange_api.connection import ReconnectionHandler
from exchange_api.utils.logger import Logger, LogConfig


# Настраиваем логирование
Logger.setup(
    config=LogConfig(level="DEBUG", colorize=True),
    console_enabled=True,
    file_enabled=False
)

# Получаем логгер
logger = Logger.get_logger()


# Обработчик сообщений WebSocket
async def message_handler(data: Dict[str, Any]) -> None:
    """Обрабатывает входящие сообщения от WebSocket."""
    timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
    
    # Форматируем сообщение для вывода
    if 'topic' in data:
        topic = data['topic']
        type_str = data.get('type', '')
        
        logger.info(f"[{timestamp}] Получены данные по теме: {topic}, тип: {type_str}")
        
        # Для демонстрации выводим только часть данных
        if 'data' in data:
            if isinstance(data['data'], list) and len(data['data']) > 0:
                logger.info(f"Получено {len(data['data'])} записей данных")
            elif isinstance(data['data'], dict):
                logger.info(f"Получены данные: {json.dumps(data['data'])[:200]}")
    else:
        # Системное сообщение
        op = data.get('op', '')
        if op:
            logger.info(f"[{timestamp}] Получено системное сообщение: {op}")
            if op == 'pong':
                logger.debug("Получен pong")


# Обработчик ошибок WebSocket
async def error_handler(error: Exception) -> None:
    """Обрабатывает ошибки WebSocket."""
    logger.error(f"WebSocket ошибка: {error}")


# Демонстрационная функция для работы с HTTP
@ReconnectionHandler.with_backoff(max_tries=3, base_delay=1.0)
async def fetch_ticker(conn: BybitConnectionManager, symbol: str) -> Dict[str, Any]:
    """
    Получает данные тикера для указанного символа.
    
    Args:
        conn: Менеджер соединений Bybit
        symbol: Символ инструмента (например, BTCUSDT)
        
    Returns:
        Dict[str, Any]: Данные тикера
    """
    response = await conn.get("/v5/market/tickers", {"category": "spot", "symbol": symbol})
    
    # Проверяем, что ответ успешный
    if 'retCode' in response and response['retCode'] == 0:
        if 'result' in response and 'list' in response['result']:
            ticker_list = response['result']['list']
            if ticker_list:
                return ticker_list[0]
    
    # Если что-то пошло не так, логируем ошибку и возвращаем пустой словарь
    logger.error(f"Ошибка получения тикера: {response}")
    return {}


# Основная асинхронная функция
async def main() -> None:
    """Основная функция для демонстрации работы с API Bybit."""
    try:
        # Создаем конфигурацию для Bybit
        config = BybitClientConfig(
            api_key="ваш_api_ключ",  # Замените на реальный API ключ или передайте None
            api_secret="ваш_секретный_ключ",  # Замените на реальный секретный ключ или передайте None
            environment=BybitEnvironmentType.TESTNET,  # Используем тестовую сеть
            debug_mode=True,
            categories=["spot", "linear"]
        )
        
        # Демонстрация работы с HTTP API
        logger.info("--- Демонстрация HTTP API ---")
        
        # Создаем менеджер соединений
        async with BybitConnectionManager(config) as conn:
            # Проверяем соединение
            is_connected = await conn.check_connection()
            if is_connected:
                logger.info("Соединение с Bybit API установлено успешно")
                
                # Получаем время сервера
                server_time = await conn.get_server_time()
                logger.info(f"Время сервера Bybit: {server_time}")
                
                # Получаем данные тикера
                ticker = await fetch_ticker(conn, "BTCUSDT")
                if ticker:
                    logger.info(f"Тикер BTCUSDT: цена {ticker.get('lastPrice', 'N/A')}, "
                                f"изменение 24ч: {ticker.get('price24hPcnt', 'N/A')}")
            else:
                logger.error("Не удалось установить соединение с Bybit API")
        
        # Пауза перед следующей демонстрацией
        await asyncio.sleep(1)
        
        # Демонстрация работы с WebSocket API
        logger.info("\n--- Демонстрация WebSocket API ---")
        
        # Создаем менеджер WebSocket соединений
        ws_manager = BybitWebSocketManager(
            config=config,
            on_message=message_handler,
            on_error=error_handler
        )
        
        # Подключаемся к WebSocket серверу
        await ws_manager.connect()
        
        # Подписываемся на канал тикеров для BTCUSDT
        await ws_manager.subscribe_public_v5("spot", "BTCUSDT", "ticker")
        
        # Подписываемся на канал сделок для ETHUSDT
        await ws_manager.subscribe_public_v5("spot", "ETHUSDT", "trade")
        
        # Ожидаем получения данных в течение 30 секунд
        logger.info("Ожидание данных WebSocket в течение 30 секунд...")
        await asyncio.sleep(30)
        
        # Отключаемся от WebSocket сервера
        await ws_manager.disconnect()
        logger.info("WebSocket соединение закрыто")
        
    except Exception as e:
        logger.error(f"Ошибка в основной функции: {e}")


# Запуск асинхронной функции
if __name__ == "__main__":
    asyncio.run(main()) 
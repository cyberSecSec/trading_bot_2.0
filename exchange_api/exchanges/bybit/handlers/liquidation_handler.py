"""
Обработчик сообщений о ликвидациях от WebSocket API Bybit.

Отвечает за разбор сообщений о ликвидациях и их преобразование
в унифицированный формат LiquidationData.
"""

from typing import Dict, Any, Callable, Awaitable, List
import re

from models.market_data import LiquidationData
from exchange_api.utils.logger import Logger

# Получаем логгер
logger = Logger.get_logger()

class LiquidationMessageHandler:
    """
    Обработчик сообщений о ликвидациях от WebSocket API Bybit.
    
    Отвечает за парсинг сообщений о ликвидациях и их преобразование
    в унифицированный формат LiquidationData.
    """
    
    # Регулярное выражение для извлечения информации из темы канала
    TOPIC_PATTERN = re.compile(r'^liquidation\.([A-Za-z0-9]+)$')
    
    def __init__(self, callback: Callable[[LiquidationData], Awaitable[None]]):
        """
        Инициализирует обработчик сообщений о ликвидациях.
        
        Args:
            callback: Асинхронная функция обратного вызова, которая будет вызываться
                     при получении новых данных. Принимает объект LiquidationData.
        """
        self.callback = callback
    
    async def handle_message(self, message: Dict[str, Any]) -> bool:
        """
        Обрабатывает входящее сообщение WebSocket.
        
        Args:
            message: Полученное сообщение
            
        Returns:
            bool: True, если сообщение было обработано, иначе False
        """
        if 'topic' not in message:
            return False
        
        topic = message['topic']
        
        # Проверяем, относится ли сообщение к ликвидациям
        match = self.TOPIC_PATTERN.match(topic)
        if not match:
            return False
        
        # Извлекаем символ из темы
        symbol = match.group(1)
        
        try:
            # Извлекаем данные о ликвидациях из сообщения
            liquidations_data = message.get('data', [])
            
            # Если данные не в списке, обернем их в список
            if not isinstance(liquidations_data, list):
                liquidations_data = [liquidations_data]
            
            # Проверка на пустые данные
            if not liquidations_data:
                logger.debug(f"Получено сообщение о ликвидациях с пустыми данными для {symbol}")
                return True
            
            # Обрабатываем каждую ликвидацию
            for liquidation_data in liquidations_data:
                # Преобразуем данные в LiquidationData
                liquidation = LiquidationData.from_bybit_ws(liquidation_data, symbol)
                
                # Логируем получение крупной ликвидации для отладки
                if liquidation.quantity >= 5.0:  # Пример условия для "крупной" ликвидации
                    side_str = "длинной" if liquidation.is_long_liquidation() else "короткой"
                    logger.info(
                        f"Крупная ликвидация {side_str} позиции {symbol}: "
                        f"Цена: {liquidation.price}, Объем: {liquidation.quantity}, "
                        f"Стоимость: ${liquidation.value():,.2f}"
                    )
                
                # Вызываем колбэк с преобразованными данными
                await self.callback(liquidation)
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при обработке сообщения о ликвидациях: {str(e)}")
            return False 
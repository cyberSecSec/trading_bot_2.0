"""
Обработчик сообщений о сделках от WebSocket API Bybit.

Отвечает за разбор сообщений о сделках и их преобразование
в унифицированный формат TradeData.
"""

from typing import Dict, Any, Callable, Awaitable, List
import re

from models.market_data import TradeData
from exchange_api.utils.logger import Logger

# Получаем логгер
logger = Logger.get_logger()

class TradeMessageHandler:
    """
    Обработчик сообщений о сделках от WebSocket API Bybit.
    
    Парсит сообщения о сделках и передает их в коллбэк-функцию.
    """
    
    # Регулярное выражение для извлечения информации из темы канала
    TOPIC_PATTERN = re.compile(r'^publicTrade\.([A-Za-z0-9]+)$')
    
    def __init__(self, callback: Callable[[TradeData], Awaitable[None]]):
        """
        Инициализирует обработчик сообщений о сделках.
        
        Args:
            callback: Асинхронная функция обратного вызова, которая будет вызываться
                     при получении новых данных. Принимает объект TradeData.
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
        
        # Проверяем, относится ли сообщение к сделкам
        match = self.TOPIC_PATTERN.match(topic)
        if not match:
            return False
        
        # Извлекаем символ из темы
        symbol = match.group(1)
        
        try:
            # Извлекаем данные о сделках из сообщения
            trades_data = message.get('data', [])
            
            # Обрабатываем каждую сделку
            for trade_data in trades_data:
                # Преобразуем данные в TradeData
                trade = TradeData.from_bybit_ws(trade_data, symbol)
                
                # Вызываем коллбэк с преобразованными данными
                await self.callback(trade)
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при обработке сообщения о сделках: {str(e)}")
            return False 
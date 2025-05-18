"""
Процессор для обработки инкрементальных обновлений стакана ордеров Bybit.

Отвечает за поддержание актуального состояния стакана ордеров
путем применения дельта-обновлений к текущему состоянию и
определения типа обновления (снимок/дельта).
"""

import logging
from typing import Dict, Any, Callable, Awaitable, Optional
from datetime import datetime

from models.market_data import OrderBookData
from models.utils.converters import timestamp_to_datetime

class OrderBookDeltaProcessor:
    """
    Процессор для обработки инкрементальных обновлений стакана ордеров.
    
    Отвечает за поддержание актуального состояния стакана ордеров путем
    применения дельта-обновлений к текущему состоянию.
    """
    
    def __init__(self, symbol: str):
        """
        Инициализирует процессор для указанного символа.
        
        Args:
            symbol: Торговый символ (например, "BTCUSDT").
        """
        self.symbol = symbol
        self.logger = logging.getLogger(__name__)
        
        # Текущее состояние стакана (последний полный снимок)
        self.current_orderbook: Optional[OrderBookData] = None
        
        # ID последнего обновления для проверки последовательности
        self.last_update_id: Optional[int] = None
        
    async def process_message(self, message: Dict[str, Any], 
                              callback: Callable[[OrderBookData], Awaitable[None]]) -> None:
        """
        Обрабатывает входящее сообщение и вызывает callback с актуальным стаканом.
        
        Args:
            message: Сообщение от WebSocket API
            callback: Функция обратного вызова для отправки обновленного стакана
        """
        # Определяем тип сообщения (снимок или обновление)
        is_snapshot = message.get('update_type', 'snapshot') == 'snapshot'
        
        # Получаем данные сообщения
        symbol = message.get('symbol', self.symbol)
        depth = message.get('depth', '25')  # Глубина стакана может присутствовать в сообщении
        timestamp = timestamp_to_datetime(message.get('timestamp', datetime.now().timestamp() * 1000))
        
        # Извлекаем данные bids и asks
        bids = message.get('bids', [])
        asks = message.get('asks', [])
        
        # Получаем ID обновления, если есть
        update_id = message.get('update_id')
        
        # Создаем объект OrderBookData из сообщения
        new_data = OrderBookData(
            symbol=symbol,
            timestamp=timestamp,
            bids=bids,
            asks=asks,
            update_id=update_id,
            is_snapshot=is_snapshot
        )
        
        # Обрабатываем сообщение в зависимости от его типа
        if is_snapshot:
            # Если это снимок, просто заменяем текущий стакан
            self.current_orderbook = new_data
            self.last_update_id = update_id
            
            self.logger.debug(
                f"Получен снимок стакана для {symbol} "
                f"с {len(bids)} bids и {len(asks)} asks, update_id={update_id}"
            )
            
            # Вызываем callback с новым стаканом
            await callback(new_data)
            
        elif self.current_orderbook is not None:
            # Проверяем, что обновления идут последовательно
            if self.last_update_id is not None and update_id is not None:
                if update_id <= self.last_update_id:
                    self.logger.warning(
                        f"Пропущено устаревшее обновление для {symbol}: "
                        f"update_id={update_id}, last_update_id={self.last_update_id}"
                    )
                    return
                
                # Если есть разрыв в последовательности
                if update_id > self.last_update_id + 1:
                    self.logger.warning(
                        f"Возможный пропуск обновлений для {symbol}: "
                        f"update_id={update_id}, last_update_id={self.last_update_id}"
                    )
                    # При значительном разрыве можно запросить новый снимок
                    # Это будет реализовано через внешний механизм
            
            # Применяем дельта-обновление к текущему стакану
            updated_orderbook = self.current_orderbook.apply_delta(new_data)
            self.current_orderbook = updated_orderbook
            self.last_update_id = update_id
            
            self.logger.debug(
                f"Применено обновление стакана для {symbol}, update_id={update_id}"
            )
            
            # Вызываем callback с обновленным стаканом
            await callback(updated_orderbook)
            
        else:
            # Если получили обновление, но у нас нет текущего стакана
            self.logger.warning(
                f"Получено обновление для {symbol}, но нет текущего стакана. "
                f"Необходимо запросить снимок."
            )
            # Отправляем обновление без применения дельты, 
            # внешний код должен будет запросить полный снимок
            await callback(new_data)
    
    def reset(self) -> None:
        """
        Сбрасывает текущее состояние стакана. 
        
        Используется при переподключении или при обнаружении 
        несогласованности данных.
        """
        self.current_orderbook = None
        self.last_update_id = None
        self.logger.info(f"Состояние стакана для {self.symbol} сброшено") 
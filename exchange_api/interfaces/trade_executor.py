"""
Интерфейсы для выполнения торговых операций в модуле Trading APIs & Exchange.

Этот модуль содержит абстрактные интерфейсы для выполнения торговых операций
через REST API и получения обновлений о торговых операциях через WebSocket.
Интерфейсы абстрагируют детали конкретных бирж и предоставляют унифицированные 
методы для работы с ордерами, позициями и аккаунтом.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Callable, Awaitable, Union
from decimal import Decimal

from models.trading import (
    OrderParams, OrderInfo, OrderStatus, ExecutionInfo, 
    PositionInfo, OrderSide, OrderType, TimeInForce,
    MarginMode, PositionIdx
)


class ITradeRestExecutor(ABC):
    """
    Интерфейс для выполнения торговых операций через REST API.
    
    Предоставляет методы для создания и управления ордерами, получения информации
    о позициях, настройки параметров торговли и других торговых операций.
    """
    
    @abstractmethod
    async def create_order(self, order_params: OrderParams) -> OrderInfo:
        """
        Создает новый ордер согласно указанным параметрам.
        
        Args:
            order_params: Параметры ордера, включающие символ, тип, сторону, цену и т.д.
            
        Returns:
            Информация о созданном ордере.
            
        Raises:
            VantaAPIError: При ошибке взаимодействия с API биржи.
            VantaOrderError: При ошибке создания ордера (недостаточно средств, неверные параметры и т.д.).
        """
        pass
    
    @abstractmethod
    async def cancel_order(self, symbol: str, order_id: str) -> OrderInfo:
        """
        Отменяет указанный ордер.
        
        Args:
            symbol: Торговый символ, для которого был создан ордер.
            order_id: Идентификатор ордера для отмены.
            
        Returns:
            Информация об отмененном ордере.
            
        Raises:
            VantaAPIError: При ошибке взаимодействия с API биржи.
            VantaOrderError: При ошибке отмены ордера (ордер не найден, уже исполнен и т.д.).
        """
        pass
    
    @abstractmethod
    async def cancel_all_orders(self, symbol: Optional[str] = None) -> List[OrderInfo]:
        """
        Отменяет все активные ордера, опционально фильтруя по символу.
        
        Args:
            symbol: Торговый символ для отмены ордеров. Если None, отменяются все ордера.
            
        Returns:
            Список информации об отмененных ордерах.
            
        Raises:
            VantaAPIError: При ошибке взаимодействия с API биржи.
            VantaOrderError: При ошибке отмены ордеров.
        """
        pass
    
    @abstractmethod
    async def get_order(self, symbol: str, order_id: str) -> OrderInfo:
        """
        Получает информацию о конкретном ордере.
        
        Args:
            symbol: Торговый символ, для которого был создан ордер.
            order_id: Идентификатор ордера.
            
        Returns:
            Информация об ордере.
            
        Raises:
            VantaAPIError: При ошибке взаимодействия с API биржи.
            VantaOrderError: При ошибке получения информации об ордере (ордер не найден и т.д.).
        """
        pass
    
    @abstractmethod
    async def get_active_orders(self, symbol: Optional[str] = None) -> List[OrderInfo]:
        """
        Получает список активных ордеров, опционально фильтруя по символу.
        
        Args:
            symbol: Торговый символ для фильтрации ордеров. Если None, возвращаются все активные ордера.
            
        Returns:
            Список активных ордеров.
            
        Raises:
            VantaAPIError: При ошибке взаимодействия с API биржи.
        """
        pass
    
    @abstractmethod
    async def get_position(self, symbol: str) -> PositionInfo:
        """
        Получает информацию о позиции по указанному символу.
        
        Args:
            symbol: Торговый символ.
            
        Returns:
            Информация о позиции.
            
        Raises:
            VantaAPIError: При ошибке взаимодействия с API биржи.
            VantaPositionError: При ошибке получения информации о позиции.
        """
        pass
    
    @abstractmethod
    async def get_all_positions(self) -> List[PositionInfo]:
        """
        Получает информацию о всех открытых позициях.
        
        Returns:
            Список информации о всех открытых позициях.
            
        Raises:
            VantaAPIError: При ошибке взаимодействия с API биржи.
        """
        pass
    
    @abstractmethod
    async def set_leverage(self, symbol: str, leverage: Union[int, Decimal]) -> bool:
        """
        Устанавливает кредитное плечо для указанного символа.
        
        Args:
            symbol: Торговый символ.
            leverage: Значение кредитного плеча (например, 5 для 5x).
            
        Returns:
            True, если операция выполнена успешно, False в противном случае.
            
        Raises:
            VantaAPIError: При ошибке взаимодействия с API биржи.
            VantaPositionError: При ошибке установки кредитного плеча (неверное значение и т.д.).
        """
        pass
    
    @abstractmethod
    async def set_margin_mode(self, symbol: str, margin_mode: MarginMode) -> bool:
        """
        Устанавливает режим маржи для указанного символа.
        
        Args:
            symbol: Торговый символ.
            margin_mode: Режим маржи (изолированная или кросс).
            
        Returns:
            True, если операция выполнена успешно, False в противном случае.
            
        Raises:
            VantaAPIError: При ошибке взаимодействия с API биржи.
            VantaPositionError: При ошибке установки режима маржи.
        """
        pass
    
    @abstractmethod
    async def set_position_mode(self, hedge_mode: bool) -> bool:
        """
        Устанавливает режим позиций (хеджирование или односторонний).
        
        Args:
            hedge_mode: True для режима хеджирования (разрешены длинные и короткие позиции
                       одновременно), False для одностороннего режима.
            
        Returns:
            True, если операция выполнена успешно, False в противном случае.
            
        Raises:
            VantaAPIError: При ошибке взаимодействия с API биржи.
            VantaPositionError: При ошибке установки режима позиций.
        """
        pass


class ITradeStreamExecutor(ABC):
    """
    Интерфейс для получения обновлений о торговых операциях через WebSocket.
    
    Предоставляет методы для подписки на обновления ордеров, исполнений,
    позиций и баланса в реальном времени.
    """
    
    @abstractmethod
    async def subscribe_to_order_updates(self, 
                                        callback: Callable[[OrderInfo], Awaitable[None]]) -> str:
        """
        Подписывается на обновления статуса ордеров.
        
        Args:
            callback: Асинхронная функция обратного вызова, которая будет вызываться
                     при получении новых данных. Принимает объект OrderInfo.
            
        Returns:
            Идентификатор подписки, который может быть использован для отписки.
            
        Raises:
            VantaAPIError: При ошибке взаимодействия с API биржи.
            VantaWebSocketError: При ошибке WebSocket соединения.
        """
        pass
    
    @abstractmethod
    async def unsubscribe_from_order_updates(self, subscription_id: str) -> bool:
        """
        Отписывается от обновлений статуса ордеров.
        
        Args:
            subscription_id: Идентификатор подписки, полученный при вызове 
                            subscribe_to_order_updates.
            
        Returns:
            True, если отписка выполнена успешно, False в противном случае.
            
        Raises:
            VantaAPIError: При ошибке взаимодействия с API биржи.
            VantaWebSocketError: При ошибке WebSocket соединения.
        """
        pass
    
    @abstractmethod
    async def subscribe_to_execution_updates(self, 
                                           callback: Callable[[ExecutionInfo], Awaitable[None]]) -> str:
        """
        Подписывается на обновления исполнения ордеров.
        
        Args:
            callback: Асинхронная функция обратного вызова, которая будет вызываться
                     при получении новых данных. Принимает объект ExecutionInfo.
            
        Returns:
            Идентификатор подписки, который может быть использован для отписки.
            
        Raises:
            VantaAPIError: При ошибке взаимодействия с API биржи.
            VantaWebSocketError: При ошибке WebSocket соединения.
        """
        pass
    
    @abstractmethod
    async def unsubscribe_from_execution_updates(self, subscription_id: str) -> bool:
        """
        Отписывается от обновлений исполнения ордеров.
        
        Args:
            subscription_id: Идентификатор подписки, полученный при вызове 
                            subscribe_to_execution_updates.
            
        Returns:
            True, если отписка выполнена успешно, False в противном случае.
            
        Raises:
            VantaAPIError: При ошибке взаимодействия с API биржи.
            VantaWebSocketError: При ошибке WebSocket соединения.
        """
        pass
    
    @abstractmethod
    async def subscribe_to_position_updates(self,
                                          callback: Callable[[PositionInfo], Awaitable[None]]) -> str:
        """
        Подписывается на обновления позиций.
        
        Args:
            callback: Асинхронная функция обратного вызова, которая будет вызываться
                     при получении новых данных. Принимает объект PositionInfo.
            
        Returns:
            Идентификатор подписки, который может быть использован для отписки.
            
        Raises:
            VantaAPIError: При ошибке взаимодействия с API биржи.
            VantaWebSocketError: При ошибке WebSocket соединения.
        """
        pass
    
    @abstractmethod
    async def unsubscribe_from_position_updates(self, subscription_id: str) -> bool:
        """
        Отписывается от обновлений позиций.
        
        Args:
            subscription_id: Идентификатор подписки, полученный при вызове 
                            subscribe_to_position_updates.
            
        Returns:
            True, если отписка выполнена успешно, False в противном случае.
            
        Raises:
            VantaAPIError: При ошибке взаимодействия с API биржи.
            VantaWebSocketError: При ошибке WebSocket соединения.
        """
        pass
    
    @abstractmethod
    async def subscribe_to_balance_updates(self, 
                                         callback: Callable[[Dict[str, Any]], Awaitable[None]]) -> str:
        """
        Подписывается на обновления баланса.
        
        Args:
            callback: Асинхронная функция обратного вызова, которая будет вызываться
                     при получении новых данных. Принимает словарь с информацией о балансе.
            
        Returns:
            Идентификатор подписки, который может быть использован для отписки.
            
        Raises:
            VantaAPIError: При ошибке взаимодействия с API биржи.
            VantaWebSocketError: При ошибке WebSocket соединения.
        """
        pass
    
    @abstractmethod
    async def unsubscribe_from_balance_updates(self, subscription_id: str) -> bool:
        """
        Отписывается от обновлений баланса.
        
        Args:
            subscription_id: Идентификатор подписки, полученный при вызове 
                            subscribe_to_balance_updates.
            
        Returns:
            True, если отписка выполнена успешно, False в противном случае.
            
        Raises:
            VantaAPIError: При ошибке взаимодействия с API биржи.
            VantaWebSocketError: При ошибке WebSocket соединения.
        """
        pass


class ITradeExecutor(ITradeRestExecutor, ITradeStreamExecutor):
    """
    Комбинированный интерфейс, объединяющий функциональность REST и WebSocket
    интерфейсов для торговых операций.
    
    Предоставляет полный набор методов для выполнения торговых операций и получения
    обновлений о торговых операциях в реальном времени.
    """
    pass 
"""
Интерфейсы для работы с рыночными данными в модуле Trading APIs & Exchange.

Этот модуль содержит абстрактные интерфейсы для получения рыночных данных 
через REST API и WebSocket соединения. Интерфейсы абстрагируют детали 
конкретных бирж и предоставляют унифицированные методы для работы 
с различными типами рыночных данных.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Callable, Awaitable
from datetime import datetime

from models.market_data import KlineData, OrderBookData, TradeData, LiquidationData, OpenInterestData
from models.market_data.kline import KlineInterval


class IMarketDataRestProvider(ABC):
    """
    Интерфейс для получения рыночных данных через REST API.
    
    Предоставляет методы для запроса различных типов рыночных данных, таких как
    OHLCV данные (свечи), стакан ордеров, сделки и открытый интерес.
    """
    
    @abstractmethod
    async def get_klines(self, symbol: str, interval: KlineInterval, 
                         limit: Optional[int] = None, 
                         start_time: Optional[datetime] = None, 
                         end_time: Optional[datetime] = None) -> List[KlineData]:
        """
        Получает исторические OHLCV данные (свечи) для указанного символа и интервала.
        
        Args:
            symbol: Торговый символ (например, "BTCUSDT").
            interval: Интервал свечей (например, KlineInterval.MIN_1, KlineInterval.HOUR_1).
            limit: Максимальное количество свечей для получения. 
                  Если None, используется значение по умолчанию API.
            start_time: Начальное время для получения данных. Если None, не используется.
            end_time: Конечное время для получения данных. Если None, не используется.
            
        Returns:
            Список объектов KlineData, отсортированных по времени (обычно от старых к новым).
            
        Raises:
            VantaAPIError: При ошибке взаимодействия с API биржи.
            VantaRateLimitError: При превышении лимита запросов к API биржи.
        """
        pass
    
    @abstractmethod
    async def get_orderbook(self, symbol: str, depth: Optional[int] = None) -> OrderBookData:
        """
        Получает текущий стакан ордеров для указанного символа.
        
        Args:
            symbol: Торговый символ (например, "BTCUSDT").
            depth: Глубина стакана ордеров (количество ценовых уровней).
                  Если None, используется значение по умолчанию API.
            
        Returns:
            Объект OrderBookData, содержащий текущий стакан ордеров.
            
        Raises:
            VantaAPIError: При ошибке взаимодействия с API биржи.
            VantaRateLimitError: При превышении лимита запросов к API биржи.
        """
        pass
    
    @abstractmethod
    async def get_recent_trades(self, symbol: str, limit: Optional[int] = None) -> List[TradeData]:
        """
        Получает список недавних сделок для указанного символа.
        
        Args:
            symbol: Торговый символ (например, "BTCUSDT").
            limit: Максимальное количество сделок для получения.
                  Если None, используется значение по умолчанию API.
            
        Returns:
            Список объектов TradeData, отсортированных по времени (обычно от старых к новым).
            
        Raises:
            VantaAPIError: При ошибке взаимодействия с API биржи.
            VantaRateLimitError: При превышении лимита запросов к API биржи.
        """
        pass
    
    @abstractmethod
    async def get_open_interest(self, symbol: str) -> OpenInterestData:
        """
        Получает текущий открытый интерес для указанного символа.
        
        Args:
            symbol: Торговый символ (например, "BTCUSDT").
            
        Returns:
            Объект OpenInterestData, содержащий информацию об открытом интересе.
            
        Raises:
            VantaAPIError: При ошибке взаимодействия с API биржи.
            VantaRateLimitError: При превышении лимита запросов к API биржи.
        """
        pass
    
    @abstractmethod
    async def get_open_interest_history(self, symbol: str, period: str, 
                                         limit: Optional[int] = None) -> List[OpenInterestData]:
        """
        Получает историю открытого интереса для указанного символа.
        
        Args:
            symbol: Торговый символ (например, "BTCUSDT").
            period: Период агрегации данных (например, "5min", "1h", "1d").
            limit: Максимальное количество записей для получения.
                  Если None, используется значение по умолчанию API.
            
        Returns:
            Список объектов OpenInterestData, отсортированных по времени (обычно от старых к новым).
            
        Raises:
            VantaAPIError: При ошибке взаимодействия с API биржи.
            VantaRateLimitError: При превышении лимита запросов к API биржи.
        """
        pass


class IMarketDataStreamProvider(ABC):
    """
    Интерфейс для подписки на потоковые рыночные данные через WebSocket.
    
    Предоставляет методы для подписки на обновления различных типов рыночных данных,
    таких как OHLCV данные (свечи), стакан ордеров, сделки, ликвидации и открытый интерес.
    """
    
    @abstractmethod
    async def subscribe_to_klines(self, symbol: str, interval: KlineInterval, 
                                  callback: Callable[[KlineData], Awaitable[None]]) -> str:
        """
        Подписывается на обновления OHLCV данных (свечей) в реальном времени.
        
        Args:
            symbol: Торговый символ (например, "BTCUSDT").
            interval: Интервал свечей (например, KlineInterval.MIN_1, KlineInterval.HOUR_1).
            callback: Асинхронная функция обратного вызова, которая будет вызываться
                     при получении новых данных. Принимает объект KlineData.
            
        Returns:
            Идентификатор подписки, который может быть использован для отписки.
            
        Raises:
            VantaAPIError: При ошибке взаимодействия с API биржи.
            VantaWebSocketError: При ошибке WebSocket соединения.
        """
        pass
    
    @abstractmethod
    async def unsubscribe_from_klines(self, subscription_id: str) -> bool:
        """
        Отписывается от обновлений OHLCV данных (свечей).
        
        Args:
            subscription_id: Идентификатор подписки, полученный при вызове subscribe_to_klines.
            
        Returns:
            True, если отписка выполнена успешно, False в противном случае.
            
        Raises:
            VantaAPIError: При ошибке взаимодействия с API биржи.
            VantaWebSocketError: При ошибке WebSocket соединения.
        """
        pass
    
    @abstractmethod
    async def subscribe_to_orderbook(self, symbol: str, 
                                    callback: Callable[[OrderBookData], Awaitable[None]],
                                    depth: Optional[int] = None) -> str:
        """
        Подписывается на обновления стакана ордеров в реальном времени.
        
        Args:
            symbol: Торговый символ (например, "BTCUSDT").
            callback: Асинхронная функция обратного вызова, которая будет вызываться
                     при получении новых данных. Принимает объект OrderBookData.
            depth: Глубина стакана ордеров (количество ценовых уровней).
                  Если None, используется значение по умолчанию API.
            
        Returns:
            Идентификатор подписки, который может быть использован для отписки.
            
        Raises:
            VantaAPIError: При ошибке взаимодействия с API биржи.
            VantaWebSocketError: При ошибке WebSocket соединения.
        """
        pass
    
    @abstractmethod
    async def unsubscribe_from_orderbook(self, subscription_id: str) -> bool:
        """
        Отписывается от обновлений стакана ордеров.
        
        Args:
            subscription_id: Идентификатор подписки, полученный при вызове subscribe_to_orderbook.
            
        Returns:
            True, если отписка выполнена успешно, False в противном случае.
            
        Raises:
            VantaAPIError: При ошибке взаимодействия с API биржи.
            VantaWebSocketError: При ошибке WebSocket соединения.
        """
        pass
    
    @abstractmethod
    async def subscribe_to_trades(self, symbol: str, 
                                 callback: Callable[[TradeData], Awaitable[None]]) -> str:
        """
        Подписывается на поток сделок в реальном времени.
        
        Args:
            symbol: Торговый символ (например, "BTCUSDT").
            callback: Асинхронная функция обратного вызова, которая будет вызываться
                     при получении новых данных. Принимает объект TradeData.
            
        Returns:
            Идентификатор подписки, который может быть использован для отписки.
            
        Raises:
            VantaAPIError: При ошибке взаимодействия с API биржи.
            VantaWebSocketError: При ошибке WebSocket соединения.
        """
        pass
    
    @abstractmethod
    async def unsubscribe_from_trades(self, subscription_id: str) -> bool:
        """
        Отписывается от потока сделок.
        
        Args:
            subscription_id: Идентификатор подписки, полученный при вызове subscribe_to_trades.
            
        Returns:
            True, если отписка выполнена успешно, False в противном случае.
            
        Raises:
            VantaAPIError: При ошибке взаимодействия с API биржи.
            VantaWebSocketError: При ошибке WebSocket соединения.
        """
        pass
    
    @abstractmethod
    async def subscribe_to_liquidations(self, symbol: str,
                                       callback: Callable[[LiquidationData], Awaitable[None]]) -> str:
        """
        Подписывается на поток ликвидаций в реальном времени.
        
        Args:
            symbol: Торговый символ (например, "BTCUSDT").
            callback: Асинхронная функция обратного вызова, которая будет вызываться
                     при получении новых данных. Принимает объект LiquidationData.
            
        Returns:
            Идентификатор подписки, который может быть использован для отписки.
            
        Raises:
            VantaAPIError: При ошибке взаимодействия с API биржи.
            VantaWebSocketError: При ошибке WebSocket соединения.
        """
        pass
    
    @abstractmethod
    async def unsubscribe_from_liquidations(self, subscription_id: str) -> bool:
        """
        Отписывается от потока ликвидаций.
        
        Args:
            subscription_id: Идентификатор подписки, полученный при вызове subscribe_to_liquidations.
            
        Returns:
            True, если отписка выполнена успешно, False в противном случае.
            
        Raises:
            VantaAPIError: При ошибке взаимодействия с API биржи.
            VantaWebSocketError: При ошибке WebSocket соединения.
        """
        pass
    
    @abstractmethod
    async def subscribe_to_open_interest(self, symbol: str,
                                        callback: Callable[[OpenInterestData], Awaitable[None]]) -> str:
        """
        Подписывается на обновления открытого интереса в реальном времени.
        
        Args:
            symbol: Торговый символ (например, "BTCUSDT").
            callback: Асинхронная функция обратного вызова, которая будет вызываться
                     при получении новых данных. Принимает объект OpenInterestData.
            
        Returns:
            Идентификатор подписки, который может быть использован для отписки.
            
        Raises:
            VantaAPIError: При ошибке взаимодействия с API биржи.
            VantaWebSocketError: При ошибке WebSocket соединения.
        """
        pass
    
    @abstractmethod
    async def unsubscribe_from_open_interest(self, subscription_id: str) -> bool:
        """
        Отписывается от обновлений открытого интереса.
        
        Args:
            subscription_id: Идентификатор подписки, полученный при вызове subscribe_to_open_interest.
            
        Returns:
            True, если отписка выполнена успешно, False в противном случае.
            
        Raises:
            VantaAPIError: При ошибке взаимодействия с API биржи.
            VantaWebSocketError: При ошибке WebSocket соединения.
        """
        pass


class IMarketDataProvider(IMarketDataRestProvider, IMarketDataStreamProvider):
    """
    Комбинированный интерфейс, объединяющий функциональность REST и WebSocket
    провайдеров рыночных данных.
    
    Предоставляет полный набор методов для получения рыночных данных и подписки
    на их обновления в реальном времени.
    """
    pass 
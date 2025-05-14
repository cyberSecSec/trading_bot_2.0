"""
Сервис для работы с рыночными данными биржи Bybit.

Объединяет функциональность REST и WebSocket провайдеров для
работы с рыночными данными биржи Bybit.
"""

from typing import List, Optional, Dict, Any, Callable, Awaitable

from exchange_api.core.config import ClientConfig
from exchange_api.connection import ConnectionManager, WebSocketManager
from exchange_api.exchanges.bybit.websocket_manager import BybitWebSocketManager
from exchange_api.interfaces.market_data import IMarketDataProvider
from exchange_api.exceptions import VantaAPIError, VantaWebSocketError

from .market_data_rest_service import BybitMarketDataRestProvider
from .market_data_stream_service import BybitMarketDataStreamProvider

from models.market_data import (
    KlineData, OrderBookData, TradeData, LiquidationData, OpenInterestData,
    KlineInterval
)


class BybitMarketDataService(IMarketDataProvider):
    """
    Сервис для работы с рыночными данными биржи Bybit.
    
    Реализует интерфейс IMarketDataProvider, объединяя функциональность
    REST и WebSocket провайдеров для удобного доступа к рыночным данным.
    """
    
    def __init__(
        self, 
        config: ClientConfig, 
        connection_manager: Optional[ConnectionManager] = None,
        websocket_manager: Optional[WebSocketManager] = None
    ):
        """
        Инициализирует сервис с указанной конфигурацией.
        
        Args:
            config: Конфигурация клиента биржи
            connection_manager: Опциональный менеджер соединений для REST API
            websocket_manager: Опциональный менеджер WebSocket соединений
        """
        self.config = config
        self.exchange_name = config.exchange_name
        
        # Создаем REST-провайдер
        self.rest_provider = BybitMarketDataRestProvider(config, connection_manager)
        
        # Создаем WebSocket-провайдер
        self.stream_provider = BybitMarketDataStreamProvider(config, websocket_manager)
    
    async def connect(self) -> None:
        """
        Устанавливает соединение с WebSocket API.
        
        Raises:
            VantaWebSocketError: Если не удалось установить соединение
        """
        await self.stream_provider.connect()
    
    async def close(self) -> None:
        """
        Закрывает соединения и освобождает ресурсы.
        """
        await self.rest_provider.close()
        await self.stream_provider.disconnect()
    
    async def __aenter__(self) -> 'BybitMarketDataService':
        """
        Контекстный менеджер: вход в контекст.
        
        Returns:
            BybitMarketDataService: Этот сервис
        """
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Контекстный менеджер: выход из контекста.
        """
        await self.close()
    
    # Методы REST API для рыночных данных
    
    async def get_klines(self, symbol: str, interval: KlineInterval, 
                         limit: Optional[int] = None, 
                         start_time: Optional[Any] = None, 
                         end_time: Optional[Any] = None) -> List[KlineData]:
        """
        Получает исторические OHLCV данные (свечи) для указанного символа и интервала.
        
        Делегирует вызов REST-провайдеру.
        
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
        return await self.rest_provider.get_klines(symbol, interval, limit, start_time, end_time)
    
    async def get_orderbook(self, symbol: str, depth: Optional[int] = None) -> OrderBookData:
        """
        Получает текущий стакан ордеров для указанного символа.
        
        Делегирует вызов REST-провайдеру.
        
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
        return await self.rest_provider.get_orderbook(symbol, depth)
    
    async def get_recent_trades(self, symbol: str, limit: Optional[int] = None) -> List[TradeData]:
        """
        Получает список недавних сделок для указанного символа.
        
        Делегирует вызов REST-провайдеру.
        
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
        return await self.rest_provider.get_recent_trades(symbol, limit)
    
    async def get_open_interest(self, symbol: str) -> OpenInterestData:
        """
        Получает текущий открытый интерес для указанного символа.
        
        Делегирует вызов REST-провайдеру.
        
        Args:
            symbol: Торговый символ (например, "BTCUSDT").
            
        Returns:
            Объект OpenInterestData, содержащий информацию об открытом интересе.
            
        Raises:
            VantaAPIError: При ошибке взаимодействия с API биржи.
            VantaRateLimitError: При превышении лимита запросов к API биржи.
        """
        return await self.rest_provider.get_open_interest(symbol)
    
    async def get_open_interest_history(self, symbol: str, period: str, 
                                        limit: Optional[int] = None) -> List[OpenInterestData]:
        """
        Получает историю открытого интереса для указанного символа.
        
        Делегирует вызов REST-провайдеру.
        
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
        return await self.rest_provider.get_open_interest_history(symbol, period, limit)
    
    # Методы WebSocket для рыночных данных
    
    async def subscribe_to_klines(self, symbol: str, interval: KlineInterval, 
                                 callback: Callable[[KlineData], Awaitable[None]]) -> str:
        """
        Подписывается на обновления OHLCV данных (свечей) в реальном времени.
        
        Делегирует вызов WebSocket-провайдеру.
        
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
        return await self.stream_provider.subscribe_to_klines(symbol, interval, callback)
    
    async def unsubscribe_from_klines(self, subscription_id: str) -> bool:
        """
        Отписывается от обновлений OHLCV данных (свечей).
        
        Делегирует вызов WebSocket-провайдеру.
        
        Args:
            subscription_id: Идентификатор подписки, полученный при вызове subscribe_to_klines.
            
        Returns:
            True, если отписка выполнена успешно, False в противном случае.
            
        Raises:
            VantaAPIError: При ошибке взаимодействия с API биржи.
            VantaWebSocketError: При ошибке WebSocket соединения.
        """
        return await self.stream_provider.unsubscribe_from_klines(subscription_id)
    
    async def subscribe_to_orderbook(self, symbol: str, 
                                    callback: Callable[[OrderBookData], Awaitable[None]],
                                    depth: Optional[int] = None) -> str:
        """
        Подписывается на обновления стакана ордеров в реальном времени.
        
        Делегирует вызов WebSocket-провайдеру.
        
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
        return await self.stream_provider.subscribe_to_orderbook(symbol, callback, depth)
    
    async def unsubscribe_from_orderbook(self, subscription_id: str) -> bool:
        """
        Отписывается от обновлений стакана ордеров.
        
        Делегирует вызов WebSocket-провайдеру.
        
        Args:
            subscription_id: Идентификатор подписки, полученный при вызове subscribe_to_orderbook.
            
        Returns:
            True, если отписка выполнена успешно, False в противном случае.
            
        Raises:
            VantaAPIError: При ошибке взаимодействия с API биржи.
            VantaWebSocketError: При ошибке WebSocket соединения.
        """
        return await self.stream_provider.unsubscribe_from_orderbook(subscription_id)
    
    async def subscribe_to_trades(self, symbol: str, 
                                 callback: Callable[[TradeData], Awaitable[None]]) -> str:
        """
        Подписывается на поток сделок в реальном времени.
        
        Делегирует вызов WebSocket-провайдеру.
        
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
        return await self.stream_provider.subscribe_to_trades(symbol, callback)
    
    async def unsubscribe_from_trades(self, subscription_id: str) -> bool:
        """
        Отписывается от потока сделок.
        
        Делегирует вызов WebSocket-провайдеру.
        
        Args:
            subscription_id: Идентификатор подписки, полученный при вызове subscribe_to_trades.
            
        Returns:
            True, если отписка выполнена успешно, False в противном случае.
            
        Raises:
            VantaAPIError: При ошибке взаимодействия с API биржи.
            VantaWebSocketError: При ошибке WebSocket соединения.
        """
        return await self.stream_provider.unsubscribe_from_trades(subscription_id)
    
    async def subscribe_to_liquidations(self, symbol: str,
                                       callback: Callable[[LiquidationData], Awaitable[None]]) -> str:
        """
        Подписывается на поток ликвидаций в реальном времени.
        
        Делегирует вызов WebSocket-провайдеру.
        
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
        return await self.stream_provider.subscribe_to_liquidations(symbol, callback)
    
    async def unsubscribe_from_liquidations(self, subscription_id: str) -> bool:
        """
        Отписывается от потока ликвидаций.
        
        Делегирует вызов WebSocket-провайдеру.
        
        Args:
            subscription_id: Идентификатор подписки, полученный при вызове subscribe_to_liquidations.
            
        Returns:
            True, если отписка выполнена успешно, False в противном случае.
            
        Raises:
            VantaAPIError: При ошибке взаимодействия с API биржи.
            VantaWebSocketError: При ошибке WebSocket соединения.
        """
        return await self.stream_provider.unsubscribe_from_liquidations(subscription_id)
    
    async def subscribe_to_open_interest(self, symbol: str,
                                        callback: Callable[[OpenInterestData], Awaitable[None]]) -> str:
        """
        Подписывается на обновления открытого интереса в реальном времени.
        
        Делегирует вызов WebSocket-провайдеру.
        
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
        return await self.stream_provider.subscribe_to_open_interest(symbol, callback)
    
    async def unsubscribe_from_open_interest(self, subscription_id: str) -> bool:
        """
        Отписывается от обновлений открытого интереса.
        
        Делегирует вызов WebSocket-провайдеру.
        
        Args:
            subscription_id: Идентификатор подписки, полученный при вызове subscribe_to_open_interest.
            
        Returns:
            True, если отписка выполнена успешно, False в противном случае.
            
        Raises:
            VantaAPIError: При ошибке взаимодействия с API биржи.
            VantaWebSocketError: При ошибке WebSocket соединения.
        """
        return await self.stream_provider.unsubscribe_from_open_interest(subscription_id) 
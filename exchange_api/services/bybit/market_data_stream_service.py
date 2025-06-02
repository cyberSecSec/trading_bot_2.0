"""
WebSocket-провайдер для получения рыночных данных с биржи Bybit.

Реализует интерфейс IMarketDataStreamProvider для получения
различных типов рыночных данных через WebSocket API Bybit.
"""

import asyncio
import uuid
from typing import Dict, Any, Set, Callable, Awaitable, Optional, List
from decimal import Decimal

from exchange_api.core.config import ClientConfig
from exchange_api.connection import WebSocketManager
from exchange_api.exchanges.bybit.websocket_manager import BybitWebSocketManager
from exchange_api.exchanges.bybit.endpoints import PublicWebSocketChannels, format_public_channel
from exchange_api.interfaces.market_data import IMarketDataStreamProvider
from exchange_api.exceptions import WebSocketError, VantaAPIError, VantaWebSocketError
from exchange_api.utils.logger import Logger

from models.market_data import (
    KlineData, OrderBookData, TradeData, LiquidationData, OpenInterestData,
    KlineInterval
)

# Получаем логгер
logger = Logger.get_logger()


class BybitMarketDataStreamProvider(IMarketDataStreamProvider):
    """
    Реализация интерфейса IMarketDataStreamProvider для биржи Bybit.
    
    Предоставляет методы для подписки на потоковые рыночные данные через WebSocket API Bybit.
    """
    
    def __init__(self, config: ClientConfig, websocket_manager: Optional[WebSocketManager] = None):
        """
        Инициализирует провайдер данных с указанной конфигурацией.
        
        Args:
            config: Конфигурация клиента биржи
            websocket_manager: Опциональный менеджер WebSocket (если не указан, будет создан новый)
        """
        self.config = config
        self.exchange_name = config.exchange_name
        
        # Создаем или используем переданный WebSocket менеджер
        self.ws_manager = websocket_manager or BybitWebSocketManager(
            config=config,
            on_message=self._on_message
        )
        
        # Словарь для хранения подписок: {subscription_id: (channel, callback)}
        self.subscriptions: Dict[str, Dict[str, Any]] = {}
        
        # Флаг, указывающий, было ли выполнено подключение
        self._is_connected = False
    
    async def connect(self) -> None:
        """
        Устанавливает соединение с WebSocket API.
        
        Raises:
            VantaWebSocketError: Если не удалось установить соединение
        """
        if not self._is_connected:
            try:
                await self.ws_manager.connect()
                self._is_connected = True
            except Exception as e:
                raise VantaWebSocketError(
                    message=f"Ошибка при подключении к WebSocket API: {str(e)}",
                    exchange=self.exchange_name
                ) from e
    
    async def disconnect(self) -> None:
        """
        Закрывает WebSocket соединение и освобождает ресурсы.
        """
        if self._is_connected:
            await self.ws_manager.disconnect()
            self._is_connected = False
    
    async def __aenter__(self) -> 'BybitMarketDataStreamProvider':
        """
        Контекстный менеджер: вход в контекст.
        
        Returns:
            BybitMarketDataStreamProvider: Этот провайдер данных
        """
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Контекстный менеджер: выход из контекста.
        """
        await self.disconnect()
    
    def _map_interval_to_bybit(self, interval: KlineInterval) -> str:
        """
        Преобразует интервал из KlineInterval в формат Bybit API.
        
        Args:
            interval: Интервал свечей из KlineInterval
            
        Returns:
            str: Интервал в формате Bybit API
        """
        # В Bybit WebSocket API интервалы имеют тот же формат, что и в REST API
        return interval
    
    async def _on_message(self, message: Dict[str, Any]) -> None:
        """
        Обрабатывает входящие сообщения от WebSocket API.
        
        Args:
            message: Полученное сообщение
        """
        try:
            # Проверяем, имеет ли сообщение тему (topic)
            if 'topic' not in message:
                return
            
            topic = message['topic']
            
            # Ищем подписки, соответствующие теме
            for subscription_id, subscription in self.subscriptions.items():
                if subscription['channel'] == topic:
                    # Извлекаем параметры и колбэк из подписки
                    callback = subscription['callback']
                    symbol = subscription['symbol']
                    
                    # В зависимости от типа канала преобразуем данные
                    if topic.startswith('kline.'):
                        # Извлекаем интервал из темы
                        interval = topic.split('.')[1]
                        
                        # Преобразуем данные в KlineData
                        kline_data = KlineData.from_bybit_ws(message, symbol, interval)
                        
                        # Вызываем колбэк с преобразованными данными
                        await callback(kline_data)
                    
                    # Обработка сообщений стакана ордеров
                    elif topic.startswith('orderbook.'):
                        # Если у подписки есть процессор
                        if 'processor' in subscription:
                            processor = subscription['processor']
                            # Преобразуем сообщение в нужный формат и передаем процессору
                            await processor.process_message(message, callback)
                        else:
                            # Для обратной совместимости: прямая обработка без процессора
                            orderbook_data = OrderBookData.from_bybit_ws(message, symbol)
                            await callback(orderbook_data)
                    
                    # Обработка сообщений о сделках
                    elif topic.startswith('publicTrade.'):
                        # Извлекаем данные о сделках из сообщения
                        trades_data = message.get('data', [])
                        
                        # Проверяем наличие валидатора последовательности в подписке
                        sequence_validator = subscription.get('sequence_validator')
                        
                        # Обрабатываем каждую сделку
                        for trade_data in trades_data:
                            # Преобразуем данные в TradeData
                            trade = TradeData.from_bybit_ws(trade_data, symbol)
                            
                            # Если есть валидатор, проверяем сделку
                            if sequence_validator:
                                is_new = sequence_validator.validate_trade(trade)
                                if is_new:
                                    # Вызываем колбэк только для новых сделок
                                    await callback(trade)
                            else:
                                # Иначе просто передаем сделку в колбэк
                                await callback(trade)
                    
                    # Обработка сообщений о ликвидациях
                    elif topic.startswith('liquidation.'):
                        # Если у подписки есть обработчик ликвидаций
                        if 'liquidation_handler' in subscription:
                            liquidation_handler = subscription['liquidation_handler']
                            # Передаем сообщение обработчику
                            await liquidation_handler.handle_message(message)
                        else:
                            # Для обратной совместимости: прямая обработка без обработчика
                            liquidation_data = message.get('data', [])
                            if isinstance(liquidation_data, list) and liquidation_data:
                                for liquidation_item in liquidation_data:
                                    liquidation = LiquidationData.from_bybit_ws(liquidation_item, symbol)
                                    await callback(liquidation)
                    
                    # Аналогично для других типов каналов...
        
        except Exception as e:
            logger.error(f"Ошибка при обработке WebSocket сообщения: {str(e)}")
    
    async def _subscribe_to_channel(self, channel: str, callback: Callable, 
                                   symbol: str, **kwargs) -> str:
        """
        Подписывается на указанный канал данных.
        
        Args:
            channel: Канал для подписки
            callback: Функция обратного вызова
            symbol: Торговый символ
            **kwargs: Дополнительные параметры для хранения с подпиской
            
        Returns:
            str: Идентификатор подписки
            
        Raises:
            VantaWebSocketError: Если не удалось подписаться на канал
        """
        try:
            # Убедимся, что соединение установлено
            if not self._is_connected:
                await self.connect()
            
            # Генерируем уникальный идентификатор подписки
            subscription_id = str(uuid.uuid4())
            
            # Сохраняем информацию о подписке
            subscription_info = {
                'channel': channel,
                'callback': callback,
                'symbol': symbol,
                **kwargs
            }
            self.subscriptions[subscription_id] = subscription_info
            
            # Подписываемся на канал
            await self.ws_manager.subscribe(channel)
            
            return subscription_id
            
        except Exception as e:
            # Если произошла ошибка, удаляем информацию о подписке
            if 'subscription_id' in locals():
                self.subscriptions.pop(subscription_id, None)
            
            # Преобразуем исключение
            raise VantaWebSocketError(
                message=f"Ошибка при подписке на канал {channel}: {str(e)}",
                exchange=self.exchange_name,
                channel=channel
            ) from e
    
    async def _unsubscribe_from_channel(self, subscription_id: str) -> bool:
        """
        Отписывается от канала данных.
        
        Args:
            subscription_id: Идентификатор подписки
            
        Returns:
            bool: True, если отписка выполнена успешно, False в противном случае
            
        Raises:
            VantaWebSocketError: Если произошла ошибка при отписке
        """
        try:
            # Проверяем наличие подписки
            if subscription_id not in self.subscriptions:
                return False
            
            # Получаем информацию о подписке
            subscription = self.subscriptions[subscription_id]
            channel = subscription['channel']
            
            # Отписываемся от канала
            await self.ws_manager.unsubscribe(channel)
            
            # Удаляем информацию о подписке
            del self.subscriptions[subscription_id]
            
            return True
            
        except Exception as e:
            # Преобразуем исключение
            raise VantaWebSocketError(
                message=f"Ошибка при отписке от канала: {str(e)}",
                exchange=self.exchange_name,
                subscription_id=subscription_id
            ) from e
    
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
        # Преобразуем интервал в формат Bybit
        bybit_interval = self._map_interval_to_bybit(interval)
        
        # Формируем имя канала
        channel = format_public_channel(
            PublicWebSocketChannels.KLINE,
            interval=bybit_interval,
            symbol=symbol
        )
        
        # Подписываемся на канал
        return await self._subscribe_to_channel(
            channel=channel,
            callback=callback,
            symbol=symbol,
            interval=interval
        )
    
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
        return await self._unsubscribe_from_channel(subscription_id)
    
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
        try:
            # Проверяем и устанавливаем глубину стакана
            valid_depths = {1, 25, 50, 100, 200, 500}
            
            # Если глубина не указана, используем значение по умолчанию
            if depth is None:
                depth = 25
            
            # Если указана неподдерживаемая глубина, выбираем ближайшую
            if depth not in valid_depths:
                nearest_depth = min(valid_depths, key=lambda x: abs(x - depth))
                logger.warning(
                    f"Глубина стакана {depth} не поддерживается. Используется ближайшее значение {nearest_depth}."
                )
                depth = nearest_depth
            
            # Формируем имя канала
            channel = format_public_channel(
                PublicWebSocketChannels.ORDERBOOK,
                depth=str(depth),
                symbol=symbol
            )
            
            # Создаем процессор для обработки инкрементальных обновлений
            from exchange_api.services.bybit.orderbook_delta_processor import OrderBookDeltaProcessor
            processor = OrderBookDeltaProcessor(symbol)
            
            # Подписываемся на канал с процессором для обработки обновлений
            return await self._subscribe_to_channel(
                channel=channel,
                callback=callback,
                symbol=symbol,
                depth=depth,
                processor=processor
            )
            
        except Exception as e:
            raise VantaWebSocketError(
                message=f"Ошибка при подписке на стакан ордеров: {str(e)}",
                exchange=self.exchange_name,
                channel=f"orderbook.{depth}.{symbol}"
            ) from e
    
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
        return await self._unsubscribe_from_channel(subscription_id)
    
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
        try:
            # Формируем имя канала
            channel = format_public_channel(
                PublicWebSocketChannels.TRADE,
                symbol=symbol
            )
            
            # Создаем валидатор последовательности сделок
            from exchange_api.services.bybit.trade_sequence_validator import TradeSequenceValidator
            sequence_validator = TradeSequenceValidator(symbol)
            
            # Подписываемся на канал
            return await self._subscribe_to_channel(
                channel=channel,
                callback=callback,
                symbol=symbol,
                sequence_validator=sequence_validator
            )
            
        except Exception as e:
            # Преобразуем исключение
            raise VantaWebSocketError(
                message=f"Ошибка при подписке на поток сделок: {str(e)}",
                exchange=self.exchange_name,
                channel=f"publicTrade.{symbol}"
            ) from e
    
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
        return await self._unsubscribe_from_channel(subscription_id)
    
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
        try:
            # Формируем имя канала
            channel = format_public_channel(
                PublicWebSocketChannels.LIQUIDATION,
                symbol=symbol
            )
            
            # Создаем обработчик сообщений о ликвидациях
            from exchange_api.exchanges.bybit.handlers.liquidation_handler import LiquidationMessageHandler
            liquidation_handler = LiquidationMessageHandler(callback)
            
            # Создаем анализатор ликвидаций
            from exchange_api.services.bybit.liquidation_analyzer import LiquidationAnalyzer
            liquidation_analyzer = LiquidationAnalyzer(
                large_liquidation_threshold=Decimal('5.0'),  # Крупной считается ликвидация от 5 BTC
                cascade_time_window_seconds=60,              # Окно 60 секунд для определения каскада
                cascade_min_volume=Decimal('20.0')           # Каскад от 20 BTC общего объема
            )
            
            # Оборачиваем callback для добавления аналитики
            async def enhanced_callback(liquidation: LiquidationData) -> None:
                # Регистрируем ликвидацию в анализаторе
                liquidation_analyzer.register_liquidation(liquidation)
                
                # Перенаправляем в оригинальный callback
                await callback(liquidation)
                
                # Периодически анализируем накопленные данные
                if liquidation_analyzer.should_analyze():
                    recent_liquidations = liquidation_analyzer.get_recent_liquidations(
                        symbol=symbol,
                        time_window_seconds=300  # Анализируем данные за последние 5 минут
                    )
                    
                    if recent_liquidations:
                        liquidation_analyzer.analyze_liquidations(recent_liquidations)
            
            # Подписываемся на канал
            return await self._subscribe_to_channel(
                channel=channel,
                callback=enhanced_callback,
                symbol=symbol,
                liquidation_handler=liquidation_handler,
                liquidation_analyzer=liquidation_analyzer
            )
            
        except Exception as e:
            # Преобразуем исключение
            raise VantaWebSocketError(
                message=f"Ошибка при подписке на поток ликвидаций: {str(e)}",
                exchange=self.exchange_name,
                channel=f"liquidation.{symbol}"
            ) from e
    
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
        return await self._unsubscribe_from_channel(subscription_id)
    
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
        # Заглушка - нужна полная реализация
        raise NotImplementedError("Метод subscribe_to_open_interest пока не реализован")
    
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
        return await self._unsubscribe_from_channel(subscription_id) 
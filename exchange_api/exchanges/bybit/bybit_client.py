"""
Модуль базового клиента для работы с Bybit API.

Предоставляет класс BybitClient, который объединяет функциональность для
работы с REST API и WebSocket API Bybit.
"""
import json
import time
import hmac
import hashlib
from typing import Dict, Any, Optional, Union, List, Callable, Awaitable
from decimal import Decimal

from exchange_api.connection import ReconnectionHandler
from exchange_api.exchanges.bybit.config import BybitClientConfig
from exchange_api.exchanges.bybit.connection_manager import BybitConnectionManager
from exchange_api.exchanges.bybit.websocket_manager import BybitWebSocketManager
from exchange_api.exchanges.bybit.endpoints import (
    MarketDataEndpoints, TradeEndpoints, PositionEndpoints, 
    AccountEndpoints, PublicWebSocketChannels
)
from exchange_api.exchanges.bybit.websocket_handlers import WebSocketMessageRouter
from exchange_api.utils.logger import Logger
from exchange_api.exceptions import (
    ConnectionError, AuthenticationError, ValidationError, 
    ExchangeError, WebSocketError, UnexpectedError
)


# Получаем логгер
logger = Logger.get_logger()


class BybitClient:
    """
    Базовый клиент для работы с Bybit API.
    
    Объединяет функциональность для работы с REST API и WebSocket API Bybit,
    предоставляя удобные методы для получения рыночных данных и выполнения
    торговых операций.
    """
    
    def __init__(self, config: BybitClientConfig):
        """
        Инициализирует клиент Bybit.
        
        Args:
            config: Конфигурация клиента Bybit
        """
        self.config = config
        
        # Создаем менеджер HTTP соединений
        self.connection_manager = BybitConnectionManager(config)
        
        # Словарь для хранения WebSocket менеджеров
        self._ws_managers: Dict[str, BybitWebSocketManager] = {}
        
        # Словарь для хранения обработчиков сообщений WebSocket
        self._ws_handlers: Dict[str, Dict[str, Callable[[Dict[str, Any]], None]]] = {}
        
        # Инициализация логгера
        self.logger = logger
        Logger.set_exchange_context(config.exchange_name)
        
        self.logger.info(f"Инициализирован клиент Bybit для {config.bybit_environment.value}")
    
    async def initialize(self) -> None:
        """
        Инициализирует клиент, устанавливая соединения.
        
        Должен быть вызван перед использованием клиента.
        """
        # Проверяем соединение с API
        try:
            await self.connection_manager.check_connection()
            self.logger.info("Соединение с Bybit API успешно установлено")
        except Exception as e:
            self.logger.error(f"Ошибка при установке соединения с Bybit API: {str(e)}")
            raise
    
    async def shutdown(self) -> None:
        """
        Завершает работу клиента, освобождая все ресурсы.
        
        Должен быть вызван при завершении работы с клиентом.
        """
        # Закрываем все WebSocket соединения
        for ws_key, ws_manager in self._ws_managers.items():
            try:
                await ws_manager.disconnect()
                self.logger.debug(f"WebSocket соединение {ws_key} закрыто")
            except Exception as e:
                self.logger.warning(f"Ошибка при закрытии WebSocket соединения {ws_key}: {str(e)}")
        
        # Очищаем словари WebSocket менеджеров и обработчиков
        self._ws_managers.clear()
        self._ws_handlers.clear()
        
        # Закрываем HTTP соединение
        try:
            await self.connection_manager.close()
            self.logger.debug("HTTP соединение закрыто")
        except Exception as e:
            self.logger.warning(f"Ошибка при закрытии HTTP соединения: {str(e)}")
        
        self.logger.info("Клиент Bybit успешно завершил работу")
    
    async def __aenter__(self) -> 'BybitClient':
        """
        Контекстный менеджер: вход в контекст.
        
        Returns:
            BybitClient: Этот клиент Bybit
        """
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Контекстный менеджер: выход из контекста.
        """
        await self.shutdown()
    
    # =====================================================================
    # Методы для работы с рыночными данными через REST API
    # =====================================================================
    
    @ReconnectionHandler.with_backoff(max_tries=3)
    async def get_server_time(self) -> int:
        """
        Получает текущее время сервера Bybit.
        
        Returns:
            int: Текущее время сервера в миллисекундах
        """
        return await self.connection_manager.get_server_time()
    
    @ReconnectionHandler.with_backoff(max_tries=3)
    async def get_klines(
        self,
        symbol: str,
        interval: str,
        limit: int = 200,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        category: str = "spot"
    ) -> List[Dict[str, Any]]:
        """
        Получает OHLCV данные (свечи) для указанного символа и интервала.
        
        Args:
            symbol: Символ инструмента (например, BTCUSDT)
            interval: Интервал свечей (например, 1, 5, 15, 30, 60, D, W, M)
            limit: Максимальное количество свечей (по умолчанию 200, макс. 1000)
            start_time: Начальное время в миллисекундах
            end_time: Конечное время в миллисекундах
            category: Категория инструмента (spot, linear, inverse, option)
            
        Returns:
            List[Dict[str, Any]]: Список OHLCV данных
        """
        # Проверяем, что категория поддерживается
        if category not in self.config.categories:
            raise ValidationError(
                message=f"Категория {category} не поддерживается в текущей конфигурации",
                exchange=self.config.exchange_name
            )
        
        # Подготавливаем параметры запроса
        params = {
            "category": category,
            "symbol": symbol,
            "interval": interval,
            "limit": limit
        }
        
        # Добавляем опциональные параметры, если они указаны
        if start_time is not None:
            params["start"] = start_time
        if end_time is not None:
            params["end"] = end_time
        
        # Выполняем запрос к API
        response = await self.connection_manager.get(
            MarketDataEndpoints.KLINE,
            params=params
        )
        
        # Проверяем, что ответ успешный
        if response.get("retCode") != 0:
            error_msg = response.get("retMsg", "Unknown error")
            raise ExchangeError(
                message=f"Ошибка при получении OHLCV данных: {error_msg}",
                exchange=self.config.exchange_name
            )
        
        # Извлекаем и преобразуем данные
        klines_data = response.get("result", {}).get("list", [])
        
        # Преобразуем данные в более удобный формат
        result = []
        for kline in klines_data:
            # Данные Bybit API возвращаются в формате [timestamp, open, high, low, close, volume, turnover]
            if len(kline) >= 7:
                result.append({
                    "timestamp": int(kline[0]),
                    "open": Decimal(str(kline[1])),
                    "high": Decimal(str(kline[2])),
                    "low": Decimal(str(kline[3])),
                    "close": Decimal(str(kline[4])),
                    "volume": Decimal(str(kline[5])),
                    "turnover": Decimal(str(kline[6]))
                })
        
        return result
    
    @ReconnectionHandler.with_backoff(max_tries=3)
    async def get_orderbook(
        self,
        symbol: str,
        limit: int = 25,
        category: str = "spot"
    ) -> Dict[str, Any]:
        """
        Получает стакан ордеров для указанного символа.
        
        Args:
            symbol: Символ инструмента (например, BTCUSDT)
            limit: Количество уровней (1-200 для spot/linear/inverse, 1-50 для option)
            category: Категория инструмента (spot, linear, inverse, option)
            
        Returns:
            Dict[str, Any]: Стакан ордеров с полями bids, asks, timestamp
        """
        # Проверяем, что категория поддерживается
        if category not in self.config.categories:
            raise ValidationError(
                message=f"Категория {category} не поддерживается в текущей конфигурации",
                exchange=self.config.exchange_name
            )
        
        # Подготавливаем параметры запроса
        params = {
            "category": category,
            "symbol": symbol,
            "limit": limit
        }
        
        # Выполняем запрос к API
        response = await self.connection_manager.get(
            MarketDataEndpoints.ORDERBOOK,
            params=params
        )
        
        # Проверяем, что ответ успешный
        if response.get("retCode") != 0:
            error_msg = response.get("retMsg", "Unknown error")
            raise ExchangeError(
                message=f"Ошибка при получении стакана ордеров: {error_msg}",
                exchange=self.config.exchange_name
            )
        
        # Извлекаем данные стакана
        orderbook_data = response.get("result", {})
        
        # Преобразуем данные в более удобный формат
        result = {
            "timestamp": int(orderbook_data.get("ts", 0)),
            "symbol": symbol,
            "bids": [],
            "asks": []
        }
        
        # Обрабатываем bids (предложения на покупку)
        for bid in orderbook_data.get("b", []):
            if len(bid) >= 2:
                result["bids"].append([
                    Decimal(str(bid[0])),  # цена
                    Decimal(str(bid[1]))   # количество
                ])
        
        # Обрабатываем asks (предложения на продажу)
        for ask in orderbook_data.get("a", []):
            if len(ask) >= 2:
                result["asks"].append([
                    Decimal(str(ask[0])),  # цена
                    Decimal(str(ask[1]))   # количество
                ])
        
        return result
    
    @ReconnectionHandler.with_backoff(max_tries=3)
    async def get_recent_trades(
        self,
        symbol: str,
        limit: int = 50,
        category: str = "spot"
    ) -> List[Dict[str, Any]]:
        """
        Получает последние сделки для указанного символа.
        
        Args:
            symbol: Символ инструмента (например, BTCUSDT)
            limit: Количество сделок (по умолчанию 50, макс. 1000)
            category: Категория инструмента (spot, linear, inverse, option)
            
        Returns:
            List[Dict[str, Any]]: Список последних сделок
        """
        # Проверяем, что категория поддерживается
        if category not in self.config.categories:
            raise ValidationError(
                message=f"Категория {category} не поддерживается в текущей конфигурации",
                exchange=self.config.exchange_name
            )
        
        # Подготавливаем параметры запроса
        params = {
            "category": category,
            "symbol": symbol,
            "limit": limit
        }
        
        # Выполняем запрос к API
        response = await self.connection_manager.get(
            MarketDataEndpoints.RECENT_TRADES,
            params=params
        )
        
        # Проверяем, что ответ успешный
        if response.get("retCode") != 0:
            error_msg = response.get("retMsg", "Unknown error")
            raise ExchangeError(
                message=f"Ошибка при получении последних сделок: {error_msg}",
                exchange=self.config.exchange_name
            )
        
        # Извлекаем данные сделок
        trades_data = response.get("result", {}).get("list", [])
        
        # Преобразуем данные в более удобный формат
        result = []
        for trade in trades_data:
            result.append({
                "id": trade.get("i", ""),
                "symbol": symbol,
                "price": Decimal(str(trade.get("p", "0"))),
                "quantity": Decimal(str(trade.get("v", "0"))),
                "side": trade.get("S", ""),  # Buy или Sell
                "timestamp": int(trade.get("T", 0)),
                "is_block_trade": trade.get("BT", False)
            })
        
        return result 
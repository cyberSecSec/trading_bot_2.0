"""
REST-провайдер для получения рыночных данных с биржи Bybit.

Реализует интерфейс IMarketDataRestProvider для получения
различных типов рыночных данных через REST API Bybit.
"""

import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime

from exchange_api.core.config import ClientConfig
from exchange_api.connection import ConnectionManager
from exchange_api.exchanges.bybit.endpoints import MarketDataEndpoints
from exchange_api.interfaces.market_data import IMarketDataRestProvider
from exchange_api.exceptions import ValidationError, VantaAPIError, VantaRateLimitError

from models.market_data import (
    KlineData, OrderBookData, TradeData, OpenInterestData,
    KlineInterval
)


class BybitMarketDataRestProvider(IMarketDataRestProvider):
    """
    Реализация интерфейса IMarketDataRestProvider для биржи Bybit.
    
    Предоставляет методы для получения рыночных данных через REST API Bybit.
    """
    
    def __init__(self, config: ClientConfig, connection_manager: Optional[ConnectionManager] = None):
        """
        Инициализирует провайдер данных с указанной конфигурацией.
        
        Args:
            config: Конфигурация клиента биржи
            connection_manager: Опциональный менеджер соединений (если не указан, будет создан новый)
        """
        self.config = config
        self.connection = connection_manager or ConnectionManager(config)
        self.exchange_name = config.exchange_name
        
        # Маппинг категорий инструментов (если указаны в конфигурации)
        self.categories = getattr(config, 'categories', {'spot', 'linear'})
    
    async def close(self) -> None:
        """
        Закрывает соединения и освобождает ресурсы.
        """
        if self.connection:
            await self.connection.close()
    
    async def __aenter__(self) -> 'BybitMarketDataRestProvider':
        """
        Контекстный менеджер: вход в контекст.
        
        Returns:
            BybitMarketDataRestProvider: Этот провайдер данных
        """
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Контекстный менеджер: выход из контекста.
        """
        await self.close()
    
    def _get_category_for_symbol(self, symbol: str) -> str:
        """
        Определяет категорию инструмента по его символу.
        
        В Bybit API v5 требуется указывать категорию инструмента.
        Эта функция пытается определить категорию на основе символа.
        
        Args:
            symbol: Торговый символ (например, "BTCUSDT")
            
        Returns:
            str: Категория инструмента ('spot', 'linear', 'inverse' и т.д.)
        """
        # По умолчанию используем первую доступную категорию
        default_category = next(iter(self.categories)) if self.categories else 'spot'
        
        # Простая эвристика для определения категории
        if symbol.endswith(('USDT', 'USDC')):
            return 'linear' if 'linear' in self.categories else default_category
        elif symbol.endswith(('USD')):
            return 'inverse' if 'inverse' in self.categories else default_category
        else:
            return 'spot' if 'spot' in self.categories else default_category
    
    def _map_interval_to_bybit(self, interval: KlineInterval) -> str:
        """
        Преобразует интервал из KlineInterval в формат Bybit API.
        
        Args:
            interval: Интервал свечей из KlineInterval
            
        Returns:
            str: Интервал в формате Bybit API
            
        Raises:
            ValidationError: Если интервал не поддерживается Bybit
        """
        return interval
    
    def _convert_datetime_to_timestamp(self, dt: Optional[datetime]) -> Optional[int]:
        """
        Преобразует datetime в миллисекунды для API Bybit.
        
        Args:
            dt: Объект datetime или None
            
        Returns:
            int: Количество миллисекунд с начала эпохи или None
        """
        if dt is None:
            return None
        return int(dt.timestamp() * 1000)
    
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
        try:
            # Определяем категорию инструмента
            category = self._get_category_for_symbol(symbol)
            
            # Формируем параметры запроса
            params = {
                'category': category,
                'symbol': symbol,
                'interval': self._map_interval_to_bybit(interval)
            }
            
            # Добавляем опциональные параметры, если они указаны
            if limit is not None:
                params['limit'] = limit
            
            if start_time is not None:
                params['start'] = self._convert_datetime_to_timestamp(start_time)
            
            if end_time is not None:
                params['end'] = self._convert_datetime_to_timestamp(end_time)
            
            # Выполняем запрос к API
            response = await self.connection.get(MarketDataEndpoints.KLINE, params)
            
            # Проверяем успешность запроса
            if response.get('retCode') != 0:
                raise VantaAPIError(
                    message=f"Ошибка при получении OHLCV данных: {response.get('retMsg', 'Unknown error')}",
                    code=response.get('retCode'),
                    exchange=self.exchange_name
                )
            
            # Извлекаем данные из ответа
            klines_data = response.get('result', {}).get('list', [])
            
            # Bybit API возвращает данные в обратном порядке (от новых к старым),
            # поэтому переворачиваем список для соответствия контракту (от старых к новым)
            klines_data.reverse()
            
            # Преобразуем данные в объекты KlineData
            klines = []
            for kline_item in klines_data:
                kline = KlineData.from_bybit_rest(kline_item, symbol, interval)
                klines.append(kline)
            
            return klines
            
        except VantaAPIError:
            # Пробрасываем ошибки API без изменений
            raise
        except Exception as e:
            # Преобразуем другие исключения в VantaAPIError
            raise VantaAPIError(
                message=f"Ошибка при получении OHLCV данных: {str(e)}",
                exchange=self.exchange_name,
                original_exception=e
            ) from e
    
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
        try:
            # Проверяем и устанавливаем глубину стакана
            valid_depths = {1, 25, 50, 100, 200, 500}
            if depth is not None and depth not in valid_depths:
                # Находим ближайшее поддерживаемое значение глубины
                nearest_depth = min(valid_depths, key=lambda x: abs(x - depth))
                self.logger.warning(
                    f"Глубина стакана {depth} не поддерживается. Используется ближайшее значение {nearest_depth}."
                )
                depth = nearest_depth
            
            # Устанавливаем глубину по умолчанию, если не указана
            if depth is None:
                depth = 25
            
            # Определяем категорию инструмента
            category = self._get_category_for_symbol(symbol)
            
            # Проверяем допустимые значения глубины для разных категорий
            if category in ["option"] and depth > 50:
                depth = 50
                self.logger.warning(
                    f"Для категории '{category}' максимальная глубина стакана: 50. Значение было скорректировано."
                )
            
            # Формируем параметры запроса
            params = {
                'category': category,
                'symbol': symbol,
                'limit': depth
            }
            
            # Выполняем запрос к API
            response = await self.connection.get(MarketDataEndpoints.ORDERBOOK, params)
            
            # Проверяем успешность запроса
            if response.get('retCode') != 0:
                raise VantaAPIError(
                    message=f"Ошибка при получении стакана ордеров: {response.get('retMsg', 'Unknown error')}",
                    code=response.get('retCode'),
                    exchange=self.exchange_name
                )
            
            # Извлекаем данные из ответа
            orderbook_data = response.get('result', {})
            
            # Преобразуем данные в формат, который ожидает OrderBookData.from_bybit_rest
            formatted_data = {
                "timestamp": orderbook_data.get("ts", 0),
                "symbol": symbol,
                "bids": orderbook_data.get("b", []),
                "asks": orderbook_data.get("a", [])
            }
            
            # Преобразуем данные в объект OrderBookData
            return OrderBookData.from_bybit_rest(formatted_data, symbol)
            
        except VantaAPIError:
            # Пробрасываем ошибки API без изменений
            raise
        except Exception as e:
            # Преобразуем другие исключения в VantaAPIError
            raise VantaAPIError(
                message=f"Ошибка при получении стакана ордеров: {str(e)}",
                exchange=self.exchange_name,
                original_exception=e
            ) from e
    
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
        # Заглушка - нужна полная реализация
        raise NotImplementedError("Метод get_recent_trades пока не реализован")
    
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
        # Заглушка - нужна полная реализация
        raise NotImplementedError("Метод get_open_interest пока не реализован")
    
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
        # Заглушка - нужна полная реализация
        raise NotImplementedError("Метод get_open_interest_history пока не реализован") 
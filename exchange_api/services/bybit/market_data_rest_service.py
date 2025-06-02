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
        try:
            # Определяем категорию инструмента
            category = self._get_category_for_symbol(symbol)
            
            # Формируем параметры запроса
            params = {
                'category': category,
                'symbol': symbol
            }
            
            # Добавляем лимит, если указан
            # Bybit API поддерживает лимит от 1 до 1000, по умолчанию 500
            if limit is not None:
                # Ограничиваем значение лимита в соответствии с API
                params['limit'] = max(1, min(1000, limit))
            
            # Выполняем запрос к API
            response = await self.connection.get(MarketDataEndpoints.RECENT_TRADES, params)
            
            # Проверяем успешность запроса
            if response.get('retCode') != 0:
                raise VantaAPIError(
                    message=f"Ошибка при получении данных о сделках: {response.get('retMsg', 'Unknown error')}",
                    code=response.get('retCode'),
                    exchange=self.exchange_name
                )
            
            # Извлекаем данные из ответа
            trades_data = response.get('result', {}).get('list', [])
            
            # Преобразуем данные в объекты TradeData
            trades = []
            for trade_item in trades_data:
                trade = TradeData.from_bybit_rest(trade_item, symbol)
                trades.append(trade)
            
            # Сортируем сделки по времени (от старых к новым)
            trades.sort(key=lambda x: x.timestamp)
            
            return trades
            
        except VantaAPIError:
            # Пробрасываем ошибки API без изменений
            raise
        except Exception as e:
            # Преобразуем другие исключения в VantaAPIError
            raise VantaAPIError(
                message=f"Ошибка при получении данных о сделках: {str(e)}",
                exchange=self.exchange_name,
                original_exception=e
            ) from e
    
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
        try:
            # Определяем категорию инструмента
            category = self._get_category_for_symbol(symbol)
            
            # Валидация символа - для фьючерсов
            if category not in ['linear', 'inverse']:
                raise ValidationError(
                    message=f"Открытый интерес доступен только для фьючерсов (linear, inverse). Текущая категория: {category}",
                    exchange=self.exchange_name
                )
            
            # Формируем параметры запроса
            params = {
                'category': category,
                'symbol': symbol
            }
            
            # Выполняем запрос к API
            response = await self.connection.get(MarketDataEndpoints.OPEN_INTEREST, params)
            
            # Проверяем успешность запроса
            if response.get('retCode') != 0:
                raise VantaAPIError(
                    message=f"Ошибка при получении открытого интереса: {response.get('retMsg', 'Unknown error')}",
                    code=response.get('retCode'),
                    exchange=self.exchange_name
                )
            
            # Извлекаем данные из ответа
            oi_data = response.get('result', {})
            
            # Проверяем наличие данных
            if not oi_data:
                raise VantaAPIError(
                    message=f"Пустой ответ при запросе открытого интереса для {symbol}",
                    exchange=self.exchange_name
                )
            
            # Преобразуем данные в объект OpenInterestData
            return OpenInterestData.from_bybit_rest(oi_data, symbol)
            
        except VantaAPIError:
            # Пробрасываем ошибки API без изменений
            raise
        except ValidationError:
            # Пробрасываем ошибки валидации
            raise
        except Exception as e:
            # Преобразуем другие исключения в VantaAPIError
            raise VantaAPIError(
                message=f"Ошибка при получении открытого интереса: {str(e)}",
                exchange=self.exchange_name,
                original_exception=e
            ) from e
    
    async def get_open_interest_history(self, symbol: str, period: str, 
                                        limit: Optional[int] = None) -> List[OpenInterestData]:
        """
        Получает историю открытого интереса для указанного символа.
        
        Args:
            symbol: Торговый символ (например, "BTCUSDT").
            period: Период агрегации данных (например, "5min", "15min", "30min", "1h", "4h", "1d").
            limit: Максимальное количество записей для получения.
                  Если None, используется значение по умолчанию API.
            
        Returns:
            Список объектов OpenInterestData, отсортированных по времени (обычно от старых к новым).
            
        Raises:
            VantaAPIError: При ошибке взаимодействия с API биржи.
            VantaRateLimitError: При превышении лимита запросов к API биржи.
        """
        try:
            # Определяем категорию инструмента
            category = self._get_category_for_symbol(symbol)
            
            # Валидация символа - для фьючерсов
            if category not in ['linear', 'inverse']:
                raise ValidationError(
                    message=f"История открытого интереса доступна только для фьючерсов (linear, inverse). Текущая категория: {category}",
                    exchange=self.exchange_name
                )
            
            # Валидация периода
            valid_periods = {'5min', '15min', '30min', '1h', '4h', '1d'}
            if period not in valid_periods:
                raise ValidationError(
                    message=f"Недопустимый период '{period}'. Допустимые периоды: {', '.join(valid_periods)}",
                    exchange=self.exchange_name
                )
            
            # Формируем параметры запроса
            params = {
                'category': category,
                'symbol': symbol,
                'intervalTime': period
            }
            
            # Добавляем лимит, если указан
            # Bybit API поддерживает лимит до 200 записей, по умолчанию 50
            if limit is not None:
                # Ограничиваем значение лимита в соответствии с API
                params['limit'] = max(1, min(200, limit))
            
            # Выполняем запрос к API
            response = await self.connection.get(MarketDataEndpoints.OPEN_INTEREST_HISTORY, params)
            
            # Проверяем успешность запроса
            if response.get('retCode') != 0:
                raise VantaAPIError(
                    message=f"Ошибка при получении истории открытого интереса: {response.get('retMsg', 'Unknown error')}",
                    code=response.get('retCode'),
                    exchange=self.exchange_name
                )
            
            # Извлекаем данные из ответа
            oi_list = response.get('result', {}).get('list', [])
            
            # Проверяем наличие данных
            if not oi_list:
                # Возвращаем пустой список, если данных нет
                return []
            
            # Преобразуем данные в список объектов OpenInterestData
            result = OpenInterestData.from_list(oi_list, symbol)
            
            # Сортируем по времени (от старых к новым)
            result.sort(key=lambda x: x.timestamp)
            
            return result
            
        except VantaAPIError:
            # Пробрасываем ошибки API без изменений
            raise
        except ValidationError:
            # Пробрасываем ошибки валидации
            raise
        except Exception as e:
            # Преобразуем другие исключения в VantaAPIError
            raise VantaAPIError(
                message=f"Ошибка при получении истории открытого интереса: {str(e)}",
                exchange=self.exchange_name,
                original_exception=e
            ) from e 
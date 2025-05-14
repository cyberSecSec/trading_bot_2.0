from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Any, List, Optional, ClassVar, Tuple
import pandas as pd
import numpy as np

from pydantic import Field, validator

from ..base import BaseMarketDataModel
from ..utils.converters import safe_decimal, timestamp_to_datetime

class KlineInterval:
    """Константы для интервалов свечей, поддерживаемых Bybit."""
    MINUTE_1 = "1"
    MINUTE_3 = "3"
    MINUTE_5 = "5"
    MINUTE_15 = "15"
    MINUTE_30 = "30"
    HOUR_1 = "60"
    HOUR_2 = "120"
    HOUR_4 = "240"
    HOUR_6 = "360"
    HOUR_12 = "720"
    DAY_1 = "D"
    WEEK_1 = "W"
    MONTH_1 = "M"
    
    @classmethod
    def to_minutes(cls, interval: str) -> int:
        """Преобразует интервал в количество минут."""
        if interval == cls.DAY_1:
            return 24 * 60
        elif interval == cls.WEEK_1:
            return 7 * 24 * 60
        elif interval == cls.MONTH_1:
            return 30 * 24 * 60
        return int(interval)
    
    @classmethod
    def to_timedelta(cls, interval: str) -> timedelta:
        """Преобразует интервал в объект timedelta."""
        minutes = cls.to_minutes(interval)
        return timedelta(minutes=minutes)


class KlineData(BaseMarketDataModel):
    """
    Модель данных для представления OHLCV данных (свечей).
    
    Данная модель представляет свечи (Kline/Candlestick) с биржи Bybit,
    включая открытие, максимум, минимум, закрытие, объем и другие параметры.
    """
    
    # Поля модели данных
    open: Decimal = Field(..., description="Цена открытия")
    high: Decimal = Field(..., description="Максимальная цена за период")
    low: Decimal = Field(..., description="Минимальная цена за период")
    close: Decimal = Field(..., description="Цена закрытия")
    volume: Decimal = Field(..., description="Объем торгов за период (в базовой валюте)")
    turnover: Decimal = Field(..., description="Оборот за период (в котируемой валюте)")
    interval: str = Field(..., description="Интервал свечи (например, '1' для 1 минуты)")
    
    # Вычисляемые поля
    is_closed: bool = Field(default=True, description="Закрыта ли свеча (True) или это текущая свеча (False)")
    
    # Форматы данных в API Bybit
    BYBIT_REST_FORMAT: ClassVar[List[str]] = [
        "start", "open", "high", "low", "close", "volume", "turnover"
    ]
    BYBIT_WS_FORMAT: ClassVar[List[str]] = [
        "start", "open", "high", "low", "close", "volume", "turnover", "confirm"
    ]
    
    @validator('open', 'high', 'low', 'close', 'volume', 'turnover', pre=True)
    def validate_decimal(cls, v):
        """Конвертирует строковые или числовые значения в Decimal."""
        return safe_decimal(v)
    
    @classmethod
    def from_bybit_rest(cls, data: Dict[str, Any], symbol: str, interval: str) -> 'KlineData':
        """
        Создает экземпляр KlineData из данных REST API Bybit.
        
        Args:
            data: Словарь с данными от Bybit API
            symbol: Торговый символ
            interval: Интервал свечи
            
        Returns:
            Экземпляр KlineData
        """
        # В Bybit API данные в виде списка со значениями
        if isinstance(data, list):
            item = {field: value for field, value in zip(cls.BYBIT_REST_FORMAT, data)}
        else:
            item = data
            
        timestamp = timestamp_to_datetime(item.get("start", item.get("timestamp")))
        
        return cls(
            symbol=symbol,
            timestamp=timestamp,
            open=item["open"],
            high=item["high"],
            low=item["low"],
            close=item["close"],
            volume=item["volume"],
            turnover=item["turnover"],
            interval=interval,
            is_closed=True
        )
    
    @classmethod
    def from_bybit_ws(cls, data: Dict[str, Any], symbol: str, interval: str) -> 'KlineData':
        """
        Создает экземпляр KlineData из данных WebSocket API Bybit.
        
        Args:
            data: Словарь с данными от Bybit WebSocket
            symbol: Торговый символ
            interval: Интервал свечи
            
        Returns:
            Экземпляр KlineData
        """
        # В Bybit WebSocket данные могут быть в различных форматах
        item = data.get("data", data)
        
        if isinstance(item, list) and len(item) > 0:
            item = item[0]  # Берем первый элемент из списка
            
        if isinstance(item, list):
            # Данные в виде списка [timestamp, open, high, low, close, volume, ...]
            kline_dict = {field: value for field, value in zip(cls.BYBIT_WS_FORMAT, item)}
        else:
            kline_dict = item
            
        timestamp = timestamp_to_datetime(kline_dict.get("start", kline_dict.get("timestamp", kline_dict.get("t"))))
        
        # Определяем, закрыта ли свеча
        is_closed = kline_dict.get("confirm", kline_dict.get("c", True))
        if isinstance(is_closed, str):
            is_closed = is_closed.lower() == "true"
            
        return cls(
            symbol=symbol,
            timestamp=timestamp,
            open=kline_dict.get("open", kline_dict.get("o")),
            high=kline_dict.get("high", kline_dict.get("h")),
            low=kline_dict.get("low", kline_dict.get("l")),
            close=kline_dict.get("close", kline_dict.get("c")),
            volume=kline_dict.get("volume", kline_dict.get("v")),
            turnover=kline_dict.get("turnover", kline_dict.get("V", 0)),
            interval=interval,
            is_closed=is_closed
        )
    
    @classmethod
    def from_list(cls, data_list: List[Dict[str, Any]], symbol: str, interval: str) -> List['KlineData']:
        """
        Создает список экземпляров KlineData из списка данных.
        
        Args:
            data_list: Список данных свечей
            symbol: Торговый символ
            interval: Интервал свечи
            
        Returns:
            Список экземпляров KlineData
        """
        return [cls.from_bybit_rest(item, symbol, interval) for item in data_list]
    
    @staticmethod
    def to_dataframe(klines: List['KlineData']) -> pd.DataFrame:
        """
        Преобразует список KlineData в pandas DataFrame.
        
        Args:
            klines: Список экземпляров KlineData
            
        Returns:
            pandas DataFrame с OHLCV данными
        """
        data = [
            {
                "timestamp": k.timestamp,
                "open": float(k.open),
                "high": float(k.high),
                "low": float(k.low),
                "close": float(k.close),
                "volume": float(k.volume),
                "turnover": float(k.turnover),
                "symbol": k.symbol,
                "interval": k.interval
            }
            for k in klines
        ]
        
        if not data:
            # Возвращаем пустой DataFrame с нужными колонками
            return pd.DataFrame(columns=[
                "timestamp", "open", "high", "low", "close", 
                "volume", "turnover", "symbol", "interval"
            ])
        
        df = pd.DataFrame(data)
        df.set_index("timestamp", inplace=True)
        return df
    
    def range(self) -> Decimal:
        """Возвращает диапазон цен (high - low)."""
        return self.high - self.low
    
    def body(self) -> Decimal:
        """Возвращает размер тела свечи (|open - close|)."""
        return abs(self.open - self.close)
    
    def is_bullish(self) -> bool:
        """Возвращает True, если свеча бычья (close > open)."""
        return self.close > self.open
    
    def is_bearish(self) -> bool:
        """Возвращает True, если свеча медвежья (close < open)."""
        return self.close < self.open
    
    def upper_wick(self) -> Decimal:
        """Возвращает размер верхнего фитиля."""
        return self.high - max(self.open, self.close)
    
    def lower_wick(self) -> Decimal:
        """Возвращает размер нижнего фитиля."""
        return min(self.open, self.close) - self.low
    
    def has_long_upper_wick(self) -> bool:
        """Возвращает True, если свеча имеет длинный верхний фитиль."""
        return self.upper_wick() > self.body() * Decimal('0.5')
    
    def has_long_lower_wick(self) -> bool:
        """Возвращает True, если свеча имеет длинный нижний фитиль."""
        return self.lower_wick() > self.body() * Decimal('0.5') 
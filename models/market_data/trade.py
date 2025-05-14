from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, Any, List, Optional, ClassVar
import pandas as pd

from pydantic import Field, validator

from ..base import BaseMarketDataModel
from ..utils.converters import safe_decimal, timestamp_to_datetime

class TradeSide(str, Enum):
    """Сторона сделки."""
    BUY = "Buy"
    SELL = "Sell"

class TradeData(BaseMarketDataModel):
    """
    Модель данных для представления сделки (trade).
    
    Данная модель представляет информацию о совершенной сделке на бирже,
    включая цену, объем, сторону и другие параметры.
    """
    
    # Поля модели данных
    id: str = Field(..., description="Уникальный идентификатор сделки")
    price: Decimal = Field(..., description="Цена сделки")
    quantity: Decimal = Field(..., description="Объем сделки (в базовой валюте)")
    side: TradeSide = Field(..., description="Сторона сделки (Buy/Sell)")
    
    # Дополнительные поля
    is_buyer_maker: bool = Field(False, description="Был ли покупатель мейкером")
    is_block_trade: bool = Field(False, description="Является ли это блочной сделкой")
    
    @validator('price', 'quantity', pre=True)
    def validate_decimal(cls, v):
        """Конвертирует строковые или числовые значения в Decimal."""
        return safe_decimal(v)
    
    @validator('side', pre=True)
    def validate_side(cls, v):
        """Нормализует сторону сделки."""
        if isinstance(v, str):
            # Приводим к нижнему регистру и проверяем разные варианты
            v_lower = v.lower()
            
            if v_lower in ('buy', 'bid', 'b', '1'):
                return TradeSide.BUY
            elif v_lower in ('sell', 'ask', 's', '2'):
                return TradeSide.SELL
        
        # Если ничего не сработало, возвращаем оригинальное значение
        # Pydantic сам вызовет ошибку, если оно недопустимо
        return v
    
    @classmethod
    def from_bybit_rest(cls, data: Dict[str, Any], symbol: str) -> 'TradeData':
        """
        Создает экземпляр TradeData из данных REST API Bybit.
        
        Args:
            data: Словарь с данными от Bybit API
            symbol: Торговый символ
            
        Returns:
            Экземпляр TradeData
        """
        timestamp = timestamp_to_datetime(data.get("time", data.get("timestamp", data.get("execTime"))))
        
        # Определяем, является ли покупатель мейкером
        is_buyer_maker = data.get("isBuyerMaker", data.get("maker_side", "").lower() == "buy")
        
        # Определяем сторону сделки
        side = data.get("side", "")
        if not side:
            # Если сторона не указана явно, определяем по maker/taker
            if is_buyer_maker:
                side = TradeSide.BUY
            else:
                side = TradeSide.SELL
        
        return cls(
            symbol=symbol,
            timestamp=timestamp,
            id=str(data.get("id", data.get("execId", ""))),
            price=data.get("price", data.get("execPrice", 0)),
            quantity=data.get("qty", data.get("size", data.get("execQty", 0))),
            side=side,
            is_buyer_maker=is_buyer_maker,
            is_block_trade=data.get("isBlockTrade", False)
        )
    
    @classmethod
    def from_bybit_ws(cls, data: Dict[str, Any], symbol: str) -> 'TradeData':
        """
        Создает экземпляр TradeData из данных WebSocket API Bybit.
        
        Args:
            data: Словарь с данными от Bybit WebSocket
            symbol: Торговый символ
            
        Returns:
            Экземпляр TradeData
        """
        # Извлекаем данные из сообщения WebSocket
        item = data.get("data", data)
        
        # Если данные в виде списка, берем первый элемент
        if isinstance(item, list) and len(item) > 0:
            item = item[0]
        
        timestamp = timestamp_to_datetime(
            item.get("timestamp", item.get("T", item.get("time", item.get("t"))))
        )
        
        # Определяем, является ли покупатель мейкером
        is_buyer_maker = item.get("m", item.get("maker", item.get("isBuyerMaker", False)))
        if isinstance(is_buyer_maker, str):
            is_buyer_maker = is_buyer_maker.lower() in ("true", "1", "yes")
        
        # Определяем сторону сделки
        side = item.get("S", item.get("side", ""))
        if not side:
            # Если сторона не указана явно, определяем по maker/taker
            if is_buyer_maker:
                side = TradeSide.BUY
            else:
                side = TradeSide.SELL
        
        return cls(
            symbol=symbol,
            timestamp=timestamp,
            id=str(item.get("i", item.get("id", item.get("tradeId", "")))),
            price=item.get("p", item.get("price", 0)),
            quantity=item.get("q", item.get("v", item.get("size", item.get("qty", 0)))),
            side=side,
            is_buyer_maker=is_buyer_maker,
            is_block_trade=item.get("isBlockTrade", item.get("blockTrade", False))
        )
    
    @classmethod
    def from_list(cls, data_list: List[Dict[str, Any]], symbol: str) -> List['TradeData']:
        """
        Создает список экземпляров TradeData из списка данных.
        
        Args:
            data_list: Список данных сделок
            symbol: Торговый символ
            
        Returns:
            Список экземпляров TradeData
        """
        return [cls.from_bybit_rest(item, symbol) for item in data_list]
    
    @staticmethod
    def to_dataframe(trades: List['TradeData']) -> pd.DataFrame:
        """
        Преобразует список TradeData в pandas DataFrame.
        
        Args:
            trades: Список экземпляров TradeData
            
        Returns:
            pandas DataFrame с данными сделок
        """
        data = [
            {
                "timestamp": t.timestamp,
                "id": t.id,
                "price": float(t.price),
                "quantity": float(t.quantity),
                "value": float(t.price * t.quantity),
                "side": t.side.value,
                "is_buyer_maker": t.is_buyer_maker,
                "symbol": t.symbol
            }
            for t in trades
        ]
        
        if not data:
            # Возвращаем пустой DataFrame с нужными колонками
            return pd.DataFrame(columns=[
                "timestamp", "id", "price", "quantity", "value", 
                "side", "is_buyer_maker", "symbol"
            ])
        
        df = pd.DataFrame(data)
        df.set_index("timestamp", inplace=True)
        return df
    
    def is_buy(self) -> bool:
        """Возвращает True, если сделка на покупку."""
        return self.side == TradeSide.BUY
    
    def is_sell(self) -> bool:
        """Возвращает True, если сделка на продажу."""
        return self.side == TradeSide.SELL
    
    def value(self) -> Decimal:
        """Возвращает общую стоимость сделки (цена * количество)."""
        return self.price * self.quantity
    
    @staticmethod
    def calculate_vwap(trades: List['TradeData']) -> Optional[Decimal]:
        """
        Вычисляет средневзвешенную цену по объему (VWAP) для списка сделок.
        
        Args:
            trades: Список сделок
            
        Returns:
            VWAP или None, если список сделок пуст
        """
        if not trades:
            return None
            
        total_volume = Decimal('0')
        volume_price_sum = Decimal('0')
        
        for trade in trades:
            total_volume += trade.quantity
            volume_price_sum += trade.quantity * trade.price
        
        if total_volume > 0:
            return volume_price_sum / total_volume
        return None
    
    @staticmethod
    def calculate_delta(trades: List['TradeData']) -> Decimal:
        """
        Вычисляет дельту объема (разницу между объемами покупок и продаж).
        
        Args:
            trades: Список сделок
            
        Returns:
            Дельта объема (положительная - превышение покупок, отрицательная - превышение продаж)
        """
        buy_volume = Decimal('0')
        sell_volume = Decimal('0')
        
        for trade in trades:
            if trade.is_buy():
                buy_volume += trade.quantity
            else:
                sell_volume += trade.quantity
        
        return buy_volume - sell_volume 
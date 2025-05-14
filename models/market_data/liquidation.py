from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, Any, List, Optional, ClassVar
import pandas as pd

from pydantic import Field, validator

from ..base import BaseMarketDataModel
from ..utils.converters import safe_decimal, timestamp_to_datetime

class LiquidationSide(str, Enum):
    """Сторона ликвидации."""
    BUY = "Buy"  # Ликвидация короткой позиции (Long - покупка)
    SELL = "Sell"  # Ликвидация длинной позиции (Short - продажа)

class LiquidationData(BaseMarketDataModel):
    """
    Модель данных для представления ликвидации.
    
    Данная модель представляет информацию о ликвидированных позициях на бирже,
    включая цену, объем, сторону и другие параметры.
    """
    
    # Поля модели данных
    price: Decimal = Field(..., description="Цена ликвидации")
    quantity: Decimal = Field(..., description="Объем ликвидации (в базовой валюте)")
    side: LiquidationSide = Field(..., description="Сторона ликвидации (Buy/Sell)")
    
    # Дополнительные поля
    order_type: Optional[str] = Field(None, description="Тип ордера ликвидации")
    position_value: Optional[Decimal] = Field(None, description="Стоимость ликвидированной позиции")
    liquidation_id: Optional[str] = Field(None, description="Идентификатор ликвидации")
    
    @validator('price', 'quantity', 'position_value', pre=True)
    def validate_decimal(cls, v):
        """Конвертирует строковые или числовые значения в Decimal."""
        return safe_decimal(v)
    
    @validator('side', pre=True)
    def validate_side(cls, v):
        """Нормализует сторону ликвидации."""
        if isinstance(v, str):
            v_lower = v.lower()
            
            if v_lower in ('buy', 'bid', 'b', '1', 'long'):
                return LiquidationSide.BUY
            elif v_lower in ('sell', 'ask', 's', '2', 'short'):
                return LiquidationSide.SELL
        
        return v
    
    @classmethod
    def from_bybit_ws(cls, data: Dict[str, Any], symbol: str) -> 'LiquidationData':
        """
        Создает экземпляр LiquidationData из данных WebSocket API Bybit.
        
        Args:
            data: Словарь с данными от Bybit WebSocket
            symbol: Торговый символ
            
        Returns:
            Экземпляр LiquidationData
        """
        # Извлекаем данные из сообщения WebSocket
        item = data.get("data", data)
        
        # Если данные в виде списка, берем первый элемент
        if isinstance(item, list) and len(item) > 0:
            item = item[0]
        
        # В Bybit WebSocket API ликвидации имеют свою структуру
        timestamp = timestamp_to_datetime(
            item.get("timestamp", item.get("updatedTime", item.get("time", item.get("T"))))
        )
        
        # Определение стороны ликвидации
        side = item.get("side", item.get("S"))
        position_value = item.get("positionValue", item.get("posValue", None))
        
        return cls(
            symbol=symbol,
            timestamp=timestamp,
            price=item.get("price", item.get("P", 0)),
            quantity=item.get("qty", item.get("size", item.get("Q", 0))),
            side=side,
            order_type=item.get("orderType", item.get("type", "Market")),
            position_value=position_value,
            liquidation_id=str(item.get("id", item.get("L", "")))
        )
    
    @classmethod
    def from_list(cls, data_list: List[Dict[str, Any]], symbol: str) -> List['LiquidationData']:
        """
        Создает список экземпляров LiquidationData из списка данных.
        
        Args:
            data_list: Список данных ликвидаций
            symbol: Торговый символ
            
        Returns:
            Список экземпляров LiquidationData
        """
        return [cls.from_bybit_ws(item, symbol) for item in data_list]
    
    @staticmethod
    def to_dataframe(liquidations: List['LiquidationData']) -> pd.DataFrame:
        """
        Преобразует список LiquidationData в pandas DataFrame.
        
        Args:
            liquidations: Список экземпляров LiquidationData
            
        Returns:
            pandas DataFrame с данными ликвидаций
        """
        data = [
            {
                "timestamp": l.timestamp,
                "price": float(l.price),
                "quantity": float(l.quantity),
                "value": float(l.price * l.quantity),
                "side": l.side.value,
                "position_value": float(l.position_value) if l.position_value else None,
                "order_type": l.order_type,
                "symbol": l.symbol
            }
            for l in liquidations
        ]
        
        if not data:
            # Возвращаем пустой DataFrame с нужными колонками
            return pd.DataFrame(columns=[
                "timestamp", "price", "quantity", "value", 
                "side", "position_value", "order_type", "symbol"
            ])
        
        df = pd.DataFrame(data)
        df.set_index("timestamp", inplace=True)
        return df
    
    def is_long_liquidation(self) -> bool:
        """Возвращает True, если это ликвидация длинной позиции (Sell)."""
        return self.side == LiquidationSide.SELL
    
    def is_short_liquidation(self) -> bool:
        """Возвращает True, если это ликвидация короткой позиции (Buy)."""
        return self.side == LiquidationSide.BUY
    
    def value(self) -> Decimal:
        """Возвращает стоимость ликвидации (цена * количество)."""
        return self.price * self.quantity
    
    @staticmethod
    def calculate_total_value(liquidations: List['LiquidationData']) -> Dict[str, Decimal]:
        """
        Вычисляет общую стоимость ликвидаций с разбивкой по сторонам.
        
        Args:
            liquidations: Список ликвидаций
            
        Returns:
            Словарь {"long": value_long, "short": value_short, "total": total_value}
        """
        long_value = Decimal('0')
        short_value = Decimal('0')
        
        for liq in liquidations:
            if liq.is_long_liquidation():
                long_value += liq.value()
            else:
                short_value += liq.value()
        
        return {
            "long": long_value,
            "short": short_value,
            "total": long_value + short_value
        }
    
    @staticmethod
    def is_cascade(liquidations: List['LiquidationData'], 
                   time_window_seconds: int = 60, 
                   min_volume: Decimal = Decimal('10')) -> bool:
        """
        Определяет, является ли группа ликвидаций каскадной (Liquidation Cascade).
        
        Каскадная ликвидация определяется как серия ликвидаций одного направления
        в короткий промежуток времени с значительным объемом.
        
        Args:
            liquidations: Список ликвидаций
            time_window_seconds: Окно времени для определения каскада (в секундах)
            min_volume: Минимальный объем для определения значимости каскада
            
        Returns:
            True, если обнаружен каскад ликвидаций
        """
        if not liquidations or len(liquidations) < 3:
            return False
        
        # Сортируем ликвидации по времени
        sorted_liq = sorted(liquidations, key=lambda x: x.timestamp)
        
        # Проверяем, все ли ликвидации одного направления
        first_side = sorted_liq[0].side
        if not all(liq.side == first_side for liq in sorted_liq):
            return False
        
        # Проверяем временное окно
        time_delta = (sorted_liq[-1].timestamp - sorted_liq[0].timestamp).total_seconds()
        if time_delta > time_window_seconds:
            return False
        
        # Проверяем общий объем
        total_volume = sum(liq.quantity for liq in sorted_liq)
        return total_volume >= min_volume 
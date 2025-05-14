from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, Any, List, Optional

from pydantic import Field, validator

from ..base import BaseTradingModel
from ..utils.converters import safe_decimal, timestamp_to_datetime
from .order_params import OrderSide

class LiquidityType(str, Enum):
    """Тип ликвидности для исполнения ордера."""
    MAKER = "Maker"  # Исполнение создало ликвидность (мейкер)
    TAKER = "Taker"  # Исполнение забрало ликвидность (тейкер)

class ExecutionInfo(BaseTradingModel):
    """
    Модель для представления информации об исполнении ордера.
    
    Данная модель содержит детальную информацию о конкретном исполнении ордера,
    включая цену, количество, комиссию и другие параметры.
    """
    
    # Идентификаторы
    exec_id: str = Field(..., description="Уникальный ID исполнения")
    order_id: str = Field(..., description="ID ордера, который был исполнен")
    order_link_id: Optional[str] = Field(None, description="Клиентский ID ордера")
    
    # Параметры исполнения
    side: OrderSide = Field(..., description="Сторона ордера (Buy/Sell)")
    price: Decimal = Field(..., description="Цена исполнения")
    qty: Decimal = Field(..., description="Количество исполнения")
    
    # Детали исполнения
    liquidity_type: LiquidityType = Field(..., description="Тип ликвидности (Maker/Taker)")
    fee: Decimal = Field(..., description="Комиссия за исполнение")
    fee_rate: Decimal = Field(..., description="Ставка комиссии")
    
    # Валюта комиссии и стоимость
    fee_currency: str = Field(..., description="Валюта комиссии")
    exec_value: Decimal = Field(..., description="Стоимость исполнения")
    
    # Временные метки
    exec_time: datetime = Field(..., description="Время исполнения")
    
    # Дополнительные поля
    is_maker: bool = Field(False, description="Был ли исполнитель мейкером")
    is_closes_position: Optional[bool] = Field(None, description="Флаг, указывающий закрывает ли сделка позицию")
    
    # Bybit-специфичные поля
    category: str = Field("linear", description="Категория торгового инструмента")
    block_trade_id: Optional[str] = Field(None, description="ID блочной сделки (для институциональных сделок)")
    
    @validator('price', 'qty', 'fee', 'fee_rate', 'exec_value', pre=True)
    def validate_decimal(cls, v):
        """Конвертирует строковые или числовые значения в Decimal."""
        return safe_decimal(v)
    
    @validator('liquidity_type', pre=True)
    def validate_liquidity_type(cls, v):
        """Нормализует тип ликвидности."""
        if isinstance(v, str):
            v_lower = v.lower()
            
            if v_lower in ('maker', 'm', '0'):
                return LiquidityType.MAKER
            elif v_lower in ('taker', 't', '1'):
                return LiquidityType.TAKER
        elif isinstance(v, bool):
            return LiquidityType.MAKER if v else LiquidityType.TAKER
        return v
    
    @validator('side', pre=True)
    def validate_side(cls, v):
        """Нормализует сторону исполнения."""
        if isinstance(v, str) and v not in (OrderSide.BUY.value, OrderSide.SELL.value):
            v_lower = v.lower()
            if v_lower in ('buy', 'bid', 'b'):
                return OrderSide.BUY
            elif v_lower in ('sell', 'ask', 's'):
                return OrderSide.SELL
        return v
    
    @classmethod
    def from_bybit_response(cls, data: Dict[str, Any]) -> 'ExecutionInfo':
        """
        Создает экземпляр ExecutionInfo из ответа API Bybit.
        
        Args:
            data: Словарь с данными от Bybit API
            
        Returns:
            Экземпляр ExecutionInfo
        """
        # Определяем время исполнения
        exec_time = timestamp_to_datetime(
            data.get("execTime", data.get("exec_time", data.get("time")))
        )
        
        # Извлекаем данные из ответа API
        return cls(
            timestamp=exec_time,  # Для BaseTradingModel
            symbol=data.get("symbol"),
            exchange="bybit",
            
            # Идентификаторы
            execution_id=data.get("execId", data.get("exec_id", "")),
            order_id=data.get("orderId", data.get("order_id", "")),
            order_link_id=data.get("orderLinkId", data.get("order_link_id")),
            
            # Параметры исполнения
            side=data.get("side"),
            price=data.get("execPrice", data.get("exec_price", data.get("price", 0))),
            qty=data.get("execQty", data.get("exec_qty", data.get("qty", 0))),
            fee=data.get("execFee", data.get("exec_fee", 0)),
            fee_rate=data.get("feeRate", data.get("fee_rate")),
            
            # Валюта комиссии
            fee_currency=data.get("feeCurrency", data.get("fee_currency")),
            
            # Время исполнения
            exec_time=exec_time,
            
            # Тип ликвидности
            is_maker=data.get("isMaker", data.get("is_maker", False)),
            
            # Закрытие позиции
            is_closes_position=data.get("closedSize", data.get("closed_size")) is not None,
            
            # Дополнительные параметры
            block_trade_id=data.get("blockTradeId", data.get("block_trade_id"))
        )
    
    @classmethod
    def from_bybit_ws(cls, data: Dict[str, Any]) -> 'ExecutionInfo':
        """
        Создает экземпляр ExecutionInfo из данных WebSocket API Bybit.
        
        Args:
            data: Словарь с данными от Bybit WebSocket
            
        Returns:
            Экземпляр ExecutionInfo
        """
        # Извлекаем данные из сообщения WebSocket
        item = data.get("data", data)
        
        # WebSocket сообщения об исполнении в Bybit часто имеют другую структуру
        if isinstance(item, list) and len(item) > 0:
            item = item[0]
            
        return cls.from_bybit_response(item)
    
    @classmethod
    def from_list(cls, data_list: List[Dict[str, Any]]) -> List['ExecutionInfo']:
        """
        Создает список экземпляров ExecutionInfo из списка данных.
        
        Args:
            data_list: Список данных об исполнении
            
        Returns:
            Список экземпляров ExecutionInfo
        """
        return [cls.from_bybit_response(item) for item in data_list]
    
    def value(self) -> Decimal:
        """
        Вычисляет стоимость сделки.
        
        Returns:
            Стоимость сделки (цена * количество)
        """
        return self.price * self.qty
    
    def net_value(self) -> Decimal:
        """
        Вычисляет чистую стоимость сделки (с учетом комиссии).
        
        Returns:
            Чистая стоимость (стоимость - комиссия)
        """
        return self.value() - self.fee 
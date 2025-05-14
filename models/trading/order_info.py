from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, Any, List, Optional, ClassVar

from pydantic import Field, validator

from ..base import BaseTradingModel
from ..utils.converters import safe_decimal, timestamp_to_datetime
from .order_params import OrderSide, OrderType, TimeInForce

class OrderStatus(str, Enum):
    """Статус ордера."""
    CREATED = "Created"  # Создан
    NEW = "New"  # Новый
    REJECTED = "Rejected"  # Отклонен
    PARTIALLY_FILLED = "PartiallyFilled"  # Частично исполнен
    FILLED = "Filled"  # Полностью исполнен
    CANCELLED = "Cancelled"  # Отменен
    PENDING_CANCEL = "PendingCancel"  # Ожидает отмены
    UNTRIGGERED = "Untriggered"  # Не активирован (для стоп-ордеров)
    TRIGGERED = "Triggered"  # Активирован (для стоп-ордеров)
    ACTIVE = "Active"  # Активный
    DEACTIVATED = "Deactivated"  # Деактивирован
    PARTIALLY_FILLED_CANCELLED = "PartiallyFilledCancelled"  # Частично исполнен и отменен

class OrderInfo(BaseTradingModel):
    """
    Модель для представления информации об ордере.
    
    Данная модель содержит полную информацию об ордере, полученную от биржи,
    включая параметры, статус, время создания и исполнения и другие детали.
    """
    
    # Идентификаторы
    order_id: str = Field(..., description="Уникальный ID ордера на бирже")
    order_link_id: Optional[str] = Field(None, description="Клиентский ID ордера")
    
    # Параметры ордера
    side: OrderSide = Field(..., description="Сторона ордера (Buy/Sell)")
    order_type: OrderType = Field(..., description="Тип ордера")
    price: Decimal = Field(..., description="Цена ордера")
    qty: Decimal = Field(..., description="Изначальное количество")
    
    # Статус и исполнение
    status: OrderStatus = Field(..., description="Текущий статус ордера")
    created_time: datetime = Field(..., description="Время создания ордера")
    updated_time: datetime = Field(..., description="Время последнего обновления")
    
    cum_exec_qty: Decimal = Field(default=Decimal('0'), description="Исполненное количество")
    cum_exec_value: Decimal = Field(default=Decimal('0'), description="Стоимость исполненного количества")
    avg_price: Optional[Decimal] = Field(None, description="Средняя цена исполнения")
    
    # Дополнительные параметры
    time_in_force: TimeInForce = Field(..., description="Условие срока действия ордера")
    reduce_only: bool = Field(default=False, description="Только для уменьшения позиции")
    close_on_trigger: bool = Field(default=False, description="Закрыть позицию при срабатывании")
    
    # Параметры для стоп-ордеров
    trigger_price: Optional[Decimal] = Field(None, description="Цена активации для стоп-ордеров")
    trigger_by: Optional[str] = Field(None, description="Тип цены для активации стоп-ордеров")
    
    # Параметры для трейлинг-стоп ордеров
    trailing_stop: Optional[Decimal] = Field(None, description="Отставание цены для трейлинг-стоп ордеров")
    
    # Стоп-лосс и тейк-профит
    stop_loss: Optional[Decimal] = Field(None, description="Цена стоп-лосс")
    take_profit: Optional[Decimal] = Field(None, description="Цена тейк-профит")
    
    # Комиссии
    cum_exec_fee: Decimal = Field(default=Decimal('0'), description="Накопленная комиссия")
    
    # Категория в Bybit
    category: str = Field("linear", description="Категория торгового инструмента")
    
    @validator('price', 'qty', 'cum_exec_qty', 'cum_exec_value', 'avg_price', 
               'trigger_price', 'trailing_stop', 'stop_loss', 'take_profit', 
               'cum_exec_fee', pre=True)
    def validate_decimal(cls, v):
        """Конвертирует строковые или числовые значения в Decimal."""
        return safe_decimal(v)
    
    @validator('side', pre=True)
    def validate_side(cls, v):
        """Нормализует сторону ордера."""
        if isinstance(v, str) and v not in (OrderSide.BUY.value, OrderSide.SELL.value):
            v_lower = v.lower()
            if v_lower in ('buy', 'bid', 'b'):
                return OrderSide.BUY
            elif v_lower in ('sell', 'ask', 's'):
                return OrderSide.SELL
        return v
    
    @validator('order_type', pre=True)
    def validate_order_type(cls, v):
        """Нормализует тип ордера."""
        if isinstance(v, str):
            type_map = {
                "limit": OrderType.LIMIT,
                "market": OrderType.MARKET,
                "stop": OrderType.STOP,
                "stop_market": OrderType.STOP_MARKET,
                "stopmarket": OrderType.STOP_MARKET,
                "take_profit": OrderType.TAKE_PROFIT,
                "takeprofit": OrderType.TAKE_PROFIT,
                "take_profit_market": OrderType.TAKE_PROFIT_MARKET,
                "takeprofitmarket": OrderType.TAKE_PROFIT_MARKET,
                "trailing_stop_market": OrderType.TRAILING_STOP_MARKET,
                "trailingstopmarket": OrderType.TRAILING_STOP_MARKET
            }
            
            v_lower = v.lower().replace("-", "_")
            if v_lower in type_map:
                return type_map[v_lower]
        return v
    
    @validator('status', pre=True)
    def validate_status(cls, v):
        """Нормализует статус ордера."""
        if isinstance(v, str):
            status_map = {
                "created": OrderStatus.CREATED,
                "new": OrderStatus.NEW,
                "rejected": OrderStatus.REJECTED,
                "partially_filled": OrderStatus.PARTIALLY_FILLED,
                "partiallyfilled": OrderStatus.PARTIALLY_FILLED,
                "filled": OrderStatus.FILLED,
                "cancelled": OrderStatus.CANCELLED,
                "canceled": OrderStatus.CANCELLED,
                "pending_cancel": OrderStatus.PENDING_CANCEL,
                "pendingcancel": OrderStatus.PENDING_CANCEL,
                "untriggered": OrderStatus.UNTRIGGERED,
                "triggered": OrderStatus.TRIGGERED,
                "active": OrderStatus.ACTIVE,
                "deactivated": OrderStatus.DEACTIVATED,
                "partially_filled_cancelled": OrderStatus.PARTIALLY_FILLED_CANCELLED,
                "partiallyfilled_canceled": OrderStatus.PARTIALLY_FILLED_CANCELLED
            }
            
            v_lower = v.lower().replace("-", "_")
            if v_lower in status_map:
                return status_map[v_lower]
        return v
    
    @validator('time_in_force', pre=True)
    def validate_time_in_force(cls, v):
        """Нормализует условие срока действия ордера."""
        if isinstance(v, str):
            tif_map = {
                "goodtillcancel": TimeInForce.GTC,
                "good_till_cancel": TimeInForce.GTC,
                "gtc": TimeInForce.GTC,
                "immediateorcancel": TimeInForce.IOC,
                "immediate_or_cancel": TimeInForce.IOC,
                "ioc": TimeInForce.IOC,
                "fillorkill": TimeInForce.FOK,
                "fill_or_kill": TimeInForce.FOK,
                "fok": TimeInForce.FOK,
                "postonly": TimeInForce.PO,
                "post_only": TimeInForce.PO,
                "po": TimeInForce.PO
            }
            
            v_lower = v.lower().replace("-", "_")
            if v_lower in tif_map:
                return tif_map[v_lower]
        return v
    
    @classmethod
    def from_bybit_response(cls, data: Dict[str, Any]) -> 'OrderInfo':
        """
        Создает экземпляр OrderInfo из ответа API Bybit.
        
        Args:
            data: Словарь с данными от Bybit API
            
        Returns:
            Экземпляр OrderInfo
        """
        # Bybit возвращает разные форматы в зависимости от эндпоинта
        # Обрабатываем ответы от /v5/order/create, /v5/order/realtime и /v5/order/history
        
        # Определяем временные метки
        created_time = timestamp_to_datetime(
            data.get("createdTime", data.get("createTime", data.get("created_at")))
        )
        updated_time = timestamp_to_datetime(
            data.get("updatedTime", data.get("updateTime", data.get("updated_at", created_time)))
        )
        
        symbol = data.get("symbol")
        category = data.get("category", "linear")
        
        # Преобразуем поля в нужный формат
        return cls(
            timestamp=updated_time,  # Для BaseTradingModel
            symbol=symbol,
            exchange="bybit",
            
            # Идентификаторы
            order_id=data.get("orderId", data.get("order_id", "")),
            order_link_id=data.get("orderLinkId", data.get("order_link_id")),
            
            # Параметры ордера
            side=data.get("side"),
            order_type=data.get("orderType", data.get("order_type")),
            price=data.get("price", 0),
            qty=data.get("qty", 0),
            
            # Статус и исполнение
            status=data.get("orderStatus", data.get("status")),
            created_time=created_time,
            updated_time=updated_time,
            
            cum_exec_qty=data.get("cumExecQty", data.get("cum_exec_qty", 0)),
            cum_exec_value=data.get("cumExecValue", data.get("cum_exec_value", 0)),
            avg_price=data.get("avgPrice", data.get("average_price")),
            
            # Дополнительные параметры
            time_in_force=data.get("timeInForce", data.get("time_in_force", "GTC")),
            reduce_only=data.get("reduceOnly", data.get("reduce_only", False)),
            close_on_trigger=data.get("closeOnTrigger", data.get("close_on_trigger", False)),
            
            # Параметры для стоп-ордеров
            trigger_price=data.get("triggerPrice", data.get("trigger_price")),
            trigger_by=data.get("triggerBy", data.get("trigger_by")),
            
            # Параметры для трейлинг-стоп ордеров
            trailing_stop=data.get("trailingStop", data.get("trailing_stop")),
            
            # Стоп-лосс и тейк-профит
            stop_loss=data.get("stopLoss", data.get("stop_loss")),
            take_profit=data.get("takeProfit", data.get("take_profit")),
            
            # Комиссии
            cum_exec_fee=data.get("cumExecFee", data.get("cum_exec_fee", 0)),
            
            # Категория
            category=category
        )
    
    @classmethod
    def from_bybit_ws(cls, data: Dict[str, Any]) -> 'OrderInfo':
        """
        Создает экземпляр OrderInfo из данных WebSocket API Bybit.
        
        Args:
            data: Словарь с данными от Bybit WebSocket
            
        Returns:
            Экземпляр OrderInfo
        """
        # Извлекаем данные из сообщения WebSocket
        item = data.get("data", data)
        
        # WebSocket сообщения об ордерах в Bybit имеют другую структуру
        return cls.from_bybit_response(item)
    
    def is_active(self) -> bool:
        """Возвращает True, если ордер активен."""
        active_statuses = [
            OrderStatus.NEW, 
            OrderStatus.PARTIALLY_FILLED,
            OrderStatus.ACTIVE,
            OrderStatus.UNTRIGGERED
        ]
        return self.status in active_statuses
    
    def is_filled(self) -> bool:
        """Возвращает True, если ордер полностью исполнен."""
        return self.status == OrderStatus.FILLED
    
    def is_partially_filled(self) -> bool:
        """Возвращает True, если ордер частично исполнен."""
        return self.status == OrderStatus.PARTIALLY_FILLED
    
    def is_cancelled(self) -> bool:
        """Возвращает True, если ордер отменен."""
        cancelled_statuses = [
            OrderStatus.CANCELLED,
            OrderStatus.PARTIALLY_FILLED_CANCELLED
        ]
        return self.status in cancelled_statuses
    
    def is_rejected(self) -> bool:
        """Возвращает True, если ордер отклонен."""
        return self.status == OrderStatus.REJECTED
    
    def fill_percent(self) -> Decimal:
        """Возвращает процент исполнения ордера (0-100%)."""
        if self.qty == 0:
            return Decimal('0')
            
        return (self.cum_exec_qty / self.qty) * Decimal('100') 
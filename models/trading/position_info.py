from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, Any, List, Optional

from pydantic import Field, validator

from ..base import BaseTradingModel
from ..utils.converters import safe_decimal, timestamp_to_datetime
from .order_params import OrderSide, PositionIdx

class MarginMode(str, Enum):
    """Режим маржи."""
    ISOLATED = "Isolated"  # Изолированная маржа
    CROSS = "Cross"  # Кросс-маржа

class PositionStatus(str, Enum):
    """Статус позиции."""
    NORMAL = "Normal"  # Нормальный
    LIQIDATION = "Liqidation"  # В процессе ликвидации
    ADL = "Adl"  # В процессе ADL (Auto-Deleveraging)
    NONE = "None"  # Позиция отсутствует
    OPEN = "Open"  # Открытая позиция
    CLOSED = "Closed"  # Закрытая позиция
    LIQUIDATING = "Liquidating"  # В процессе ликвидации
    LIQUIDATED = "Liquidated"  # Ликвидированная позиция
    PARTIALLY_CLOSED = "PartiallyClosed"  # Частично закрытая позиция

class PositionInfo(BaseTradingModel):
    """
    Модель для представления информации о позиции.
    
    Данная модель содержит детальную информацию о позиции,
    включая размер, направление, маржу, ликвидационную цену и другие параметры.
    """
    
    # Базовые параметры позиции
    position_idx: PositionIdx = Field(..., description="Индекс позиции (0: одностороння, 1: длинная хедж, 2: короткая хедж)")
    side: Optional[OrderSide] = Field(None, description="Сторона позиции (Buy/Sell)")
    size: Decimal = Field(..., description="Размер позиции (в контрактах)")
    
    # Цены
    entry_price: Decimal = Field(..., description="Цена входа")
    market_price: Decimal = Field(..., description="Текущая рыночная цена")
    liq_price: Optional[Decimal] = Field(None, description="Ликвидационная цена")
    bust_price: Optional[Decimal] = Field(None, description="Цена банкротства")
    
    # Маржа и PnL
    position_value: Decimal = Field(..., description="Стоимость позиции")
    position_margin: Decimal = Field(..., description="Маржа позиции")
    realised_pnl: Decimal = Field(..., description="Реализованный PnL")
    unrealised_pnl: Decimal = Field(..., description="Нереализованный PnL")
    
    # Параметры риска
    leverage: Decimal = Field(..., description="Кредитное плечо")
    margin_mode: MarginMode = Field(..., description="Режим маржи (Isolated/Cross)")
    stop_loss: Optional[Decimal] = Field(None, description="Цена стоп-лосс")
    take_profit: Optional[Decimal] = Field(None, description="Цена тейк-профит")
    trailing_stop: Optional[Decimal] = Field(None, description="Отставание для трейлинг-стопа")
    
    # Статус
    status: PositionStatus = Field(PositionStatus.NORMAL, description="Статус позиции")
    auto_add_margin: bool = Field(False, description="Автоматическое добавление маржи")
    adl_rank: Optional[int] = Field(None, description="Ранг ADL (Auto-Deleveraging)")
    
    # Дополнительные параметры
    order_margin: Optional[Decimal] = Field(None, description="Маржа под ордера")
    
    # Bybit-специфичные поля
    category: str = Field("linear", description="Категория торгового инструмента")
    created_time: Optional[datetime] = Field(None, description="Время создания позиции")
    updated_time: Optional[datetime] = Field(None, description="Время последнего обновления")
    
    @validator('size', 'entry_price', 'market_price', 'liq_price', 'bust_price', 
               'position_value', 'position_margin', 'realised_pnl', 'unrealised_pnl', 
               'leverage', 'stop_loss', 'take_profit', 'trailing_stop', 'order_margin', pre=True)
    def validate_decimal(cls, v):
        """Конвертирует строковые или числовые значения в Decimal."""
        return safe_decimal(v)
    
    @validator('created_time', 'updated_time', pre=True)
    def validate_datetime(cls, v):
        """Конвертирует временную метку в datetime."""
        if v is None:
            return None
        return timestamp_to_datetime(v)
    
    @validator('position_idx', pre=True)
    def validate_position_idx(cls, v):
        """Нормализует индекс позиции."""
        if isinstance(v, str) and v.isdigit():
            v = int(v)
        
        if isinstance(v, int) and v in [0, 1, 2]:
            return PositionIdx(v)
        
        return v
    
    @validator('margin_mode', pre=True)
    def validate_margin_mode(cls, v):
        """Нормализует режим маржи."""
        if isinstance(v, str):
            v_lower = v.lower()
            
            if v_lower in ('isolated', 'iso'):
                return MarginMode.ISOLATED
            elif v_lower in ('cross', 'cx'):
                return MarginMode.CROSS
        return v
    
    @validator('status', pre=True)
    def validate_status(cls, v):
        """Нормализует статус позиции."""
        if isinstance(v, str):
            status_map = {
                "none": PositionStatus.NONE,
                "open": PositionStatus.OPEN,
                "closed": PositionStatus.CLOSED,
                "liquidating": PositionStatus.LIQUIDATING,
                "liquidated": PositionStatus.LIQUIDATED,
                "normal": PositionStatus.NORMAL,
                "liqidation": PositionStatus.LIQIDATION,
                "liq": PositionStatus.LIQIDATION,
                "adl": PositionStatus.ADL,
                "auto-deleveraging": PositionStatus.ADL,
                "partially_closed": PositionStatus.PARTIALLY_CLOSED,
                "partiallyclosed": PositionStatus.PARTIALLY_CLOSED
            }
            
            v_lower = v.lower()
            if v_lower in status_map:
                return status_map[v_lower]
        return v
    
    @validator('side', pre=True)
    def validate_side(cls, v):
        """Определяет сторону из размера позиции, если она не указана."""
        if v is None:
            return None
            
        if isinstance(v, str):
            v_lower = v.lower()
            
            if v_lower in ('buy', 'b', 'long'):
                return OrderSide.BUY
            elif v_lower in ('sell', 's', 'short'):
                return OrderSide.SELL
        return v
    
    @classmethod
    def from_bybit_response(cls, data: Dict[str, Any]) -> 'PositionInfo':
        """
        Создает экземпляр PositionInfo из ответа API Bybit.
        
        Args:
            data: Словарь с данными от Bybit API
            
        Returns:
            Экземпляр PositionInfo
        """
        # Bybit возвращает разные форматы в зависимости от эндпоинта
        
        symbol = data.get("symbol")
        category = data.get("category", "linear")
        
        # Определяем сторону позиции из размера
        size = safe_decimal(data.get("size", data.get("positionAmt", 0)))
        side = data.get("side", None)
        
        if side is None and size != 0:
            side = OrderSide.BUY if size > 0 else OrderSide.SELL
            
        # Размер всегда положительный в модели
        size = abs(size)
            
        # Определяем временные метки
        created_time = timestamp_to_datetime(data.get("createdTime", data.get("created_time")))
        updated_time = timestamp_to_datetime(data.get("updatedTime", data.get("updated_time", data.get("time"))))
        
        # Используем текущее время для timestamp
        timestamp = updated_time or datetime.now()
        
        # Преобразуем поля в нужный формат
        return cls(
            timestamp=timestamp,  # Для BaseTradingModel
            symbol=symbol,
            exchange="bybit",
            
            # Базовые параметры позиции
            position_idx=data.get("positionIdx", data.get("position_idx", 0)),
            side=side,
            size=size,
            
            # Цены
            entry_price=data.get("entryPrice", data.get("entry_price", 0)),
            market_price=data.get("markPrice", data.get("market_price", data.get("mark_price", 0))),
            liq_price=data.get("liqPrice", data.get("liq_price")),
            bust_price=data.get("bustPrice", data.get("bust_price")),
            
            # Маржа и PnL
            position_value=data.get("positionValue", data.get("position_value", 0)),
            position_margin=data.get("positionMargin", data.get("position_margin", 0)),
            realised_pnl=data.get("realisedPnl", data.get("realised_pnl", data.get("realised_profit", 0))),
            unrealised_pnl=data.get("unrealisedPnl", data.get("unrealised_pnl", data.get("unrealised_profit", 0))),
            
            # Параметры риска
            leverage=data.get("leverage", 1),
            margin_mode=data.get("marginMode", data.get("margin_mode", "isolated")),
            stop_loss=data.get("stopLoss", data.get("stop_loss")),
            take_profit=data.get("takeProfit", data.get("take_profit")),
            trailing_stop=data.get("trailingStop", data.get("trailing_stop")),
            
            # Статус
            status=data.get("positionStatus", data.get("position_status", "Normal")),
            auto_add_margin=data.get("autoAddMargin", data.get("auto_add_margin", False)),
            adl_rank=data.get("adlRank", data.get("adl_rank")),
            
            # Дополнительные параметры
            order_margin=data.get("orderMargin", data.get("order_margin")),
            
            # Bybit-специфичные поля
            category=category,
            created_time=created_time,
            updated_time=updated_time
        )
    
    @classmethod
    def from_bybit_ws(cls, data: Dict[str, Any]) -> 'PositionInfo':
        """
        Создает экземпляр PositionInfo из данных WebSocket API Bybit.
        
        Args:
            data: Словарь с данными от Bybit WebSocket
            
        Returns:
            Экземпляр PositionInfo
        """
        # Извлекаем данные из сообщения WebSocket
        item = data.get("data", data)
        
        # WebSocket сообщения о позициях в Bybit имеют другую структуру
        if isinstance(item, list) and len(item) > 0:
            item = item[0]
            
        return cls.from_bybit_response(item)
    
    def is_long(self) -> bool:
        """Возвращает True, если позиция длинная (Buy)."""
        return self.side == OrderSide.BUY
    
    def is_short(self) -> bool:
        """Возвращает True, если позиция короткая (Sell)."""
        return self.side == OrderSide.SELL
    
    def is_empty(self) -> bool:
        """Возвращает True, если позиция пуста (размер = 0)."""
        return self.size == 0
    
    def is_open(self) -> bool:
        """Возвращает True, если позиция открыта."""
        return self.status in [PositionStatus.OPEN, PositionStatus.NORMAL] and self.size > 0
    
    def is_isolated(self) -> bool:
        """Возвращает True, если используется изолированная маржа."""
        return self.margin_mode == MarginMode.ISOLATED
    
    def is_cross(self) -> bool:
        """Возвращает True, если используется кросс-маржа."""
        return self.margin_mode == MarginMode.CROSS
    
    def is_in_profit(self) -> bool:
        """Возвращает True, если позиция в прибыли."""
        return self.unrealised_pnl > 0
    
    def is_in_loss(self) -> bool:
        """Возвращает True, если позиция в убытке."""
        return self.unrealised_pnl < 0
    
    def total_pnl(self) -> Decimal:
        """Возвращает общий P&L (реализованный + нереализованный)."""
        return self.realised_pnl + self.unrealised_pnl
    
    def value(self) -> Decimal:
        """Возвращает текущую стоимость позиции (size * market_price)."""
        return self.size * self.market_price
    
    def liquidation_price_change(self) -> Decimal:
        """Возвращает процентное расстояние до ликвидационной цены."""
        if not self.liq_price or self.market_price == 0 or self.size == 0:
            return Decimal('0')
            
        if self.is_long():
            return ((self.market_price - self.liq_price) / self.market_price) * Decimal('100')
        else:
            return ((self.liq_price - self.market_price) / self.market_price) * Decimal('100')
    
    def pnl_percent(self) -> Decimal:
        """Возвращает процентный P&L от стоимости позиции."""
        if self.position_value == 0:
            return Decimal('0')
            
        return (self.unrealised_pnl / self.position_value) * Decimal('100')
    
    def margin_ratio(self) -> Decimal:
        """Возвращает отношение маржи к стоимости позиции."""
        if self.position_value == 0:
            return Decimal('0')
            
        return (self.position_margin / self.position_value) * Decimal('100') 
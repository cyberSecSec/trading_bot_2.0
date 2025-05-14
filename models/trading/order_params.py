from decimal import Decimal
from enum import Enum
from typing import Dict, Any, List, Optional, Union

from pydantic import Field, validator

from ..base import BaseTradingModel
from ..utils.converters import safe_decimal

class OrderSide(str, Enum):
    """Сторона ордера."""
    BUY = "Buy"
    SELL = "Sell"

class OrderType(str, Enum):
    """Тип ордера."""
    LIMIT = "Limit"
    MARKET = "Market"
    STOP = "Stop"
    STOP_MARKET = "StopMarket"
    TAKE_PROFIT = "TakeProfit"
    TAKE_PROFIT_MARKET = "TakeProfitMarket"
    TRAILING_STOP_MARKET = "TrailingStopMarket"

class TimeInForce(str, Enum):
    """Условие срока действия ордера."""
    GTC = "GoodTillCancel"  # Действителен до отмены
    IOC = "ImmediateOrCancel"  # Исполнить немедленно или отменить
    FOK = "FillOrKill"  # Исполнить полностью или отменить
    PO = "PostOnly"  # Только как лимитный ордер

class TriggerBy(str, Enum):
    """Тип цены для активации стоп-ордеров."""
    LAST_PRICE = "LastPrice"  # Последняя цена
    INDEX_PRICE = "IndexPrice"  # Индексная цена
    MARK_PRICE = "MarkPrice"  # Цена маркировки

class PositionIdx(int, Enum):
    """Индекс позиции."""
    ONE_WAY = 0  # Одностороння позиция
    HEDGE_BUY = 1  # Хеджирование - длинная позиция
    HEDGE_SELL = 2  # Хеджирование - короткая позиция

class OrderParams(BaseTradingModel):
    """
    Модель параметров для создания ордера.
    
    Эта модель используется для формирования параметров при создании ордеров на бирже Bybit.
    """
    
    side: OrderSide = Field(..., description="Сторона ордера (Buy/Sell)")
    order_type: OrderType = Field(..., description="Тип ордера")
    qty: Decimal = Field(..., description="Количество контрактов/токенов")
    
    # Параметры, необходимые для определенных типов ордеров
    price: Optional[Decimal] = Field(None, description="Цена для лимитных ордеров")
    stop_loss: Optional[Decimal] = Field(None, description="Цена стоп-лосс")
    take_profit: Optional[Decimal] = Field(None, description="Цена тейк-профит")
    
    # Дополнительные параметры
    time_in_force: TimeInForce = Field(default=TimeInForce.GTC, description="Условие срока действия ордера")
    reduce_only: bool = Field(default=False, description="Только для уменьшения позиции")
    close_on_trigger: bool = Field(default=False, description="Закрыть позицию при срабатывании")
    position_idx: Optional[PositionIdx] = Field(None, description="Индекс позиции для хеджирования")
    
    # Параметры для стоп-ордеров
    trigger_price: Optional[Decimal] = Field(None, description="Цена активации для стоп-ордеров")
    trigger_by: Optional[TriggerBy] = Field(None, description="Тип цены для активации стоп-ордеров")
    
    # Параметры для трейлинг-стоп ордеров
    trailing_stop: Optional[Decimal] = Field(None, description="Отставание цены для трейлинг-стоп ордеров")
    
    # Идентификаторы и теги
    order_link_id: Optional[str] = Field(None, description="Клиентский ID ордера")
    take_profit_limit_price: Optional[Decimal] = Field(None, description="Лимитная цена для тейк-профит ордеров")
    stop_loss_limit_price: Optional[Decimal] = Field(None, description="Лимитная цена для стоп-лосс ордеров")
    
    # Параметры для Bybit конкретно
    category: str = Field("linear", description="Категория торгового инструмента")
    
    @validator('qty', 'price', 'stop_loss', 'take_profit', 'trigger_price', 
               'trailing_stop', 'take_profit_limit_price', 'stop_loss_limit_price', pre=True)
    def validate_decimal(cls, v):
        """Конвертирует строковые или числовые значения в Decimal."""
        return safe_decimal(v)
    
    def to_bybit_request(self) -> Dict[str, Any]:
        """
        Преобразует параметры ордера в формат для запроса к API Bybit.
        
        Returns:
            Словарь с параметрами для API Bybit
        """
        # Базовые параметры
        params = {
            "symbol": self.symbol,
            "side": self.side.value,
            "orderType": self.order_type.value,
            "qty": str(self.qty),
            "timeInForce": self.time_in_force.value,
            "category": self.category
        }
        
        # Добавляем цену для лимитных ордеров
        if self.price is not None:
            params["price"] = str(self.price)
        
        # Добавляем опциональные параметры
        if self.reduce_only:
            params["reduceOnly"] = self.reduce_only
        
        if self.close_on_trigger:
            params["closeOnTrigger"] = self.close_on_trigger
        
        if self.position_idx is not None:
            params["positionIdx"] = self.position_idx.value
        
        # Параметры для стоп-ордеров
        if self.trigger_price is not None:
            params["triggerPrice"] = str(self.trigger_price)
        
        if self.trigger_by is not None:
            params["triggerBy"] = self.trigger_by.value
        
        # Параметры для трейлинг-стоп ордеров
        if self.trailing_stop is not None:
            params["trailingStop"] = str(self.trailing_stop)
        
        # Стоп-лосс и тейк-профит
        if self.stop_loss is not None:
            params["stopLoss"] = str(self.stop_loss)
        
        if self.take_profit is not None:
            params["takeProfit"] = str(self.take_profit)
        
        # Лимитные цены для SL/TP
        if self.stop_loss_limit_price is not None:
            params["slLimitPrice"] = str(self.stop_loss_limit_price)
        
        if self.take_profit_limit_price is not None:
            params["tpLimitPrice"] = str(self.take_profit_limit_price)
        
        # Клиентский ID ордера
        if self.order_link_id is not None:
            params["orderLinkId"] = self.order_link_id
        
        return params
    
    @classmethod
    def market_order(cls, symbol: str, side: Union[OrderSide, str], qty: Decimal, **kwargs) -> 'OrderParams':
        """
        Создает параметры для рыночного ордера.
        
        Args:
            symbol: Торговый символ
            side: Сторона ордера (Buy/Sell)
            qty: Количество контрактов/токенов
            **kwargs: Дополнительные параметры
            
        Returns:
            Экземпляр OrderParams для рыночного ордера
        """
        if isinstance(side, str):
            side = OrderSide(side)
        
        return cls(
            symbol=symbol,
            side=side,
            order_type=OrderType.MARKET,
            qty=qty,
            time_in_force=TimeInForce.IOC,  # Для рыночных ордеров используем IOC
            **kwargs
        )
    
    @classmethod
    def limit_order(cls, symbol: str, side: Union[OrderSide, str], qty: Decimal, 
                    price: Decimal, **kwargs) -> 'OrderParams':
        """
        Создает параметры для лимитного ордера.
        
        Args:
            symbol: Торговый символ
            side: Сторона ордера (Buy/Sell)
            qty: Количество контрактов/токенов
            price: Цена лимитного ордера
            **kwargs: Дополнительные параметры
            
        Returns:
            Экземпляр OrderParams для лимитного ордера
        """
        if isinstance(side, str):
            side = OrderSide(side)
        
        return cls(
            symbol=symbol,
            side=side,
            order_type=OrderType.LIMIT,
            qty=qty,
            price=price,
            **kwargs
        )
    
    @classmethod
    def stop_order(cls, symbol: str, side: Union[OrderSide, str], qty: Decimal, 
                   trigger_price: Decimal, **kwargs) -> 'OrderParams':
        """
        Создает параметры для стоп-ордера.
        
        Args:
            symbol: Торговый символ
            side: Сторона ордера (Buy/Sell)
            qty: Количество контрактов/токенов
            trigger_price: Цена активации стоп-ордера
            **kwargs: Дополнительные параметры
            
        Returns:
            Экземпляр OrderParams для стоп-ордера
        """
        if isinstance(side, str):
            side = OrderSide(side)
        
        # Определяем тип ордера в зависимости от наличия цены
        order_type = OrderType.STOP_MARKET
        if 'price' in kwargs:
            order_type = OrderType.STOP
        
        params = {
            "symbol": symbol,
            "side": side,
            "order_type": order_type,
            "qty": qty,
            "trigger_price": trigger_price,
            "trigger_by": kwargs.pop("trigger_by", TriggerBy.LAST_PRICE)
        }
        
        params.update(kwargs)
        
        return cls(**params) 
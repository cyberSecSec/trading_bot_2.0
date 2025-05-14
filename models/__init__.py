"""
Модуль моделей данных для VANTA Trading APIs & Exchange.

Включает базовые классы и модели для рыночных данных и торговых операций.
"""

from .base import BaseDataModel, BaseMarketDataModel, BaseTradingModel
from .market_data import KlineData, KlineInterval, OrderBookData, OrderBookLevel, TradeData, TradeSide, LiquidationData, LiquidationSide, OpenInterestData
from .trading import (
    OrderParams, OrderSide, OrderType, TimeInForce, TriggerBy, PositionIdx,
    OrderInfo, OrderStatus,
    ExecutionInfo, LiquidityType,
    PositionInfo, PositionStatus, MarginMode
)

__version__ = "0.1.0" 
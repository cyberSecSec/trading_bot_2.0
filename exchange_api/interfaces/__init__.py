"""
Interfaces-модуль, определяющий контракты для взаимодействия с другими модулями.

Включает интерфейсы для рыночных данных и торговых операций.
""" 

from .market_data import (
    IMarketDataProvider,
    IMarketDataRestProvider,
    IMarketDataStreamProvider
)

from .trade_executor import (
    ITradeExecutor, 
    ITradeRestExecutor,
    ITradeStreamExecutor
)

__all__ = [
    'IMarketDataProvider',
    'IMarketDataRestProvider',
    'IMarketDataStreamProvider',
    'ITradeExecutor',
    'ITradeRestExecutor',
    'ITradeStreamExecutor'
] 
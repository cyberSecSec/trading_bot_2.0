"""
Модуль с определениями эндпоинтов API Bybit.

Содержит константы с путями к эндпоинтам REST API и WebSocket каналам
для различных типов данных в Bybit API v5.
"""
from typing import Dict, Any


# Базовый путь API v5
API_V5_BASE = "/v5"

# REST API эндпоинты для рыночных данных
class MarketDataEndpoints:
    """Эндпоинты для получения рыночных данных."""
    
    # OHLCV данные (свечи)
    KLINE = f"{API_V5_BASE}/market/kline"
    
    # Стакан ордеров
    ORDERBOOK = f"{API_V5_BASE}/market/orderbook"
    
    # Последние сделки
    RECENT_TRADES = f"{API_V5_BASE}/market/recent-trade"
    
    # Тикеры (быстрая информация о рынке)
    TICKERS = f"{API_V5_BASE}/market/tickers"
    
    # Открытый интерес
    OPEN_INTEREST = f"{API_V5_BASE}/market/open-interest"
    
    # История открытого интереса
    OPEN_INTEREST_HISTORY = f"{API_V5_BASE}/market/open-interest-history"
    
    # Инструменты (информация о торговых парах)
    INSTRUMENTS_INFO = f"{API_V5_BASE}/market/instruments-info"
    
    # Время сервера
    TIME = f"{API_V5_BASE}/market/time"


# REST API эндпоинты для торговых операций
class TradeEndpoints:
    """Эндпоинты для торговых операций."""
    
    # Создание ордера
    CREATE_ORDER = f"{API_V5_BASE}/order/create"
    
    # Аммендинг (изменение) ордера
    AMEND_ORDER = f"{API_V5_BASE}/order/amend"
    
    # Отмена ордера
    CANCEL_ORDER = f"{API_V5_BASE}/order/cancel"
    
    # Отмена всех ордеров
    CANCEL_ALL_ORDERS = f"{API_V5_BASE}/order/cancel-all"
    
    # Информация об ордере в реальном времени
    ORDER_REALTIME = f"{API_V5_BASE}/order/realtime"
    
    # История ордеров
    ORDER_HISTORY = f"{API_V5_BASE}/order/history"
    
    # Создание условного ордера
    CREATE_CONDITIONAL_ORDER = f"{API_V5_BASE}/order/create-conditional"
    
    # Отмена условного ордера
    CANCEL_CONDITIONAL_ORDER = f"{API_V5_BASE}/order/cancel-conditional"
    
    # История исполнения ордеров
    EXECUTION_HISTORY = f"{API_V5_BASE}/execution/list"


# REST API эндпоинты для управления позициями
class PositionEndpoints:
    """Эндпоинты для управления позициями."""
    
    # Список позиций
    POSITION_LIST = f"{API_V5_BASE}/position/list"
    
    # Установка режима позиций (single/hedge)
    SET_POSITION_MODE = f"{API_V5_BASE}/position/switch-mode"
    
    # Установка кредитного плеча
    SET_LEVERAGE = f"{API_V5_BASE}/position/set-leverage"
    
    # Установка маржи
    SET_MARGIN = f"{API_V5_BASE}/position/add-margin"
    
    # Установка режима маржи (isolated/cross)
    SET_MARGIN_MODE = f"{API_V5_BASE}/position/switch-isolated"
    
    # Установка стоп-лосса и тейк-профита
    SET_STOP_LOSS_TAKE_PROFIT = f"{API_V5_BASE}/position/trading-stop"
    
    # Установка trailing stop
    SET_TRAILING_STOP = f"{API_V5_BASE}/position/set-tpsl-mode"


# REST API эндпоинты для управления аккаунтом
class AccountEndpoints:
    """Эндпоинты для управления аккаунтом."""
    
    # Баланс кошелька
    WALLET_BALANCE = f"{API_V5_BASE}/account/wallet-balance"
    
    # Журнал транзакций
    TRANSACTION_LOG = f"{API_V5_BASE}/account/transaction-log"
    
    # Информация об аккаунте
    ACCOUNT_INFO = f"{API_V5_BASE}/account/info"
    
    # Настройки аккаунта
    ACCOUNT_SETTING = f"{API_V5_BASE}/account/set-margin-mode"
    
    # Безопасные средства
    COLLATERAL_INFO = f"{API_V5_BASE}/account/collateral-info"
    
    # Лимиты переводов
    TRANSFER_LIMITS = f"{API_V5_BASE}/account/transfer-limit"
    
    # Внутренний перевод между счетами
    INTERNAL_TRANSFER = f"{API_V5_BASE}/asset/internal-transfer"


# WebSocket каналы для публичных данных
class PublicWebSocketChannels:
    """Каналы WebSocket для публичных данных."""
    
    # Формат канала для OHLCV данных: kline.{interval}.{symbol}
    # Например: kline.1.BTCUSDT
    KLINE = "kline.{interval}.{symbol}"
    
    # Формат канала для стакана ордеров: orderbook.{depth}.{symbol}
    # Например: orderbook.50.BTCUSDT
    ORDERBOOK = "orderbook.{depth}.{symbol}"
    
    # Формат канала для сделок: publicTrade.{symbol}
    # Например: publicTrade.BTCUSDT
    TRADE = "publicTrade.{symbol}"
    
    # Формат канала для тикеров: tickers.{symbol}
    # Например: tickers.BTCUSDT
    TICKERS = "tickers.{symbol}"
    
    # Формат канала для ликвидаций: liquidation.{symbol}
    # Например: liquidation.BTCUSDT
    LIQUIDATION = "liquidation.{symbol}"
    
    # Формат канала для открытого интереса: openInterest.{symbol}
    # Например: openInterest.BTCUSDT
    OPEN_INTEREST = "openInterest.{symbol}"


# WebSocket каналы для приватных данных
class PrivateWebSocketChannels:
    """Каналы WebSocket для приватных данных."""
    
    # Канал для ордеров
    ORDER = "order"
    
    # Канал для позиций
    POSITION = "position"
    
    # Канал для исполнений
    EXECUTION = "execution"
    
    # Канал для кошелька
    WALLET = "wallet"


def format_public_channel(channel_template: str, **kwargs) -> str:
    """
    Форматирует шаблон публичного канала, подставляя нужные параметры.
    
    Args:
        channel_template: Шаблон канала с плейсхолдерами
        **kwargs: Параметры для подстановки в шаблон
        
    Returns:
        str: Отформатированная строка канала
    """
    return channel_template.format(**kwargs) 
"""
Модуль с константами для работы с API Bybit.

Содержит URL-адреса API, WebSocket URL-адреса, таймфреймы,
типы инструментов и другие константы, необходимые для работы с Bybit API.
"""
from enum import Enum, auto
from typing import Dict, List, Optional, Set


# URL-адреса API
API_URL_MAINNET = "https://api.bybit.com"
API_URL_TESTNET = "https://api-testnet.bybit.com"

# URL-адреса WebSocket
WS_URL_MAINNET = "wss://stream.bybit.com"
WS_URL_TESTNET = "wss://stream-testnet.bybit.com"

# Префикс для переменных окружения
ENV_PREFIX = "VANTA_BYBIT_"

# Категории инструментов
CATEGORY_SPOT = "spot"       # Спот
CATEGORY_LINEAR = "linear"   # Линейные контракты
CATEGORY_INVERSE = "inverse" # Инверсные контракты
CATEGORY_OPTION = "option"   # Опционы

# Доступные категории инструментов
VALID_CATEGORIES = {CATEGORY_SPOT, CATEGORY_LINEAR, CATEGORY_INVERSE, CATEGORY_OPTION}

# Версия API
API_VERSION = "v5"

# Базовый путь API v5
API_BASE_PATH = f"/{API_VERSION}"


class OrderType(str, Enum):
    """Типы ордеров, поддерживаемые Bybit."""
    LIMIT = "Limit"            # Лимитный ордер
    MARKET = "Market"          # Рыночный ордер
    LIMIT_MAKER = "Limit_maker" # Лимитный ордер типа "мейкер"
    CONDITIONAL = "Conditional" # Условный ордер


class OrderSide(str, Enum):
    """Стороны ордера."""
    BUY = "Buy"     # Покупка
    SELL = "Sell"   # Продажа


class TimeInForce(str, Enum):
    """Время действия ордера."""
    GTC = "GTC"   # Good Till Cancel - действует до отмены
    IOC = "IOC"   # Immediate Or Cancel - исполнить немедленно или отменить
    FOK = "FOK"   # Fill Or Kill - исполнить полностью или отменить
    PO = "PO"     # Post Only - только как мейкер


class PositionSide(str, Enum):
    """Стороны позиции."""
    BOTH = "Both"    # Обе стороны (режим одной позиции)
    LONG = "Long"    # Длинная позиция
    SHORT = "Short"  # Короткая позиция


class PositionMode(str, Enum):
    """Режимы позиции."""
    BOTH_SIDES = "BothSides"    # Режим хеджирования (отдельные позиции long и short)
    MERGE_SINGLE = "MergedSingle"  # Режим одной позиции (объединенные long и short)


class MarginMode(str, Enum):
    """Режимы маржи."""
    CROSS = "REGULAR_MARGIN"    # Кросс-маржа (shared)
    ISOLATED = "ISOLATED_MARGIN"  # Изолированная маржа


class TriggerDirection(str, Enum):
    """Направления срабатывания условного ордера."""
    RISE = "1"     # При повышении цены до указанного уровня
    FALL = "2"     # При снижении цены до указанного уровня


class TriggerPriceType(str, Enum):
    """Типы триггерных цен для условных ордеров."""
    LAST_PRICE = "LastPrice"        # Последняя цена
    INDEX_PRICE = "IndexPrice"      # Индексная цена
    MARK_PRICE = "MarkPrice"        # Расчетная (mark) цена
    LAST_PRICE_ASK = "LastPriceAsk" # Последняя цена аска
    LAST_PRICE_BID = "LastPriceBid" # Последняя цена бида


class Timeframe(str, Enum):
    """Таймфреймы для OHLCV данных."""
    M1 = "1"        # 1 минута
    M3 = "3"        # 3 минуты
    M5 = "5"        # 5 минут
    M15 = "15"      # 15 минут
    M30 = "30"      # 30 минут
    H1 = "60"       # 1 час
    H2 = "120"      # 2 часа
    H4 = "240"      # 4 часа
    H6 = "360"      # 6 часов
    H12 = "720"     # 12 часов
    D1 = "D"        # 1 день
    W1 = "W"        # 1 неделя
    M1_MONTH = "M"  # 1 месяц


# Глубина стакана ордеров
class OrderBookDepth(str, Enum):
    """Доступные значения глубины стакана ордеров."""
    DEPTH_1 = "1"      # 1 уровень
    DEPTH_50 = "50"    # 50 уровней
    DEPTH_200 = "200"  # 200 уровней
    DEPTH_500 = "500"  # 500 уровней


# Словарь кодов ошибок и их описаний
ERROR_CODES = {
    # Общие ошибки
    "0": "Success",
    "10001": "Parameter error",
    "10002": "Рисунки parameter error",
    "10003": "Required parameter cannot be null",
    "10004": "Invalid request",
    "10005": "Too many visits",
    "10006": "Signature verification failed",
    "10007": "IP rate limit exceeded",
    "10010": "Unknown system exception",
    "10016": "Service is upgrading, please try again later",
    "10017": "Request path not found",
    "10018": "IP is blocked, please contact customer service",
    "10020": "Request timeout, please try again later",
    "10021": "Timestamp is in seconds", 
    
    # Ошибки аутентификации и прав доступа
    "110001": "Permission denied for current API key",
    "110002": "apikey does not exist",
    "110003": "This API key is disabled",
    "110004": "This API key is expired",
    
    # Ошибки торговых операций
    "130006": "Symbol does not exist",
    "130021": "Order does not exist",
    "130074": "The position mode cannot be changed as there are existing positions",
    "130150": "Invalid leverage",
    "130182": "Position does not exist",
}


# WebSocket каналы
class WebSocketChannel(str, Enum):
    """Каналы для подписки через WebSocket."""
    # Публичные каналы
    ORDERBOOK = "orderbook"            # Стакан ордеров
    TRADE = "publicTrade"              # Публичные сделки
    TICKERS = "tickers"                # Тикеры
    KLINE = "kline"                    # OHLCV свечи
    LIQUIDATION = "liquidation"        # Ликвидации
    OPEN_INTEREST = "openInterest"     # Открытый интерес
    # Приватные каналы
    POSITION = "position"              # Позиции
    EXECUTION = "execution"            # Исполнение ордеров
    ORDER = "order"                    # Ордеры
    WALLET = "wallet"                  # Кошелек 
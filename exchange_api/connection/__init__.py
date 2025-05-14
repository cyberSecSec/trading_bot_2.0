"""
Пакет для управления соединениями с API криптовалютных бирж.

Предоставляет компоненты для работы с HTTP и WebSocket соединениями,
а также механизмы управления переподключениями.
"""

from exchange_api.connection.connection_manager import ConnectionManager, RateLimiter
from exchange_api.connection.websocket_manager import WebSocketManager, WebSocketState
from exchange_api.connection.reconnection_handler import (
    ReconnectionHandler,
    should_retry_on_exception,
    get_retry_delay,
    create_exponential_backoff_handler
)

__all__ = [
    # ConnectionManager
    'ConnectionManager',
    'RateLimiter',
    
    # WebSocketManager
    'WebSocketManager',
    'WebSocketState',
    
    # ReconnectionHandler
    'ReconnectionHandler',
    'should_retry_on_exception',
    'get_retry_delay',
    'create_exponential_backoff_handler'
] 
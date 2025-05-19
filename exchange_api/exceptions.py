"""
Модуль, определяющий иерархию исключений для модуля Trading APIs & Exchange.

Содержит специализированные исключения для различных типов ошибок и ситуаций.
"""
from typing import Optional, Dict, Any, List, Union


class VantaTradingError(Exception):
    """
    Базовый класс для всех исключений модуля Trading APIs & Exchange.
    
    Attributes:
        message: Сообщение об ошибке
        code: Код ошибки (если применимо)
        request_info: Информация о запросе, который привел к ошибке
        response_info: Информация об ответе, который привел к ошибке
        exchange: Название биржи, с которой связана ошибка
    """
    def __init__(
        self, 
        message: str, 
        code: Optional[int] = None,
        request_info: Optional[Dict[str, Any]] = None,
        response_info: Optional[Dict[str, Any]] = None,
        exchange: Optional[str] = None
    ):
        """
        Инициализирует исключение с заданными параметрами.
        
        Args:
            message: Сообщение об ошибке
            code: Код ошибки (если применимо)
            request_info: Информация о запросе, который привел к ошибке
            response_info: Информация об ответе, который привел к ошибке
            exchange: Название биржи, с которой связана ошибка
        """
        self.message = message
        self.code = code
        self.request_info = request_info or {}
        self.response_info = response_info or {}
        self.exchange = exchange
        super().__init__(self.message)
    
    def __str__(self) -> str:
        """
        Возвращает строковое представление исключения.
        
        Returns:
            str: Строковое представление исключения
        """
        result = f"{self.message}"
        if self.code is not None:
            result += f" (code: {self.code})"
        if self.exchange:
            result += f" [exchange: {self.exchange}]"
        return result
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Преобразует исключение в словарь для логирования или отладки.
        
        Returns:
            Dict[str, Any]: Словарь с информацией об исключении
        """
        result = {
            "error_type": self.__class__.__name__,
            "message": self.message
        }
        
        if self.code is not None:
            result["code"] = self.code
            
        if self.exchange:
            result["exchange"] = self.exchange
            
        if self.request_info:
            result["request_info"] = self.request_info
            
        if self.response_info:
            result["response_info"] = self.response_info
            
        return result


class ConnectionError(VantaTradingError):
    """
    Исключение, вызываемое при ошибках соединения с биржей.
    
    Включает сетевые ошибки, таймауты, ошибки DNS и другие проблемы соединения.
    """
    def __init__(
        self, 
        message: str, 
        code: Optional[int] = None,
        request_info: Optional[Dict[str, Any]] = None,
        response_info: Optional[Dict[str, Any]] = None,
        exchange: Optional[str] = None,
        retry_after: Optional[float] = None
    ):
        """
        Инициализирует исключение с заданными параметрами.
        
        Args:
            message: Сообщение об ошибке
            code: Код ошибки (если применимо)
            request_info: Информация о запросе, который привел к ошибке
            response_info: Информация об ответе, который привел к ошибке
            exchange: Название биржи, с которой связана ошибка
            retry_after: Рекомендуемое время в секундах до повторного запроса
        """
        super().__init__(message, code, request_info, response_info, exchange)
        self.retry_after = retry_after
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Преобразует исключение в словарь с дополнительной информацией о retry_after.
        
        Returns:
            Dict[str, Any]: Словарь с информацией об исключении
        """
        result = super().to_dict()
        if self.retry_after is not None:
            result["retry_after"] = self.retry_after
        return result


class AuthenticationError(VantaTradingError):
    """
    Исключение, вызываемое при ошибках аутентификации.
    
    Включает ошибки API ключей, подписи запросов, истечения срока действия ключей и т.д.
    """
    pass


class RateLimitError(ConnectionError):
    """
    Исключение, вызываемое при превышении лимитов запросов к API.
    
    Наследуется от ConnectionError, так как обычно требует повторного соединения после задержки.
    """
    def __init__(
        self, 
        message: str, 
        code: Optional[int] = None,
        request_info: Optional[Dict[str, Any]] = None,
        response_info: Optional[Dict[str, Any]] = None,
        exchange: Optional[str] = None,
        retry_after: Optional[float] = None,
        limit_type: Optional[str] = None
    ):
        """
        Инициализирует исключение с заданными параметрами.
        
        Args:
            message: Сообщение об ошибке
            code: Код ошибки (если применимо)
            request_info: Информация о запросе, который привел к ошибке
            response_info: Информация об ответе, который привел к ошибке
            exchange: Название биржи, с которой связана ошибка
            retry_after: Рекомендуемое время в секундах до повторного запроса
            limit_type: Тип лимита, который был превышен (например, "IP", "API key", "weight")
        """
        super().__init__(message, code, request_info, response_info, exchange, retry_after)
        self.limit_type = limit_type
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Преобразует исключение в словарь с дополнительной информацией о limit_type.
        
        Returns:
            Dict[str, Any]: Словарь с информацией об исключении
        """
        result = super().to_dict()
        if self.limit_type:
            result["limit_type"] = self.limit_type
        return result


class ValidationError(VantaTradingError):
    """
    Исключение, вызываемое при ошибках валидации входных или выходных данных.
    
    Включает ошибки в параметрах запросов, неверные форматы данных и т.д.
    """
    def __init__(
        self, 
        message: str, 
        code: Optional[int] = None,
        request_info: Optional[Dict[str, Any]] = None,
        response_info: Optional[Dict[str, Any]] = None,
        exchange: Optional[str] = None,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        expected: Optional[Any] = None
    ):
        """
        Инициализирует исключение с заданными параметрами.
        
        Args:
            message: Сообщение об ошибке
            code: Код ошибки (если применимо)
            request_info: Информация о запросе, который привел к ошибке
            response_info: Информация об ответе, который привел к ошибке
            exchange: Название биржи, с которой связана ошибка
            field: Название поля, которое не прошло валидацию
            value: Значение, которое не прошло валидацию
            expected: Ожидаемое значение или формат
        """
        super().__init__(message, code, request_info, response_info, exchange)
        self.field = field
        self.value = value
        self.expected = expected
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Преобразует исключение в словарь с дополнительной информацией о валидации.
        
        Returns:
            Dict[str, Any]: Словарь с информацией об исключении
        """
        result = super().to_dict()
        if self.field:
            result["field"] = self.field
        if self.value is not None:
            result["value"] = str(self.value)
        if self.expected is not None:
            result["expected"] = str(self.expected)
        return result


class OrderError(VantaTradingError):
    """
    Исключение, вызываемое при ошибках, связанных с операциями ордеров.
    
    Включает ошибки создания, отмены, получения информации об ордерах.
    """
    def __init__(
        self, 
        message: str, 
        code: Optional[int] = None,
        request_info: Optional[Dict[str, Any]] = None,
        response_info: Optional[Dict[str, Any]] = None,
        exchange: Optional[str] = None,
        order_id: Optional[str] = None,
        symbol: Optional[str] = None
    ):
        """
        Инициализирует исключение с заданными параметрами.
        
        Args:
            message: Сообщение об ошибке
            code: Код ошибки (если применимо)
            request_info: Информация о запросе, который привел к ошибке
            response_info: Информация об ответе, который привел к ошибке
            exchange: Название биржи, с которой связана ошибка
            order_id: Идентификатор ордера
            symbol: Символ торговой пары
        """
        super().__init__(message, code, request_info, response_info, exchange)
        self.order_id = order_id
        self.symbol = symbol
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Преобразует исключение в словарь с дополнительной информацией об ордере.
        
        Returns:
            Dict[str, Any]: Словарь с информацией об исключении
        """
        result = super().to_dict()
        if self.order_id:
            result["order_id"] = self.order_id
        if self.symbol:
            result["symbol"] = self.symbol
        return result


class PositionError(VantaTradingError):
    """
    Исключение, вызываемое при ошибках, связанных с управлением позициями.
    
    Включает ошибки получения, изменения позиций, настройки плеча и маржи.
    """
    def __init__(
        self, 
        message: str, 
        code: Optional[int] = None,
        request_info: Optional[Dict[str, Any]] = None,
        response_info: Optional[Dict[str, Any]] = None,
        exchange: Optional[str] = None,
        symbol: Optional[str] = None,
        position_side: Optional[str] = None
    ):
        """
        Инициализирует исключение с заданными параметрами.
        
        Args:
            message: Сообщение об ошибке
            code: Код ошибки (если применимо)
            request_info: Информация о запросе, который привел к ошибке
            response_info: Информация об ответе, который привел к ошибке
            exchange: Название биржи, с которой связана ошибка
            symbol: Символ торговой пары
            position_side: Сторона позиции ("long", "short")
        """
        super().__init__(message, code, request_info, response_info, exchange)
        self.symbol = symbol
        self.position_side = position_side
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Преобразует исключение в словарь с дополнительной информацией о позиции.
        
        Returns:
            Dict[str, Any]: Словарь с информацией об исключении
        """
        result = super().to_dict()
        if self.symbol:
            result["symbol"] = self.symbol
        if self.position_side:
            result["position_side"] = self.position_side
        return result


class MarketDataError(VantaTradingError):
    """
    Исключение, вызываемое при ошибках получения рыночных данных.
    
    Включает ошибки запроса OHLCV данных, стакана ордеров, сделок и т.д.
    """
    def __init__(
        self, 
        message: str, 
        code: Optional[int] = None,
        request_info: Optional[Dict[str, Any]] = None,
        response_info: Optional[Dict[str, Any]] = None,
        exchange: Optional[str] = None,
        symbol: Optional[str] = None,
        data_type: Optional[str] = None
    ):
        """
        Инициализирует исключение с заданными параметрами.
        
        Args:
            message: Сообщение об ошибке
            code: Код ошибки (если применимо)
            request_info: Информация о запросе, который привел к ошибке
            response_info: Информация об ответе, который привел к ошибке
            exchange: Название биржи, с которой связана ошибка
            symbol: Символ торговой пары
            data_type: Тип рыночных данных ("klines", "orderbook", "trades", и т.д.)
        """
        super().__init__(message, code, request_info, response_info, exchange)
        self.symbol = symbol
        self.data_type = data_type
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Преобразует исключение в словарь с дополнительной информацией о рыночных данных.
        
        Returns:
            Dict[str, Any]: Словарь с информацией об исключении
        """
        result = super().to_dict()
        if self.symbol:
            result["symbol"] = self.symbol
        if self.data_type:
            result["data_type"] = self.data_type
        return result


class WebSocketError(VantaTradingError):
    """
    Исключение, вызываемое при ошибках WebSocket соединений.
    
    Включает ошибки установки соединения, подписки на каналы, разрывы соединения.
    """
    def __init__(
        self, 
        message: str, 
        code: Optional[int] = None,
        request_info: Optional[Dict[str, Any]] = None,
        response_info: Optional[Dict[str, Any]] = None,
        exchange: Optional[str] = None,
        channel: Optional[str] = None,
        should_reconnect: bool = True
    ):
        """
        Инициализирует исключение с заданными параметрами.
        
        Args:
            message: Сообщение об ошибке
            code: Код ошибки (если применимо)
            request_info: Информация о запросе, который привел к ошибке
            response_info: Информация об ответе, который привел к ошибке
            exchange: Название биржи, с которой связана ошибка
            channel: Название канала WebSocket
            should_reconnect: Нужно ли пытаться переподключиться
        """
        super().__init__(message, code, request_info, response_info, exchange)
        self.channel = channel
        self.should_reconnect = should_reconnect
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Преобразует исключение в словарь с дополнительной информацией о WebSocket.
        
        Returns:
            Dict[str, Any]: Словарь с информацией об исключении
        """
        result = super().to_dict()
        if self.channel:
            result["channel"] = self.channel
        result["should_reconnect"] = self.should_reconnect
        return result


class ConfigurationError(VantaTradingError):
    """
    Исключение, вызываемое при ошибках конфигурации компонентов.
    
    Включает отсутствующие или некорректные параметры конфигурации, ошибки загрузки и т.д.
    """
    def __init__(
        self, 
        message: str, 
        code: Optional[int] = None,
        request_info: Optional[Dict[str, Any]] = None,
        response_info: Optional[Dict[str, Any]] = None,
        exchange: Optional[str] = None,
        config_param: Optional[str] = None
    ):
        """
        Инициализирует исключение с заданными параметрами.
        
        Args:
            message: Сообщение об ошибке
            code: Код ошибки (если применимо)
            request_info: Информация о запросе, который привел к ошибке
            response_info: Информация об ответе, который привел к ошибке
            exchange: Название биржи, с которой связана ошибка
            config_param: Имя параметра конфигурации, с которым связана ошибка
        """
        super().__init__(message, code, request_info, response_info, exchange)
        self.config_param = config_param
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Преобразует исключение в словарь с дополнительной информацией о конфигурации.
        
        Returns:
            Dict[str, Any]: Словарь с информацией об исключении
        """
        result = super().to_dict()
        if self.config_param:
            result["config_param"] = self.config_param
        return result


class ExchangeError(VantaTradingError):
    """
    Исключение, вызываемое при ошибках, связанных с биржей.
    
    Включает общие ошибки биржи, проблемы с соединением с биржей и т.д.
    """
    pass


class VantaAPIError(VantaTradingError):
    """
    Исключение, вызываемое при ошибках взаимодействия с API биржи.
    
    Включает общие API ошибки, проблемы с форматом ответа и т.д.
    """
    def __init__(
        self, 
        message: str, 
        code: Optional[int] = None,
        request_info: Optional[Dict[str, Any]] = None,
        response_info: Optional[Dict[str, Any]] = None,
        exchange: Optional[str] = None,
        original_exception: Optional[Exception] = None
    ):
        """
        Инициализирует исключение с заданными параметрами.
        
        Args:
            message: Сообщение об ошибке
            code: Код ошибки (если применимо)
            request_info: Информация о запросе, который привел к ошибке
            response_info: Информация об ответе, который привел к ошибке
            exchange: Название биржи, с которой связана ошибка
            original_exception: Исходное исключение, которое привело к этой ошибке
        """
        super().__init__(message, code, request_info, response_info, exchange)
        self.original_exception = original_exception
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Преобразует исключение в словарь с дополнительной информацией.
        
        Returns:
            Dict[str, Any]: Словарь с информацией об исключении
        """
        result = super().to_dict()
        if self.original_exception:
            result["original_exception"] = str(self.original_exception)
            result["original_exception_type"] = type(self.original_exception).__name__
        return result


class VantaRateLimitError(RateLimitError):
    """
    Исключение, вызываемое при превышении лимитов запросов к API биржи VANTA.
    
    Наследуется от RateLimitError и содержит дополнительную информацию о лимитах.
    """
    pass


class VantaWebSocketError(WebSocketError):
    """
    Исключение, вызываемое при ошибках WebSocket соединения с биржей VANTA.
    
    Наследуется от WebSocketError и содержит дополнительную информацию о канале.
    """
    pass


class UnexpectedError(VantaTradingError):
    """
    Исключение, вызываемое при неожиданных ошибках, не входящих в другие категории.
    
    Включает внутренние ошибки сервера, неожиданные форматы ответов и т.д.
    """
    def __init__(
        self, 
        message: str, 
        code: Optional[int] = None,
        request_info: Optional[Dict[str, Any]] = None,
        response_info: Optional[Dict[str, Any]] = None,
        exchange: Optional[str] = None,
        original_exception: Optional[Exception] = None
    ):
        """
        Инициализирует исключение с заданными параметрами.
        
        Args:
            message: Сообщение об ошибке
            code: Код ошибки (если применимо)
            request_info: Информация о запросе, который привел к ошибке
            response_info: Информация об ответе, который привел к ошибке
            exchange: Название биржи, с которой связана ошибка
            original_exception: Исходное исключение, которое вызвало эту ошибку
        """
        super().__init__(message, code, request_info, response_info, exchange)
        self.original_exception = original_exception
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Преобразует исключение в словарь с дополнительной информацией об исходном исключении.
        
        Returns:
            Dict[str, Any]: Словарь с информацией об исключении
        """
        result = super().to_dict()
        if self.original_exception:
            result["original_exception"] = {
                "type": type(self.original_exception).__name__,
                "message": str(self.original_exception)
            }
        return result 
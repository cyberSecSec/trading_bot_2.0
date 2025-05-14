"""
Модуль для управления WebSocket соединениями с Bybit API.

Расширяет базовый WebSocketManager, добавляя специфичную для Bybit
функциональность, включая формирование сообщений подписки и аутентификацию.
"""
import hashlib
import hmac
import json
import time
from typing import Dict, Any, Optional, Union, List, Callable, Awaitable, Set

from exchange_api.connection.websocket_manager import WebSocketManager
from exchange_api.exchanges.bybit.config import BybitClientConfig
from exchange_api.utils.logger import Logger
from exchange_api.exceptions import WebSocketError


# Получаем логгер
logger = Logger.get_logger()


class BybitWebSocketManager(WebSocketManager):
    """
    Менеджер WebSocket соединений для Bybit API.
    
    Расширяет базовый WebSocketManager, добавляя специфичную для Bybit
    функциональность, включая формирование сообщений подписки и аутентификацию.
    """
    
    def __init__(
        self,
        config: BybitClientConfig,
        ws_url: Optional[str] = None,
        on_message: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None,
        on_error: Optional[Callable[[Exception], Awaitable[None]]] = None,
        on_connect: Optional[Callable[[], Awaitable[None]]] = None,
        on_disconnect: Optional[Callable[[], Awaitable[None]]] = None,
        ping_interval: float = 20.0,
        ping_timeout: float = 10.0,
        close_timeout: float = 5.0
    ):
        """
        Инициализирует менеджер WebSocket соединений для Bybit.
        
        Args:
            config: Конфигурация клиента Bybit
            ws_url: URL для WebSocket соединения (если None, используется из конфигурации)
            on_message: Обратный вызов для обработки входящих сообщений
            on_error: Обратный вызов для обработки ошибок
            on_connect: Обратный вызов при успешном подключении
            on_disconnect: Обратный вызов при отключении
            ping_interval: Интервал отправки ping-сообщений в секундах
            ping_timeout: Таймаут ожидания pong-ответа в секундах
            close_timeout: Таймаут при закрытии соединения в секундах
        """
        # Определяем URL для WebSocket соединения, если не указан
        if not ws_url:
            # Формируем URL в зависимости от режима (testnet или mainnet)
            ws_url_base = config.connection.ws_url
            
            # URL может содержать плейсхолдер для категории, если нет - добавляем /v5/public
            if "{category}" in ws_url_base:
                ws_url = ws_url_base.replace("{category}", "spot")
            else:
                ws_url = ws_url_base.rstrip('/') + '/v5/public'
        
        super().__init__(
            config=config,
            ws_url=ws_url,
            on_message=on_message,
            on_error=on_error,
            on_connect=on_connect,
            on_disconnect=on_disconnect,
            ping_interval=ping_interval,
            ping_timeout=ping_timeout,
            close_timeout=close_timeout
        )
        
        # Сохраняем конфигурацию Bybit
        self.bybit_config = config
        
        # Идентификаторы для подписок (используется для сопоставления ответов)
        self._subscription_ids: Dict[str, int] = {}
        
        # Обратное отображение id -> канал
        self._id_to_channel: Dict[int, str] = {}
        
        # Счетчик для генерации уникальных ID
        self._id_counter = 1
        
        logger.debug(f"Создан BybitWebSocketManager с URL: {ws_url}")
    
    def _get_next_id(self) -> int:
        """
        Генерирует уникальный ID для запросов.
        
        Returns:
            int: Уникальный ID
        """
        current_id = self._id_counter
        self._id_counter += 1
        return current_id
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """
        Формирует заголовки аутентификации для WebSocket соединения.
        
        Для Bybit WebSocket не требуются заголовки аутентификации в момент подключения.
        Аутентификация выполняется через отдельное сообщение после установки соединения.
        
        Returns:
            Dict[str, str]: Пустой словарь заголовков
        """
        return {}
    
    async def _authenticate(self) -> None:
        """
        Аутентифицирует WebSocket соединение.
        
        Отправляет сообщение аутентификации, если есть API ключи.
        
        Raises:
            WebSocketError: Если аутентификация не удалась
        """
        # Проверяем, есть ли учетные данные
        if not hasattr(self.config, 'credentials'):
            logger.debug("Нет учетных данных для аутентификации WebSocket")
            return
        
        api_key = self.config.credentials.get_api_key()
        api_secret = self.config.credentials.get_api_secret()
        
        if not api_key or not api_secret:
            logger.debug("Отсутствуют API ключи для аутентификации WebSocket")
            return
        
        # Текущее время в миллисекундах
        timestamp = int(time.time() * 1000)
        
        # Формируем строку для подписи: timestamp + api_key
        to_sign = f"{timestamp}{api_key}"
        
        # Генерируем подпись с использованием HMAC SHA256
        signature = hmac.new(
            api_secret.encode('utf-8'),
            to_sign.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        # Формируем сообщение аутентификации
        auth_message = {
            "op": "auth",
            "args": [api_key, timestamp, signature]
        }
        
        # Отправляем сообщение аутентификации
        try:
            await self._send(auth_message)
            logger.debug("WebSocket аутентификация отправлена")
        except Exception as e:
            raise WebSocketError(
                message=f"Ошибка при аутентификации WebSocket: {str(e)}",
                exchange=self.exchange_name
            ) from e
    
    async def connect(self) -> None:
        """
        Устанавливает WebSocket соединение с сервером Bybit.
        
        Расширяет базовый метод, добавляя аутентификацию после подключения.
        
        Raises:
            ConnectionError: Если не удалось установить соединение
        """
        # Устанавливаем соединение с помощью базового метода
        await super().connect()
        
        # Если соединение успешно установлено, выполняем аутентификацию
        if self.is_connected:
            try:
                await self._authenticate()
            except Exception as e:
                logger.error(f"Ошибка при аутентификации Bybit WebSocket: {str(e)}")
                # Продолжаем работу даже в случае ошибки аутентификации,
                # так как можно использовать публичные каналы без аутентификации
    
    async def _handle_subscription_response(self, data: Dict[str, Any]) -> None:
        """
        Обрабатывает подтверждение подписки от сервера Bybit.
        
        Args:
            data: Данные от WebSocket сервера
        """
        # Проверяем, является ли сообщение ответом на подписку
        if "op" in data and data["op"] == "subscribe":
            # Если сообщение содержит success и success == true
            if "success" in data and data["success"]:
                # Получаем идентификатор запроса
                req_id = data.get("req_id")
                
                # Если есть req_id и он есть в таблице соответствия
                if req_id and req_id in self._id_to_channel:
                    channel = self._id_to_channel[req_id]
                    
                    # Переносим канал из ожидающих в активные подписки
                    if channel in self.pending_subscriptions:
                        self.pending_subscriptions.remove(channel)
                        self.subscriptions.add(channel)
                        logger.info(f"Подписка активирована: {channel}")
                    
                    # Удаляем запись из таблицы соответствия
                    del self._id_to_channel[req_id]
                    if channel in self._subscription_ids:
                        del self._subscription_ids[channel]
                    
                    # Если все ожидающие подписки обработаны, устанавливаем состояние готовности
                    if not self.pending_subscriptions and self.state != self.WebSocketState.READY:
                        self.state = self.WebSocketState.READY
                        self._ready_event.set()
                
                # Если нет req_id, но есть args - список каналов
                elif "args" in data and isinstance(data["args"], list):
                    for channel in data["args"]:
                        # Переносим канал из ожидающих в активные подписки
                        if channel in self.pending_subscriptions:
                            self.pending_subscriptions.remove(channel)
                            self.subscriptions.add(channel)
                            logger.info(f"Подписка активирована: {channel}")
                    
                    # Если все ожидающие подписки обработаны, устанавливаем состояние готовности
                    if not self.pending_subscriptions and self.state != self.WebSocketState.READY:
                        self.state = self.WebSocketState.READY
                        self._ready_event.set()
            
            # Если подписка не удалась
            elif "success" in data and not data["success"]:
                error_msg = data.get("ret_msg", "Неизвестная ошибка")
                req_id = data.get("req_id")
                
                # Получаем канал по идентификатору запроса
                channel = None
                if req_id and req_id in self._id_to_channel:
                    channel = self._id_to_channel[req_id]
                    
                    # Удаляем запись из таблицы соответствия
                    del self._id_to_channel[req_id]
                    if channel in self._subscription_ids:
                        del self._subscription_ids[channel]
                
                logger.error(f"Ошибка подписки на канал {channel}: {error_msg}")
                
                # Удаляем канал из ожидающих подписок
                if channel and channel in self.pending_subscriptions:
                    self.pending_subscriptions.remove(channel)
                
                # Если все ожидающие подписки обработаны, устанавливаем состояние готовности
                if not self.pending_subscriptions and self.state != self.WebSocketState.READY:
                    self.state = self.WebSocketState.READY
                    self._ready_event.set()
        
        # Обработка ответа на аутентификацию
        elif "op" in data and data["op"] == "auth":
            if "success" in data and data["success"]:
                logger.info("WebSocket аутентификация успешна")
            else:
                error_msg = data.get("ret_msg", "Неизвестная ошибка")
                logger.error(f"Ошибка аутентификации WebSocket: {error_msg}")
    
    def _create_subscription_message(self, channel: str) -> Dict[str, Any]:
        """
        Формирует сообщение для подписки на канал Bybit.
        
        Args:
            channel: Идентификатор канала для подписки
            
        Returns:
            Dict[str, Any]: Сообщение для подписки
        """
        # Генерируем уникальный ID для запроса
        req_id = self._get_next_id()
        
        # Сохраняем соответствие ID и канала
        self._subscription_ids[channel] = req_id
        self._id_to_channel[req_id] = channel
        
        # Формируем сообщение подписки в формате Bybit
        return {
            "op": "subscribe",
            "args": [channel],
            "req_id": req_id
        }
    
    def _create_unsubscription_message(self, channel: str) -> Dict[str, Any]:
        """
        Формирует сообщение для отписки от канала Bybit.
        
        Args:
            channel: Идентификатор канала для отписки
            
        Returns:
            Dict[str, Any]: Сообщение для отписки
        """
        # Генерируем уникальный ID для запроса
        req_id = self._get_next_id()
        
        # Формируем сообщение отписки в формате Bybit
        return {
            "op": "unsubscribe",
            "args": [channel],
            "req_id": req_id
        }
    
    async def ping(self) -> None:
        """
        Отправляет ping-сообщение на сервер Bybit.
        
        В Bybit используется специальный формат ping-сообщений.
        """
        if self.is_connected:
            try:
                # Формируем ping-сообщение в формате Bybit
                ping_message = {"op": "ping"}
                await self._send(ping_message)
                logger.debug("Отправлен ping")
            except Exception as e:
                logger.warning(f"Ошибка при отправке ping: {str(e)}")
    
    async def subscribe_to_private_topics(self, topics: List[str]) -> None:
        """
        Подписывается на приватные каналы данных.
        
        Args:
            topics: Список каналов для подписки
            
        Raises:
            WebSocketError: Если не удалось подписаться на каналы
        """
        # Проверяем, есть ли аутентификация
        if not hasattr(self.config, 'credentials'):
            raise WebSocketError(
                message="Невозможно подписаться на приватные каналы без аутентификации",
                exchange=self.exchange_name
            )
        
        api_key = self.config.credentials.get_api_key()
        api_secret = self.config.credentials.get_api_secret()
        
        if not api_key or not api_secret:
            raise WebSocketError(
                message="Отсутствуют API ключи для подписки на приватные каналы",
                exchange=self.exchange_name
            )
        
        # Подписываемся на каждый канал
        for topic in topics:
            await self.subscribe(topic)
    
    async def subscribe_public_v5(self, category: str, symbol: str, topic_type: str) -> None:
        """
        Подписывается на публичный канал Bybit V5 API.
        
        Args:
            category: Категория инструмента (spot, linear, inverse, option)
            symbol: Символ инструмента (например, BTCUSDT)
            topic_type: Тип данных (например, orderbook, trade, ticker)
            
        Raises:
            WebSocketError: Если не удалось подписаться на канал
        """
        # Формируем канал в формате Bybit V5 API
        channel = f"{topic_type}.{symbol}"
        
        # Подписываемся на канал
        await self.subscribe(channel)
    
    async def subscribe_private_v5(self, topic_type: str) -> None:
        """
        Подписывается на приватный канал Bybit V5 API.
        
        Args:
            topic_type: Тип данных (например, order, position, wallet)
            
        Raises:
            WebSocketError: Если не удалось подписаться на канал
        """
        # Формируем канал в формате Bybit V5 API
        channel = f"{topic_type}"
        
        # Подписываемся на канал
        await self.subscribe_to_private_topics([channel]) 
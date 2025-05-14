"""
Модуль для управления WebSocket соединениями с биржами.

Предоставляет адаптер над asyncio WebSocket для работы с событиями и подписками
на потоки данных криптовалютных бирж.
"""
import asyncio
import json
import time
from typing import Dict, Any, Optional, Union, List, Callable, Set, Awaitable
from enum import Enum, auto
from urllib.parse import urlparse

import websockets
from websockets.client import WebSocketClientProtocol
from websockets.exceptions import WebSocketException, ConnectionClosed

from exchange_api.core.config import ClientConfig
from exchange_api.utils.logger import Logger
from exchange_api.exceptions import ConnectionError, WebSocketError, UnexpectedError


# Получаем логгер
logger = Logger.get_logger()


class WebSocketState(Enum):
    """Состояния WebSocket соединения."""
    INITIALIZING = auto()  # Инициализация
    CONNECTING = auto()    # Подключение
    CONNECTED = auto()     # Подключено
    SUBSCRIBING = auto()   # Подписка на каналы
    READY = auto()         # Готово к работе
    RECONNECTING = auto()  # Переподключение
    DISCONNECTING = auto() # Отключение
    DISCONNECTED = auto()  # Отключено
    ERROR = auto()         # Ошибка


class WebSocketManager:
    """
    Менеджер WebSocket соединений для работы с API криптобирж.
    
    Предоставляет унифицированный интерфейс для работы с WebSocket API различных
    криптовалютных бирж, обеспечивая подписку на каналы данных и обработку событий.
    """
    
    def __init__(
        self,
        config: ClientConfig,
        ws_url: Optional[str] = None,
        on_message: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None,
        on_error: Optional[Callable[[Exception], Awaitable[None]]] = None,
        on_connect: Optional[Callable[[], Awaitable[None]]] = None,
        on_disconnect: Optional[Callable[[], Awaitable[None]]] = None,
        ping_interval: float = 30.0,
        ping_timeout: float = 10.0,
        close_timeout: float = 5.0
    ):
        """
        Инициализирует менеджер WebSocket соединений.
        
        Args:
            config: Конфигурация клиента биржи
            ws_url: URL для WebSocket соединения (если None, используется из конфигурации)
            on_message: Обратный вызов для обработки входящих сообщений
            on_error: Обратный вызов для обработки ошибок
            on_connect: Обратный вызов при успешном подключении
            on_disconnect: Обратный вызов при отключении
            ping_interval: Интервал отправки ping-сообщений в секундах
            ping_timeout: Таймаут ожидания pong-ответа в секундах
            close_timeout: Таймаут при закрытии соединения в секундах
        """
        self.config = config
        self.exchange_name = config.exchange_name
        
        # URL для WebSocket соединения
        self.ws_url = ws_url or config.connection.ws_url
        
        # Проверка URL
        parsed_url = urlparse(self.ws_url)
        if not parsed_url.scheme in ('ws', 'wss'):
            raise ValueError(f"Некорректный WebSocket URL: {self.ws_url}. Должен начинаться с ws:// или wss://")
        
        # Обратные вызовы
        self.on_message = on_message
        self.on_error = on_error
        self.on_connect = on_connect
        self.on_disconnect = on_disconnect
        
        # Настройки соединения
        self.ping_interval = ping_interval
        self.ping_timeout = ping_timeout
        self.close_timeout = close_timeout
        
        # WebSocket соединение
        self.connection: Optional[WebSocketClientProtocol] = None
        
        # Подписки на каналы
        self.subscriptions: Set[str] = set()
        self.pending_subscriptions: Set[str] = set()
        
        # Состояние соединения
        self._state = WebSocketState.INITIALIZING
        
        # Таймаут для последнего полученного сообщения
        self._last_message_time = 0
        
        # Задачи для выполнения в фоне
        self._tasks: List[asyncio.Task] = []
        
        # Флаг для контроля работы циклов
        self._running = False
        
        # Событие для оповещения о готовности соединения
        self._ready_event = asyncio.Event()
        
        # Семафор для синхронизации переподключений
        self._reconnect_semaphore = asyncio.Semaphore(1)
        
        # Установка контекста логгера
        Logger.set_exchange_context(self.exchange_name)
        
        logger.debug(f"Создан WebSocketManager для {self.exchange_name}")
    
    @property
    def state(self) -> WebSocketState:
        """Возвращает текущее состояние WebSocket соединения."""
        return self._state
    
    @state.setter
    def state(self, new_state: WebSocketState) -> None:
        """
        Устанавливает новое состояние WebSocket соединения и логирует изменение.
        
        Args:
            new_state: Новое состояние
        """
        if new_state != self._state:
            logger.debug(f"WebSocket состояние: {self._state.name} -> {new_state.name}")
            self._state = new_state
    
    @property
    def is_connected(self) -> bool:
        """Возвращает True, если WebSocket соединение активно."""
        return (
            self.connection is not None and 
            self.connection.open and 
            self._state in (WebSocketState.CONNECTED, WebSocketState.SUBSCRIBING, WebSocketState.READY)
        )
    
    @property
    def is_ready(self) -> bool:
        """Возвращает True, если WebSocket соединение готово к работе (все подписки активированы)."""
        return self._state == WebSocketState.READY
    
    async def connect(self) -> None:
        """
        Устанавливает WebSocket соединение с сервером.
        
        Raises:
            ConnectionError: Если не удалось установить соединение
        """
        if self.is_connected:
            logger.debug("WebSocket уже подключен")
            return
        
        # Устанавливаем состояние подключения
        self.state = WebSocketState.CONNECTING
        
        try:
            # Устанавливаем соединение
            extra_headers = self._get_auth_headers()
            
            # Создаем соединение
            self.connection = await websockets.connect(
                uri=self.ws_url,
                extra_headers=extra_headers,
                ping_interval=self.ping_interval,
                ping_timeout=self.ping_timeout,
                close_timeout=self.close_timeout
            )
            
            # Обновляем состояние и время последнего сообщения
            self.state = WebSocketState.CONNECTED
            self._last_message_time = time.time()
            
            # Вызываем обратный вызов при подключении
            if self.on_connect:
                await self.on_connect()
            
            logger.info(f"WebSocket соединение установлено: {self.ws_url}")
            
            # Если у нас есть подписки, переводим их в ожидающие и обновляем состояние
            if self.subscriptions:
                self.pending_subscriptions = self.subscriptions.copy()
                self.subscriptions.clear()
                self.state = WebSocketState.SUBSCRIBING
            else:
                # Если нет подписок, сразу переходим в состояние готовности
                self.state = WebSocketState.READY
                self._ready_event.set()
            
            # Запускаем задачи для обработки сообщений и пинга
            self._running = True
            self._tasks.append(asyncio.create_task(self._message_handler()))
            self._tasks.append(asyncio.create_task(self._heartbeat_handler()))
            
        except (WebSocketException, ConnectionError, Exception) as e:
            self.state = WebSocketState.ERROR
            error_msg = f"Ошибка при подключении к WebSocket: {str(e)}"
            logger.error(error_msg)
            
            # Преобразуем исключение в ConnectionError
            if not isinstance(e, ConnectionError):
                raise ConnectionError(
                    message=error_msg,
                    exchange=self.exchange_name
                ) from e
            raise
    
    async def disconnect(self) -> None:
        """
        Закрывает WebSocket соединение и освобождает ресурсы.
        """
        if not self.is_connected:
            logger.debug("WebSocket уже отключен")
            return
        
        try:
            # Устанавливаем состояние и флаг работы
            self.state = WebSocketState.DISCONNECTING
            self._running = False
            self._ready_event.clear()
            
            # Отменяем все задачи
            for task in self._tasks:
                if not task.done():
                    task.cancel()
            
            # Очищаем список задач
            self._tasks.clear()
            
            # Если есть активное соединение, закрываем его
            if self.connection and self.connection.open:
                await self.connection.close()
                self.connection = None
            
            # Вызываем обратный вызов при отключении
            if self.on_disconnect:
                await self.on_disconnect()
            
            # Обновляем состояние
            self.state = WebSocketState.DISCONNECTED
            logger.info("WebSocket соединение закрыто")
            
        except Exception as e:
            logger.error(f"Ошибка при закрытии WebSocket соединения: {str(e)}")
    
    async def _message_handler(self) -> None:
        """
        Обработчик входящих сообщений от WebSocket.
        
        Выполняется в фоновом режиме, получая и обрабатывая сообщения.
        """
        if not self.connection:
            logger.error("Попытка обработки сообщений без активного соединения")
            return
        
        try:
            async for message in self.connection:
                # Обновляем время последнего сообщения
                self._last_message_time = time.time()
                
                try:
                    # Пытаемся разобрать JSON
                    data = json.loads(message)
                    
                    # Логируем сообщение, если включен режим отладки
                    if self.config.debug_mode:
                        logger.debug(f"WebSocket получено: {message[:1000]}")
                    
                    # Обрабатываем подтверждения подписок
                    await self._handle_subscription_response(data)
                    
                    # Вызываем обратный вызов для обработки сообщения
                    if self.on_message:
                        await self.on_message(data)
                        
                except json.JSONDecodeError:
                    logger.warning(f"Получено некорректное WebSocket сообщение: {message[:200]}")
                except Exception as e:
                    logger.error(f"Ошибка при обработке WebSocket сообщения: {str(e)}")
                    if self.on_error:
                        await self.on_error(e)
        
        except ConnectionClosed as e:
            # Соединение закрыто с кодом и причиной
            close_status = f"код: {e.code}" if hasattr(e, 'code') else "неизвестный код"
            reason = f"причина: {e.reason}" if hasattr(e, 'reason') else "без причины"
            
            logger.warning(f"WebSocket соединение закрыто: {close_status}, {reason}")
            
            # Если мы не в процессе отключения, инициируем переподключение
            if self._running and self._state not in (WebSocketState.DISCONNECTING, WebSocketState.DISCONNECTED):
                await self._reconnect()
                
        except Exception as e:
            # Другие ошибки
            logger.error(f"Ошибка в обработчике WebSocket сообщений: {str(e)}")
            
            if self.on_error:
                await self.on_error(e)
            
            # Если мы не в процессе отключения, инициируем переподключение
            if self._running and self._state not in (WebSocketState.DISCONNECTING, WebSocketState.DISCONNECTED):
                await self._reconnect()
    
    async def _heartbeat_handler(self) -> None:
        """
        Обработчик проверки активности соединения.
        
        Выполняется в фоновом режиме, проверяя активность соединения
        и инициируя переподключение при необходимости.
        """
        while self._running:
            try:
                # Если соединение активно и с момента последнего сообщения прошло
                # слишком много времени, инициируем переподключение
                if (self.is_connected and 
                    time.time() - self._last_message_time > self.ping_interval + self.ping_timeout):
                    logger.warning("WebSocket таймаут: нет активности")
                    await self._reconnect()
                
                # Ждем некоторое время перед следующей проверкой
                await asyncio.sleep(self.ping_interval / 2)
                
            except asyncio.CancelledError:
                # Задача отменена
                break
            except Exception as e:
                logger.error(f"Ошибка в обработчике WebSocket heartbeat: {str(e)}")
                await asyncio.sleep(1)  # Пауза перед повторной попыткой
    
    async def _reconnect(self) -> None:
        """
        Переподключается к WebSocket серверу при обрыве соединения.
        
        Использует семафор для предотвращения одновременных попыток переподключения.
        """
        # Проверяем, что мы не в процессе переподключения и не отключаемся
        if not self._running or self._state in (WebSocketState.DISCONNECTING, WebSocketState.DISCONNECTED):
            return
        
        # Используем семафор для предотвращения одновременных попыток переподключения
        if not self._reconnect_semaphore.locked():
            async with self._reconnect_semaphore:
                # Проверяем еще раз, возможно состояние изменилось пока ждали семафор
                if not self._running or self._state in (WebSocketState.DISCONNECTING, WebSocketState.DISCONNECTED):
                    return
                
                # Устанавливаем состояние переподключения
                self.state = WebSocketState.RECONNECTING
                self._ready_event.clear()
                
                # Сохраняем текущие подписки
                subscriptions_to_restore = self.subscriptions.copy()
                subscriptions_to_restore.update(self.pending_subscriptions)
                
                # Очищаем текущие подписки
                self.subscriptions.clear()
                self.pending_subscriptions.clear()
                
                # Закрываем текущее соединение, если оно есть
                if self.connection and self.connection.open:
                    try:
                        await self.connection.close()
                    except Exception as e:
                        logger.warning(f"Ошибка при закрытии соединения перед переподключением: {str(e)}")
                
                self.connection = None
                
                # Отменяем текущие задачи
                for task in self._tasks:
                    if not task.done():
                        task.cancel()
                
                self._tasks.clear()
                
                # Пытаемся переподключиться
                try:
                    logger.info("Переподключение к WebSocket...")
                    await self.connect()
                    
                    # Восстанавливаем подписки
                    if subscriptions_to_restore:
                        for subscription in subscriptions_to_restore:
                            await self.subscribe(subscription)
                        
                    logger.info("WebSocket переподключение выполнено успешно")
                    
                except Exception as e:
                    logger.error(f"Ошибка при переподключении к WebSocket: {str(e)}")
                    
                    # Устанавливаем состояние ошибки
                    self.state = WebSocketState.ERROR
                    
                    # Если у нас включен режим работы, пробуем переподключиться снова через некоторое время
                    if self._running:
                        reconnect_delay = 5.0  # Задержка перед повторной попыткой в секундах
                        logger.info(f"Повторная попытка переподключения через {reconnect_delay} секунд")
                        await asyncio.sleep(reconnect_delay)
                        asyncio.create_task(self._reconnect())
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """
        Формирует заголовки аутентификации для WebSocket соединения.
        
        Базовая реализация возвращает пустые заголовки. Этот метод должен быть
        переопределен в классах-наследниках для конкретных бирж.
        
        Returns:
            Dict[str, str]: Заголовки аутентификации
        """
        return {}
    
    async def _handle_subscription_response(self, data: Dict[str, Any]) -> None:
        """
        Обрабатывает подтверждение подписки от сервера.
        
        Базовая реализация не выполняет никаких действий. Этот метод должен быть
        переопределен в классах-наследниках для конкретных бирж.
        
        Args:
            data: Данные от WebSocket сервера
        """
        # Базовая реализация не делает ничего
        # Должна быть переопределена в классах для конкретных бирж
        pass
    
    async def subscribe(self, channel: str) -> None:
        """
        Подписывается на канал данных.
        
        Args:
            channel: Идентификатор канала для подписки
            
        Raises:
            WebSocketError: Если не удалось подписаться на канал
        """
        # Если канал уже в подписках, ничего не делаем
        if channel in self.subscriptions or channel in self.pending_subscriptions:
            logger.debug(f"Уже подписан на канал: {channel}")
            return
        
        # Если соединение не установлено или не готово, подключаемся
        if not self.is_connected:
            try:
                await self.connect()
            except Exception as e:
                raise WebSocketError(
                    message=f"Не удалось подключиться для подписки на канал {channel}: {str(e)}",
                    exchange=self.exchange_name,
                    channel=channel
                ) from e
        
        # Добавляем канал в ожидающие подписки
        self.pending_subscriptions.add(channel)
        
        # Если соединение готово к работе, отправляем запрос на подписку
        try:
            # Формируем и отправляем сообщение подписки
            subscription_message = self._create_subscription_message(channel)
            await self._send(subscription_message)
            
            logger.debug(f"Отправлен запрос на подписку: {channel}")
            
        except Exception as e:
            # Удаляем канал из ожидающих подписок
            self.pending_subscriptions.discard(channel)
            
            # Формируем и выбрасываем исключение
            raise WebSocketError(
                message=f"Ошибка при подписке на канал {channel}: {str(e)}",
                exchange=self.exchange_name,
                channel=channel
            ) from e
    
    async def unsubscribe(self, channel: str) -> None:
        """
        Отписывается от канала данных.
        
        Args:
            channel: Идентификатор канала для отписки
            
        Raises:
            WebSocketError: Если не удалось отписаться от канала
        """
        # Если канала нет в подписках и ожидающих подписках, ничего не делаем
        if channel not in self.subscriptions and channel not in self.pending_subscriptions:
            logger.debug(f"Нет подписки на канал: {channel}")
            return
        
        # Удаляем канал из подписок и ожидающих подписок
        self.subscriptions.discard(channel)
        self.pending_subscriptions.discard(channel)
        
        # Если соединение не установлено, ничего не делаем
        if not self.is_connected:
            logger.debug(f"WebSocket не подключен, отписка от канала не требуется: {channel}")
            return
        
        try:
            # Формируем и отправляем сообщение отписки
            unsubscription_message = self._create_unsubscription_message(channel)
            await self._send(unsubscription_message)
            
            logger.debug(f"Отправлен запрос на отписку: {channel}")
            
        except Exception as e:
            # Формируем и выбрасываем исключение
            raise WebSocketError(
                message=f"Ошибка при отписке от канала {channel}: {str(e)}",
                exchange=self.exchange_name,
                channel=channel
            ) from e
    
    async def _send(self, data: Union[Dict[str, Any], str]) -> None:
        """
        Отправляет сообщение на WebSocket сервер.
        
        Args:
            data: Данные для отправки (словарь будет сериализован в JSON)
            
        Raises:
            ConnectionError: Если соединение не установлено
            WebSocketError: Если произошла ошибка при отправке сообщения
        """
        if not self.is_connected or not self.connection:
            raise ConnectionError(
                message="WebSocket соединение не установлено",
                exchange=self.exchange_name
            )
        
        try:
            # Если данные переданы как словарь, сериализуем в JSON
            message = json.dumps(data) if isinstance(data, dict) else data
            
            # Логируем сообщение, если включен режим отладки
            if self.config.debug_mode:
                logger.debug(f"WebSocket отправка: {message}")
            
            # Отправляем сообщение
            await self.connection.send(message)
            
        except WebSocketException as e:
            # Ошибка WebSocket
            raise WebSocketError(
                message=f"Ошибка при отправке сообщения: {str(e)}",
                exchange=self.exchange_name
            ) from e
        except Exception as e:
            # Другие ошибки
            raise UnexpectedError(
                message=f"Неожиданная ошибка при отправке сообщения: {str(e)}",
                exchange=self.exchange_name,
                original_exception=e
            ) from e
    
    def _create_subscription_message(self, channel: str) -> Dict[str, Any]:
        """
        Формирует сообщение для подписки на канал.
        
        Базовая реализация возвращает обобщенный формат. Этот метод должен быть
        переопределен в классах-наследниках для конкретных бирж.
        
        Args:
            channel: Идентификатор канала для подписки
            
        Returns:
            Dict[str, Any]: Сообщение для подписки
        """
        # Базовая реализация с общим форматом
        return {
            "method": "subscribe",
            "params": [channel],
            "id": id(channel)  # Используем id объекта как уникальный идентификатор
        }
    
    def _create_unsubscription_message(self, channel: str) -> Dict[str, Any]:
        """
        Формирует сообщение для отписки от канала.
        
        Базовая реализация возвращает обобщенный формат. Этот метод должен быть
        переопределен в классах-наследниках для конкретных бирж.
        
        Args:
            channel: Идентификатор канала для отписки
            
        Returns:
            Dict[str, Any]: Сообщение для отписки
        """
        # Базовая реализация с общим форматом
        return {
            "method": "unsubscribe",
            "params": [channel],
            "id": id(channel)  # Используем id объекта как уникальный идентификатор
        }
    
    async def wait_until_ready(self, timeout: Optional[float] = None) -> bool:
        """
        Ожидает, пока WebSocket соединение не будет готово к работе.
        
        Args:
            timeout: Максимальное время ожидания в секундах (None - ждать бесконечно)
            
        Returns:
            bool: True, если соединение готово к работе, False если истек таймаут
        """
        if self.is_ready:
            return True
        
        try:
            await asyncio.wait_for(self._ready_event.wait(), timeout=timeout)
            return self.is_ready
        except asyncio.TimeoutError:
            return False
    
    async def __aenter__(self) -> 'WebSocketManager':
        """
        Контекстный менеджер: вход в контекст.
        
        Returns:
            WebSocketManager: Этот менеджер WebSocket соединений
        """
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Контекстный менеджер: выход из контекста.
        """
        await self.disconnect() 
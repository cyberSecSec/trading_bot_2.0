"""
Модуль для управления HTTP соединениями с биржами.

Предоставляет адаптер над aiohttp для работы с REST API криптовалютных бирж,
обеспечивая единый интерфейс выполнения запросов с учетом ограничений API.
"""
import asyncio
import time
import json
from typing import Dict, Any, Optional, Union, List, Callable, Awaitable
from urllib.parse import urljoin

import aiohttp
from aiohttp import ClientSession, ClientTimeout, ClientResponse, TCPConnector

from exchange_api.core.config import ClientConfig, ConnectionConfig
from exchange_api.utils.logger import Logger
from exchange_api.exceptions import (
    ConnectionError, AuthenticationError, RateLimitError, 
    ValidationError, ExchangeError, UnexpectedError
)

# Получаем логгер
logger = Logger.get_logger()


class RateLimiter:
    """
    Класс для контроля частоты запросов к API бирж.
    
    Реализует алгоритм токенного ведра для ограничения количества запросов
    в единицу времени и предотвращения превышения лимитов API.
    """
    
    def __init__(self, 
                 max_requests_per_second: int = 20, 
                 max_requests_per_minute: int = 1200):
        """
        Инициализирует ограничитель запросов.
        
        Args:
            max_requests_per_second: Максимальное количество запросов в секунду
            max_requests_per_minute: Максимальное количество запросов в минуту
        """
        self.max_rps = max_requests_per_second
        self.max_rpm = max_requests_per_minute
        
        # Счетчики для отслеживания запросов
        self.second_count = 0
        self.minute_count = 0
        
        # Время последнего сброса счетчиков
        self.last_second_reset = time.time()
        self.last_minute_reset = time.time()
        
        # Блокировка для синхронизации доступа к счетчикам
        self.lock = asyncio.Lock()
    
    async def acquire(self) -> None:
        """
        Получает разрешение на выполнение запроса.
        
        Ожидает, если текущее количество запросов превышает установленные лимиты.
        Выбрасывает исключение, если превышен общий лимит запросов.
        
        Raises:
            RateLimitError: Если достигнут предел запросов и требуется ожидание
        """
        async with self.lock:
            current_time = time.time()
            
            # Сбрасываем счетчик секундных запросов если прошла секунда
            if current_time - self.last_second_reset >= 1.0:
                self.second_count = 0
                self.last_second_reset = current_time
            
            # Сбрасываем счетчик минутных запросов если прошла минута
            if current_time - self.last_minute_reset >= 60.0:
                self.minute_count = 0
                self.last_minute_reset = current_time
            
            # Проверяем лимиты
            if self.second_count >= self.max_rps:
                # Вычисляем время до сброса секундного счетчика
                wait_time = 1.0 - (current_time - self.last_second_reset)
                if wait_time > 0:
                    logger.debug(f"Rate limit: ожидание {wait_time:.2f}с (достигнут лимит RPS)")
                    await asyncio.sleep(wait_time)
                    # Рекурсивно проверяем снова после ожидания
                    await self.acquire()
                    return
            
            if self.minute_count >= self.max_rpm:
                # Вычисляем время до сброса минутного счетчика
                wait_time = 60.0 - (current_time - self.last_minute_reset)
                if wait_time > 0:
                    raise RateLimitError(
                        message=f"Превышен лимит запросов в минуту ({self.max_rpm}). Повторите через {wait_time:.2f}с",
                        retry_after=wait_time,
                        limit_type="minute"
                    )
            
            # Увеличиваем счетчики
            self.second_count += 1
            self.minute_count += 1
    
    def update_limits(self, max_requests_per_second: int, max_requests_per_minute: int) -> None:
        """
        Обновляет лимиты запросов.
        
        Args:
            max_requests_per_second: Новый лимит запросов в секунду
            max_requests_per_minute: Новый лимит запросов в минуту
        """
        self.max_rps = max_requests_per_second
        self.max_rpm = max_requests_per_minute


class ConnectionManager:
    """
    Менеджер соединений для работы с API криптобирж.
    
    Предоставляет унифицированный интерфейс для выполнения HTTP-запросов
    к различным биржам с учетом их особенностей и ограничений.
    """
    
    def __init__(self, config: ClientConfig):
        """
        Инициализирует менеджер соединений с заданной конфигурацией.
        
        Args:
            config: Конфигурация клиента биржи
        """
        self.config = config
        self.conn_config = config.connection
        self.exchange_name = config.exchange_name
        
        # Создаем ограничитель запросов на основе конфигурации
        self.rate_limiter = RateLimiter(
            max_requests_per_second=config.rate_limit.max_requests_per_second,
            max_requests_per_minute=config.rate_limit.max_requests_per_minute
        )
        
        # Сессия будет создана при первом использовании
        self._session: Optional[ClientSession] = None
        
        # Флаг для отслеживания закрытия сессии
        self._closed = False
        
        # Установка контекста логгера
        Logger.set_exchange_context(self.exchange_name)
        
        logger.debug(f"Создан ConnectionManager для {self.exchange_name}")
    
    async def _get_session(self) -> ClientSession:
        """
        Получает текущую сессию или создает новую, если она не существует.
        
        Returns:
            ClientSession: Сессия для выполнения HTTP-запросов
        
        Raises:
            ConnectionError: Если менеджер соединений уже закрыт
        """
        if self._closed:
            raise ConnectionError("Менеджер соединений уже закрыт")
        
        if self._session is None or self._session.closed:
            # Настройка прокси, если требуется
            proxy = self.conn_config.proxy_url if self.conn_config.use_proxy else None
            
            # Создаем TCP-коннектор с ограничением общего количества соединений
            connector = TCPConnector(
                limit=self.config.rate_limit.max_connections,
                ssl=None  # Можно настроить SSL-контекст при необходимости
            )
            
            # Создаем таймаут для запросов
            timeout = ClientTimeout(total=self.conn_config.timeout)
            
            # Создаем новую сессию
            self._session = ClientSession(
                connector=connector,
                timeout=timeout,
                trust_env=True  # Позволяет использовать переменные окружения для прокси
            )
            
            logger.debug(f"Создана новая HTTP-сессия для {self.exchange_name}")
        
        return self._session
    
    async def close(self) -> None:
        """
        Закрывает менеджер соединений и освобождает ресурсы.
        """
        if not self._closed and self._session is not None and not self._session.closed:
            await self._session.close()
            logger.debug(f"HTTP-сессия для {self.exchange_name} закрыта")
        
        self._closed = True
    
    async def __aenter__(self) -> 'ConnectionManager':
        """
        Контекстный менеджер: вход в контекст.
        
        Returns:
            ConnectionManager: Этот менеджер соединений
        """
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Контекстный менеджер: выход из контекста.
        """
        await self.close()
    
    def _prepare_url(self, endpoint: str) -> str:
        """
        Подготавливает полный URL для запроса.
        
        Args:
            endpoint: Конечная точка API
            
        Returns:
            str: Полный URL для запроса
        """
        # Если endpoint уже является полным URL
        if endpoint.startswith(('http://', 'https://')):
            return endpoint
        
        # Иначе объединяем с базовым URL
        if endpoint.startswith('/'):
            endpoint = endpoint[1:]
        
        return urljoin(self.conn_config.base_url, endpoint)
    
    def _prepare_headers(self, headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """
        Подготавливает заголовки для запроса.
        
        Args:
            headers: Дополнительные заголовки
            
        Returns:
            Dict[str, str]: Объединенные заголовки
        """
        # Базовые заголовки
        default_headers = {
            'User-Agent': f'VANTA-Trading-Bot/{self.exchange_name}',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        
        # Добавляем пользовательские заголовки, если они переданы
        if headers:
            default_headers.update(headers)
        
        return default_headers
    
    async def _process_response(self, response: ClientResponse) -> Dict[str, Any]:
        """
        Обрабатывает ответ от API.
        
        Args:
            response: Ответ API
            
        Returns:
            Dict[str, Any]: Обработанный ответ в виде словаря
            
        Raises:
            ConnectionError: При проблемах с соединением
            AuthenticationError: При ошибках аутентификации
            RateLimitError: При превышении лимитов API
            ValidationError: При ошибках валидации
            ExchangeError: При ошибках на стороне биржи
            UnexpectedError: При неожиданных ошибках
        """
        status_code = response.status
        
        # Формируем информацию о запросе для логирования и исключений
        request_info = {
            'method': response.method,
            'url': str(response.url),
            'headers': dict(response.request_info.headers),
        }
        
        # Информация об ответе
        response_info = {
            'status': status_code,
            'headers': dict(response.headers),
        }
        
        try:
            # Получаем текст ответа
            text = await response.text()
            
            # Логируем ответ, если включен режим отладки
            if self.config.debug_mode:
                logger.debug(f"API ответ [{status_code}]: {text[:1000]}")
            
            # Пытаемся разобрать JSON
            try:
                data = json.loads(text)
                response_info['body'] = data
            except json.JSONDecodeError:
                # Если не получилось разобрать JSON, используем текст как есть
                response_info['body'] = text
                # Если ответ не JSON и код ответа указывает на ошибку
                if status_code >= 400:
                    raise ValidationError(
                        message=f"Не удалось разобрать ответ как JSON: {text[:200]}",
                        code=status_code,
                        request_info=request_info,
                        response_info=response_info,
                        exchange=self.exchange_name
                    )
            
            # Обрабатываем ошибки по коду статуса
            if status_code >= 400:
                # Формируем сообщение об ошибке
                error_message = f"HTTP ошибка {status_code}"
                if isinstance(data, dict):
                    # Пытаемся извлечь сообщение об ошибке из ответа
                    if 'error' in data:
                        error_message = f"{error_message}: {data['error']}"
                    elif 'message' in data:
                        error_message = f"{error_message}: {data['message']}"
                
                # Определяем тип исключения в зависимости от кода статуса
                if status_code == 401 or status_code == 403:
                    raise AuthenticationError(
                        message=error_message,
                        code=status_code,
                        request_info=request_info,
                        response_info=response_info,
                        exchange=self.exchange_name
                    )
                elif status_code == 429:
                    # Получаем Retry-After из заголовков, если есть
                    retry_after = None
                    if 'Retry-After' in response.headers:
                        try:
                            retry_after = float(response.headers['Retry-After'])
                        except (ValueError, TypeError):
                            pass
                    
                    raise RateLimitError(
                        message=error_message,
                        code=status_code,
                        request_info=request_info,
                        response_info=response_info,
                        exchange=self.exchange_name,
                        retry_after=retry_after
                    )
                elif status_code == 400 or status_code == 422:
                    raise ValidationError(
                        message=error_message,
                        code=status_code,
                        request_info=request_info,
                        response_info=response_info,
                        exchange=self.exchange_name
                    )
                elif status_code >= 500:
                    raise ExchangeError(
                        message=error_message,
                        code=status_code,
                        request_info=request_info,
                        response_info=response_info,
                        exchange=self.exchange_name
                    )
                else:
                    raise UnexpectedError(
                        message=error_message,
                        code=status_code,
                        request_info=request_info,
                        response_info=response_info,
                        exchange=self.exchange_name
                    )
            
            # Возвращаем данные если все хорошо
            return data if isinstance(data, dict) else {'data': data}
            
        except aiohttp.ClientError as e:
            # Обрабатываем ошибки клиента aiohttp
            raise ConnectionError(
                message=f"Ошибка соединения: {str(e)}",
                request_info=request_info,
                response_info=response_info,
                exchange=self.exchange_name
            ) from e
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        authenticate: bool = False,
        retry_count: int = 0
    ) -> Dict[str, Any]:
        """
        Выполняет HTTP-запрос к API биржи.
        
        Args:
            method: HTTP-метод (GET, POST, PUT, DELETE)
            endpoint: Конечная точка API
            params: Параметры запроса для URL
            data: Данные для тела запроса
            headers: Дополнительные заголовки
            authenticate: Нужно ли аутентифицировать запрос
            retry_count: Текущее количество повторных попыток
            
        Returns:
            Dict[str, Any]: Ответ от API в виде словаря
            
        Raises:
            ConnectionError: При проблемах с соединением
            Различные исключения из _process_response
        """
        # Получаем сессию
        session = await self._get_session()
        
        # Подготавливаем URL и заголовки
        url = self._prepare_url(endpoint)
        headers = self._prepare_headers(headers)
        
        # Если нужна аутентификация, добавляем заголовки аутентификации
        # Конкретная реализация добавления заголовков должна быть в подклассе
        if authenticate:
            self._add_auth_headers(method, url, params, data, headers)
        
        # Преобразуем тело запроса в JSON, если оно есть
        json_data = None
        if data is not None:
            json_data = data
        
        # Логируем запрос, если включен режим отладки
        if self.config.debug_mode:
            debug_msg = f"API запрос: {method} {url}"
            if params:
                debug_msg += f", params: {params}"
            if data:
                # Маскируем секретные данные в логах
                safe_data = json.dumps(self._mask_sensitive_data(data))
                debug_msg += f", data: {safe_data}"
            logger.debug(debug_msg)
        
        # Запрашиваем разрешение от rate limiter
        try:
            await self.rate_limiter.acquire()
        except RateLimitError as e:
            # Если rate limiter отклонил запрос, пробуем повторить после паузы
            if e.retry_after and retry_count < self.conn_config.max_retries:
                logger.warning(f"Rate limit exceeded, retrying after {e.retry_after}s...")
                await asyncio.sleep(e.retry_after)
                return await self._make_request(
                    method, endpoint, params, data, headers, authenticate, retry_count + 1
                )
            else:
                raise
        
        try:
            # Выполняем запрос
            async with session.request(
                method=method,
                url=url,
                params=params,
                json=json_data,
                headers=headers,
                proxy=self.conn_config.proxy_url if self.conn_config.use_proxy else None
            ) as response:
                # Обрабатываем ответ
                return await self._process_response(response)
                
        except (
            ConnectionError, AuthenticationError, ValidationError, 
            ExchangeError, UnexpectedError
        ) as e:
            # Если произошла ошибка и есть еще попытки, пробуем снова
            if retry_count < self.conn_config.max_retries and isinstance(e, (ConnectionError, ExchangeError)):
                logger.warning(f"Ошибка запроса, повторная попытка {retry_count + 1}/{self.conn_config.max_retries}...")
                # Экспоненциальная задержка перед повторной попыткой
                delay = self.conn_config.retry_delay * (2 ** retry_count)
                await asyncio.sleep(delay)
                return await self._make_request(
                    method, endpoint, params, data, headers, authenticate, retry_count + 1
                )
            # Иначе пробрасываем исключение дальше
            raise
        except Exception as e:
            # Для всех остальных ошибок
            raise UnexpectedError(
                message=f"Неожиданная ошибка при выполнении запроса: {str(e)}",
                request_info={
                    'method': method,
                    'url': url,
                    'params': params,
                    'headers': headers
                },
                exchange=self.exchange_name,
                original_exception=e
            ) from e
    
    def _add_auth_headers(
        self, 
        method: str, 
        url: str, 
        params: Optional[Dict[str, Any]], 
        data: Optional[Dict[str, Any]], 
        headers: Dict[str, str]
    ) -> None:
        """
        Добавляет заголовки аутентификации к запросу.
        
        Этот метод должен быть переопределен в производных классах для
        конкретных бирж, так как механизмы аутентификации отличаются.
        
        Args:
            method: HTTP метод
            url: URL запроса
            params: Параметры запроса
            data: Данные запроса
            headers: Заголовки запроса, которые нужно дополнить
        """
        # Базовая реализация просто добавляет API-ключ в заголовки
        # Для конкретной биржи этот метод должен быть переопределен
        if hasattr(self.config, 'credentials'):
            api_key = self.config.credentials.get_api_key()
            if api_key:
                headers['X-API-Key'] = api_key
    
    def _mask_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Маскирует чувствительные данные в логах.
        
        Args:
            data: Исходные данные
            
        Returns:
            Dict[str, Any]: Данные с замаскированными чувствительными полями
        """
        # Создаем копию словаря
        masked_data = data.copy()
        
        # Список ключей, которые могут содержать чувствительные данные
        sensitive_keys = ['api_key', 'apiKey', 'key', 'secret', 'password', 'passphrase', 'token']
        
        # Маскируем чувствительные данные
        for key in masked_data:
            if key.lower() in [k.lower() for k in sensitive_keys]:
                masked_data[key] = '***MASKED***'
            elif isinstance(masked_data[key], dict):
                masked_data[key] = self._mask_sensitive_data(masked_data[key])
        
        return masked_data
    
    async def get(
        self, 
        endpoint: str, 
        params: Optional[Dict[str, Any]] = None, 
        headers: Optional[Dict[str, str]] = None,
        authenticate: bool = False
    ) -> Dict[str, Any]:
        """
        Выполняет GET-запрос к API.
        
        Args:
            endpoint: Конечная точка API
            params: Параметры запроса
            headers: Дополнительные заголовки
            authenticate: Нужно ли аутентифицировать запрос
            
        Returns:
            Dict[str, Any]: Ответ от API
        """
        return await self._make_request('GET', endpoint, params, None, headers, authenticate)
    
    async def post(
        self, 
        endpoint: str, 
        data: Optional[Dict[str, Any]] = None, 
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        authenticate: bool = False
    ) -> Dict[str, Any]:
        """
        Выполняет POST-запрос к API.
        
        Args:
            endpoint: Конечная точка API
            data: Данные для отправки в теле запроса
            params: Параметры запроса
            headers: Дополнительные заголовки
            authenticate: Нужно ли аутентифицировать запрос
            
        Returns:
            Dict[str, Any]: Ответ от API
        """
        return await self._make_request('POST', endpoint, params, data, headers, authenticate)
    
    async def put(
        self, 
        endpoint: str, 
        data: Optional[Dict[str, Any]] = None, 
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        authenticate: bool = False
    ) -> Dict[str, Any]:
        """
        Выполняет PUT-запрос к API.
        
        Args:
            endpoint: Конечная точка API
            data: Данные для отправки в теле запроса
            params: Параметры запроса
            headers: Дополнительные заголовки
            authenticate: Нужно ли аутентифицировать запрос
            
        Returns:
            Dict[str, Any]: Ответ от API
        """
        return await self._make_request('PUT', endpoint, params, data, headers, authenticate)
    
    async def delete(
        self, 
        endpoint: str, 
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        authenticate: bool = False
    ) -> Dict[str, Any]:
        """
        Выполняет DELETE-запрос к API.
        
        Args:
            endpoint: Конечная точка API
            params: Параметры запроса
            data: Данные для отправки в теле запроса
            headers: Дополнительные заголовки
            authenticate: Нужно ли аутентифицировать запрос
            
        Returns:
            Dict[str, Any]: Ответ от API
        """
        return await self._make_request('DELETE', endpoint, params, data, headers, authenticate) 
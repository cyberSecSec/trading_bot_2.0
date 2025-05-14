"""
Модуль для управления переподключениями при сбоях соединения.

Предоставляет механизмы для автоматического переподключения с использованием
экспоненциальной задержки и адаптивной стратегии повторных попыток.
"""
import asyncio
import time
import random
from functools import wraps
from typing import Callable, Any, Optional, TypeVar, Type, Dict, Union, List, Awaitable

import backoff

from exchange_api.utils.logger import Logger
from exchange_api.exceptions import ConnectionError, RateLimitError, ExchangeError


# Получаем логгер
logger = Logger.get_logger()


# Типовая переменная для декораторов
T = TypeVar('T')


class ReconnectionHandler:
    """
    Обработчик переподключений при сбоях соединения.
    
    Предоставляет декораторы и утилиты для управления повторными попытками
    при временных проблемах с сетью или API.
    """
    
    @staticmethod
    def with_backoff(
        max_tries: int = 5,
        max_time: Optional[float] = 60.0,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        factor: float = 2.0,
        jitter: Optional[float] = 0.1,
        exceptions: List[Type[Exception]] = [ConnectionError, ExchangeError]
    ) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
        """
        Декоратор для повторных попыток с экспоненциальной задержкой.
        
        Args:
            max_tries: Максимальное количество попыток
            max_time: Максимальное время выполнения в секундах
            base_delay: Начальная задержка между попытками в секундах
            max_delay: Максимальная задержка между попытками в секундах
            factor: Множитель для экспоненциальной задержки
            jitter: Коэффициент случайного отклонения задержки (None - без отклонения)
            exceptions: Список исключений, которые следует обрабатывать
            
        Returns:
            Callable: Декоратор для асинхронной функции
        """
        def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
            @wraps(func)
            async def wrapper(*args: Any, **kwargs: Any) -> T:
                # Определяем генератор задержек для backoff
                def backoff_handler(details: Dict[str, Any]) -> None:
                    attempt = details['tries']
                    wait = details['wait']
                    exception = details.get('exception')
                    exception_name = exception.__class__.__name__ if exception else 'Unknown'
                    
                    logger.warning(
                        f"Попытка {attempt} не удалась с ошибкой {exception_name}, "
                        f"повторная попытка через {wait:.2f}с"
                    )
                
                @backoff.on_exception(
                    wait_gen=backoff.expo,
                    exception=tuple(exceptions),
                    max_tries=max_tries,
                    max_time=max_time,
                    base=base_delay,
                    factor=factor,
                    max_value=max_delay,
                    jitter=jitter,
                    on_backoff=backoff_handler,
                    raise_on_giveup=True
                )
                async def _execute_with_backoff() -> T:
                    return await func(*args, **kwargs)
                
                return await _execute_with_backoff()
            
            return wrapper
        
        return decorator
    
    @staticmethod
    def with_rate_limit_handling(
        initial_delay: float = 1.0,
        max_delay: float = 120.0,
        factor: float = 2.0
    ) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
        """
        Декоратор для обработки ошибок превышения лимитов запросов.
        
        Args:
            initial_delay: Начальная задержка при отсутствии Retry-After в секундах
            max_delay: Максимальная задержка в секундах
            factor: Множитель для увеличения задержки при повторных ошибках
            
        Returns:
            Callable: Декоратор для асинхронной функции
        """
        def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
            @wraps(func)
            async def wrapper(*args: Any, **kwargs: Any) -> T:
                retry_count = 0
                current_delay = initial_delay
                
                while True:
                    try:
                        return await func(*args, **kwargs)
                    except RateLimitError as e:
                        retry_count += 1
                        
                        # Используем Retry-After из ответа, если он есть
                        if e.retry_after:
                            wait_time = min(e.retry_after, max_delay)
                        else:
                            # Иначе используем экспоненциальную задержку
                            wait_time = min(current_delay * (factor ** (retry_count - 1)), max_delay)
                        
                        logger.warning(
                            f"Превышен лимит запросов ({e.limit_type or 'unknown'}), "
                            f"ожидание {wait_time:.2f}с перед повторной попыткой"
                        )
                        
                        # Ожидаем перед повторной попыткой
                        await asyncio.sleep(wait_time)
                        
                        # Увеличиваем базовую задержку для следующей попытки
                        current_delay = wait_time
                    
            return wrapper
        
        return decorator
    
    @staticmethod
    def with_state_recovery(
        recovery_func: Callable[[Dict[str, Any]], Awaitable[None]]
    ) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
        """
        Декоратор для восстановления состояния после переподключения.
        
        Args:
            recovery_func: Функция для восстановления состояния после переподключения
            
        Returns:
            Callable: Декоратор для асинхронной функции
        """
        def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
            @wraps(func)
            async def wrapper(*args: Any, **kwargs: Any) -> T:
                try:
                    return await func(*args, **kwargs)
                except ConnectionError as e:
                    # Восстанавливаем состояние
                    context = {
                        'args': args,
                        'kwargs': kwargs,
                        'exception': e,
                        'time': time.time()
                    }
                    
                    logger.info("Восстановление состояния после ошибки соединения")
                    await recovery_func(context)
                    
                    # Повторно вызываем функцию
                    return await func(*args, **kwargs)
                
            return wrapper
        
        return decorator
    
    @staticmethod
    async def wait_with_jitter(
        base_delay: float,
        factor: float = 1.0,
        jitter: float = 0.1
    ) -> float:
        """
        Ожидает с добавлением случайной вариации к задержке.
        
        Args:
            base_delay: Базовая задержка в секундах
            factor: Множитель для задержки
            jitter: Коэффициент случайного отклонения (0.1 = 10%)
            
        Returns:
            float: Фактическое время ожидания в секундах
        """
        delay = base_delay * factor
        
        # Добавляем случайное отклонение
        if jitter > 0:
            delay = delay * (1 + jitter * (2 * random.random() - 1))
        
        # Гарантируем, что задержка положительная
        delay = max(0.001, delay)
        
        logger.debug(f"Ожидание {delay:.3f}с перед повторной попыткой")
        await asyncio.sleep(delay)
        
        return delay


# Утилиты для работы с backoff

def should_retry_on_exception(exception: Exception) -> bool:
    """
    Определяет, нужно ли повторить попытку для данного исключения.
    
    Args:
        exception: Исключение для проверки
        
    Returns:
        bool: True, если нужно повторить попытку, иначе False
    """
    # Повторяем попытку для ошибок соединения и ошибок на стороне биржи
    if isinstance(exception, (ConnectionError, ExchangeError)):
        return True
    
    # Для ошибок превышения лимитов - только если указан retry_after
    if isinstance(exception, RateLimitError):
        return exception.retry_after is not None
    
    # Для остальных исключений не повторяем
    return False


def get_retry_delay(exception: Exception, base_delay: float = 1.0) -> float:
    """
    Определяет задержку перед повторной попыткой на основе исключения.
    
    Args:
        exception: Исключение для анализа
        base_delay: Базовая задержка в секундах
        
    Returns:
        float: Рекомендуемая задержка в секундах
    """
    # Для ошибок с явно указанным временем до повторной попытки
    if isinstance(exception, (ConnectionError, RateLimitError)) and exception.retry_after:
        return exception.retry_after
    
    # Для остальных возвращаем базовую задержку
    return base_delay


def create_exponential_backoff_handler(
    max_tries: int = 5,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    factor: float = 2.0,
    jitter: Optional[float] = 0.1,
    retry_checker: Callable[[Exception], bool] = should_retry_on_exception
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """
    Создает обработчик экспоненциальной задержки для повторных попыток.
    
    Args:
        max_tries: Максимальное количество попыток
        base_delay: Начальная задержка между попытками в секундах
        max_delay: Максимальная задержка между попытками в секундах
        factor: Множитель для экспоненциальной задержки
        jitter: Коэффициент случайного отклонения задержки (None - без отклонения)
        retry_checker: Функция, определяющая необходимость повторной попытки
        
    Returns:
        Callable: Декоратор для асинхронной функции
    """
    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            attempt = 0
            current_delay = base_delay
            
            while True:
                attempt += 1
                
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    # Проверяем, нужно ли повторять попытку
                    if not retry_checker(e) or attempt >= max_tries:
                        raise
                    
                    # Вычисляем задержку
                    delay = min(current_delay, max_delay)
                    
                    # Добавляем случайное отклонение
                    if jitter:
                        delay = delay * (1 + jitter * (2 * random.random() - 1))
                    
                    logger.warning(
                        f"Попытка {attempt} не удалась с ошибкой {e.__class__.__name__}, "
                        f"повторная попытка через {delay:.2f}с"
                    )
                    
                    # Ожидаем перед повторной попыткой
                    await asyncio.sleep(delay)
                    
                    # Увеличиваем задержку для следующей попытки
                    current_delay = current_delay * factor
        
        return wrapper
    
    return decorator 
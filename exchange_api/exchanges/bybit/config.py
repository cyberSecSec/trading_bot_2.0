"""
Модуль для специфичной конфигурации Bybit.

Расширяет базовый класс ClientConfig, добавляя специфичные для Bybit
параметры конфигурации и методы.
"""
import os
from enum import Enum
from typing import Optional, Dict, Any, List, Union, Set
from pathlib import Path

from pydantic import Field, validator, root_validator

from exchange_api.core.config import ClientConfig, EnvironmentType, ConnectionConfig
from exchange_api.exceptions import ConfigurationError
from exchange_api.exchanges.bybit.constants import (
    API_URL_MAINNET, 
    API_URL_TESTNET, 
    WS_URL_MAINNET, 
    WS_URL_TESTNET,
    ENV_PREFIX,
    VALID_CATEGORIES
)


class BybitEnvironmentType(str, Enum):
    """
    Типы окружений для Bybit.
    
    Attributes:
        MAINNET: Основная сеть (реальная торговля)
        TESTNET: Тестовая сеть (тестирование API)
    """
    MAINNET = "mainnet"
    TESTNET = "testnet"


class BybitClientConfig(ClientConfig):
    """
    Конфигурация клиента Bybit.
    
    Расширяет базовый ClientConfig, добавляя специфичные для Bybit параметры.
    
    Attributes:
        bybit_environment: Тип окружения Bybit (mainnet или testnet)
        categories: Категории инструментов для работы (spot, linear, inverse, option)
        recv_window: Окно приема для запросов (в миллисекундах)
    """
    bybit_environment: BybitEnvironmentType = BybitEnvironmentType.MAINNET
    categories: Set[str] = Field(default_factory=lambda: {"spot", "linear"})
    recv_window: int = 5000  # Default receive window is 5 seconds (5000 ms)
    
    @validator('categories')
    def validate_categories(cls, v):
        """Проверка валидности указанных категорий инструментов."""
        if not v:
            raise ValueError("Необходимо указать хотя бы одну категорию инструментов")
        
        invalid_categories = v - VALID_CATEGORIES
        if invalid_categories:
            raise ValueError(f"Недопустимые категории: {invalid_categories}. "
                            f"Допустимые категории: {VALID_CATEGORIES}")
        
        return v
    
    @validator('recv_window')
    def validate_recv_window(cls, v):
        """Проверка корректности значения recv_window."""
        if v < 1000:
            raise ValueError("recv_window должен быть не менее 1000 мс")
        if v > 60000:
            raise ValueError("recv_window должен быть не более 60000 мс")
        return v
    
    @root_validator
    def set_urls_based_on_environment(cls, values):
        """
        Устанавливает URL-адреса API и WebSocket в зависимости от типа окружения.
        """
        bybit_env = values.get('bybit_environment')
        test_mode = values.get('test_mode')
        
        # Автоматически установить test_mode=True для testnet
        if bybit_env == BybitEnvironmentType.TESTNET:
            values['test_mode'] = True
        
        # Автоматически установить bybit_environment на основе test_mode
        if test_mode and bybit_env == BybitEnvironmentType.MAINNET:
            values['bybit_environment'] = BybitEnvironmentType.TESTNET
        
        # Получаем или создаем объект connection
        connection = values.get('connection', ConnectionConfig(base_url="", ws_url=""))
        
        # Устанавливаем URL-адреса в зависимости от окружения
        if values.get('bybit_environment') == BybitEnvironmentType.TESTNET:
            connection.base_url = API_URL_TESTNET
            connection.ws_url = WS_URL_TESTNET
        else:
            connection.base_url = API_URL_MAINNET
            connection.ws_url = WS_URL_MAINNET
        
        values['connection'] = connection
        return values
    
    @classmethod
    def from_env(cls) -> 'BybitClientConfig':
        """
        Создает конфигурацию из переменных окружения специфичных для Bybit.
        
        Переменные окружения имеют префикс VANTA_BYBIT_.
        
        Returns:
            BybitClientConfig: Объект конфигурации
            
        Raises:
            ValueError: Если не найдены необходимые переменные окружения
        """
        # Получаем базовую конфигурацию из переменных окружения
        base_config = super().from_env("BYBIT")
        
        # Получаем специфичные для Bybit параметры
        bybit_env = os.environ.get(f"{ENV_PREFIX}ENVIRONMENT", BybitEnvironmentType.MAINNET.value)
        
        # Получаем список категорий из переменной окружения
        categories_str = os.environ.get(f"{ENV_PREFIX}CATEGORIES", "spot,linear")
        categories = {cat.strip() for cat in categories_str.split(",")} if categories_str else {"spot", "linear"}
        
        # Получаем recv_window из переменной окружения
        recv_window = int(os.environ.get(f"{ENV_PREFIX}RECV_WINDOW", "5000"))
        
        # Создаем новую конфигурацию с дополнительными параметрами
        return cls(
            exchange_name="bybit",
            environment=base_config.environment,
            credentials=base_config.credentials,
            connection=base_config.connection,
            rate_limit=base_config.rate_limit,
            test_mode=base_config.test_mode,
            debug_mode=base_config.debug_mode,
            symbols=base_config.symbols,
            bybit_environment=bybit_env,
            categories=categories,
            recv_window=recv_window
        )
    
    @classmethod
    def get_default(cls) -> 'BybitClientConfig':
        """
        Создает конфигурацию с безопасными значениями по умолчанию для Bybit.
        
        Returns:
            BybitClientConfig: Объект конфигурации с дефолтными значениями
        """
        base_config = super().get_default("bybit")
        
        # Добавляем специфичные для Bybit параметры
        return cls(
            exchange_name="bybit",
            environment=base_config.environment,
            credentials=base_config.credentials,
            connection=base_config.connection,
            rate_limit=base_config.rate_limit,
            test_mode=True,  # По умолчанию используем тестовый режим для безопасности
            debug_mode=base_config.debug_mode,
            symbols=base_config.symbols,
            bybit_environment=BybitEnvironmentType.TESTNET,  # По умолчанию используем testnet
            categories={"spot", "linear"},  # По умолчанию доступны spot и linear
            recv_window=5000
        )
    
    def to_dict(self, exclude_secrets: bool = True) -> Dict[str, Any]:
        """
        Преобразует расширенную конфигурацию в словарь.
        
        Args:
            exclude_secrets: Исключать ли секретные данные из результата
            
        Returns:
            Dict[str, Any]: Словарь с параметрами конфигурации
        """
        config_dict = super().to_dict(exclude_secrets=exclude_secrets)
        
        # Добавляем специфичные для Bybit параметры
        config_dict["bybit_environment"] = self.bybit_environment
        config_dict["categories"] = list(self.categories)
        config_dict["recv_window"] = self.recv_window
        
        return config_dict 
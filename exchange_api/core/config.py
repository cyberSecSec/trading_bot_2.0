"""
Модуль для конфигурации клиента криптобиржи.

Содержит классы для настройки параметров соединения, аутентификации
и управления конфигурацией в различных окружениях.
"""
import os
import json
from enum import Enum
from typing import Optional, Dict, Any, List, Union
from pathlib import Path

import dotenv
from pydantic import BaseModel, Field, validator, root_validator, SecretStr

# Загрузка переменных окружения из .env файла
dotenv.load_dotenv()


class EnvironmentType(str, Enum):
    """Типы окружений для работы клиента."""
    PRODUCTION = "production"
    DEVELOPMENT = "development"
    TEST = "test"


class RateLimitConfig(BaseModel):
    """
    Конфигурация лимитов запросов к API.
    
    Attributes:
        max_requests_per_second: Максимальное количество запросов в секунду
        max_requests_per_minute: Максимальное количество запросов в минуту
        max_connections: Максимальное количество одновременных соединений
    """
    max_requests_per_second: int = 20
    max_requests_per_minute: int = 1200
    max_connections: int = 50
    
    class Config:
        """Конфигурация Pydantic модели."""
        validate_assignment = True


class ConnectionConfig(BaseModel):
    """
    Конфигурация соединения с API биржи.
    
    Attributes:
        base_url: Базовый URL API
        ws_url: URL для WebSocket соединения
        timeout: Таймаут для HTTP запросов в секундах
        max_retries: Максимальное количество повторных попыток при ошибках
        retry_delay: Задержка между повторными попытками в секундах
        use_proxy: Использовать ли прокси для соединения
        proxy_url: URL прокси-сервера (если use_proxy=True)
    """
    base_url: str
    ws_url: str
    timeout: float = 10.0
    max_retries: int = 3
    retry_delay: float = 1.0
    use_proxy: bool = False
    proxy_url: Optional[str] = None
    
    @validator('base_url', 'ws_url')
    def validate_urls(cls, v):
        """Валидация URL-адресов для соединения с API."""
        if not v.startswith(('http://', 'https://', 'ws://', 'wss://')):
            raise ValueError('URL должен начинаться с http://, https://, ws:// или wss://')
        return v
    
    @validator('timeout', 'retry_delay')
    def validate_positive_float(cls, v):
        """Проверка, что значение является положительным числом."""
        if v <= 0:
            raise ValueError('Значение должно быть положительным числом')
        return v
    
    @validator('max_retries')
    def validate_positive_int(cls, v):
        """Проверка, что значение является положительным целым числом."""
        if v < 0:
            raise ValueError('Значение должно быть неотрицательным целым числом')
        return v
    
    @validator('proxy_url')
    def validate_proxy_url(cls, v, values):
        """Валидация URL прокси-сервера, если use_proxy=True."""
        if values.get('use_proxy', False) and not v:
            raise ValueError('При use_proxy=True необходимо указать proxy_url')
        if v and not v.startswith(('http://', 'https://', 'socks5://')):
            raise ValueError('Proxy URL должен начинаться с http://, https:// или socks5://')
        return v
    
    class Config:
        """Конфигурация Pydantic модели."""
        validate_assignment = True


class ApiCredentials(BaseModel):
    """
    Учетные данные для доступа к API биржи.
    
    Attributes:
        api_key: API ключ для аутентификации
        api_secret: Секретный ключ для подписи запросов
        passphrase: Пароль (используется некоторыми биржами)
    """
    api_key: SecretStr
    api_secret: SecretStr
    passphrase: Optional[SecretStr] = None
    
    def get_api_key(self) -> str:
        """
        Получает значение API ключа.
        
        Returns:
            str: API ключ
        """
        return self.api_key.get_secret_value()
    
    def get_api_secret(self) -> str:
        """
        Получает значение секретного ключа.
        
        Returns:
            str: Секретный ключ
        """
        return self.api_secret.get_secret_value()
    
    def get_passphrase(self) -> Optional[str]:
        """
        Получает значение пароля, если он установлен.
        
        Returns:
            Optional[str]: Пароль или None, если не установлен
        """
        if self.passphrase:
            return self.passphrase.get_secret_value()
        return None
    
    class Config:
        """Конфигурация Pydantic модели."""
        validate_assignment = True


class ClientConfig(BaseModel):
    """
    Основная конфигурация клиента криптобиржи.
    
    Attributes:
        exchange_name: Название биржи
        environment: Тип окружения (production, development, test)
        credentials: Учетные данные для API
        connection: Конфигурация соединения
        rate_limit: Конфигурация лимитов запросов
        test_mode: Режим тестирования (использование тестового API)
        debug_mode: Режим отладки (расширенное логирование)
        symbols: Список символов инструментов для работы
    """
    exchange_name: str
    environment: EnvironmentType = EnvironmentType.PRODUCTION
    credentials: ApiCredentials
    connection: ConnectionConfig
    rate_limit: RateLimitConfig = Field(default_factory=RateLimitConfig)
    test_mode: bool = False
    debug_mode: bool = False
    symbols: List[str] = []
    
    @root_validator(skip_on_failure=True)
    def validate_test_mode_and_environment(cls, values):
        """
        Проверяет согласованность режима тестирования и типа окружения.
        
        Если environment = TEST, то test_mode должен быть True.
        """
        env = values.get('environment')
        test_mode = values.get('test_mode')
        
        if env == EnvironmentType.TEST and not test_mode:
            values['test_mode'] = True
        
        return values
    
    class Config:
        """Конфигурация Pydantic модели."""
        validate_assignment = True
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'ClientConfig':
        """
        Создает конфигурацию из словаря.
        
        Args:
            config_dict: Словарь с параметрами конфигурации
            
        Returns:
            ClientConfig: Объект конфигурации
        """
        return cls(**config_dict)
    
    @classmethod
    def from_json(cls, json_path: Union[str, Path]) -> 'ClientConfig':
        """
        Создает конфигурацию из JSON файла.
        
        Args:
            json_path: Путь к JSON файлу с конфигурацией
            
        Returns:
            ClientConfig: Объект конфигурации
            
        Raises:
            FileNotFoundError: Если файл не найден
            json.JSONDecodeError: Если файл содержит невалидный JSON
        """
        path = Path(json_path)
        if not path.exists():
            raise FileNotFoundError(f"Файл конфигурации не найден: {json_path}")
        
        with open(path, 'r') as f:
            config_dict = json.load(f)
            
        return cls.from_dict(config_dict)
    
    @classmethod
    def from_env(cls, exchange_name: str) -> 'ClientConfig':
        """
        Создает конфигурацию из переменных окружения.
        
        Ищет переменные с префиксом VANTA_{EXCHANGE_NAME}_
        
        Args:
            exchange_name: Название биржи
            
        Returns:
            ClientConfig: Объект конфигурации
            
        Raises:
            ValueError: Если не найдены необходимые переменные окружения
        """
        exchange_name = exchange_name.upper()
        prefix = f"VANTA_{exchange_name}_"
        
        # Обязательные переменные
        try:
            api_key = os.environ[f"{prefix}API_KEY"]
            api_secret = os.environ[f"{prefix}API_SECRET"]
            base_url = os.environ[f"{prefix}BASE_URL"]
            ws_url = os.environ[f"{prefix}WS_URL"]
        except KeyError as e:
            raise ValueError(f"Отсутствует обязательная переменная окружения: {e}")
        
        # Необязательные переменные с значениями по умолчанию
        environment = os.environ.get(f"{prefix}ENVIRONMENT", EnvironmentType.PRODUCTION.value)
        test_mode = os.environ.get(f"{prefix}TEST_MODE", "").lower() in ("true", "1", "yes")
        debug_mode = os.environ.get(f"{prefix}DEBUG_MODE", "").lower() in ("true", "1", "yes")
        
        # Таймауты и повторные попытки
        timeout = float(os.environ.get(f"{prefix}TIMEOUT", "10.0"))
        max_retries = int(os.environ.get(f"{prefix}MAX_RETRIES", "3"))
        retry_delay = float(os.environ.get(f"{prefix}RETRY_DELAY", "1.0"))
        
        # Прокси
        use_proxy = os.environ.get(f"{prefix}USE_PROXY", "").lower() in ("true", "1", "yes")
        proxy_url = os.environ.get(f"{prefix}PROXY_URL", None)
        
        # Лимиты запросов
        max_req_per_sec = int(os.environ.get(f"{prefix}MAX_REQUESTS_PER_SECOND", "20"))
        max_req_per_min = int(os.environ.get(f"{prefix}MAX_REQUESTS_PER_MINUTE", "1200"))
        max_connections = int(os.environ.get(f"{prefix}MAX_CONNECTIONS", "50"))
        
        # Символы инструментов
        symbols_str = os.environ.get(f"{prefix}SYMBOLS", "")
        symbols = [s.strip() for s in symbols_str.split(",")] if symbols_str else []
        
        # Создание учетных данных
        credentials = ApiCredentials(
            api_key=api_key,
            api_secret=api_secret,
            passphrase=os.environ.get(f"{prefix}PASSPHRASE")
        )
        
        # Создание конфигурации соединения
        connection = ConnectionConfig(
            base_url=base_url,
            ws_url=ws_url,
            timeout=timeout,
            max_retries=max_retries,
            retry_delay=retry_delay,
            use_proxy=use_proxy,
            proxy_url=proxy_url if use_proxy else None
        )
        
        # Создание конфигурации лимитов запросов
        rate_limit = RateLimitConfig(
            max_requests_per_second=max_req_per_sec,
            max_requests_per_minute=max_req_per_min,
            max_connections=max_connections
        )
        
        return cls(
            exchange_name=exchange_name.lower(),
            environment=environment,
            credentials=credentials,
            connection=connection,
            rate_limit=rate_limit,
            test_mode=test_mode,
            debug_mode=debug_mode,
            symbols=symbols
        )
    
    @classmethod
    def get_default(cls, exchange_name: str) -> 'ClientConfig':
        """
        Создает конфигурацию с безопасными значениями по умолчанию.
        
        Args:
            exchange_name: Название биржи
            
        Returns:
            ClientConfig: Объект конфигурации с дефолтными значениями
        """
        credentials = ApiCredentials(
            api_key="dummy_key",
            api_secret="dummy_secret"
        )
        
        connection = ConnectionConfig(
            base_url=f"https://api.{exchange_name}.com",
            ws_url=f"wss://ws.{exchange_name}.com",
            timeout=10.0,
            max_retries=3,
            retry_delay=1.0
        )
        
        return cls(
            exchange_name=exchange_name.lower(),
            environment=EnvironmentType.DEVELOPMENT,
            credentials=credentials,
            connection=connection,
            test_mode=True,
            debug_mode=True
        )
    
    def to_dict(self, exclude_secrets: bool = True) -> Dict[str, Any]:
        """
        Преобразует конфигурацию в словарь.
        
        Args:
            exclude_secrets: Исключать ли секретные данные из результата
            
        Returns:
            Dict[str, Any]: Словарь с параметрами конфигурации
        """
        # Используем встроенный метод Pydantic для сериализации в словарь
        config_dict = self.dict(
            exclude_none=True,
            by_alias=True
        )
        
        # Если нужно исключить секретные данные
        if exclude_secrets:
            if 'credentials' in config_dict:
                if 'api_key' in config_dict['credentials']:
                    config_dict['credentials']['api_key'] = '***'
                if 'api_secret' in config_dict['credentials']:
                    config_dict['credentials']['api_secret'] = '***'
                if 'passphrase' in config_dict['credentials'] and config_dict['credentials']['passphrase']:
                    config_dict['credentials']['passphrase'] = '***'
        
        return config_dict
    
    def to_json(self, json_path: Union[str, Path], exclude_secrets: bool = True) -> None:
        """
        Сохраняет конфигурацию в JSON файл.
        
        Args:
            json_path: Путь для сохранения JSON файла
            exclude_secrets: Исключать ли секретные данные из результата
            
        Returns:
            None
        """
        config_dict = self.to_dict(exclude_secrets=exclude_secrets)
        
        path = Path(json_path)
        
        # Создаем родительские директории, если они не существуют
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w') as f:
            json.dump(config_dict, f, indent=4)
    
    def merge(self, other_config: 'ClientConfig') -> 'ClientConfig':
        """
        Объединяет текущую конфигурацию с другой.
        
        Параметры из other_config перезаписывают соответствующие параметры текущей конфигурации.
        
        Args:
            other_config: Другая конфигурация для объединения
            
        Returns:
            ClientConfig: Новый объект с объединенной конфигурацией
        """
        # Преобразуем оба объекта в словари
        self_dict = self.dict(exclude_none=True)
        other_dict = other_config.dict(exclude_none=True)
        
        # Рекурсивно объединяем словари
        def merge_dicts(d1, d2):
            for k, v in d2.items():
                if k in d1 and isinstance(d1[k], dict) and isinstance(v, dict):
                    merge_dicts(d1[k], v)
                else:
                    d1[k] = v
        
        merged_dict = self_dict.copy()
        merge_dicts(merged_dict, other_dict)
        
        # Создаем новый объект конфигурации
        return ClientConfig(**merged_dict) 
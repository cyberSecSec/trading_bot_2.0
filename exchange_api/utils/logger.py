"""
Модуль для настройки и управления логированием.

Использует библиотеку loguru для гибкого и производительного логирования.
"""
import os
import sys
from enum import Enum
from typing import Dict, Any, Optional, Union, List
from pathlib import Path

from loguru import logger


class LogLevel(str, Enum):
    """Уровни логирования."""
    TRACE = "TRACE"
    DEBUG = "DEBUG"
    INFO = "INFO"
    SUCCESS = "SUCCESS"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogConfig:
    """
    Конфигурация логирования.
    
    Attributes:
        level: Уровень логирования
        format: Формат сообщений лога
        colorize: Использовать ли цветной вывод в консоль
        diagnose: Показывать ли расширенную информацию об исключениях
        backtrace: Включать ли трассировку стека в логи
        rotation: Политика ротации файлов логов (например, "10 MB")
        compression: Формат сжатия (например, "zip")
        retention: Политика хранения логов (например, "1 week")
        file_level: Уровень логирования для файлов (если отличается от основного)
        json_format: Использовать ли JSON формат для файловых логов
    """
    
    def __init__(
        self,
        level: Union[LogLevel, str] = LogLevel.INFO,
        format: str = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        colorize: bool = True,
        diagnose: bool = True,
        backtrace: bool = True,
        rotation: str = "10 MB",
        compression: str = "zip",
        retention: str = "1 month",
        file_level: Optional[Union[LogLevel, str]] = None,
        json_format: bool = False
    ):
        """
        Инициализирует конфигурацию логирования.
        
        Args:
            level: Уровень логирования
            format: Формат сообщений лога
            colorize: Использовать ли цветной вывод в консоль
            diagnose: Показывать ли расширенную информацию об исключениях
            backtrace: Включать ли трассировку стека в логи
            rotation: Политика ротации файлов логов
            compression: Формат сжатия
            retention: Политика хранения логов
            file_level: Уровень логирования для файлов
            json_format: Использовать ли JSON формат для файловых логов
        """
        self.level = level
        self.format = format
        self.colorize = colorize
        self.diagnose = diagnose
        self.backtrace = backtrace
        self.rotation = rotation
        self.compression = compression
        self.retention = retention
        self.file_level = file_level if file_level is not None else level
        self.json_format = json_format
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'LogConfig':
        """
        Создает конфигурацию из словаря.
        
        Args:
            config_dict: Словарь с параметрами конфигурации
            
        Returns:
            LogConfig: Объект конфигурации логирования
        """
        return cls(**config_dict)
    
    def get_console_config(self) -> Dict[str, Any]:
        """
        Возвращает конфигурацию для логирования в консоль.
        
        Returns:
            Dict[str, Any]: Словарь с параметрами для настройки консольного sink
        """
        return {
            "sink": sys.stderr,
            "level": self.level,
            "format": self.format,
            "colorize": self.colorize,
            "diagnose": self.diagnose,
            "backtrace": self.backtrace
        }
    
    def get_file_config(self, log_file: Union[str, Path]) -> Dict[str, Any]:
        """
        Возвращает конфигурацию для логирования в файл.
        
        Args:
            log_file: Путь к файлу лога
            
        Returns:
            Dict[str, Any]: Словарь с параметрами для настройки файлового sink
        """
        # Для JSON логирования используем другой формат
        if self.json_format:
            format_str = "{{\"time\": \"{time:YYYY-MM-DD HH:mm:ss.SSS}\", \"level\": \"{level}\", \"message\": \"{message}\", \"name\": \"{name}\", \"function\": \"{function}\", \"line\": {line}}}"
        else:
            format_str = self.format
            
        return {
            "sink": log_file,
            "level": self.file_level,
            "format": format_str,
            "rotation": self.rotation,
            "compression": self.compression,
            "retention": self.retention,
            "diagnose": self.diagnose,
            "backtrace": self.backtrace,
            "enqueue": True  # Асинхронная запись для повышения производительности
        }


class Logger:
    """
    Класс для настройки и управления логированием.
    
    Обертка над библиотекой loguru для удобства использования в проекте.
    """
    
    @staticmethod
    def setup(
        config: Optional[LogConfig] = None,
        log_dir: Optional[Union[str, Path]] = None,
        log_filename: str = "vanta_exchange_api.log",
        console_enabled: bool = True,
        file_enabled: bool = True
    ) -> None:
        """
        Настраивает логирование с заданной конфигурацией.
        
        Args:
            config: Конфигурация логирования
            log_dir: Директория для хранения файлов логов
            log_filename: Имя файла лога
            console_enabled: Включить ли вывод в консоль
            file_enabled: Включить ли запись в файл
            
        Returns:
            None
        """
        # Используем конфигурацию по умолчанию, если не передана
        if config is None:
            config = LogConfig()
        
        # Удаляем все существующие обработчики
        logger.remove()
        
        # Настраиваем диагностику и трассировку
        logger.configure(
            handlers=[],
            extra={"exchange": ""}
        )
        
        # Добавляем обработчик для консоли, если требуется
        if console_enabled:
            console_config = config.get_console_config()
            logger.add(**console_config)
        
        # Добавляем обработчик для файла, если требуется
        if file_enabled and log_dir is not None:
            # Создаем директорию для логов, если не существует
            log_path = Path(log_dir) / log_filename
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            file_config = config.get_file_config(log_path)
            logger.add(**file_config)
    
    @staticmethod
    def setup_from_client_config(client_config: Any) -> None:
        """
        Настраивает логирование на основе конфигурации клиента.
        
        Args:
            client_config: Объект конфигурации клиента
            
        Returns:
            None
        """
        # Определяем уровень логирования на основе режима отладки
        level = LogLevel.DEBUG if client_config.debug_mode else LogLevel.INFO
        
        # Создаем конфигурацию логирования
        log_config = LogConfig(
            level=level,
            diagnose=client_config.debug_mode,
            backtrace=client_config.debug_mode
        )
        
        # Определяем директорию для логов
        log_dir = "logs"
        
        # Формируем имя файла лога на основе названия биржи и режима
        mode_suffix = "_test" if client_config.test_mode else ""
        log_filename = f"{client_config.exchange_name}{mode_suffix}.log"
        
        # Настраиваем логирование
        Logger.setup(
            config=log_config,
            log_dir=log_dir,
            log_filename=log_filename,
            console_enabled=True,
            file_enabled=True
        )
    
    @staticmethod
    def get_logger():
        """
        Возвращает настроенный логгер.
        
        Returns:
            logger: Объект логгера
        """
        return logger
    
    @staticmethod
    def set_exchange_context(exchange_name: str) -> None:
        """
        Устанавливает контекст биржи для логов.
        
        Args:
            exchange_name: Название биржи
            
        Returns:
            None
        """
        logger.configure(extra={"exchange": exchange_name})
    
    @staticmethod
    def with_context(**kwargs) -> Any:
        """
        Создает логгер с дополнительным контекстом.
        
        Args:
            **kwargs: Дополнительные поля контекста
            
        Returns:
            logger: Новый объект логгера с контекстом
        """
        return logger.bind(**kwargs)
    

# Настройка логирования по умолчанию
Logger.setup()

# Экспорт логгера для удобства
log = Logger.get_logger() 
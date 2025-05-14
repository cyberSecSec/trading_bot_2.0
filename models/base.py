from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any, List, Optional, TypeVar, Generic, Union
from pydantic import BaseModel, Field, validator

# Базовый класс для всех моделей данных
class BaseDataModel(BaseModel):
    """Базовый класс для всех моделей данных в системе VANTA."""
    
    class Config:
        """Конфигурация Pydantic модели."""
        extra = 'ignore'  # Игнорировать лишние поля при создании модели
        arbitrary_types_allowed = True
        
    @classmethod
    def from_exchange_data(cls, data: Dict[str, Any]) -> 'BaseDataModel':
        """
        Создает экземпляр модели из данных, полученных от биржи.
        
        Args:
            data: Данные, полученные от биржи.
            
        Returns:
            Экземпляр модели данных.
        """
        return cls(**data)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Преобразует модель в словарь.
        
        Returns:
            Словарь с данными модели.
        """
        return self.dict(exclude_none=True)


# Базовый класс для моделей рыночных данных
class BaseMarketDataModel(BaseDataModel):
    """Базовый класс для моделей рыночных данных."""
    
    symbol: str = Field(..., description="Торговый символ (например, 'BTCUSDT')")
    timestamp: datetime = Field(..., description="Временная метка данных")
    exchange: str = Field(default="bybit", description="Биржа, с которой получены данные")
    
    @validator('timestamp', pre=True)
    def validate_timestamp(cls, v):
        """Конвертирует временную метку из разных форматов в datetime."""
        if isinstance(v, (int, float)):
            # Предполагаем, что временная метка в миллисекундах
            return datetime.fromtimestamp(v / 1000)
        return v


# Базовый класс для моделей торговых операций
class BaseTradingModel(BaseDataModel):
    """Базовый класс для моделей торговых операций."""
    
    symbol: str = Field(..., description="Торговый символ (например, 'BTCUSDT')")
    timestamp: datetime = Field(..., description="Временная метка операции")
    exchange: str = Field(default="bybit", description="Биржа, на которой выполнена операция")
    
    @validator('timestamp', pre=True)
    def validate_timestamp(cls, v):
        """Конвертирует временную метку из разных форматов в datetime."""
        if isinstance(v, (int, float)):
            # Предполагаем, что временная метка в миллисекундах
            return datetime.fromtimestamp(v / 1000)
        return v 
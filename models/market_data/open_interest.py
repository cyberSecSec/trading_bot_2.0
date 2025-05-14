from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, List, Optional, ClassVar
import pandas as pd

from pydantic import Field, validator

from ..base import BaseMarketDataModel
from ..utils.converters import safe_decimal, timestamp_to_datetime

class OpenInterestData(BaseMarketDataModel):
    """
    Модель данных для представления открытого интереса.
    
    Данная модель представляет информацию о суммарном объеме открытых
    контрактов для определенного символа.
    """
    
    # Поля модели данных
    open_interest: Decimal = Field(..., description="Значение открытого интереса (в контрактах)")
    open_interest_value: Optional[Decimal] = Field(None, description="Стоимость открытого интереса (в USD)")
    
    # Дополнительные поля
    funding_rate: Optional[Decimal] = Field(None, description="Текущая ставка финансирования")
    next_funding_time: Optional[datetime] = Field(None, description="Время следующей выплаты финансирования")
    
    @validator('open_interest', 'open_interest_value', 'funding_rate', pre=True)
    def validate_decimal(cls, v):
        """Конвертирует строковые или числовые значения в Decimal."""
        return safe_decimal(v)
    
    @validator('next_funding_time', pre=True)
    def validate_datetime(cls, v):
        """Конвертирует временную метку в datetime."""
        if v is None:
            return None
        return timestamp_to_datetime(v)
    
    @classmethod
    def from_bybit_rest(cls, data: Dict[str, Any], symbol: str) -> 'OpenInterestData':
        """
        Создает экземпляр OpenInterestData из данных REST API Bybit.
        
        Args:
            data: Словарь с данными от Bybit API
            symbol: Торговый символ
            
        Returns:
            Экземпляр OpenInterestData
        """
        timestamp = timestamp_to_datetime(data.get("timestamp", data.get("time")))
        
        return cls(
            symbol=symbol,
            timestamp=timestamp,
            open_interest=data.get("openInterest", data.get("oi", 0)),
            open_interest_value=data.get("openInterestValue", None),
            funding_rate=data.get("fundingRate", None),
            next_funding_time=data.get("nextFundingTime", None)
        )
    
    @classmethod
    def from_bybit_ws(cls, data: Dict[str, Any], symbol: str) -> 'OpenInterestData':
        """
        Создает экземпляр OpenInterestData из данных WebSocket API Bybit.
        
        Args:
            data: Словарь с данными от Bybit WebSocket
            symbol: Торговый символ
            
        Returns:
            Экземпляр OpenInterestData
        """
        # Извлекаем данные из сообщения WebSocket
        item = data.get("data", data)
        
        # Если данные в виде списка, берем первый элемент
        if isinstance(item, list) and len(item) > 0:
            item = item[0]
        
        timestamp = timestamp_to_datetime(
            item.get("timestamp", item.get("ts", item.get("time")))
        )
        
        return cls(
            symbol=symbol,
            timestamp=timestamp,
            open_interest=item.get("openInterest", item.get("oi", 0)),
            open_interest_value=item.get("openInterestValue", None),
            funding_rate=item.get("fundingRate", item.get("fr", None)),
            next_funding_time=item.get("nextFundingTime", item.get("nft", None))
        )
    
    @classmethod
    def from_list(cls, data_list: List[Dict[str, Any]], symbol: str) -> List['OpenInterestData']:
        """
        Создает список экземпляров OpenInterestData из списка данных.
        
        Args:
            data_list: Список данных открытого интереса
            symbol: Торговый символ
            
        Returns:
            Список экземпляров OpenInterestData
        """
        return [cls.from_bybit_rest(item, symbol) for item in data_list]
    
    @staticmethod
    def to_dataframe(oi_list: List['OpenInterestData']) -> pd.DataFrame:
        """
        Преобразует список OpenInterestData в pandas DataFrame.
        
        Args:
            oi_list: Список экземпляров OpenInterestData
            
        Returns:
            pandas DataFrame с данными открытого интереса
        """
        data = [
            {
                "timestamp": oi.timestamp,
                "symbol": oi.symbol,
                "open_interest": float(oi.open_interest),
                "open_interest_value": float(oi.open_interest_value) if oi.open_interest_value else None,
                "funding_rate": float(oi.funding_rate) if oi.funding_rate else None,
                "next_funding_time": oi.next_funding_time
            }
            for oi in oi_list
        ]
        
        if not data:
            # Возвращаем пустой DataFrame с нужными колонками
            return pd.DataFrame(columns=[
                "timestamp", "symbol", "open_interest", 
                "open_interest_value", "funding_rate", "next_funding_time"
            ])
        
        df = pd.DataFrame(data)
        df.set_index("timestamp", inplace=True)
        return df
    
    @staticmethod
    def calculate_change(current: 'OpenInterestData', 
                          previous: 'OpenInterestData') -> Dict[str, Any]:
        """
        Вычисляет изменение открытого интереса между двумя точками.
        
        Args:
            current: Текущее значение открытого интереса
            previous: Предыдущее значение открытого интереса
            
        Returns:
            Словарь с абсолютным и процентным изменением
        """
        if not previous or previous.open_interest == 0:
            return {"absolute": Decimal('0'), "percentage": Decimal('0')}
        
        absolute_change = current.open_interest - previous.open_interest
        percentage_change = (absolute_change / previous.open_interest) * Decimal('100')
        
        return {
            "absolute": absolute_change,
            "percentage": percentage_change
        }
    
    @staticmethod
    def calculate_average(oi_list: List['OpenInterestData']) -> Optional[Decimal]:
        """
        Вычисляет среднее значение открытого интереса за период.
        
        Args:
            oi_list: Список значений открытого интереса
            
        Returns:
            Среднее значение или None, если список пуст
        """
        if not oi_list:
            return None
            
        total = sum(oi.open_interest for oi in oi_list)
        return total / Decimal(len(oi_list))
    
    @staticmethod
    def detect_anomalies(oi_list: List['OpenInterestData'], 
                           threshold_percent: Decimal = Decimal('5')) -> List[Dict[str, Any]]:
        """
        Обнаруживает аномальные изменения открытого интереса.
        
        Args:
            oi_list: Список значений открытого интереса
            threshold_percent: Пороговое значение для определения аномалии (в процентах)
            
        Returns:
            Список аномалий с указанием времени, величины изменения и типа
        """
        if not oi_list or len(oi_list) < 2:
            return []
            
        # Сортируем по времени
        sorted_oi = sorted(oi_list, key=lambda x: x.timestamp)
        
        anomalies = []
        for i in range(1, len(sorted_oi)):
            current = sorted_oi[i]
            previous = sorted_oi[i-1]
            
            change = OpenInterestData.calculate_change(current, previous)
            
            # Проверяем, превышает ли изменение пороговое значение
            if abs(change["percentage"]) >= threshold_percent:
                anomaly_type = "increase" if change["absolute"] > 0 else "decrease"
                
                anomalies.append({
                    "timestamp": current.timestamp,
                    "previous_value": previous.open_interest,
                    "current_value": current.open_interest,
                    "absolute_change": change["absolute"],
                    "percentage_change": change["percentage"],
                    "type": anomaly_type
                })
                
        return anomalies 
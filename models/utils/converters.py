from decimal import Decimal, InvalidOperation
from datetime import datetime
from typing import Union, Any, Optional

def safe_decimal(value: Any) -> Decimal:
    """
    Безопасно преобразует значение в Decimal.
    
    Args:
        value: Значение для преобразования (строка, число или None)
        
    Returns:
        Объект Decimal или Decimal('0') в случае ошибки
    """
    if value is None:
        return Decimal('0')
        
    try:
        if isinstance(value, str):
            # Удаляем лишние пробелы и нормализуем разделители
            cleaned = value.strip().replace(',', '.')
            return Decimal(cleaned)
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal('0')

def timestamp_to_datetime(timestamp: Union[int, float, str, None]) -> datetime:
    """
    Преобразует временную метку в объект datetime.
    
    Args:
        timestamp: Временная метка (в миллисекундах или секундах)
        
    Returns:
        Объект datetime или текущее время в случае ошибки
    """
    if timestamp is None:
        return datetime.now()
        
    try:
        if isinstance(timestamp, str):
            timestamp = float(timestamp)
            
        # Проверяем формат: если больше 2e10, то это миллисекунды
        if timestamp > 2e10:
            return datetime.fromtimestamp(timestamp / 1000)
        else:
            return datetime.fromtimestamp(timestamp)
    except (ValueError, TypeError, OverflowError):
        # Пробуем интерпретировать как строку с датой
        try:
            if isinstance(timestamp, str):
                return datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        except (ValueError, TypeError):
            pass
            
        return datetime.now()

def interval_to_milliseconds(interval: str) -> int:
    """
    Преобразует интервал свечей в миллисекунды.
    
    Args:
        interval: Строка с интервалом (например, '1m', '1h', '1d')
        
    Returns:
        Количество миллисекунд в интервале
    """
    # Переводим сокращенную форму Bybit в минуты
    if interval.endswith('m'):
        minutes = int(interval[:-1])
    elif interval.endswith('h'):
        minutes = int(interval[:-1]) * 60
    elif interval.endswith('d'):
        minutes = int(interval[:-1]) * 60 * 24
    elif interval.endswith('w'):
        minutes = int(interval[:-1]) * 60 * 24 * 7
    elif interval.endswith('M'):
        minutes = int(interval[:-1]) * 60 * 24 * 30
    else:
        # Предполагаем, что это минуты в формате Bybit
        try:
            minutes = int(interval)
        except ValueError:
            # Значения по умолчанию для специальных интервалов Bybit
            if interval == 'D':
                minutes = 60 * 24
            elif interval == 'W':
                minutes = 60 * 24 * 7
            elif interval == 'M':
                minutes = 60 * 24 * 30
            else:
                minutes = 1  # Значение по умолчанию - 1 минута
                
    return minutes * 60 * 1000  # Преобразуем минуты в миллисекунды 
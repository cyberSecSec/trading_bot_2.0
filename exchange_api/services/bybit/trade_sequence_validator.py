"""
Валидатор последовательности сделок для биржи Bybit.

Отвечает за проверку целостности данных о сделках,
обнаружение пропусков и отслеживание статистики.
"""

from typing import Dict, Set, List, Optional
from datetime import datetime, timedelta

from models.market_data import TradeData
from exchange_api.utils.logger import Logger

# Получаем логгер
logger = Logger.get_logger()

class TradeSequenceValidator:
    """
    Валидатор для проверки последовательности сделок.
    
    Отслеживает ID сделок для обнаружения пропусков и ведет
    статистику по обработанным сделкам.
    """
    
    def __init__(self, symbol: str, window_size: int = 1000):
        """
        Инициализирует валидатор последовательности сделок.
        
        Args:
            symbol: Торговый символ (например, "BTCUSDT")
            window_size: Размер окна для отслеживания ID сделок
        """
        self.symbol = symbol
        self.window_size = window_size
        
        # Множество для хранения последних ID сделок
        self.trade_ids: Set[str] = set()
        
        # Словарь для хранения статистики
        self.stats = {
            'total_trades': 0,
            'duplicates': 0,
            'gaps_detected': 0,
            'last_timestamp': None
        }
        
        # Наибольший и наименьший ID сделки в текущем окне
        self.min_id: Optional[str] = None
        self.max_id: Optional[str] = None
        
        # Время последней проверки статистики
        self.last_stats_time = datetime.now()
    
    def validate_trade(self, trade: TradeData) -> bool:
        """
        Проверяет сделку на уникальность и последовательность.
        
        Args:
            trade: Объект TradeData для проверки
            
        Returns:
            bool: True, если сделка новая, False, если дубликат
        """
        # Обновляем статистику
        self.stats['total_trades'] += 1
        self.stats['last_timestamp'] = trade.timestamp
        
        # Проверяем, не дубликат ли это
        if trade.id in self.trade_ids:
            self.stats['duplicates'] += 1
            return False
        
        # Добавляем ID в множество
        self.trade_ids.add(trade.id)
        
        # Обновляем минимальный и максимальный ID
        if self.min_id is None or trade.id < self.min_id:
            self.min_id = trade.id
        
        if self.max_id is None or trade.id > self.max_id:
            self.max_id = trade.id
        
        # Если размер множества превышает окно, удаляем старые ID
        if len(self.trade_ids) > self.window_size:
            # Очищаем старые ID (простая реализация - полная очистка)
            # В реальном приложении нужно более сложное управление окном
            old_size = len(self.trade_ids)
            self.trade_ids = {id for id in self.trade_ids if id >= self.min_id}
            new_size = len(self.trade_ids)
            
            if old_size - new_size > 0:
                logger.debug(f"Удалено {old_size - new_size} старых ID сделок из валидатора для {self.symbol}")
        
        # Логируем статистику каждые 5 минут
        if datetime.now() - self.last_stats_time > timedelta(minutes=5):
            self.log_statistics()
            self.last_stats_time = datetime.now()
        
        return True
    
    def check_for_gaps(self, trade_ids: List[str]) -> List[str]:
        """
        Проверяет наличие пропусков в последовательности ID сделок.
        
        Args:
            trade_ids: Список ID сделок для проверки
            
        Returns:
            List[str]: Список диапазонов пропущенных ID
        """
        # Преобразуем строковые ID в числовые, если это возможно
        try:
            numeric_ids = [int(id) for id in trade_ids]
            numeric_ids.sort()
            
            # Ищем пропуски в последовательности
            gaps = []
            for i in range(1, len(numeric_ids)):
                if numeric_ids[i] - numeric_ids[i-1] > 1:
                    gap = f"{numeric_ids[i-1]+1}-{numeric_ids[i]-1}"
                    gaps.append(gap)
                    self.stats['gaps_detected'] += 1
            
            return gaps
            
        except ValueError:
            # Если ID не числовые, просто возвращаем пустой список
            logger.warning(f"Не удалось преобразовать ID сделок в числовые для {self.symbol}")
            return []
    
    def log_statistics(self):
        """
        Логирует статистику обработки сделок.
        """
        logger.info(f"Статистика сделок для {self.symbol}: "
                   f"Всего обработано: {self.stats['total_trades']}, "
                   f"Дубликатов: {self.stats['duplicates']}, "
                   f"Обнаружено пропусков: {self.stats['gaps_detected']}")
        
    def reset(self):
        """
        Сбрасывает состояние валидатора.
        """
        self.trade_ids.clear()
        self.stats = {
            'total_trades': 0,
            'duplicates': 0,
            'gaps_detected': 0,
            'last_timestamp': None
        }
        self.min_id = None
        self.max_id = None
        self.last_stats_time = datetime.now() 
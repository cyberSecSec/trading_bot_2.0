"""
Анализатор ликвидаций для Bybit.

Предоставляет функционал для анализа потока ликвидаций,
выявления значимых событий и паттернов.
"""

from typing import Dict, List, Any, Optional, Set
from decimal import Decimal
from datetime import datetime, timedelta
import collections

from models.market_data import LiquidationData, LiquidationSide
from exchange_api.utils.logger import Logger

# Получаем логгер
logger = Logger.get_logger()

class LiquidationAnalyzer:
    """
    Анализатор данных о ликвидациях.
    
    Предоставляет функционал для фильтрации, агрегирования и выявления
    значимых паттернов в потоке ликвидаций.
    """
    
    def __init__(self, 
                 large_liquidation_threshold: Decimal = Decimal('10.0'),
                 cascade_time_window_seconds: int = 60,
                 cascade_min_volume: Decimal = Decimal('50.0'),
                 max_liquidations_history: int = 1000):
        """
        Инициализирует анализатор ликвидаций.
        
        Args:
            large_liquidation_threshold: Пороговое значение объема для определения крупной ликвидации
            cascade_time_window_seconds: Временное окно для определения каскада ликвидаций (в секундах)
            cascade_min_volume: Минимальный суммарный объем для определения каскада ликвидаций
            max_liquidations_history: Максимальное количество ликвидаций для хранения в истории
        """
        # Пороговые значения
        self.large_liquidation_threshold = Decimal(large_liquidation_threshold)
        self.cascade_time_window_seconds = cascade_time_window_seconds
        self.cascade_min_volume = Decimal(cascade_min_volume)
        self.max_liquidations_history = max_liquidations_history
        
        # Хранение истории ликвидаций с ограничением размера
        self.recent_liquidations: collections.deque = collections.deque(maxlen=max_liquidations_history)
        
        # Отслеживание последних анализов
        self.last_analysis_time = datetime.now()
        self.analysis_interval_seconds = 15  # Время между анализами
        
        # Статистика
        self.stats = {
            'total_count': 0,
            'long_liquidations': 0,
            'short_liquidations': 0,
            'total_volume': Decimal('0'),
            'large_liquidations': 0,
            'cascade_events': 0,
            'symbols': set()
        }
    
    def register_liquidation(self, liquidation: LiquidationData) -> None:
        """
        Регистрирует ликвидацию в анализаторе.
        
        Args:
            liquidation: Данные о ликвидации
        """
        # Добавляем ликвидацию в историю
        self.recent_liquidations.append(liquidation)
        
        # Обновляем статистику
        self.stats['total_count'] += 1
        self.stats['symbols'].add(liquidation.symbol)
        self.stats['total_volume'] += liquidation.quantity
        
        if liquidation.is_long_liquidation():
            self.stats['long_liquidations'] += 1
        else:
            self.stats['short_liquidations'] += 1
            
        if self.is_large_liquidation(liquidation):
            self.stats['large_liquidations'] += 1
    
    def is_large_liquidation(self, liquidation: LiquidationData) -> bool:
        """
        Определяет, является ли ликвидация крупной.
        
        Args:
            liquidation: Данные о ликвидации
            
        Returns:
            bool: True, если ликвидация является крупной
        """
        return liquidation.quantity >= self.large_liquidation_threshold
    
    def should_analyze(self) -> bool:
        """
        Определяет, нужно ли выполнять анализ ликвидаций.
        
        Предотвращает слишком частый анализ, который может создать избыточную нагрузку.
        
        Returns:
            bool: True, если нужно выполнить анализ
        """
        now = datetime.now()
        if (now - self.last_analysis_time).total_seconds() >= self.analysis_interval_seconds:
            self.last_analysis_time = now
            return True
        return False
    
    def get_recent_liquidations(self, 
                               symbol: Optional[str] = None, 
                               time_window_seconds: Optional[int] = None) -> List[LiquidationData]:
        """
        Возвращает список недавних ликвидаций с возможностью фильтрации.
        
        Args:
            symbol: Если указан, возвращает только ликвидации для этого символа
            time_window_seconds: Если указан, возвращает только ликвидации за указанный период
            
        Returns:
            List[LiquidationData]: Список ликвидаций с примененными фильтрами
        """
        result = list(self.recent_liquidations)
        
        # Фильтрация по символу
        if symbol:
            result = [liq for liq in result if liq.symbol == symbol]
        
        # Фильтрация по временному окну
        if time_window_seconds:
            cutoff_time = datetime.now() - timedelta(seconds=time_window_seconds)
            result = [liq for liq in result if liq.timestamp >= cutoff_time]
        
        return result
    
    def analyze_liquidations(self, 
                            liquidations: List[LiquidationData]) -> Dict[str, Any]:
        """
        Анализирует список ликвидаций для выявления паттернов.
        
        Args:
            liquidations: Список ликвидаций для анализа
            
        Returns:
            Dict[str, Any]: Результаты анализа, включая информацию о каскадах и крупных ликвидациях
        """
        # Подготовка результата анализа
        result = {
            'total_count': len(liquidations),
            'total_volume': Decimal('0'),
            'long_liquidations_count': 0,
            'short_liquidations_count': 0,
            'large_liquidations': [],
            'cascade_detected': False,
            'cascade_side': None,
            'cascade_volume': Decimal('0'),
            'symbols': set(),
            'volume_by_symbol': {},
            'largest_liquidation_volume': Decimal('0'),
            'largest_liquidation_side': None,
        }
        
        if not liquidations:
            return result
        
        # Сортируем ликвидации по времени
        sorted_liquidations = sorted(liquidations, key=lambda x: x.timestamp)
        
        # Группируем ликвидации по символу
        liquidations_by_symbol = {}
        for liq in liquidations:
            symbol = liq.symbol
            result['symbols'].add(symbol)
            
            if symbol not in liquidations_by_symbol:
                liquidations_by_symbol[symbol] = []
            liquidations_by_symbol[symbol].append(liq)
            
            # Обновляем базовую статистику
            result['total_volume'] += liq.quantity
            
            # Обновляем статистику по сторонам
            if liq.is_long_liquidation():
                result['long_liquidations_count'] += 1
            else:
                result['short_liquidations_count'] += 1
            
            # Обновляем статистику по объему по символам
            if symbol not in result['volume_by_symbol']:
                result['volume_by_symbol'][symbol] = {
                    'total': Decimal('0'),
                    'long': Decimal('0'),
                    'short': Decimal('0')
                }
            
            result['volume_by_symbol'][symbol]['total'] += liq.quantity
            if liq.is_long_liquidation():
                result['volume_by_symbol'][symbol]['long'] += liq.quantity
            else:
                result['volume_by_symbol'][symbol]['short'] += liq.quantity
            
            # Фиксируем крупные ликвидации
            if self.is_large_liquidation(liq):
                result['large_liquidations'].append({
                    'symbol': liq.symbol,
                    'side': liq.side.value,
                    'volume': liq.quantity,
                    'price': liq.price,
                    'timestamp': liq.timestamp,
                    'value': liq.value()
                })
                
                # Обновляем информацию о самой крупной ликвидации
                if liq.quantity > result['largest_liquidation_volume']:
                    result['largest_liquidation_volume'] = liq.quantity
                    result['largest_liquidation_side'] = liq.side
        
        # Анализ каскадных ликвидаций по каждому символу
        for symbol, symbol_liquidations in liquidations_by_symbol.items():
            if LiquidationData.is_cascade(
                symbol_liquidations, 
                self.cascade_time_window_seconds, 
                self.cascade_min_volume
            ):
                # Обнаружен каскад ликвидаций
                result['cascade_detected'] = True
                
                # Определяем доминирующую сторону каскада
                long_count = sum(1 for liq in symbol_liquidations if liq.is_long_liquidation())
                short_count = len(symbol_liquidations) - long_count
                
                cascade_side = LiquidationSide.SELL if long_count > short_count else LiquidationSide.BUY
                result['cascade_side'] = cascade_side
                
                # Рассчитываем объем каскада
                cascade_volume = sum(liq.quantity for liq in symbol_liquidations)
                result['cascade_volume'] = cascade_volume
                
                # Логируем обнаружение каскада
                side_str = "длинных" if cascade_side == LiquidationSide.SELL else "коротких"
                logger.warning(
                    f"Обнаружен каскад ликвидаций {side_str} позиций для {symbol}! "
                    f"Объем: {cascade_volume}, Количество: {len(symbol_liquidations)}"
                )
                
                # Увеличиваем счетчик каскадов в общей статистике
                self.stats['cascade_events'] += 1
                
                # Так как каскад обнаружен, можно прервать цикл
                break
        
        return result
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Возвращает общую статистику ликвидаций.
        
        Returns:
            Dict[str, Any]: Статистика ликвидаций
        """
        return {
            'total_count': self.stats['total_count'],
            'long_liquidations': self.stats['long_liquidations'],
            'short_liquidations': self.stats['short_liquidations'],
            'total_volume': float(self.stats['total_volume']),
            'large_liquidations': self.stats['large_liquidations'],
            'cascade_events': self.stats['cascade_events'],
            'symbols': list(self.stats['symbols']),
            'long_ratio': self.stats['long_liquidations'] / max(1, self.stats['total_count']),
            'short_ratio': self.stats['short_liquidations'] / max(1, self.stats['total_count'])
        }
    
    def reset_statistics(self) -> None:
        """
        Сбрасывает статистику ликвидаций.
        """
        self.stats = {
            'total_count': 0,
            'long_liquidations': 0,
            'short_liquidations': 0,
            'total_volume': Decimal('0'),
            'large_liquidations': 0,
            'cascade_events': 0,
            'symbols': set()
        }
        self.recent_liquidations.clear() 
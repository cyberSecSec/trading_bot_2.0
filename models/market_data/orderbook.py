from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, List, Optional, Tuple, ClassVar
import pandas as pd
import numpy as np

from pydantic import Field, validator

from ..base import BaseMarketDataModel
from ..utils.converters import safe_decimal, timestamp_to_datetime

class OrderBookLevel:
    """Представляет один ценовой уровень в стакане ордеров."""
    
    def __init__(self, price: Decimal, quantity: Decimal):
        """
        Инициализирует уровень стакана ордеров.
        
        Args:
            price: Цена уровня
            quantity: Количество на данном уровне
        """
        self.price = price
        self.quantity = quantity
        
    @property
    def value(self) -> Decimal:
        """Возвращает общую стоимость уровня (цена * количество)."""
        return self.price * self.quantity
        
    def to_tuple(self) -> Tuple[Decimal, Decimal]:
        """Возвращает уровень в виде кортежа (price, quantity)."""
        return (self.price, self.quantity)
        
    def to_list(self) -> List[Decimal]:
        """Возвращает уровень в виде списка [price, quantity]."""
        return [self.price, self.quantity]
        
    def to_dict(self) -> Dict[str, Decimal]:
        """Возвращает уровень в виде словаря {'price': price, 'quantity': quantity}."""
        return {'price': self.price, 'quantity': self.quantity}
        
    @classmethod
    def from_tuple(cls, data: Tuple) -> 'OrderBookLevel':
        """Создает уровень из кортежа (price, quantity)."""
        return cls(price=safe_decimal(data[0]), quantity=safe_decimal(data[1]))
        
    @classmethod
    def from_list(cls, data: List) -> 'OrderBookLevel':
        """Создает уровень из списка [price, quantity]."""
        return cls(price=safe_decimal(data[0]), quantity=safe_decimal(data[1]))
        
    @classmethod
    def from_dict(cls, data: Dict) -> 'OrderBookLevel':
        """Создает уровень из словаря {'price': price, 'quantity': quantity}."""
        return cls(
            price=safe_decimal(data.get('price', data.get('p', 0))),
            quantity=safe_decimal(data.get('quantity', data.get('qty', data.get('q', 0))))
        )


class OrderBookData(BaseMarketDataModel):
    """
    Модель данных для представления стакана ордеров (OrderBook).
    
    Представляет снимок стакана ордеров с бид и аск уровнями.
    """
    
    # Поля модели данных
    bids: List[OrderBookLevel] = Field(default_factory=list, description="Уровни спроса (биды)")
    asks: List[OrderBookLevel] = Field(default_factory=list, description="Уровни предложения (аски)")
    
    # Вычисляемые поля
    update_id: Optional[int] = Field(None, description="ID обновления стакана")
    is_snapshot: bool = Field(default=True, description="Является ли это полным снимком стакана")
    
    class Config:
        """Конфигурация модели Pydantic."""
        json_encoders = {
            OrderBookLevel: lambda l: l.to_list()
        }
        
    @validator('bids', 'asks', pre=True)
    def validate_levels(cls, v):
        """Конвертирует уровни в объекты OrderBookLevel."""
        if not v:
            return []
            
        result = []
        for level in v:
            if isinstance(level, OrderBookLevel):
                result.append(level)
            elif isinstance(level, (list, tuple)) and len(level) >= 2:
                result.append(OrderBookLevel.from_list(level))
            elif isinstance(level, dict):
                result.append(OrderBookLevel.from_dict(level))
        return result
    
    @classmethod
    def from_bybit_rest(cls, data: Dict[str, Any], symbol: str) -> 'OrderBookData':
        """
        Создает экземпляр OrderBookData из данных REST API Bybit.
        
        Args:
            data: Словарь с данными от Bybit API
            symbol: Торговый символ
            
        Returns:
            Экземпляр OrderBookData
        """
        timestamp = timestamp_to_datetime(data.get("time", data.get("timestamp")))
        
        # Получаем и преобразуем биды и аски
        bids_data = data.get("bids", data.get("b", []))
        asks_data = data.get("asks", data.get("a", []))
        
        bids = [OrderBookLevel.from_list(level) for level in bids_data]
        asks = [OrderBookLevel.from_list(level) for level in asks_data]
        
        # Сортируем биды по убыванию цены (лучшие сверху)
        bids.sort(key=lambda x: x.price, reverse=True)
        
        # Сортируем аски по возрастанию цены (лучшие сверху)
        asks.sort(key=lambda x: x.price)
        
        return cls(
            symbol=symbol,
            timestamp=timestamp,
            bids=bids,
            asks=asks,
            update_id=data.get("update_id"),
            is_snapshot=True
        )
    
    @classmethod
    def from_bybit_ws(cls, data: Dict[str, Any], symbol: str) -> 'OrderBookData':
        """
        Создает экземпляр OrderBookData из данных WebSocket API Bybit.
        
        Args:
            data: Словарь с данными от Bybit WebSocket
            symbol: Торговый символ
            
        Returns:
            Экземпляр OrderBookData
        """
        # Извлекаем данные из сообщения WebSocket
        message_data = data.get("data", data)
        
        timestamp = timestamp_to_datetime(
            message_data.get("timestamp", message_data.get("t", data.get("ts")))
        )
        
        # Получаем и преобразуем биды и аски
        bids_data = message_data.get("bids", message_data.get("b", []))
        asks_data = message_data.get("asks", message_data.get("a", []))
        
        bids = [OrderBookLevel.from_list(level) for level in bids_data]
        asks = [OrderBookLevel.from_list(level) for level in asks_data]
        
        # Сортируем биды по убыванию цены
        bids.sort(key=lambda x: x.price, reverse=True)
        
        # Сортируем аски по возрастанию цены
        asks.sort(key=lambda x: x.price)
        
        # Определяем тип сообщения (снимок или обновление)
        is_snapshot = message_data.get("type", "") == "snapshot"
        
        return cls(
            symbol=symbol,
            timestamp=timestamp,
            bids=bids,
            asks=asks,
            update_id=message_data.get("update_id", message_data.get("u")),
            is_snapshot=is_snapshot
        )
    
    def apply_delta(self, delta: 'OrderBookData') -> 'OrderBookData':
        """
        Применяет дельта-обновление к текущему стакану.
        
        Args:
            delta: Дельта-обновление стакана
            
        Returns:
            Новый экземпляр OrderBookData с примененными изменениями
        """
        # Создаем словари для быстрого поиска по цене
        bids_dict = {level.price: level.quantity for level in self.bids}
        asks_dict = {level.price: level.quantity for level in self.asks}
        
        # Применяем обновления для бидов
        for bid in delta.bids:
            if bid.quantity == Decimal('0'):
                # Удаляем уровень, если количество стало 0
                bids_dict.pop(bid.price, None)
            else:
                # Обновляем или добавляем уровень
                bids_dict[bid.price] = bid.quantity
        
        # Применяем обновления для асков
        for ask in delta.asks:
            if ask.quantity == Decimal('0'):
                # Удаляем уровень, если количество стало 0
                asks_dict.pop(ask.price, None)
            else:
                # Обновляем или добавляем уровень
                asks_dict[ask.price] = ask.quantity
        
        # Преобразуем обратно в списки OrderBookLevel и сортируем
        new_bids = [OrderBookLevel(price, qty) for price, qty in bids_dict.items()]
        new_bids.sort(key=lambda x: x.price, reverse=True)
        
        new_asks = [OrderBookLevel(price, qty) for price, qty in asks_dict.items()]
        new_asks.sort(key=lambda x: x.price)
        
        # Создаем новый экземпляр с обновленными данными
        return OrderBookData(
            symbol=self.symbol,
            timestamp=delta.timestamp,  # Используем временную метку из дельты
            bids=new_bids,
            asks=new_asks,
            update_id=delta.update_id,
            is_snapshot=False
        )
    
    def to_dataframe(self) -> Dict[str, pd.DataFrame]:
        """
        Преобразует стакан ордеров в pandas DataFrame.
        
        Returns:
            Словарь из двух DataFrame: {'bids': df_bids, 'asks': df_asks}
        """
        bids_data = [
            {
                "price": float(level.price),
                "quantity": float(level.quantity),
                "value": float(level.value)
            }
            for level in self.bids
        ]
        
        asks_data = [
            {
                "price": float(level.price),
                "quantity": float(level.quantity),
                "value": float(level.value)
            }
            for level in self.asks
        ]
        
        df_bids = pd.DataFrame(bids_data) if bids_data else pd.DataFrame(columns=["price", "quantity", "value"])
        df_asks = pd.DataFrame(asks_data) if asks_data else pd.DataFrame(columns=["price", "quantity", "value"])
        
        # Устанавливаем индексы по цене
        if not df_bids.empty:
            df_bids.set_index("price", inplace=True)
        if not df_asks.empty:
            df_asks.set_index("price", inplace=True)
        
        return {"bids": df_bids, "asks": df_asks}
    
    def best_bid(self) -> Optional[OrderBookLevel]:
        """Возвращает лучший бид (наивысшую цену покупки)."""
        return self.bids[0] if self.bids else None
    
    def best_ask(self) -> Optional[OrderBookLevel]:
        """Возвращает лучший аск (наименьшую цену продажи)."""
        return self.asks[0] if self.asks else None
    
    def mid_price(self) -> Optional[Decimal]:
        """Возвращает среднюю цену между лучшим бидом и аском."""
        best_bid = self.best_bid()
        best_ask = self.best_ask()
        
        if best_bid and best_ask:
            return (best_bid.price + best_ask.price) / Decimal('2')
        return None
    
    def spread(self) -> Optional[Decimal]:
        """Возвращает спред между лучшим аском и бидом."""
        best_bid = self.best_bid()
        best_ask = self.best_ask()
        
        if best_bid and best_ask:
            return best_ask.price - best_bid.price
        return None
    
    def spread_percentage(self) -> Optional[Decimal]:
        """Возвращает процентный спред относительно средней цены."""
        spread = self.spread()
        mid_price = self.mid_price()
        
        if spread is not None and mid_price is not None and mid_price > 0:
            return (spread / mid_price) * Decimal('100')
        return None
    
    def volume_at_price(self, price: Decimal) -> Decimal:
        """Возвращает общий объем на указанном ценовом уровне."""
        volume = Decimal('0')
        
        # Ищем в бидах
        for level in self.bids:
            if level.price == price:
                volume += level.quantity
        
        # Ищем в асках
        for level in self.asks:
            if level.price == price:
                volume += level.quantity
        
        return volume
    
    def volume_up_to(self, price: Decimal) -> Dict[str, Decimal]:
        """
        Возвращает накопленный объем до указанной цены.
        
        Args:
            price: Целевая цена
            
        Returns:
            Словарь {'bids': bid_volume, 'asks': ask_volume}
        """
        bid_volume = Decimal('0')
        ask_volume = Decimal('0')
        
        # Суммируем объем бидов выше указанной цены
        for level in self.bids:
            if level.price >= price:
                bid_volume += level.quantity
        
        # Суммируем объем асков ниже указанной цены
        for level in self.asks:
            if level.price <= price:
                ask_volume += level.quantity
        
        return {"bids": bid_volume, "asks": ask_volume}
    
    def imbalance(self) -> Decimal:
        """
        Возвращает дисбаланс между объемами спроса и предложения.
        
        Положительное значение указывает на превышение спроса,
        отрицательное - на превышение предложения.
        """
        bid_volume = sum(level.quantity for level in self.bids)
        ask_volume = sum(level.quantity for level in self.asks)
        
        total_volume = bid_volume + ask_volume
        
        if total_volume > 0:
            return (bid_volume - ask_volume) / total_volume
        return Decimal('0') 
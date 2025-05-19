"""
Тесты для сервиса доступа к данным о сделках Bybit.

Проверяет функциональность получения сделок через REST API
и подписки на обновления через WebSocket.
"""

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from exchange_api.core.config import ClientConfig
from exchange_api.services.bybit.market_data_rest_service import BybitMarketDataRestProvider
from exchange_api.services.bybit.market_data_stream_service import BybitMarketDataStreamProvider
from exchange_api.services.bybit.trade_sequence_validator import TradeSequenceValidator

from models.market_data import TradeData, TradeSide


class TestTradeService(unittest.TestCase):
    """Тесты для сервиса доступа к данным о сделках Bybit."""
    
    def setUp(self):
        """Подготовка тестового окружения."""
        # Создаем тестовую конфигурацию
        self.config = ClientConfig(
            exchange_name="bybit",
            test_mode=True
        )
        
        # Создаем тестовый объект TradeData
        self.sample_trade = TradeData(
            symbol="BTCUSDT",
            timestamp=datetime.now(),
            id="12345",
            price=50000.0,
            quantity=0.01,
            side=TradeSide.BUY,
            is_buyer_maker=False
        )
        
        # Подготавливаем тестовый ответ от API
        self.sample_rest_response = {
            'retCode': 0,
            'result': {
                'list': [
                    {
                        'id': '12345',
                        'symbol': 'BTCUSDT',
                        'price': '50000.0',
                        'qty': '0.01',
                        'side': 'Buy',
                        'time': '1620000000000',
                        'isBuyerMaker': False
                    },
                    {
                        'id': '12346',
                        'symbol': 'BTCUSDT',
                        'price': '50001.0',
                        'qty': '0.02',
                        'side': 'Sell',
                        'time': '1620000001000',
                        'isBuyerMaker': True
                    }
                ]
            }
        }
        
        # Подготавливаем тестовое сообщение WebSocket
        self.sample_ws_message = {
            'topic': 'publicTrade.BTCUSDT',
            'data': [
                {
                    'i': '12347',
                    'p': '50002.0',
                    'q': '0.03',
                    'S': 'Buy',
                    't': '1620000002000',
                    'm': False
                }
            ]
        }
    
    @patch('exchange_api.connection.ConnectionManager')
    async def test_get_recent_trades(self, mock_connection):
        """Тест метода get_recent_trades."""
        # Настраиваем поведение мока соединения
        mock_connection_instance = MagicMock()
        mock_connection_instance.get = AsyncMock(return_value=self.sample_rest_response)
        mock_connection.return_value = mock_connection_instance
        
        # Создаем экземпляр провайдера с моком соединения
        provider = BybitMarketDataRestProvider(self.config, mock_connection_instance)
        
        # Вызываем тестируемый метод
        trades = await provider.get_recent_trades("BTCUSDT", limit=10)
        
        # Проверяем, что запрос был выполнен с правильными параметрами
        mock_connection_instance.get.assert_called_once()
        args, kwargs = mock_connection_instance.get.call_args
        self.assertEqual(args[0], "/v5/market/recent-trade")
        self.assertEqual(kwargs['params']['symbol'], "BTCUSDT")
        self.assertEqual(kwargs['params']['limit'], 10)
        
        # Проверяем, что результат содержит правильное количество сделок
        self.assertEqual(len(trades), 2)
        
        # Проверяем, что сделки были правильно преобразованы
        self.assertEqual(trades[0].id, "12345")
        self.assertEqual(trades[0].side, TradeSide.BUY)
        self.assertEqual(float(trades[0].price), 50000.0)
        
        self.assertEqual(trades[1].id, "12346")
        self.assertEqual(trades[1].side, TradeSide.SELL)
        self.assertEqual(float(trades[1].price), 50001.0)
    
    @patch('exchange_api.exchanges.bybit.websocket_manager.BybitWebSocketManager')
    async def test_subscribe_to_trades(self, mock_ws_manager):
        """Тест метода subscribe_to_trades."""
        # Настраиваем поведение мока WebSocket менеджера
        mock_ws_manager_instance = MagicMock()
        mock_ws_manager_instance.connect = AsyncMock()
        mock_ws_manager_instance.subscribe = AsyncMock()
        mock_ws_manager.return_value = mock_ws_manager_instance
        
        # Создаем экземпляр провайдера с моком WebSocket менеджера
        provider = BybitMarketDataStreamProvider(self.config, mock_ws_manager_instance)
        
        # Мок для callback-функции
        callback = AsyncMock()
        
        # Вызываем тестируемый метод
        subscription_id = await provider.subscribe_to_trades("BTCUSDT", callback)
        
        # Проверяем, что соединение было установлено
        mock_ws_manager_instance.connect.assert_called_once()
        
        # Проверяем, что была выполнена подписка на нужный канал
        mock_ws_manager_instance.subscribe.assert_called_once()
        args, kwargs = mock_ws_manager_instance.subscribe.call_args
        self.assertEqual(args[0], "publicTrade.BTCUSDT")
        
        # Проверяем, что подписка была сохранена
        self.assertIn(subscription_id, provider.subscriptions)
        self.assertEqual(provider.subscriptions[subscription_id]['channel'], "publicTrade.BTCUSDT")
        self.assertEqual(provider.subscriptions[subscription_id]['symbol'], "BTCUSDT")
        
        # Проверяем, что был создан валидатор последовательности
        self.assertIsInstance(provider.subscriptions[subscription_id]['sequence_validator'], TradeSequenceValidator)
    
    @patch('exchange_api.exchanges.bybit.websocket_manager.BybitWebSocketManager')
    async def test_on_message_trades(self, mock_ws_manager):
        """Тест обработки сообщений о сделках."""
        # Настраиваем поведение мока WebSocket менеджера
        mock_ws_manager_instance = MagicMock()
        mock_ws_manager_instance.connect = AsyncMock()
        mock_ws_manager_instance.subscribe = AsyncMock()
        mock_ws_manager.return_value = mock_ws_manager_instance
        
        # Создаем экземпляр провайдера с моком WebSocket менеджера
        provider = BybitMarketDataStreamProvider(self.config, mock_ws_manager_instance)
        
        # Мок для callback-функции
        callback = AsyncMock()
        
        # Вызываем метод subscribe_to_trades
        subscription_id = await provider.subscribe_to_trades("BTCUSDT", callback)
        
        # Симулируем получение сообщения
        await provider._on_message(self.sample_ws_message)
        
        # Проверяем, что callback был вызван с правильными данными
        callback.assert_called_once()
        args, kwargs = callback.call_args
        trade = args[0]
        
        # Проверяем аргументы вызова
        self.assertIsInstance(trade, TradeData)
        self.assertEqual(trade.id, "12347")
        self.assertEqual(trade.symbol, "BTCUSDT")
        self.assertEqual(float(trade.price), 50002.0)
        self.assertEqual(float(trade.quantity), 0.03)
        self.assertEqual(trade.side, TradeSide.BUY)
    
    def test_trade_sequence_validator(self):
        """Тест валидатора последовательности сделок."""
        # Создаем валидатор
        validator = TradeSequenceValidator("BTCUSDT")
        
        # Создаем тестовые сделки
        trade1 = TradeData(
            symbol="BTCUSDT",
            timestamp=datetime.now(),
            id="1001",
            price=50000.0,
            quantity=0.01,
            side=TradeSide.BUY,
            is_buyer_maker=False
        )
        
        trade2 = TradeData(
            symbol="BTCUSDT",
            timestamp=datetime.now(),
            id="1002",
            price=50001.0,
            quantity=0.02,
            side=TradeSide.SELL,
            is_buyer_maker=True
        )
        
        # Дубликат первой сделки
        trade_dup = TradeData(
            symbol="BTCUSDT",
            timestamp=datetime.now(),
            id="1001",
            price=50000.0,
            quantity=0.01,
            side=TradeSide.BUY,
            is_buyer_maker=False
        )
        
        # Проверяем, что первая сделка валидна
        self.assertTrue(validator.validate_trade(trade1))
        
        # Проверяем, что вторая сделка валидна
        self.assertTrue(validator.validate_trade(trade2))
        
        # Проверяем, что дубликат определяется
        self.assertFalse(validator.validate_trade(trade_dup))
        
        # Проверяем, что статистика обновляется
        self.assertEqual(validator.stats['total_trades'], 3)
        self.assertEqual(validator.stats['duplicates'], 1)
        
        # Проверяем обнаружение пропусков
        gaps = validator.check_for_gaps(["1001", "1003", "1004"])
        self.assertEqual(len(gaps), 1)
        self.assertEqual(gaps[0], "1002-1002")  # Пропуск ID 1002


if __name__ == '__main__':
    unittest.main() 
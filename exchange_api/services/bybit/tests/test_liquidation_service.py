"""
Тесты для сервиса доступа к данным о ликвидациях Bybit.

Проверяет функциональность подписки на обновления
о ликвидациях через WebSocket.
"""

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from decimal import Decimal

from exchange_api.core.config import ClientConfig
from exchange_api.services.bybit.market_data_stream_service import BybitMarketDataStreamProvider
from exchange_api.exchanges.bybit.handlers.liquidation_handler import LiquidationMessageHandler
from exchange_api.services.bybit.liquidation_analyzer import LiquidationAnalyzer

from models.market_data import LiquidationData, LiquidationSide


class TestLiquidationService(unittest.TestCase):
    """Тесты для сервиса доступа к данным о ликвидациях Bybit."""
    
    def setUp(self):
        """Подготовка тестового окружения."""
        # Создаем тестовую конфигурацию
        self.config = ClientConfig(
            exchange_name="bybit",
            test_mode=True
        )
        
        # Создаем тестовый объект LiquidationData
        self.sample_liquidation = LiquidationData(
            symbol="BTCUSDT",
            timestamp=datetime.now(),
            price=Decimal("50000.0"),
            quantity=Decimal("2.5"),
            side=LiquidationSide.SELL
        )
        
        # Подготавливаем тестовое сообщение WebSocket
        self.sample_ws_message = {
            'topic': 'liquidation.BTCUSDT',
            'data': [
                {
                    'symbol': 'BTCUSDT',
                    'side': 'Sell',
                    'price': '50000.00',
                    'qty': '2.5',
                    'time': 1675942858664
                }
            ]
        }
    
    @patch('exchange_api.exchanges.bybit.websocket_manager.BybitWebSocketManager')
    async def test_subscribe_to_liquidations(self, mock_ws_manager):
        """Тест метода subscribe_to_liquidations."""
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
        subscription_id = await provider.subscribe_to_liquidations("BTCUSDT", callback)
        
        # Проверяем, что соединение было установлено
        mock_ws_manager_instance.connect.assert_called_once()
        
        # Проверяем, что была выполнена подписка на нужный канал
        mock_ws_manager_instance.subscribe.assert_called_once()
        args, kwargs = mock_ws_manager_instance.subscribe.call_args
        self.assertEqual(args[0], "liquidation.BTCUSDT")
        
        # Проверяем, что подписка была сохранена
        self.assertIn(subscription_id, provider.subscriptions)
        self.assertEqual(provider.subscriptions[subscription_id]['channel'], "liquidation.BTCUSDT")
        self.assertEqual(provider.subscriptions[subscription_id]['symbol'], "BTCUSDT")
        
        # Проверяем, что был создан обработчик сообщений о ликвидациях
        self.assertIn('liquidation_handler', provider.subscriptions[subscription_id])
        self.assertIsInstance(provider.subscriptions[subscription_id]['liquidation_handler'], LiquidationMessageHandler)
        
        # Проверяем, что был создан анализатор ликвидаций
        self.assertIn('liquidation_analyzer', provider.subscriptions[subscription_id])
        self.assertIsInstance(provider.subscriptions[subscription_id]['liquidation_analyzer'], LiquidationAnalyzer)
    
    @patch('exchange_api.exchanges.bybit.websocket_manager.BybitWebSocketManager')
    async def test_on_message_liquidations(self, mock_ws_manager):
        """Тест обработки сообщений о ликвидациях."""
        # Настраиваем поведение мока WebSocket менеджера
        mock_ws_manager_instance = MagicMock()
        mock_ws_manager_instance.connect = AsyncMock()
        mock_ws_manager_instance.subscribe = AsyncMock()
        mock_ws_manager.return_value = mock_ws_manager_instance
        
        # Создаем экземпляр провайдера с моком WebSocket менеджера
        provider = BybitMarketDataStreamProvider(self.config, mock_ws_manager_instance)
        
        # Мок для callback-функции
        callback = AsyncMock()
        
        # Вызываем метод subscribe_to_liquidations
        subscription_id = await provider.subscribe_to_liquidations("BTCUSDT", callback)
        
        # Симулируем получение сообщения
        await provider._on_message(self.sample_ws_message)
        
        # Проверяем, что callback был вызван с правильными данными
        callback.assert_called_once()
        args, kwargs = callback.call_args
        liquidation = args[0]
        
        # Проверяем аргументы вызова
        self.assertIsInstance(liquidation, LiquidationData)
        self.assertEqual(liquidation.symbol, "BTCUSDT")
        self.assertEqual(liquidation.side, LiquidationSide.SELL)
        self.assertEqual(liquidation.price, Decimal("50000.0"))
        self.assertEqual(liquidation.quantity, Decimal("2.5"))
    
    def test_liquidation_analyzer(self):
        """Тест анализатора ликвидаций."""
        # Создаем анализатор
        analyzer = LiquidationAnalyzer(
            large_liquidation_threshold=Decimal('1.0'),  # Низкий порог для тестирования
            cascade_time_window_seconds=60,
            cascade_min_volume=Decimal('5.0')  # Низкий порог для тестирования
        )
        
        # Регистрируем тестовую ликвидацию
        analyzer.register_liquidation(self.sample_liquidation)
        
        # Проверяем, что ликвидация была правильно отмечена как крупная
        self.assertTrue(analyzer.is_large_liquidation(self.sample_liquidation))
        
        # Проверяем статистику
        stats = analyzer.get_statistics()
        self.assertEqual(stats['total_count'], 1)
        self.assertEqual(stats['long_liquidations'], 1)  # SELL = ликвидация длинной позиции
        self.assertEqual(stats['short_liquidations'], 0)
        self.assertEqual(stats['large_liquidations'], 1)
        
        # Получаем недавние ликвидации
        recent_liquidations = analyzer.get_recent_liquidations()
        self.assertEqual(len(recent_liquidations), 1)
        
        # Анализируем ликвидации
        analysis = analyzer.analyze_liquidations(recent_liquidations)
        self.assertEqual(analysis['total_count'], 1)
        self.assertEqual(analysis['long_liquidations_count'], 1)
        self.assertEqual(analysis['short_liquidations_count'], 0)
        self.assertEqual(len(analysis['large_liquidations']), 1)
        
        # Проверяем сброс статистики
        analyzer.reset_statistics()
        stats = analyzer.get_statistics()
        self.assertEqual(stats['total_count'], 0)
        self.assertEqual(len(analyzer.recent_liquidations), 0)
    
    def test_liquidation_handler(self):
        """Тест обработчика сообщений о ликвидациях."""
        # Создаем мок для callback-функции
        callback = AsyncMock()
        
        # Создаем обработчик
        handler = LiquidationMessageHandler(callback)
        
        # Выполняем тест асинхронно
        async def run_test():
            # Тестируем обработку сообщения
            result = await handler.handle_message(self.sample_ws_message)
            
            # Проверяем, что сообщение было обработано
            self.assertTrue(result)
            
            # Проверяем, что callback был вызван с правильными данными
            callback.assert_called_once()
            args, kwargs = callback.call_args
            liquidation = args[0]
            
            # Проверяем аргументы вызова
            self.assertIsInstance(liquidation, LiquidationData)
            self.assertEqual(liquidation.symbol, "BTCUSDT")
            self.assertEqual(liquidation.side, LiquidationSide.SELL)
            self.assertEqual(liquidation.price, Decimal("50000.0"))
            self.assertEqual(liquidation.quantity, Decimal("2.5"))
        
        # Запускаем асинхронный тест
        asyncio.run(run_test())


if __name__ == '__main__':
    unittest.main() 
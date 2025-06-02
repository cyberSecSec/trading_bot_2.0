"""
Тесты для сервисов открытого интереса.
"""

import pytest
import asyncio
from decimal import Decimal
from typing import Dict, Any, List
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock

from exchange_api.core.config import ClientConfig
from exchange_api.services.bybit.market_data_rest_service import BybitMarketDataRestProvider
from exchange_api.services.bybit.market_data_stream_service import BybitMarketDataStreamProvider
from exchange_api.exceptions import ValidationError, VantaAPIError

from models.market_data import OpenInterestData


class TestOpenInterestRestService:
    """Тесты для REST сервиса открытого интереса."""
    
    @pytest.fixture
    def config(self):
        """Фикстура для создания конфигурации."""
        return ClientConfig(
            api_key="test_key",
            api_secret="test_secret",
            base_url="https://api-testnet.bybit.com",
            exchange_name="bybit",
            categories=['linear', 'inverse', 'spot']
        )
    
    @pytest.fixture
    def mock_connection(self):
        """Фикстура для создания мока соединения."""
        with patch('exchange_api.connection.ConnectionManager') as mock:
            connection = mock.return_value
            yield connection
    
    @pytest.fixture
    def rest_provider(self, config, mock_connection):
        """Фикстура для создания REST провайдера данных."""
        provider = BybitMarketDataRestProvider(config, mock_connection)
        yield provider
    
    async def test_get_open_interest_success(self, rest_provider, mock_connection):
        """Тест успешного получения текущего открытого интереса."""
        # Подготавливаем данные для мока
        mock_response = {
            "retCode": 0,
            "retMsg": "OK",
            "result": {
                "symbol": "BTCUSDT",
                "timestamp": 1682928000000,
                "openInterest": "100.123",
                "openInterestValue": "2915778.538",
                "fundingRate": "0.0001",
                "nextFundingTime": 1683072000000
            }
        }
        
        # Настраиваем мок соединения
        mock_connection.get.return_value = mock_response
        
        # Вызываем метод
        result = await rest_provider.get_open_interest("BTCUSDT")
        
        # Проверяем вызовы мока
        mock_connection.get.assert_called_once()
        
        # Проверяем результат
        assert isinstance(result, OpenInterestData)
        assert result.symbol == "BTCUSDT"
        assert result.open_interest == Decimal("100.123")
        assert result.open_interest_value == Decimal("2915778.538")
        assert result.funding_rate == Decimal("0.0001")
        assert isinstance(result.next_funding_time, datetime)
    
    async def test_get_open_interest_invalid_category(self, rest_provider):
        """Тест получения открытого интереса для неверной категории."""
        # Настраиваем мок для метода _get_category_for_symbol
        with patch.object(rest_provider, '_get_category_for_symbol', return_value='spot'):
            # Ожидаем исключение ValidationError
            with pytest.raises(ValidationError):
                await rest_provider.get_open_interest("BTCUSDT")
    
    async def test_get_open_interest_api_error(self, rest_provider, mock_connection):
        """Тест обработки ошибки API при получении открытого интереса."""
        # Подготавливаем данные для мока
        mock_response = {
            "retCode": 10001,
            "retMsg": "Parameter error",
            "result": {}
        }
        
        # Настраиваем мок соединения
        mock_connection.get.return_value = mock_response
        
        # Ожидаем исключение VantaAPIError
        with pytest.raises(VantaAPIError):
            await rest_provider.get_open_interest("BTCUSDT")
    
    async def test_get_open_interest_history_success(self, rest_provider, mock_connection):
        """Тест успешного получения истории открытого интереса."""
        # Подготавливаем данные для мока
        mock_response = {
            "retCode": 0,
            "retMsg": "OK",
            "result": {
                "list": [
                    {
                        "symbol": "BTCUSDT",
                        "timestamp": 1682928000000,
                        "openInterest": "100.123",
                        "openInterestValue": "2915778.538"
                    },
                    {
                        "symbol": "BTCUSDT",
                        "timestamp": 1682924400000,
                        "openInterest": "98.456",
                        "openInterestValue": "2862778.987"
                    }
                ]
            }
        }
        
        # Настраиваем мок соединения
        mock_connection.get.return_value = mock_response
        
        # Вызываем метод
        result = await rest_provider.get_open_interest_history("BTCUSDT", "1h")
        
        # Проверяем вызовы мока
        mock_connection.get.assert_called_once()
        
        # Проверяем результат
        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(item, OpenInterestData) for item in result)
        
        # Проверяем сортировку (от старых к новым)
        assert result[0].timestamp < result[1].timestamp
    
    async def test_get_open_interest_history_invalid_period(self, rest_provider):
        """Тест получения истории открытого интереса с неверным периодом."""
        # Ожидаем исключение ValidationError
        with pytest.raises(ValidationError):
            await rest_provider.get_open_interest_history("BTCUSDT", "invalid_period")
    
    async def test_get_open_interest_history_empty_result(self, rest_provider, mock_connection):
        """Тест получения пустой истории открытого интереса."""
        # Подготавливаем данные для мока
        mock_response = {
            "retCode": 0,
            "retMsg": "OK",
            "result": {
                "list": []
            }
        }
        
        # Настраиваем мок соединения
        mock_connection.get.return_value = mock_response
        
        # Вызываем метод
        result = await rest_provider.get_open_interest_history("BTCUSDT", "1h")
        
        # Проверяем результат
        assert isinstance(result, list)
        assert len(result) == 0


class TestOpenInterestStreamService:
    """Тесты для WebSocket сервиса открытого интереса."""
    
    @pytest.fixture
    def config(self):
        """Фикстура для создания конфигурации."""
        return ClientConfig(
            api_key="test_key",
            api_secret="test_secret",
            base_url="wss://stream-testnet.bybit.com",
            exchange_name="bybit",
            categories=['linear', 'inverse', 'spot']
        )
    
    @pytest.fixture
    def mock_ws_manager(self):
        """Фикстура для создания мока WebSocket менеджера."""
        with patch('exchange_api.connection.WebSocketManager') as mock:
            ws_manager = mock.return_value
            ws_manager.subscribe = AsyncMock()
            ws_manager.unsubscribe = AsyncMock()
            yield ws_manager
    
    @pytest.fixture
    def stream_provider(self, config, mock_ws_manager):
        """Фикстура для создания WebSocket провайдера данных."""
        provider = BybitMarketDataStreamProvider(config, mock_ws_manager)
        provider._is_connected = True  # Имитируем установленное соединение
        yield provider
    
    async def test_subscribe_to_open_interest_success(self, stream_provider, mock_ws_manager):
        """Тест успешной подписки на обновления открытого интереса."""
        # Подготавливаем колбэк
        callback = AsyncMock()
        
        # Патчим метод _get_category_for_symbol
        with patch.object(stream_provider, '_get_category_for_symbol', return_value='linear'):
            # Вызываем метод
            subscription_id = await stream_provider.subscribe_to_open_interest("BTCUSDT", callback)
            
            # Проверяем результат
            assert isinstance(subscription_id, str)
            assert subscription_id != ""
            
            # Проверяем вызовы мока
            mock_ws_manager.subscribe.assert_called_once_with("openInterest.BTCUSDT")
            
            # Проверяем сохранение подписки
            assert subscription_id in stream_provider.subscriptions
            subscription = stream_provider.subscriptions[subscription_id]
            assert subscription['channel'] == "openInterest.BTCUSDT"
            assert subscription['symbol'] == "BTCUSDT"
            assert 'oi_analyzer' in subscription
    
    async def test_subscribe_to_open_interest_invalid_category(self, stream_provider):
        """Тест подписки на обновления открытого интереса для неверной категории."""
        # Патчим метод _get_category_for_symbol
        with patch.object(stream_provider, '_get_category_for_symbol', return_value='spot'):
            # Ожидаем исключение ValidationError
            with pytest.raises(ValidationError):
                await stream_provider.subscribe_to_open_interest("BTCUSDT", AsyncMock())
    
    async def test_unsubscribe_from_open_interest_success(self, stream_provider, mock_ws_manager):
        """Тест успешной отписки от обновлений открытого интереса."""
        # Подготавливаем колбэк
        callback = AsyncMock()
        
        # Патчим метод _get_category_for_symbol
        with patch.object(stream_provider, '_get_category_for_symbol', return_value='linear'):
            # Вызываем метод подписки
            subscription_id = await stream_provider.subscribe_to_open_interest("BTCUSDT", callback)
            
            # Вызываем метод отписки
            result = await stream_provider.unsubscribe_from_open_interest(subscription_id)
            
            # Проверяем результат
            assert result is True
            
            # Проверяем вызовы мока
            mock_ws_manager.unsubscribe.assert_called_once_with("openInterest.BTCUSDT")
            
            # Проверяем удаление подписки
            assert subscription_id not in stream_provider.subscriptions
    
    async def test_on_message_open_interest(self, stream_provider):
        """Тест обработки сообщений об открытом интересе."""
        # Подготавливаем колбэк
        callback = AsyncMock()
        
        # Подготавливаем данные подписки
        subscription_id = "test_subscription_id"
        stream_provider.subscriptions[subscription_id] = {
            'channel': "openInterest.BTCUSDT",
            'callback': callback,
            'symbol': "BTCUSDT",
            'oi_analyzer': MagicMock()
        }
        
        # Подготавливаем сообщение WebSocket
        message = {
            'topic': "openInterest.BTCUSDT",
            'data': [
                {
                    'symbol': "BTCUSDT",
                    'timestamp': 1682928000000,
                    'openInterest': "100.123",
                    'openInterestValue': "2915778.538"
                }
            ]
        }
        
        # Вызываем метод
        await stream_provider._on_message(message)
        
        # Проверяем вызовы колбэка
        callback.assert_called_once()
        
        # Проверяем аргументы вызова
        args, _ = callback.call_args
        assert len(args) == 1
        assert isinstance(args[0], OpenInterestData)
        assert args[0].symbol == "BTCUSDT"
        assert args[0].open_interest == Decimal("100.123")
        assert args[0].open_interest_value == Decimal("2915778.538")


if __name__ == "__main__":
    pytest.main(["-v", "test_open_interest.py"]) 
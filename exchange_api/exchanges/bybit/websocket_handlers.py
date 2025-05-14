"""
Модуль обработчиков WebSocket сообщений для Bybit API.

Предоставляет классы и функции для обработки различных типов сообщений,
получаемых через WebSocket соединение с Bybit API.
"""
import json
import time
from typing import Dict, Any, Optional, Union, List, Callable, Awaitable
from decimal import Decimal

from exchange_api.utils.logger import Logger


# Получаем логгер
logger = Logger.get_logger()


class BaseMessageHandler:
    """
    Базовый класс для обработчиков WebSocket сообщений.
    
    Определяет общий интерфейс и базовую функциональность для обработки
    различных типов сообщений от WebSocket API Bybit.
    """
    
    def __init__(self, 
                 callback: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None):
        """
        Инициализирует обработчик сообщений.
        
        Args:
            callback: Асинхронная функция обратного вызова для обработки данных
        """
        self.callback = callback
        self.logger = logger
    
    async def handle(self, message: Dict[str, Any]) -> bool:
        """
        Обрабатывает входящее сообщение.
        
        Args:
            message: Сообщение от WebSocket API
            
        Returns:
            bool: True, если сообщение было успешно обработано, иначе False
        """
        # Базовая реализация просто возвращает False, 
        # так как не умеет обрабатывать конкретные типы сообщений
        return False
    
    async def _invoke_callback(self, data: Dict[str, Any]) -> None:
        """
        Вызывает функцию обратного вызова с обработанными данными.
        
        Args:
            data: Обработанные данные для передачи в callback
        """
        if self.callback:
            try:
                await self.callback(data)
            except Exception as e:
                self.logger.error(f"Ошибка в callback-функции: {str(e)}")


class SystemMessageHandler(BaseMessageHandler):
    """
    Обработчик системных сообщений от Bybit WebSocket API.
    
    Обрабатывает сообщения о подключении, аутентификации, подписках и т.д.
    """
    
    async def handle(self, message: Dict[str, Any]) -> bool:
        """
        Обрабатывает системное сообщение.
        
        Args:
            message: Сообщение от WebSocket API
            
        Returns:
            bool: True, если сообщение было успешно обработано, иначе False
        """
        # Проверяем, является ли сообщение системным
        if 'op' in message:
            op = message['op']
            
            # Обрабатываем различные типы операций
            if op == 'ping':
                self.logger.debug("Получено системное сообщение: ping")
                return True
                
            elif op == 'pong':
                self.logger.debug("Получено системное сообщение: pong")
                return True
                
            elif op == 'subscribe' or op == 'unsubscribe':
                # Проверяем успешность подписки/отписки
                success = message.get('success', False)
                req_id = message.get('req_id', 'unknown')
                
                if success:
                    operation = "Подписка" if op == 'subscribe' else "Отписка"
                    args = message.get('args', [])
                    self.logger.info(f"{operation} успешна: {args}, req_id: {req_id}")
                else:
                    error_msg = message.get('ret_msg', 'Unknown error')
                    self.logger.error(f"Ошибка операции {op}: {error_msg}, req_id: {req_id}")
                
                return True
                
            elif op == 'auth':
                # Обрабатываем результат аутентификации
                success = message.get('success', False)
                
                if success:
                    self.logger.info("Аутентификация WebSocket успешна")
                else:
                    error_msg = message.get('ret_msg', 'Unknown error')
                    self.logger.error(f"Ошибка аутентификации: {error_msg}")
                
                return True
        
        # Это не системное сообщение
        return False


class KlineMessageHandler(BaseMessageHandler):
    """
    Обработчик сообщений с OHLCV данными (свечами).
    """
    
    async def handle(self, message: Dict[str, Any]) -> bool:
        """
        Обрабатывает сообщение с OHLCV данными.
        
        Args:
            message: Сообщение от WebSocket API
            
        Returns:
            bool: True, если сообщение было успешно обработано, иначе False
        """
        # Проверяем, содержит ли сообщение тему kline
        if 'topic' in message and message['topic'].startswith('kline.'):
            self.logger.debug(f"Обработка сообщения kline: {message['topic']}")
            
            # Извлекаем данные и интервал из темы
            topic_parts = message['topic'].split('.')
            if len(topic_parts) >= 3:
                interval = topic_parts[1]
                symbol = topic_parts[2]
                
                # Извлекаем данные OHLCV
                data = message.get('data', [])
                
                if data:
                    # Обрабатываем каждую свечу
                    processed_data = []
                    
                    for candle in data:
                        # Преобразуем данные свечи в стандартный формат
                        processed_candle = {
                            'symbol': symbol,
                            'interval': interval,
                            'start_time': int(candle[0]),
                            'open': Decimal(str(candle[1])),
                            'high': Decimal(str(candle[2])),
                            'low': Decimal(str(candle[3])),
                            'close': Decimal(str(candle[4])),
                            'volume': Decimal(str(candle[5])),
                            'turnover': Decimal(str(candle[6])) if len(candle) > 6 else None
                        }
                        
                        processed_data.append(processed_candle)
                    
                    # Вызываем callback с обработанными данными
                    await self._invoke_callback({
                        'type': 'kline',
                        'symbol': symbol,
                        'interval': interval,
                        'data': processed_data
                    })
                    
                    return True
            
            self.logger.warning(f"Не удалось обработать сообщение kline: {message}")
        
        # Это не сообщение kline
        return False


class OrderbookMessageHandler(BaseMessageHandler):
    """
    Обработчик сообщений со стаканом ордеров.
    """
    
    async def handle(self, message: Dict[str, Any]) -> bool:
        """
        Обрабатывает сообщение со стаканом ордеров.
        
        Args:
            message: Сообщение от WebSocket API
            
        Returns:
            bool: True, если сообщение было успешно обработано, иначе False
        """
        # Проверяем, содержит ли сообщение тему orderbook
        if 'topic' in message and message['topic'].startswith('orderbook.'):
            self.logger.debug(f"Обработка сообщения orderbook: {message['topic']}")
            
            # Извлекаем глубину и символ из темы
            topic_parts = message['topic'].split('.')
            if len(topic_parts) >= 3:
                depth = topic_parts[1]
                symbol = topic_parts[2]
                
                # Извлекаем тип обновления
                update_type = message.get('type', 'snapshot')
                
                # Извлекаем данные стакана
                data = message.get('data', {})
                
                if data:
                    # Извлекаем временную метку
                    timestamp = data.get('ts', int(time.time() * 1000))
                    
                    # Извлекаем и преобразуем bids и asks
                    bids = []
                    asks = []
                    
                    for bid in data.get('b', []):
                        if len(bid) >= 2:
                            bids.append([Decimal(str(bid[0])), Decimal(str(bid[1]))])
                    
                    for ask in data.get('a', []):
                        if len(ask) >= 2:
                            asks.append([Decimal(str(ask[0])), Decimal(str(ask[1]))])
                    
                    # Вызываем callback с обработанными данными
                    await self._invoke_callback({
                        'type': 'orderbook',
                        'symbol': symbol,
                        'depth': depth,
                        'update_type': update_type,
                        'timestamp': timestamp,
                        'bids': bids,
                        'asks': asks
                    })
                    
                    return True
            
            self.logger.warning(f"Не удалось обработать сообщение orderbook: {message}")
        
        # Это не сообщение orderbook
        return False


class TradeMessageHandler(BaseMessageHandler):
    """
    Обработчик сообщений о сделках.
    """
    
    async def handle(self, message: Dict[str, Any]) -> bool:
        """
        Обрабатывает сообщение о сделках.
        
        Args:
            message: Сообщение от WebSocket API
            
        Returns:
            bool: True, если сообщение было успешно обработано, иначе False
        """
        # Проверяем, содержит ли сообщение тему publicTrade
        if 'topic' in message and message['topic'].startswith('publicTrade.'):
            self.logger.debug(f"Обработка сообщения publicTrade: {message['topic']}")
            
            # Извлекаем символ из темы
            topic_parts = message['topic'].split('.')
            if len(topic_parts) >= 2:
                symbol = topic_parts[1]
                
                # Извлекаем данные о сделках
                data = message.get('data', [])
                
                if data:
                    # Обрабатываем каждую сделку
                    processed_trades = []
                    
                    for trade in data:
                        # Преобразуем данные сделки в стандартный формат
                        processed_trade = {
                            'symbol': symbol,
                            'id': trade.get('i', ''),
                            'price': Decimal(str(trade.get('p', '0'))),
                            'quantity': Decimal(str(trade.get('v', '0'))),
                            'side': trade.get('S', ''),  # Buy или Sell
                            'timestamp': int(trade.get('T', 0)),
                            'is_block_trade': trade.get('BT', False)
                        }
                        
                        processed_trades.append(processed_trade)
                    
                    # Вызываем callback с обработанными данными
                    await self._invoke_callback({
                        'type': 'trade',
                        'symbol': symbol,
                        'data': processed_trades
                    })
                    
                    return True
            
            self.logger.warning(f"Не удалось обработать сообщение publicTrade: {message}")
        
        # Это не сообщение publicTrade
        return False


class LiquidationMessageHandler(BaseMessageHandler):
    """
    Обработчик сообщений о ликвидациях.
    """
    
    async def handle(self, message: Dict[str, Any]) -> bool:
        """
        Обрабатывает сообщение о ликвидациях.
        
        Args:
            message: Сообщение от WebSocket API
            
        Returns:
            bool: True, если сообщение было успешно обработано, иначе False
        """
        # Проверяем, содержит ли сообщение тему liquidation
        if 'topic' in message and message['topic'].startswith('liquidation.'):
            self.logger.debug(f"Обработка сообщения liquidation: {message['topic']}")
            
            # Извлекаем символ из темы
            topic_parts = message['topic'].split('.')
            if len(topic_parts) >= 2:
                symbol = topic_parts[1]
                
                # Извлекаем данные о ликвидациях
                data = message.get('data', [])
                
                if data:
                    # Обрабатываем каждую ликвидацию
                    processed_liquidations = []
                    
                    for liq in data:
                        # Преобразуем данные ликвидации в стандартный формат
                        processed_liq = {
                            'symbol': symbol,
                            'side': liq.get('S', ''),  # Buy или Sell
                            'price': Decimal(str(liq.get('p', '0'))),
                            'quantity': Decimal(str(liq.get('v', '0'))),
                            'timestamp': int(liq.get('T', 0))
                        }
                        
                        processed_liquidations.append(processed_liq)
                    
                    # Вызываем callback с обработанными данными
                    await self._invoke_callback({
                        'type': 'liquidation',
                        'symbol': symbol,
                        'data': processed_liquidations
                    })
                    
                    return True
            
            self.logger.warning(f"Не удалось обработать сообщение liquidation: {message}")
        
        # Это не сообщение liquidation
        return False


class OrderUpdateHandler(BaseMessageHandler):
    """
    Обработчик обновлений ордеров.
    """
    
    async def handle(self, message: Dict[str, Any]) -> bool:
        """
        Обрабатывает сообщение обновления ордера.
        
        Args:
            message: Сообщение от WebSocket API
            
        Returns:
            bool: True, если сообщение было успешно обработано, иначе False
        """
        # Проверяем, содержит ли сообщение тему order
        if 'topic' in message and message['topic'] == 'order':
            self.logger.debug("Обработка сообщения обновления ордера")
            
            # Извлекаем данные обновления ордера
            data = message.get('data', [])
            
            if data:
                # Обрабатываем каждое обновление ордера
                processed_orders = []
                
                for order in data:
                    # Преобразуем данные ордера в стандартный формат
                    processed_order = {
                        'symbol': order.get('s', ''),
                        'order_id': order.get('i', ''),
                        'client_order_id': order.get('c', ''),
                        'side': order.get('S', ''),
                        'order_type': order.get('o', ''),
                        'price': Decimal(str(order.get('p', '0'))),
                        'quantity': Decimal(str(order.get('q', '0'))),
                        'executed_quantity': Decimal(str(order.get('z', '0'))),
                        'remaining_quantity': Decimal(str(order.get('l', '0'))),
                        'status': order.get('X', ''),
                        'time_in_force': order.get('f', ''),
                        'create_time': int(order.get('O', 0)),
                        'update_time': int(order.get('T', 0))
                    }
                    
                    processed_orders.append(processed_order)
                
                # Вызываем callback с обработанными данными
                await self._invoke_callback({
                    'type': 'order_update',
                    'data': processed_orders
                })
                
                return True
        
        # Это не сообщение обновления ордера
        return False


class PositionUpdateHandler(BaseMessageHandler):
    """
    Обработчик обновлений позиций.
    """
    
    async def handle(self, message: Dict[str, Any]) -> bool:
        """
        Обрабатывает сообщение обновления позиции.
        
        Args:
            message: Сообщение от WebSocket API
            
        Returns:
            bool: True, если сообщение было успешно обработано, иначе False
        """
        # Проверяем, содержит ли сообщение тему position
        if 'topic' in message and message['topic'] == 'position':
            self.logger.debug("Обработка сообщения обновления позиции")
            
            # Извлекаем данные обновления позиции
            data = message.get('data', [])
            
            if data:
                # Обрабатываем каждое обновление позиции
                processed_positions = []
                
                for position in data:
                    # Преобразуем данные позиции в стандартный формат
                    processed_position = {
                        'symbol': position.get('s', ''),
                        'side': position.get('ps', ''),
                        'size': Decimal(str(position.get('sz', '0'))),
                        'entry_price': Decimal(str(position.get('ep', '0'))),
                        'leverage': Decimal(str(position.get('l', '0'))),
                        'position_value': Decimal(str(position.get('v', '0'))),
                        'margin_type': position.get('mt', ''),
                        'position_status': position.get('st', ''),
                        'take_profit': Decimal(str(position.get('tp', '0'))),
                        'stop_loss': Decimal(str(position.get('sl', '0'))),
                        'unrealised_pnl': Decimal(str(position.get('up', '0'))),
                        'created_time': int(position.get('ct', 0)),
                        'updated_time': int(position.get('ut', 0))
                    }
                    
                    processed_positions.append(processed_position)
                
                # Вызываем callback с обработанными данными
                await self._invoke_callback({
                    'type': 'position_update',
                    'data': processed_positions
                })
                
                return True
        
        # Это не сообщение обновления позиции
        return False


class WalletUpdateHandler(BaseMessageHandler):
    """
    Обработчик обновлений кошелька.
    """
    
    async def handle(self, message: Dict[str, Any]) -> bool:
        """
        Обрабатывает сообщение обновления кошелька.
        
        Args:
            message: Сообщение от WebSocket API
            
        Returns:
            bool: True, если сообщение было успешно обработано, иначе False
        """
        # Проверяем, содержит ли сообщение тему wallet
        if 'topic' in message and message['topic'] == 'wallet':
            self.logger.debug("Обработка сообщения обновления кошелька")
            
            # Извлекаем данные обновления кошелька
            data = message.get('data', [])
            
            if data:
                # Обрабатываем каждое обновление кошелька
                processed_wallets = []
                
                for wallet in data:
                    # Преобразуем данные кошелька в стандартный формат
                    processed_wallet = {
                        'account_type': wallet.get('a', ''),
                        'account_lTV': Decimal(str(wallet.get('l', '0'))),
                        'account_IMR': Decimal(str(wallet.get('m', '0'))),
                        'account_MMR': Decimal(str(wallet.get('mw', '0'))),
                        'total_equity': Decimal(str(wallet.get('te', '0'))),
                        'total_wallet_balance': Decimal(str(wallet.get('wb', '0'))),
                        'total_margin_balance': Decimal(str(wallet.get('mb', '0'))),
                        'total_available_balance': Decimal(str(wallet.get('ab', '0'))),
                        'total_perp_UPL': Decimal(str(wallet.get('u', '0'))),
                        'total_initial_margin': Decimal(str(wallet.get('mt', '0'))),
                        'total_maintenance_margin': Decimal(str(wallet.get('mm', '0')))
                    }
                    
                    # Извлекаем информацию о балансах по валютам
                    coin_list = wallet.get('c', [])
                    balances = {}
                    
                    for coin in coin_list:
                        currency = coin.get('n', '')
                        if currency:
                            balances[currency] = {
                                'equity': Decimal(str(coin.get('e', '0'))),
                                'wallet_balance': Decimal(str(coin.get('wb', '0'))),
                                'available_balance': Decimal(str(coin.get('ab', '0')))
                            }
                    
                    processed_wallet['balances'] = balances
                    processed_wallets.append(processed_wallet)
                
                # Вызываем callback с обработанными данными
                await self._invoke_callback({
                    'type': 'wallet_update',
                    'data': processed_wallets
                })
                
                return True
        
        # Это не сообщение обновления кошелька
        return False


class WebSocketMessageRouter:
    """
    Маршрутизатор сообщений WebSocket.
    
    Направляет входящие сообщения соответствующим обработчикам на основе
    их содержимого.
    """
    
    def __init__(self, exchange_name: str = "bybit"):
        """
        Инициализирует маршрутизатор сообщений.
        
        Args:
            exchange_name: Название биржи для контекста логирования
        """
        self.exchange_name = exchange_name
        self.handlers = []
        self.logger = logger
        
        # Устанавливаем контекст логгера
        Logger.set_exchange_context(self.exchange_name)
    
    def add_handler(self, handler: BaseMessageHandler) -> None:
        """
        Добавляет обработчик сообщений в маршрутизатор.
        
        Args:
            handler: Обработчик сообщений для добавления
        """
        self.handlers.append(handler)
    
    async def route_message(self, message: Dict[str, Any]) -> bool:
        """
        Маршрутизирует сообщение соответствующему обработчику.
        
        Args:
            message: Сообщение для маршрутизации
            
        Returns:
            bool: True, если сообщение было обработано каким-либо обработчиком, иначе False
        """
        # Логируем сообщение в режиме отладки
        if 'topic' in message:
            self.logger.debug(f"Маршрутизация сообщения с темой: {message['topic']}")
        elif 'op' in message:
            self.logger.debug(f"Маршрутизация системного сообщения с op: {message['op']}")
        
        # Пытаемся обработать сообщение каждым обработчиком
        for handler in self.handlers:
            try:
                if await handler.handle(message):
                    return True
            except Exception as e:
                self.logger.error(f"Ошибка в обработчике {handler.__class__.__name__}: {str(e)}")
        
        # Если сообщение не было обработано ни одним обработчиком
        self.logger.warning(f"Не найден обработчик для сообщения: {json.dumps(message)[:200]}...")
        return False
    
    def create_default_router(
        callback_map: Dict[str, Callable[[Dict[str, Any]], Awaitable[None]]] = None
    ) -> 'WebSocketMessageRouter':
        """
        Создает маршрутизатор с набором стандартных обработчиков.
        
        Args:
            callback_map: Словарь с функциями обратного вызова для каждого типа сообщений
                        (ключи: 'system', 'kline', 'orderbook', 'trade', 'liquidation',
                        'order', 'position', 'wallet')
                        
        Returns:
            WebSocketMessageRouter: Настроенный маршрутизатор сообщений
        """
        router = WebSocketMessageRouter("bybit")
        
        # Создаем словарь callbackов, если он не передан
        if callback_map is None:
            callback_map = {}
        
        # Добавляем обработчики с соответствующими функциями обратного вызова
        router.add_handler(SystemMessageHandler(callback_map.get('system')))
        router.add_handler(KlineMessageHandler(callback_map.get('kline')))
        router.add_handler(OrderbookMessageHandler(callback_map.get('orderbook')))
        router.add_handler(TradeMessageHandler(callback_map.get('trade')))
        router.add_handler(LiquidationMessageHandler(callback_map.get('liquidation')))
        router.add_handler(OrderUpdateHandler(callback_map.get('order')))
        router.add_handler(PositionUpdateHandler(callback_map.get('position')))
        router.add_handler(WalletUpdateHandler(callback_map.get('wallet')))
        
        return router 
"""
Модуль для управления HTTP соединениями с Bybit API.

Расширяет базовый ConnectionManager, добавляя специфичную для Bybit
функциональность, включая генерацию подписей для запросов.
"""
import hashlib
import hmac
import time
from typing import Dict, Any, Optional, Union, List

from exchange_api.connection.connection_manager import ConnectionManager
from exchange_api.exchanges.bybit.config import BybitClientConfig
from exchange_api.utils.logger import Logger


# Получаем логгер
logger = Logger.get_logger()


class BybitConnectionManager(ConnectionManager):
    """
    Менеджер соединений для работы с API Bybit.
    
    Расширяет базовый ConnectionManager, добавляя специфичную для Bybit
    функциональность, включая генерацию подписей для авторизации запросов.
    """
    
    def __init__(self, config: BybitClientConfig):
        """
        Инициализирует менеджер соединений для Bybit.
        
        Args:
            config: Конфигурация клиента Bybit
        """
        super().__init__(config)
        self.bybit_config = config
        self.recv_window = config.recv_window
        logger.debug(f"Создан BybitConnectionManager с recv_window={self.recv_window}")
    
    def _add_auth_headers(
        self, 
        method: str, 
        url: str, 
        params: Optional[Dict[str, Any]], 
        data: Optional[Dict[str, Any]], 
        headers: Dict[str, str]
    ) -> None:
        """
        Добавляет заголовки аутентификации для запросов к Bybit API.
        
        Bybit использует HMAC SHA256 для подписи запросов с использованием 
        timestamp, API-ключа и секрета.
        
        Args:
            method: HTTP метод
            url: URL запроса
            params: Параметры запроса
            data: Данные запроса
            headers: Заголовки запроса, которые нужно дополнить
        """
        # Получаем учетные данные
        api_key = self.config.credentials.get_api_key()
        api_secret = self.config.credentials.get_api_secret()
        
        if not api_key or not api_secret:
            logger.warning("Отсутствуют API ключи для аутентификации Bybit")
            return
        
        # Добавляем API ключ в заголовки
        headers['X-BAPI-API-KEY'] = api_key
        
        # Текущее время в миллисекундах
        timestamp = str(int(time.time() * 1000))
        
        # Формируем строку для подписи
        to_sign = self._get_signature_payload(timestamp, api_key, params, data)
        
        # Генерируем подпись с использованием HMAC SHA256
        signature = hmac.new(
            api_secret.encode('utf-8'),
            to_sign.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        # Добавляем подпись и timestamp в заголовки
        headers['X-BAPI-TIMESTAMP'] = timestamp
        headers['X-BAPI-SIGN'] = signature
        
        # Добавляем recv_window, если установлен
        if self.recv_window:
            headers['X-BAPI-RECV-WINDOW'] = str(self.recv_window)
    
    def _get_signature_payload(
        self, 
        timestamp: str, 
        api_key: str, 
        params: Optional[Dict[str, Any]], 
        data: Optional[Dict[str, Any]]
    ) -> str:
        """
        Формирует строку для подписи запроса к Bybit API.
        
        Args:
            timestamp: Текущее время в миллисекундах
            api_key: API ключ
            params: Параметры GET запроса
            data: Данные POST запроса
            
        Returns:
            str: Строка для подписи
        """
        # Формат строки для подписи: timestamp + api_key + recv_window + параметры
        payload = timestamp
        
        # Добавляем API ключ
        payload += api_key
        
        # Добавляем recv_window, если установлен
        if self.recv_window:
            payload += str(self.recv_window)
        
        # Добавляем параметры GET запроса, если есть
        if params:
            # Сортируем параметры по ключу в алфавитном порядке
            params_str = self._dict_to_query_string(params)
            if params_str:
                payload += params_str
        
        # Добавляем данные POST запроса, если есть
        if data:
            # Преобразуем данные JSON в строку
            import json
            data_str = json.dumps(data, separators=(',', ':'))
            payload += data_str
        
        return payload
    
    def _dict_to_query_string(self, params: Dict[str, Any]) -> str:
        """
        Преобразует словарь параметров в строку запроса.
        
        Args:
            params: Словарь параметров
            
        Returns:
            str: Строка запроса в формате "key1=value1&key2=value2"
        """
        # Сортируем параметры по ключу
        sorted_params = sorted(params.items())
        
        # Преобразуем в строку запроса
        return ''.join([f"{key}={value}" for key, value in sorted_params])
    
    async def get_server_time(self) -> int:
        """
        Получает текущее время сервера Bybit.
        
        Returns:
            int: Текущее время сервера в миллисекундах
        """
        response = await self.get("/v5/market/time")
        return int(response['result']['timeNano'] // 1_000_000)
    
    async def check_connection(self) -> bool:
        """
        Проверяет соединение с API Bybit.
        
        Returns:
            bool: True, если соединение успешно установлено
        """
        try:
            await self.get_server_time()
            return True
        except Exception as e:
            logger.error(f"Ошибка при проверке соединения с Bybit: {e}")
            return False 
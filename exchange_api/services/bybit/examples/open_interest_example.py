"""
Примеры использования сервиса для работы с открытым интересом.
"""

import asyncio
import logging
from decimal import Decimal
from datetime import datetime, timedelta
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter

from exchange_api.core.config import ClientConfig
from exchange_api.services.bybit.market_data_service import BybitMarketDataService
from exchange_api.services.bybit.market_data_rest_service import BybitMarketDataRestProvider
from exchange_api.services.bybit.market_data_stream_service import BybitMarketDataStreamProvider

from models.market_data import OpenInterestData


# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def get_current_open_interest_example():
    """
    Пример получения текущего открытого интереса.
    """
    # Создаем конфигурацию
    config = ClientConfig(
        api_key="YOUR_API_KEY",       # Можно оставить пустым для публичных эндпоинтов
        api_secret="YOUR_API_SECRET", # Можно оставить пустым для публичных эндпоинтов
        base_url="https://api-testnet.bybit.com",
        exchange_name="bybit"
    )
    
    # Создаем REST провайдер
    async with BybitMarketDataRestProvider(config) as rest_provider:
        try:
            # Получаем текущий открытый интерес для BTCUSDT
            oi_data = await rest_provider.get_open_interest("BTCUSDT")
            
            # Выводим информацию
            logger.info(f"Открытый интерес для BTCUSDT:")
            logger.info(f"  Значение: {oi_data.open_interest}")
            logger.info(f"  Стоимость в USD: {oi_data.open_interest_value} USD")
            logger.info(f"  Временная метка: {oi_data.timestamp}")
            
            if oi_data.funding_rate is not None:
                logger.info(f"  Ставка финансирования: {oi_data.funding_rate * 100}%")
            
            if oi_data.next_funding_time is not None:
                logger.info(f"  Следующее финансирование: {oi_data.next_funding_time}")
                
            return oi_data
            
        except Exception as e:
            logger.error(f"Ошибка при получении открытого интереса: {str(e)}")
            raise


async def get_open_interest_history_example():
    """
    Пример получения истории открытого интереса.
    """
    # Создаем конфигурацию
    config = ClientConfig(
        api_key="YOUR_API_KEY",       # Можно оставить пустым для публичных эндпоинтов
        api_secret="YOUR_API_SECRET", # Можно оставить пустым для публичных эндпоинтов
        base_url="https://api-testnet.bybit.com",
        exchange_name="bybit"
    )
    
    # Создаем REST провайдер
    async with BybitMarketDataRestProvider(config) as rest_provider:
        try:
            # Получаем историю открытого интереса для BTCUSDT за последние 100 часов
            oi_history = await rest_provider.get_open_interest_history(
                symbol="BTCUSDT",
                period="1h",  # 1-часовые интервалы
                limit=100     # 100 записей
            )
            
            # Выводим информацию
            logger.info(f"Получено {len(oi_history)} записей истории открытого интереса")
            
            # Преобразуем данные в DataFrame для анализа
            df = OpenInterestData.to_dataframe(oi_history)
            
            # Выводим базовую статистику
            logger.info("\nСтатистика открытого интереса:")
            logger.info(f"  Минимум: {df['open_interest'].min()}")
            logger.info(f"  Максимум: {df['open_interest'].max()}")
            logger.info(f"  Среднее: {df['open_interest'].mean():.2f}")
            logger.info(f"  Медиана: {df['open_interest'].median():.2f}")
            
            # Вычисляем изменение открытого интереса
            if len(oi_history) >= 2:
                first_oi = oi_history[0]
                last_oi = oi_history[-1]
                change = OpenInterestData.calculate_change(last_oi, first_oi)
                
                logger.info("\nИзменение открытого интереса за период:")
                logger.info(f"  Абсолютное: {change['absolute']}")
                logger.info(f"  Процентное: {change['percentage']:.2f}%")
            
            # Обнаружение аномалий
            if len(oi_history) >= 2:
                anomalies = OpenInterestData.detect_anomalies(
                    oi_history,
                    threshold_percent=Decimal('5.0')  # 5% изменение считается аномальным
                )
                
                if anomalies:
                    logger.info("\nОбнаружены аномалии:")
                    for anomaly in anomalies:
                        logger.info(
                            f"  {anomaly['timestamp']}: {anomaly['type']} на {anomaly['percentage_change']:.2f}% "
                            f"({anomaly['previous_value']} -> {anomaly['current_value']})"
                        )
            
            return oi_history
            
        except Exception as e:
            logger.error(f"Ошибка при получении истории открытого интереса: {str(e)}")
            raise


async def plot_open_interest_history(oi_history):
    """
    Пример визуализации истории открытого интереса.
    """
    if not oi_history:
        logger.warning("Нет данных для визуализации")
        return
    
    # Преобразуем данные в DataFrame
    df = OpenInterestData.to_dataframe(oi_history)
    
    # Создаем график
    fig, ax1 = plt.subplots(figsize=(12, 6))
    
    # Строим график открытого интереса
    ax1.set_xlabel('Время')
    ax1.set_ylabel('Открытый интерес', color='tab:blue')
    ax1.plot(df.index, df['open_interest'], color='tab:blue')
    ax1.tick_params(axis='y', labelcolor='tab:blue')
    
    # Добавляем второй y-axis для стоимости
    if 'open_interest_value' in df.columns and not df['open_interest_value'].isna().all():
        ax2 = ax1.twinx()
        ax2.set_ylabel('Стоимость (USD)', color='tab:red')
        ax2.plot(df.index, df['open_interest_value'], color='tab:red')
        ax2.tick_params(axis='y', labelcolor='tab:red')
    
    # Форматируем оси
    plt.title('История открытого интереса')
    date_form = DateFormatter("%Y-%m-%d %H:%M")
    ax1.xaxis.set_major_formatter(date_form)
    fig.autofmt_xdate()  # Наклоняем даты для лучшей читаемости
    
    # Добавляем сетку
    ax1.grid(True, alpha=0.3)
    
    # Добавляем аномалии, если они есть
    if len(oi_history) >= 2:
        anomalies = OpenInterestData.detect_anomalies(
            oi_history,
            threshold_percent=Decimal('5.0')
        )
        
        if anomalies:
            anomaly_times = [anomaly['timestamp'] for anomaly in anomalies]
            anomaly_values = [float(anomaly['current_value']) for anomaly in anomalies]
            anomaly_types = [anomaly['type'] for anomaly in anomalies]
            
            # Разные цвета для разных типов аномалий
            colors = {'increase': 'green', 'decrease': 'red'}
            
            for time, value, type_ in zip(anomaly_times, anomaly_values, anomaly_types):
                ax1.scatter(time, value, color=colors.get(type_, 'orange'), s=80, zorder=5)
    
    plt.tight_layout()
    plt.show()


async def real_time_open_interest_example():
    """
    Пример получения обновлений открытого интереса в реальном времени.
    """
    # Создаем конфигурацию
    config = ClientConfig(
        api_key="YOUR_API_KEY",       # Можно оставить пустым для публичных эндпоинтов
        api_secret="YOUR_API_SECRET", # Можно оставить пустым для публичных эндпоинтов
        base_url="wss://stream-testnet.bybit.com",
        exchange_name="bybit"
    )
    
    # Последние полученные значения
    values = []
    
    # Колбэк-функция для обработки обновлений
    async def on_open_interest_update(oi_data: OpenInterestData):
        values.append(oi_data)
        
        # Ограничиваем размер списка
        if len(values) > 100:
            values.pop(0)
        
        logger.info(
            f"Обновление OI для {oi_data.symbol}: {oi_data.open_interest} "
            f"(стоимость: {oi_data.open_interest_value} USD)"
        )
        
        # Если есть предыдущее значение, вычисляем изменение
        if len(values) >= 2:
            prev_oi = values[-2]
            change = OpenInterestData.calculate_change(oi_data, prev_oi)
            
            # Выводим информацию об изменении, если оно значительное
            if abs(change['percentage']) >= Decimal('0.5'):
                logger.info(
                    f"  Изменение: {change['absolute']} ({change['percentage']:.2f}%)"
                )
    
    # Создаем WebSocket провайдер
    async with BybitMarketDataStreamProvider(config) as stream_provider:
        try:
            # Устанавливаем соединение
            await stream_provider.connect()
            
            # Подписываемся на обновления открытого интереса для BTCUSDT
            subscription_id = await stream_provider.subscribe_to_open_interest(
                "BTCUSDT",
                on_open_interest_update
            )
            
            logger.info(f"Подписка на обновления открытого интереса установлена (ID: {subscription_id})")
            logger.info("Нажмите Ctrl+C для завершения...")
            
            # Ожидаем обновлений
            try:
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                logger.info("Получен сигнал завершения")
            
            # Отписываемся при завершении
            await stream_provider.unsubscribe_from_open_interest(subscription_id)
            logger.info("Отписка выполнена")
            
        except Exception as e:
            logger.error(f"Ошибка при работе с WebSocket: {str(e)}")
            raise


async def combined_service_example():
    """
    Пример использования объединенного сервиса для работы с открытым интересом.
    """
    # Создаем конфигурацию
    config = ClientConfig(
        api_key="YOUR_API_KEY",       # Можно оставить пустым для публичных эндпоинтов
        api_secret="YOUR_API_SECRET", # Можно оставить пустым для публичных эндпоинтов
        base_url="https://api-testnet.bybit.com",
        ws_base_url="wss://stream-testnet.bybit.com",
        exchange_name="bybit"
    )
    
    # Создаем объединенный сервис
    async with BybitMarketDataService(config) as service:
        try:
            # Получаем текущий открытый интерес
            current_oi = await service.get_open_interest("BTCUSDT")
            logger.info(f"Текущий открытый интерес: {current_oi.open_interest}")
            
            # Получаем историю
            oi_history = await service.get_open_interest_history("BTCUSDT", "1h", 10)
            logger.info(f"Получено {len(oi_history)} записей истории")
            
            # Устанавливаем колбэк для обновлений
            updates_received = 0
            
            async def on_update(oi_data: OpenInterestData):
                nonlocal updates_received
                updates_received += 1
                logger.info(f"Получено обновление #{updates_received}: {oi_data.open_interest}")
            
            # Подписываемся на обновления
            subscription_id = await service.subscribe_to_open_interest("BTCUSDT", on_update)
            
            # Ожидаем несколько обновлений
            logger.info("Ожидание обновлений в течение 30 секунд...")
            await asyncio.sleep(30)
            
            # Отписываемся
            await service.unsubscribe_from_open_interest(subscription_id)
            logger.info(f"Отписка выполнена. Всего получено {updates_received} обновлений.")
            
        except Exception as e:
            logger.error(f"Ошибка при работе с сервисом: {str(e)}")
            raise


async def main():
    """
    Основная функция для демонстрации примеров.
    """
    logger.info("Начало демонстрации примеров работы с открытым интересом")
    
    try:
        # Пример получения текущего открытого интереса
        logger.info("\n=== Пример 1: Получение текущего открытого интереса ===")
        await get_current_open_interest_example()
        
        # Пример получения истории открытого интереса
        logger.info("\n=== Пример 2: Получение истории открытого интереса ===")
        oi_history = await get_open_interest_history_example()
        
        # Пример визуализации
        logger.info("\n=== Пример 3: Визуализация истории открытого интереса ===")
        await plot_open_interest_history(oi_history)
        
        # Пример получения обновлений в реальном времени
        logger.info("\n=== Пример 4: Обновления открытого интереса в реальном времени ===")
        await real_time_open_interest_example()
        
        # Пример использования объединенного сервиса
        logger.info("\n=== Пример 5: Использование объединенного сервиса ===")
        await combined_service_example()
        
    except Exception as e:
        logger.error(f"Ошибка при выполнении примеров: {str(e)}")
    
    logger.info("Демонстрация завершена")


if __name__ == "__main__":
    # Запускаем асинхронную функцию в цикле событий
    asyncio.run(main()) 
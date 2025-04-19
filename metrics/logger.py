# logger.py
import logging
import json
from datetime import datetime


class MetricLogger:
    def __init__(self):
        self.logger = logging.getLogger('minutely_metrics')
        self.logger.setLevel(logging.INFO)

        # Настройка обработчика для записи в файл
        handler = logging.FileHandler('minutely_metrics.log')
        handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
        self.logger.addHandler(handler)

    def log_metrics(self, metrics):
        try:
            log_data = {
                'timestamp': metrics['timestamp'],
                'metrics': metrics['metrics']
            }

            # Логируем в JSON формате для удобства последующего анализа
            self.logger.info(json.dumps(log_data, indent=2, ensure_ascii=False))

            # Дополнительно выводим ключевые метрики в консоль
            print(f"\n=== Minutely Metrics [{metrics['metrics']['current_minute']}] ===")
            print(f"Transactions: {metrics['metrics']['transactions_last_min']}")
            print(f"Avg Price: {metrics['metrics']['avg_price_last_min']:.2f}")
            print(f"Active Sessions: {metrics['metrics']['active_sessions']}")
            print(f"New Logins: {metrics['metrics']['new_logins']}")
            print(f"Errors: {metrics['metrics']['errors_last_min']}")

        except Exception as e:
            self.logger.error(f"Failed to log metrics: {str(e)}")
            print(f"Error logging metrics: {str(e)}")
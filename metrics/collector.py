# collector.py
from datetime import datetime, timedelta
from collections import defaultdict
import statistics


class MetricsCollector:
    @staticmethod
    def collect_all(db_sess):
        from .models import User, ErrorLog

        now = datetime.now()
        minute_key = now.strftime('%Y-%m-%d %H:%M')
        hour_key = now.strftime('%Y-%m-%d %H:00')
        day_key = now.strftime('%Y-%m-%d')

        users = db_sess.query(User).all()
        recent_errors = db_sess.query(ErrorLog).filter(
            ErrorLog.timestamp >= now - timedelta(minutes=1)
        ).count()

        metrics = {
            'minutely': defaultdict(list),
            'hourly': defaultdict(list),
            'daily': defaultdict(list),
            'user_activity': {
                'logins_last_min': 0,
                'active_sessions': 0,
                'new_sessions': 0
            },
            'errors': {
                'last_minute': recent_errors,
                'total_today': db_sess.query(ErrorLog).filter(
                    ErrorLog.timestamp >= datetime(now.year, now.month, now.day)
                ).count()
            }
        }

        for user in users:
            # Анализ активности
            if user.login_time and (now - user.login_time <= timedelta(minutes=1)):
                metrics['user_activity']['logins_last_min'] += 1

            if user.login_time and ((not user.logout_time) or (user.login_time > user.logout_time)):
                metrics['user_activity']['active_sessions'] += 1

            # Анализ транзакций
            price_history = user.get_price_history()
            for entry in price_history:
                entry_time = datetime.strptime(entry['date'], '%Y-%m-%d %H:%M:%S')
                time_diff = now - entry_time

                if time_diff <= timedelta(minutes=1):
                    metrics['minutely']['prices'].append(entry['price'])
                    if entry['volume']:
                        metrics['minutely']['volumes'].append(float(entry['volume']))
                    if entry['waste_class']:
                        metrics['minutely'][f"waste_{entry['waste_class']}"].append(entry['price'])

                if time_diff <= timedelta(hours=1):
                    metrics['hourly'][hour_key].append(entry['price'])

                if entry_time.date() == now.date():
                    metrics['daily'][day_key].append(entry['price'])

        # Расчет агрегированных метрик
        result = {
            'timestamp': now.isoformat(),
            'metrics': {
                'current_minute': minute_key,
                'transactions_last_min': len(metrics['minutely']['prices']),
                'avg_price_last_min': statistics.mean(metrics['minutely']['prices']) if metrics['minutely'][
                    'prices'] else 0,
                'avg_volume_last_min': statistics.mean(metrics['minutely']['volumes']) if metrics['minutely'][
                    'volumes'] else 0,
                'active_sessions': metrics['user_activity']['active_sessions'],
                'new_logins': metrics['user_activity']['logins_last_min'],
                'errors_last_min': metrics['errors']['last_minute'],
                'hourly_metrics': {},
                'waste_class_metrics': {}
            }
        }

        # Добавляем метрики по классам отходов
        for key in metrics['minutely']:
            if key.startswith('waste_'):
                class_name = key.replace('waste_', '')
                result['metrics']['waste_class_metrics'][class_name] = {
                    'avg_price': statistics.mean(metrics['minutely'][key]),
                    'transactions': len(metrics['minutely'][key])
                }

        # Агрегация по часам
        for hour, prices in metrics['hourly'].items():
            result['metrics']['hourly_metrics'][hour] = {
                'avg_price': statistics.mean(prices) if prices else 0,
                'transactions': len(prices)
            }

        # Дневные метрики
        for day, prices in metrics['daily'].items():
            result['metrics']['daily_metrics'] = {
                'avg_price': statistics.mean(prices) if prices else 0,
                'transactions': len(prices)
            }

        return result
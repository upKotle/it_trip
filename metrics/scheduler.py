from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import timedelta
from data import db_session


def init_scheduler(app):
    """Инициализация планировщика метрик"""
    scheduler = BackgroundScheduler(daemon=True)

    def collect_and_log():
        with app.app_context():
            db_sess = db_session.create_session()
            try:
                from .collector import MetricsCollector
                from .logger import MetricLogger

                metrics = MetricsCollector.collect_all(db_sess)
                logger = MetricLogger()
                logger.log_metrics(metrics)
            except Exception as e:
                app.logger.error(f"Metrics collection error: {str(e)}")
            finally:
                db_sess.close()

    scheduler.add_job(
        collect_and_log,
        trigger=IntervalTrigger(minutes=1),
        id='metrics_collection',
        replace_existing=True
    )

    scheduler.start()
# Используем официальный образ Python
FROM python:3.9-slim

# Устанавливаем зависимости системы
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Создаем и переходим в рабочую директорию
WORKDIR /app

# Копируем зависимости и устанавливаем их
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь проект
COPY . .

# Создаем необходимые директории
RUN mkdir -p /app/logs /app/db /app/static/img /app/metrics

# Указываем переменные окружения
ENV FLASK_APP=main.py
ENV FLASK_ENV=production
ENV DATABASE_URL=sqlite:////app/db/GreenAtom.db

# Открываем порт
EXPOSE 5000

# Команда для запуска приложения
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "main:app"]
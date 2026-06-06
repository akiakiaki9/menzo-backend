FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/static /app/staticfiles /media

# Создаем скрипт запуска
RUN echo '#!/bin/bash\n\
python manage.py migrate --noinput\n\
python manage.py create_superuser\n\
gunicorn --bind 0.0.0.0:8000 core.wsgi:application' > /app/start.sh && chmod +x /app/start.sh

CMD ["/app/start.sh"]
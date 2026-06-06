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

# Временно закомментировать collectstatic
# RUN python manage.py collectstatic --noinput

# Создаем скрипт запуска
RUN echo '#!/bin/bash\n\
python manage.py migrate --noinput\n\
python manage.py collectstatic --noinput --ignore=node_modules\n\
gunicorn --bind 0.0.0.0:8000 core.wsgi:application' > /app/start.sh && chmod +x /app/start.sh

CMD ["/app/start.sh"]
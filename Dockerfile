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

RUN python manage.py migrate --noinput || true
RUN echo "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.filter(username='superadmin').exists() or User.objects.create_superuser('superadmin', 'tillayevakbarshoh@gmail.com', '151204Akbar999+*%')" | python manage.py shell

# Запускаем миграции и сервер
CMD python manage.py migrate --noinput && gunicorn --bind 0.0.0.0:8000 core.wsgi:application
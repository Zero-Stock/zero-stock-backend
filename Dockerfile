FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python manage.py collectstatic --noinput

#CMD ["sh", "-c", "gunicorn canteen_system.wsgi:application --bind 0.0.0.0:${PORT}"]

#CMD ["sh", "-c", "python manage.py migrate --noinput && gunicorn canteen_system.wsgi:application --bind 0.0.0.0:${PORT}"]

#CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py shel -c \"from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.filter(username='admin').exists() or User.objects.create_superuser('admin', 'admin@example.com', 'admin123')\" && gunicorn canteen_system.wsgi:application --bind 0.0.0.0:${PORT}"]

CMD ["sh", "-c", "gunicorn canteen_system.wsgi:application --bind 0.0.0.0:${PORT}"]

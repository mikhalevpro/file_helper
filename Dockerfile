FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /djangoProject

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN mkdir -p djangoProject/
COPY djangoProject /djangoProject/
ENV DJANGO_SETTINGS_MODULE=djangoProject.settings
CMD ["sh", "-c", "while ! pg_isready -h db -U file_helper -d db_file_helper -q; do echo 'wait database'; sleep 2; done; echo 'database Done!'; python3 manage.py migrate && python3 manage.py runserver 0.0.0.0:8000"]

FROM python:3.9-slim

# Открываем порт, который использует dockhost по умолчанию
EXPOSE 5000

WORKDIR /app

# Копируем зависимости первыми для кэширования
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Используем gunicorn для production
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "app:bot"]

FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Rode o worker ao subir o container
CMD ["python", "-m", "telegram_worker.bot"]

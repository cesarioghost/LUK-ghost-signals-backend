FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Por segurança, garanta que o TZ esteja correto (opcional)
ENV TZ=UTC

# Processo principal: bot do Telegram
CMD ["python", "-m", "telegram_worker.bot"]

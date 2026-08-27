FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY config.py db.py mikrotik.py provisioning.py bot.py ./

RUN mkdir -p /data

ENV DATABASE_PATH=/data/vpn-bot.db

CMD ["python", "-u", "bot.py"]

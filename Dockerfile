FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt && \
    python -m playwright install --with-deps chromium

COPY . .

CMD ["python", "main.py"]

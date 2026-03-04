FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
ARG CACHEBUST=3
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run migrations then start server
CMD alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}

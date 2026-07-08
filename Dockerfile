# Vuln Geeks Shop — image aplikasi (FastAPI/Uvicorn)
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# psycopg2-binary butuh libpq di runtime; slim image sudah cukup untuk wheel.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl iputils-ping \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Bind ke 0.0.0.0 HANYA di dalam container (jaringan internal Docker).
# Publikasi ke host dibatasi ke 127.0.0.1 lewat port mapping di docker-compose.yml.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

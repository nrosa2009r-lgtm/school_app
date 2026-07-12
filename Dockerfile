# ============================================================
#  School Catering Application - Dockerfile
#  Wersja: 2.0 Enterprise
# ============================================================

FROM python:3.11-slim

LABEL maintainer="School Catering Team"
LABEL description="School Catering Application - Multi-Tenant Enterprise Edition"

# Zmienne srodowiskowe
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV TZ=Europe/Warsaw

WORKDIR /app

# Instalacja zaleznosci systemowych
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Kopiowanie plikow zaleznosci
COPY requirements.txt .

# Instalacja zaleznosci Python
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Kopiowanie kodu aplikacji
COPY . .

# Tworzenie niezbednych katalogow
RUN mkdir -p /app/venv/database /app/venv/log /app/venv/config

# Porty
EXPOSE 8000
EXPOSE 8550

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

# Wolumen na dane
VOLUME ["/app/venv/database", "/app/venv/config", "/app/venv/log"]

# Uruchomienie
CMD ["sh", "-c", "python main.py --check-or-setup --non-interactive && uvicorn api.main:app --host 0.0.0.0 --port 8000"]

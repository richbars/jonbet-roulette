FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Dependências mínimas para Chromium + Playwright
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    ca-certificates \
    fonts-liberation \
    libglib2.0-0 \
    libnss3 \
    libx11-6 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libxrender1 \
    libxss1 \
    libxtst6 \
    wget \
    unzip \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# Copia requirements e instala Python packages
COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Instala Playwright e navegadores
RUN pip install playwright && playwright install --with-deps

# Copia o código da aplicação
COPY . .

EXPOSE 8000

CMD ["python", "polling.py"]
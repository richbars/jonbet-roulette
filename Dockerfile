FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Instala dependências do sistema necessárias para Playwright e Chromium
RUN apt-get update && apt-get install -y \
    build-essential \
    wget \
    curl \
    unzip \
    ca-certificates \
    libglib2.0-0 \
    libnss3 \
    libgconf-2-4 \
    libfontconfig1 \
    libx11-6 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxi6 \
    libxrandr2 \
    libxrender1 \
    libxss1 \
    libxtst6 \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# Copia requirements e instala Python packages
COPY requirements.txt .

RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Instala Playwright e os navegadores
RUN pip install playwright && playwright install --with-deps

# Copia o restante do código
COPY . .

# Variável opcional para Playwright localizar Chromium
ENV CHROME_BIN=/usr/bin/chromium

EXPOSE 8000

CMD ["python", "polling.py"]
FROM python:3.13-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 🔥 Dependências do sistema (Chrome + libs)
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
    ca-certificates \
    fonts-liberation \
    libnss3 \
    libatk-bridge2.0-0 \
    libx11-xcb1 \
    libxcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libatk1.0-0 \
    libcups2 \
    libxshmfence1 \
    libxfixes3 \
    libxi6 \
    libxtst6 \
    libglib2.0-0 \
    libdrm2 \
    libxkbcommon0 \
    libatspi2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# 🔥 Instalar Google Chrome
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/google.gpg] http://dl.google.com/linux/chrome/deb/ stable main" \
    > /etc/apt/sources.list.d/google.list && \
    apt-get update && \
    apt-get install -y google-chrome-stable && \
    rm -rf /var/lib/apt/lists/*

# 🔥 Copiar requirements e instalar Python deps
COPY requirements.txt .

RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 🔥 Copiar projeto
COPY . .

# 🔥 Garantir que Chrome está acessível
ENV CHROME_BIN=/usr/bin/google-chrome

EXPOSE 8000

CMD ["python", "polling.py"]
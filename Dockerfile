# Pin the base to avoid surprise breakages
FROM python:3.11-slim-bookworm

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1 \
    CHROME_BIN=/usr/bin/google-chrome

# System deps + Google Chrome repo + Chrome install (one layer, cleaned)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      ca-certificates curl wget unzip gnupg xdg-utils \
      fonts-liberation \
      # Chrome/Selenium runtime libs
      libasound2 libatk-bridge2.0-0 libatk1.0-0 libcairo2 libcups2 \
      libdbus-1-3 libgdk-pixbuf-2.0-0 libnspr4 libnss3 \
      libx11-6 libx11-xcb1 libxcomposite1 libxdamage1 libxext6 libxfixes3 \
      libxi6 libxrandr2 libxrender1 libxss1 libxtst6 libgbm1 libgtk-3-0 \
      libayatana-appindicator3-1 \
      xvfb && \
    # Add Google’s signing key + repo the modern way
    install -m 0755 -d /etc/apt/keyrings && \
    curl -fsSL https://dl.google.com/linux/linux_signing_key.pub \
      | gpg --dearmor -o /etc/apt/keyrings/google-linux.gpg && \
    chmod a+r /etc/apt/keyrings/google-linux.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/google-linux.gpg] http://dl.google.com/linux/chrome/deb/ stable main" \
      > /etc/apt/sources.list.d/google-chrome.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends google-chrome-stable && \
    # Clean apt caches to keep image small
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt .
RUN pip install -r requirements.txt

# App
WORKDIR /app
COPY . /app

# Default command (your cron runner)
CMD ["python", "run_all_scrapers.py"]

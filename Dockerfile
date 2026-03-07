# Das Caner - Docker Configuration
# Build: docker build -t caner .
# Run: docker run -p 30823:30823 --env-file .env caner

FROM python:3.13-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UV_SYSTEM_PYTHON=1 \
    DEBIAN_FRONTEND=noninteractive

# Set work directory
WORKDIR /app

# Install system dependencies including Firefox and geckodriver for Selenium
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    cron \
    supervisor \
    logrotate \
    firefox-esr \
    wget \
    bzip2 \
    && rm -rf /var/lib/apt/lists/*

# Install geckodriver for Firefox/Selenium (pinned version for reliability)
RUN GECKODRIVER_VERSION="v0.35.0" \
    && wget -q "https://github.com/mozilla/geckodriver/releases/download/${GECKODRIVER_VERSION}/geckodriver-${GECKODRIVER_VERSION}-linux64.tar.gz" \
    && tar -xzf "geckodriver-${GECKODRIVER_VERSION}-linux64.tar.gz" -C /usr/local/bin \
    && rm "geckodriver-${GECKODRIVER_VERSION}-linux64.tar.gz" \
    && chmod +x /usr/local/bin/geckodriver

# Install uv using pip for better security (instead of curl | sh)
RUN pip install --no-cache-dir uv

# Copy project files
COPY pyproject.toml uv.lock ./
COPY requirements.txt ./

# Install Python dependencies using uv
RUN uv sync --frozen --no-dev

# Copy application code
COPY . .

# Create log directory and set up log rotation
RUN mkdir -p /app/logs

# Configure logrotate for data_fetcher logs
RUN printf '%s\n' '/app/logs/data_fetcher.log {' '    daily' '    rotate 7' '    compress' '    delaycompress' '    missingok' '    notifempty' '    create 644 root root' '}' > /etc/logrotate.d/data_fetcher

# Set timezone to Europe/Berlin (CET/CEST)
ENV TZ=Europe/Berlin
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Create cron script for data fetcher - runs at 6:00 AM and 11:00 AM CET
RUN echo '0 6,11 * * * cd /app && uv run --frozen python data_fetcher.py >> /app/logs/data_fetcher.log 2>&1' > /etc/cron.d/data_fetcher \
    && chmod 0644 /etc/cron.d/data_fetcher \
    && crontab /etc/cron.d/data_fetcher

# Create necessary directories
RUN mkdir -p /var/run /var/log/supervisor

# Expose port
EXPOSE 30823

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:30823/ || exit 1

# Run supervisord as root
CMD ["supervisord", "-c", "/app/supervisord.conf"]

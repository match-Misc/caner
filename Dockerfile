# Das Caner - Docker Configuration
# Build: docker build -t caner .
# Run: docker run -p 30823:30823 --env-file .env caner

FROM python:3.13-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UV_SYSTEM_PYTHON=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    cron \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Copy project files
COPY pyproject.toml uv.lock ./
COPY requirements.txt ./

# Install Python dependencies using uv
RUN uv sync --frozen --no-dev

# Copy application code
COPY app.py ./
COPY main.py ./
COPY models.py ./
COPY gunicorn.conf.py ./
COPY supervisord.conf ./
COPY data_fetcher.py ./
COPY data_loader.py ./
COPY utils/ ./utils/
COPY templates/ ./templates/
COPY static/ ./static/

# Create log directory
RUN mkdir -p /app/logs

# Set timezone to Europe/Berlin (CET/CEST)
ENV TZ=Europe/Berlin
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Create cron script for data fetcher - runs at 6:00 AM and 11:00 AM CET
RUN echo '0 6,11 * * * root cd /app && uv run --frozen python data_fetcher.py >> /app/logs/data_fetcher.log 2>&1' > /etc/cron.d/data_fetcher && \
    chmod 0644 /etc/cron.d/data_fetcher && \
    crontab /etc/cron.d/data_fetcher

# Expose port (matching the original script)
EXPOSE 30823

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:30823/ || exit 1

# Use supervisord to manage gunicorn and cron
CMD ["supervisord", "-c", "/app/supervisord.conf"]

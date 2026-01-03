FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies (cron + postgresql-client for pg_isready)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    cron \
    postgresql-client && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy scripts
COPY scripts/ ./scripts/
RUN chmod +x ./scripts/*.py

# Copy cron file to /etc/cron.d/
COPY crontab /etc/cron.d/openfoodfacts-cron

# Set permissions
RUN chmod 0644 /etc/cron.d/openfoodfacts-cron

# Create log file
RUN touch /var/log/cron.log

# Copy entrypoint script
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Run entrypoint script
CMD ["/app/entrypoint.sh"]

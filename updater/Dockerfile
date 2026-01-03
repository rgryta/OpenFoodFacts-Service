FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies (including cron)
RUN apt-get update && \
    apt-get install -y --no-install-recommends cron && \
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

# Run cron in foreground
CMD ["cron", "-f"]

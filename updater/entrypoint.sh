#!/bin/bash
set -e

echo "OpenFoodFacts Updater - Starting..."

# Wait for database to be ready
echo "Waiting for database to be ready..."
until pg_isready -h off-db -p 5432 -U offuser; do
    echo "Database is unavailable - sleeping"
    sleep 2
done
echo "Database is ready!"

# Check if database has products
echo "Checking if database needs initialization..."
PRODUCT_COUNT=$(PGPASSWORD="${POSTGRES_PASSWORD:-password}" psql -h off-db -U offuser -d openfoodfacts -t -c "SELECT COUNT(*) FROM products;" 2>/dev/null || echo "0")
PRODUCT_COUNT=$(echo $PRODUCT_COUNT | xargs)  # Trim whitespace

echo "Current product count: $PRODUCT_COUNT"

if [ "$PRODUCT_COUNT" -eq "0" ]; then
    echo "Database is empty. Starting initialization..."
    python3 /app/scripts/initial_load.py

    if [ $? -eq 0 ]; then
        echo "Initialization completed successfully!"
    else
        echo "Initialization failed!"
        exit 1
    fi
else
    echo "Database already contains $PRODUCT_COUNT products. Skipping initialization."

    # Ensure bootstrap marker exists
    touch /app/data/.bootstrap_complete
fi

# Start cron in foreground
echo "Starting cron scheduler for delta updates..."
cron -f

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

# Check if bootstrap is complete (marker file exists)
BOOTSTRAP_MARKER="/app/data/.bootstrap_complete"

if [ -f "$BOOTSTRAP_MARKER" ]; then
    PRODUCT_COUNT=$(PGPASSWORD="${POSTGRES_PASSWORD:-password}" psql -h off-db -U offuser -d openfoodfacts -t -c "SELECT COUNT(*) FROM products;" 2>/dev/null || echo "0")
    PRODUCT_COUNT=$(echo $PRODUCT_COUNT | xargs)
    echo "Bootstrap already complete. Database contains $PRODUCT_COUNT products."
else
    echo "Bootstrap marker not found. Running initialization..."
    PRODUCT_COUNT=$(PGPASSWORD="${POSTGRES_PASSWORD:-password}" psql -h off-db -U offuser -d openfoodfacts -t -c "SELECT COUNT(*) FROM products;" 2>/dev/null || echo "0")
    PRODUCT_COUNT=$(echo $PRODUCT_COUNT | xargs)

    if [ "$PRODUCT_COUNT" -gt "0" ]; then
        echo "Found $PRODUCT_COUNT existing products. Bootstrap will resume/update."
    fi

    python3 /app/scripts/initial_load.py

    if [ $? -eq 0 ]; then
        echo "Initialization completed successfully!"
    else
        echo "Initialization failed!"
        exit 1
    fi
fi

# Start cron in foreground
echo "Starting cron scheduler for delta updates..."
cron -f

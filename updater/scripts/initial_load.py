#!/usr/bin/env python3
"""
Initial bootstrap script for OpenFoodFacts database.
Downloads JSONL file from OpenFoodFacts and loads into PostgreSQL.
Uses streaming to minimize memory usage.
"""
import os
import sys
import logging
import asyncio
from pathlib import Path

# Add utils to path
sys.path.insert(0, str(Path(__file__).parent))

from utils.download import download_file
from utils.parser import parse_jsonl_file
from utils.db import create_connection, upsert_products_batch

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://offuser:password@off-db:5432/openfoodfacts")
JSONL_URL = os.getenv(
    "OFF_JSONL_URL",
    "https://static.openfoodfacts.org/data/openfoodfacts-products.jsonl.gz"
)
DATA_DIR = Path("/app/data")
BATCH_SIZE = 5000


async def main():
    """Main bootstrap function"""
    logger.info("Starting OpenFoodFacts database bootstrap")

    # Create data directory
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    jsonl_file = DATA_DIR / "openfoodfacts-products.jsonl.gz"

    # Step 1: Download JSONL file
    logger.info(f"Downloading JSONL file from {JSONL_URL}")
    logger.info("This will download ~7 GB (compressed), please be patient...")
    success = await download_file(JSONL_URL, jsonl_file, timeout=7200)  # 2 hour timeout

    if not success:
        logger.error("Failed to download JSONL file")
        sys.exit(1)

    # Step 2: Process JSONL and insert to PostgreSQL
    try:
        logger.info("Connecting to PostgreSQL...")
        pg_conn = await create_connection(DATABASE_URL)

        logger.info(f"Processing products in batches of {BATCH_SIZE:,}...")
        logger.info("This will take 1-2 hours. Progress logged every 100k products.")

        total_processed = 0
        batch = []

        # Stream parse JSONL file (memory efficient)
        for product in parse_jsonl_file(jsonl_file):
            batch.append(product)

            # Upsert when batch is full
            if len(batch) >= BATCH_SIZE:
                await upsert_products_batch(pg_conn, batch)
                total_processed += len(batch)
                # Progress logged by parser every 100k
                batch = []

        # Insert remaining products
        if batch:
            await upsert_products_batch(pg_conn, batch)
            total_processed += len(batch)
            logger.info(f"Final batch processed. Total: {total_processed:,}")

        # Close connection
        await pg_conn.close()

        logger.info(f"Bootstrap complete! Loaded {total_processed:,} products")

        # Cleanup JSONL file to save space
        logger.info("Cleaning up JSONL file...")
        jsonl_file.unlink()

        # Create bootstrap completion marker
        bootstrap_marker = DATA_DIR / ".bootstrap_complete"
        bootstrap_marker.touch()
        logger.info("Bootstrap marker created")

        logger.info("Bootstrap successful!")

    except Exception as e:
        logger.exception(f"Bootstrap failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python3
"""
Weekly cleanup script for OpenFoodFacts database.
Compares database with fresh JSONL to identify and remove deleted products.
"""
import os
import sys
import logging
import asyncio
import json
import gzip
from pathlib import Path

# Add utils to path
sys.path.insert(0, str(Path(__file__).parent))

from utils.download import download_file
from utils.db import create_connection, get_all_product_codes, delete_products_by_codes

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


async def main():
    """Main cleanup function"""
    logger.info("Starting OpenFoodFacts weekly cleanup")

    # Create data directory
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Check if bootstrap has completed
    bootstrap_marker = DATA_DIR / ".bootstrap_complete"
    if not bootstrap_marker.exists():
        logger.warning("Bootstrap not complete. Skipping weekly cleanup.")
        logger.info("Run initial_load.py first to bootstrap the database.")
        return

    jsonl_file = DATA_DIR / "openfoodfacts_cleanup.jsonl.gz"

    # Step 1: Download fresh JSONL file
    logger.info(f"Downloading JSONL file from {JSONL_URL}")
    logger.info("This will download ~7 GB (compressed), please be patient...")
    success = await download_file(JSONL_URL, jsonl_file, timeout=7200)

    if not success:
        logger.error("Failed to download JSONL file")
        sys.exit(1)

    # Step 2: Get product codes from JSONL (streaming to save memory)
    logger.info("Extracting product codes from JSONL...")

    try:
        jsonl_codes = set()
        count = 0

        with gzip.open(jsonl_file, "rt", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue

                try:
                    product_data = json.loads(line)
                    code = product_data.get("code") or product_data.get("_id")

                    if code:
                        jsonl_codes.add(str(code))
                        count += 1

                        # Log progress every 500k products
                        if count % 500000 == 0:
                            logger.info(f"Extracted {count:,} product codes...")

                except json.JSONDecodeError:
                    continue

        logger.info(f"JSONL contains {len(jsonl_codes):,} products")

        # Step 3: Get product codes from database
        logger.info("Fetching product codes from database...")
        conn = await create_connection(DATABASE_URL)

        db_codes = await get_all_product_codes(conn)
        logger.info(f"Database contains {len(db_codes):,} products")

        # Step 4: Find products in database but not in JSONL (deleted)
        deleted_codes = db_codes - jsonl_codes
        logger.info(f"Found {len(deleted_codes):,} products to delete")

        # Step 5: Delete products
        if deleted_codes:
            logger.info("Deleting obsolete products...")
            deleted_count = await delete_products_by_codes(conn, list(deleted_codes))
            logger.info(f"Deleted {deleted_count:,} products")
        else:
            logger.info("No products to delete")

        # Close connection
        await conn.close()

        # Cleanup JSONL file
        logger.info("Cleaning up JSONL file...")
        jsonl_file.unlink()

        logger.info("Weekly cleanup complete!")

    except Exception as e:
        logger.exception(f"Cleanup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

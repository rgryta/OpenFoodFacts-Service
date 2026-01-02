#!/usr/bin/env python3
"""
Weekly cleanup script for OpenFoodFacts database.
Compares database with fresh Parquet to identify and remove deleted products.
"""
import os
import sys
import logging
import asyncio
from pathlib import Path
import duckdb

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
PARQUET_URL = os.getenv(
    "OFF_PARQUET_URL",
    "https://huggingface.co/datasets/openfoodfacts/product-database/resolve/main/food.parquet"
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

    parquet_file = DATA_DIR / "openfoodfacts_cleanup.parquet"

    # Step 1: Download fresh Parquet file
    logger.info(f"Downloading Parquet file from {PARQUET_URL}")
    success = await download_file(PARQUET_URL, parquet_file)

    if not success:
        logger.error("Failed to download Parquet file")
        sys.exit(1)

    # Step 2: Get product codes from Parquet
    logger.info("Extracting product codes from Parquet...")

    try:
        duck_conn = duckdb.connect()

        # Get all codes from Parquet
        parquet_codes_result = duck_conn.execute(
            f"""
            SELECT code
            FROM '{parquet_file}'
            WHERE code IS NOT NULL
            """
        ).fetchall()

        parquet_codes = {str(row[0]) for row in parquet_codes_result}
        logger.info(f"Parquet contains {len(parquet_codes):,} products")

        duck_conn.close()

        # Step 3: Get product codes from database
        logger.info("Fetching product codes from database...")
        conn = await create_connection(DATABASE_URL)

        db_codes = await get_all_product_codes(conn)
        logger.info(f"Database contains {len(db_codes):,} products")

        # Step 4: Find products in database but not in Parquet (deleted)
        deleted_codes = db_codes - parquet_codes
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

        # Cleanup Parquet file
        logger.info("Cleaning up Parquet file...")
        parquet_file.unlink()

        logger.info("Weekly cleanup complete!")

    except Exception as e:
        logger.exception(f"Cleanup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

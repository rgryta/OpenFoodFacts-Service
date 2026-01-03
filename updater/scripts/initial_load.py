#!/usr/bin/env python3
"""
Initial bootstrap script for OpenFoodFacts database.
Downloads Parquet file from Hugging Face and loads into PostgreSQL.
"""
import os
import sys
import logging
import asyncio
from pathlib import Path
import duckdb
import pandas as pd

# Add utils to path
sys.path.insert(0, str(Path(__file__).parent))

from utils.download import download_file
from utils.parser import extract_product_fields
from utils.db import create_connection, upsert_products_batch

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
BATCH_SIZE = 1000


async def main():
    """Main bootstrap function"""
    logger.info("Starting OpenFoodFacts database bootstrap")

    # Create data directory
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    parquet_file = DATA_DIR / "openfoodfacts.parquet"

    # Step 1: Download Parquet file
    logger.info(f"Downloading Parquet file from {PARQUET_URL}")
    success = await download_file(PARQUET_URL, parquet_file)

    if not success:
        logger.error("Failed to download Parquet file")
        sys.exit(1)

    # Step 2: Load Parquet with DuckDB
    logger.info("Loading Parquet file with DuckDB...")

    try:
        # Connect to DuckDB (in-memory)
        duck_conn = duckdb.connect()

        # Query total row count
        total_count = duck_conn.execute(f"SELECT COUNT(*) FROM '{parquet_file}'").fetchone()[0]
        logger.info(f"Total products in Parquet: {total_count:,}")

        # Step 3: Connect to PostgreSQL
        logger.info("Connecting to PostgreSQL...")
        pg_conn = await create_connection(DATABASE_URL)

        logger.info(f"Processing products in batches of {BATCH_SIZE:,}...")

        total_processed = 0
        batch = []

        # Stream rows in chunks to save memory
        query = f"SELECT * FROM '{parquet_file}'"
        res = duck_conn.execute(query)

        batch_size = BATCH_SIZE
        offset = 0

        while True:
            batch_df = res.fetch_df_chunk(batch_size)
            if batch_df.empty:
                break

            batch = []
            for row in batch_df.itertuples(index=False):
                product_data = row._asdict()
                product = extract_product_fields(product_data)
                if product:
                    batch.append(product)

            if batch:
                logger.info(f"Upserting batch of {len(batch)} products. Sample: {batch[:3]}")
                await upsert_products_batch(pg_conn, batch)
                total_processed += len(batch)
                logger.info(f"Progress: {total_processed:,}/{total_count:,} ({(total_processed/total_count)*100:.1f}%)")


        # Close connections
        await pg_conn.close()
        duck_conn.close()

        logger.info(f"Bootstrap complete! Loaded {total_processed:,} products")

        # Cleanup Parquet file
        logger.info("Cleaning up Parquet file...")
        parquet_file.unlink()

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

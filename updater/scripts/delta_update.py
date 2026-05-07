#!/usr/bin/env python3
"""
Daily delta update script for OpenFoodFacts database.
Downloads and applies delta JSONL files from OpenFoodFacts.
"""
import os
import sys
import logging
import asyncio
from pathlib import Path
import httpx

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
DELTA_URL = os.getenv("OFF_DELTA_URL", "https://static.openfoodfacts.org/data/delta")
DATA_DIR = Path("/app/data")
BATCH_SIZE = 1000
APPLIED_DELTAS_FILE = DATA_DIR / ".applied_deltas.txt"


def load_applied_deltas() -> set:
    """
    Load set of already-applied delta filenames.

    Returns:
        Set of applied delta filenames
    """
    if not APPLIED_DELTAS_FILE.exists():
        return set()

    try:
        with open(APPLIED_DELTAS_FILE, "r") as f:
            deltas = {line.strip() for line in f if line.strip()}
        logger.info(f"Loaded {len(deltas)} previously applied deltas")
        return deltas
    except Exception as e:
        logger.exception(f"Error loading applied deltas: {e}")
        return set()


def mark_delta_applied(delta_filename: str):
    """
    Mark a delta as applied by appending to tracking file.

    Args:
        delta_filename: Name of the delta file
    """
    try:
        with open(APPLIED_DELTAS_FILE, "a") as f:
            f.write(f"{delta_filename}\n")
        logger.info(f"Marked delta as applied: {delta_filename}")
    except Exception as e:
        logger.exception(f"Error marking delta as applied: {e}")


async def get_available_deltas() -> list:
    """
    Fetch list of available delta files from OpenFoodFacts.

    Returns:
        List of delta filenames sorted by timestamp
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{DELTA_URL}/index.txt")
            response.raise_for_status()

            # Parse index file (one filename per line)
            filenames = [
                line.strip()
                for line in response.text.splitlines()
                if line.strip() and line.endswith(".json.gz")
            ]

            logger.info(f"Found {len(filenames)} delta files available")
            return sorted(filenames)

    except Exception as e:
        logger.exception(f"Failed to fetch delta index: {e}")
        return []


async def apply_delta(delta_file: Path, conn):
    """
    Apply a delta file to the database.

    Args:
        delta_file: Path to delta JSONL file
        conn: Database connection
    """
    logger.info(f"Applying delta: {delta_file.name}")

    total_processed = 0
    batch = []

    try:
        # Parse JSONL and process in batches
        for product in parse_jsonl_file(delta_file):
            batch.append(product)

            if len(batch) >= BATCH_SIZE:
                await upsert_products_batch(conn, batch)
                total_processed += len(batch)
                logger.info(f"Processed {total_processed:,} products...")
                batch = []

        # Insert remaining products
        if batch:
            await upsert_products_batch(conn, batch)
            total_processed += len(batch)

        logger.info(f"Delta applied successfully. Total products: {total_processed:,}")

    except Exception as e:
        logger.exception(f"Error applying delta: {e}")
        raise


async def main():
    """Main delta update function"""
    logger.info("Starting OpenFoodFacts delta update")

    # Create data directory
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Check if bootstrap has completed
    bootstrap_marker = DATA_DIR / ".bootstrap_complete"
    if not bootstrap_marker.exists():
        logger.warning("Bootstrap not complete. Skipping delta update.")
        logger.info("Run initial_load.py first to bootstrap the database.")
        return

    # Get available deltas
    all_deltas = await get_available_deltas()

    if not all_deltas:
        logger.warning("No delta files available")
        return

    # Load already-applied deltas
    applied_deltas = load_applied_deltas()

    # Find deltas that need to be applied (not yet applied)
    pending_deltas = [d for d in all_deltas if d not in applied_deltas]

    if not pending_deltas:
        logger.info("All available deltas have been applied. Nothing to do.")
        return

    logger.info(f"Found {len(pending_deltas)} delta(s) to apply")

    # Connect to database (reuse connection for all deltas)
    logger.info("Connecting to database...")
    conn = await create_connection(DATABASE_URL)

    try:
        # Apply each pending delta in chronological order
        for delta_filename in pending_deltas:
            logger.info(f"Processing delta: {delta_filename}")

            # Download delta
            delta_url = f"{DELTA_URL}/{delta_filename}"
            local_delta = DATA_DIR / delta_filename

            logger.info(f"Downloading {delta_url}")
            success = await download_file(delta_url, local_delta, timeout=1800)

            if not success:
                logger.error(f"Failed to download {delta_filename}, skipping")
                continue

            # Apply delta to database
            try:
                await apply_delta(local_delta, conn)

                # Mark as applied
                mark_delta_applied(delta_filename)

                # Cleanup delta file
                logger.info("Cleaning up delta file...")
                local_delta.unlink()

            except Exception as e:
                logger.exception(f"Failed to apply delta {delta_filename}: {e}")
                # Don't mark as applied if it failed
                # Will retry on next run
                if local_delta.exists():
                    local_delta.unlink()
                continue

        logger.info("Delta update complete!")

    except Exception as e:
        logger.exception(f"Delta update failed: {e}")
        sys.exit(1)
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())

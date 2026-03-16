"""
Database operations for updater scripts
"""
import logging
import asyncpg
import json
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


def _sanitize_text(value: str | None) -> str | None:
    """Remove null bytes from text that PostgreSQL cannot store."""
    if value is None:
        return None
    return value.replace("\x00", "")


def _sanitize_json(data: dict) -> str:
    """Serialize dict to JSON, removing null bytes."""
    json_str = json.dumps(data)
    # Remove both literal null bytes and JSON-escaped null bytes (\u0000)
    return json_str.replace("\x00", "").replace("\\u0000", "")


async def create_connection(database_url: str) -> asyncpg.Connection:
    """
    Create a database connection.

    Args:
        database_url: PostgreSQL connection URL

    Returns:
        Database connection
    """
    try:
        conn = await asyncpg.connect(database_url)
        logger.info("Database connection established")
        return conn
    except Exception as e:
        logger.exception(f"Failed to connect to database: {e}")
        raise


async def upsert_products_batch(
    conn: asyncpg.Connection,
    products: List[Dict[str, Any]],
    existing_codes: set = None
) -> int:
    """
    Insert or update a batch of products using UPSERT.
    Skips products that already exist if existing_codes is provided.

    Args:
        conn: Database connection
        products: List of product dictionaries
        existing_codes: Set of codes already in DB (to skip)

    Returns:
        Number of products upserted
    """
    if not products:
        return 0

    # Filter out existing products if codes provided
    if existing_codes:
        products = [p for p in products if p["code"] not in existing_codes]
        if not products:
            return 0

    try:
        # Prepare data for batch insert (sanitize text fields to remove null bytes)
        values = [
            (
                _sanitize_text(p["code"]),
                _sanitize_text(p.get("product_name")),
                _sanitize_text(p.get("product_name_en")),
                _sanitize_text(p.get("brands")),
                _sanitize_text(p.get("quantity")),
                p.get("countries_tags", []),
                p.get("categories_tags", []),
                p.get("energy_100g"),
                p.get("energy_kcal_100g"),
                p.get("proteins_100g"),
                p.get("carbohydrates_100g"),
                p.get("fat_100g"),
                p.get("sugars_100g"),
                p.get("fiber_100g"),
                p.get("sodium_100g"),
                _sanitize_text(p.get("image_url")),
                _sanitize_text(p.get("image_small_url")),
                _sanitize_json(p.get("data", {}))  # Convert dict to JSON string
            )
            for p in products
        ]

        # Execute batch upsert
        result = await conn.executemany(
            """
            INSERT INTO products (
                code, product_name, product_name_en, brands, quantity, countries_tags,
                categories_tags,
                energy_100g, energy_kcal_100g, proteins_100g,
                carbohydrates_100g, fat_100g, sugars_100g,
                fiber_100g, sodium_100g, image_url, image_small_url, data
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18::jsonb)
            ON CONFLICT (code) DO UPDATE SET
                product_name = COALESCE(EXCLUDED.product_name, products.product_name),
                product_name_en = COALESCE(EXCLUDED.product_name_en, products.product_name_en),
                brands = COALESCE(EXCLUDED.brands, products.brands),
                quantity = COALESCE(EXCLUDED.quantity, products.quantity),
                countries_tags = CASE
                    WHEN EXCLUDED.countries_tags IS NOT NULL AND array_length(EXCLUDED.countries_tags, 1) > 0
                    THEN EXCLUDED.countries_tags
                    ELSE products.countries_tags
                END,
                categories_tags = CASE
                    WHEN EXCLUDED.categories_tags IS NOT NULL AND array_length(EXCLUDED.categories_tags, 1) > 0
                    THEN EXCLUDED.categories_tags
                    ELSE products.categories_tags
                END,
                energy_100g = COALESCE(EXCLUDED.energy_100g, products.energy_100g),
                energy_kcal_100g = COALESCE(EXCLUDED.energy_kcal_100g, products.energy_kcal_100g),
                proteins_100g = COALESCE(EXCLUDED.proteins_100g, products.proteins_100g),
                carbohydrates_100g = COALESCE(EXCLUDED.carbohydrates_100g, products.carbohydrates_100g),
                fat_100g = COALESCE(EXCLUDED.fat_100g, products.fat_100g),
                sugars_100g = COALESCE(EXCLUDED.sugars_100g, products.sugars_100g),
                fiber_100g = COALESCE(EXCLUDED.fiber_100g, products.fiber_100g),
                sodium_100g = COALESCE(EXCLUDED.sodium_100g, products.sodium_100g),
                image_url = COALESCE(EXCLUDED.image_url, products.image_url),
                image_small_url = COALESCE(EXCLUDED.image_small_url, products.image_small_url),
                data = EXCLUDED.data,
                updated_at = NOW()
            """,
            values
        )

        return len(products)

    except Exception as e:
        logger.exception(f"Error upserting products batch: {e}")
        raise


async def delete_products_by_codes(conn: asyncpg.Connection, codes: List[str]) -> int:
    """
    Delete products by their codes.

    Args:
        conn: Database connection
        codes: List of product codes to delete

    Returns:
        Number of products deleted
    """
    if not codes:
        return 0

    try:
        result = await conn.execute(
            "DELETE FROM products WHERE code = ANY($1)",
            codes
        )
        # Extract number from result like "DELETE 123"
        count = int(result.split()[-1])
        return count

    except Exception as e:
        logger.exception(f"Error deleting products: {e}")
        raise


async def get_all_product_codes(conn: asyncpg.Connection) -> set:
    """
    Get all product codes from database.

    Args:
        conn: Database connection

    Returns:
        Set of product codes
    """
    try:
        rows = await conn.fetch("SELECT code FROM products")
        codes = {row["code"] for row in rows}
        logger.info(f"Retrieved {len(codes):,} product codes from database")
        return codes

    except Exception as e:
        logger.exception(f"Error fetching product codes: {e}")
        raise

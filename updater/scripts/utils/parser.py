"""
Utility functions for parsing OpenFoodFacts data
"""
import json
import logging
import gzip
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Max value for NUMERIC(15,4): 11 digits before decimal
MAX_NUMERIC_VALUE = Decimal("99999999999.9999")


def _safe_numeric(value: Any) -> Optional[Decimal]:
    """Convert to Decimal rounded to 4 places, clamped to NUMERIC(15,4) limits."""
    if value is None:
        return None
    try:
        d = Decimal(str(value)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        if d > MAX_NUMERIC_VALUE:
            return MAX_NUMERIC_VALUE
        if d < -MAX_NUMERIC_VALUE:
            return -MAX_NUMERIC_VALUE
        return d
    except (InvalidOperation, ValueError, TypeError):
        return None


def extract_product_fields(product_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract and normalize product fields from OpenFoodFacts JSON data.

    Args:
        product_data: Raw product data from OpenFoodFacts

    Returns:
        Normalized product dictionary with extracted fields
    """
    # Helper function to safely get nested values
    def safe_get(data, *keys, default=None):
        for key in keys:
            if isinstance(data, dict):
                data = data.get(key, default)
            else:
                return default
        return data

    # Extract code (barcode)
    code = product_data.get("code") or product_data.get("_id")

    if not code:
        return None

    # Extract nutriments
    nutriments = product_data.get("nutriments", {})

    # Extract image URLs
    images = product_data.get("images", {})
    selected_images = product_data.get("selected_images", {})

    # Get best available product image URL
    image_url = None
    image_small_url = None

    if selected_images:
        front_images = selected_images.get("front", {}).get("display", {})
        image_url = front_images.get("en") or front_images.get("fr") or list(front_images.values())[0] if front_images else None
        image_small_url = selected_images.get("front", {}).get("small", {}).get("en")

    # Fallback to image_url field
    if not image_url:
        image_url = product_data.get("image_url")
    if not image_small_url:
        image_small_url = product_data.get("image_small_url")

    return {
        "code": str(code),
        "product_name": product_data.get("product_name"),
        "product_name_en": product_data.get("product_name_en"),
        "brands": product_data.get("brands"),
        "quantity": product_data.get("quantity"),
        "countries_tags": product_data.get("countries_tags", []),
        "categories_tags": product_data.get("categories_tags", []),
        "energy_100g": _safe_numeric(nutriments.get("energy_100g")),
        "energy_kcal_100g": _safe_numeric(nutriments.get("energy-kcal_100g")),
        "proteins_100g": _safe_numeric(nutriments.get("proteins_100g")),
        "carbohydrates_100g": _safe_numeric(nutriments.get("carbohydrates_100g")),
        "fat_100g": _safe_numeric(nutriments.get("fat_100g")),
        "sugars_100g": _safe_numeric(nutriments.get("sugars_100g")),
        "fiber_100g": _safe_numeric(nutriments.get("fiber_100g")),
        "sodium_100g": _safe_numeric(nutriments.get("sodium_100g")),
        "image_url": image_url,
        "image_small_url": image_small_url,
        "data": product_data  # Store full JSON including ALL language variants
    }


def parse_jsonl_file(file_path: Path):
    """
    Generator to parse JSONL file (gzipped or plain text).
    Yields extracted product dictionaries one by one.

    Args:
        file_path: Path to JSONL file (.jsonl or .jsonl.gz)

    Yields:
        Normalized product dictionaries
    """
    logger.info(f"Parsing JSONL file: {file_path}")

    count = 0
    errors = 0

    # Determine if file is gzipped
    open_func = gzip.open if file_path.suffix == ".gz" else open

    try:
        with open_func(file_path, "rt", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                if not line.strip():
                    continue

                try:
                    product_data = json.loads(line)
                    product = extract_product_fields(product_data)

                    if product:
                        yield product
                        count += 1

                        # Log progress every 100k products
                        if count % 100000 == 0:
                            logger.info(f"Parsed {count:,} products...")

                except json.JSONDecodeError as e:
                    errors += 1
                    if errors < 10:  # Only log first few errors
                        logger.warning(f"JSON decode error at line {line_num}: {e}")

                except Exception as e:
                    errors += 1
                    if errors < 10:
                        logger.exception(f"Error parsing line {line_num}: {e}")

    except Exception as e:
        logger.exception(f"Fatal error parsing file: {e}")

    logger.info(f"Parsing complete. Processed {count:,} products, {errors} errors")

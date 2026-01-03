"""
Product search endpoints
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query, Security
from typing import List
import asyncpg

from ..models import ProductResponse, SearchResponse, ProductSearchResult, NutrientsModel, ProductImagesModel
from ..database import get_pool
from ..middleware.auth import api_key_dependency, api_key_header, verify_api_key

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/products", tags=["Products"])


@router.get("/barcode/{code}", response_model=ProductResponse)
async def search_by_barcode(code: str, api_key: str = Security(api_key_header)):
    """
    Search for a product by exact barcode/code match.
    Requires API key authentication.
    """
    # Validate API key
    await verify_api_key(api_key)

    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT code, product_name, brands, quantity,
                       energy_100g, energy_kcal_100g, proteins_100g,
                       carbohydrates_100g, fat_100g, sugars_100g,
                       fiber_100g, sodium_100g,
                       image_url, image_small_url
                FROM products
                WHERE code = $1
                """,
                code
            )

            if not row:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Product with code {code} not found"
                )

            return ProductResponse(
                code=row["code"],
                product_name=row["product_name"],
                brands=row["brands"],
                quantity=row["quantity"],
                nutrients=NutrientsModel(
                    energy_100g=row["energy_100g"],
                    energy_kcal_100g=row["energy_kcal_100g"],
                    proteins_100g=row["proteins_100g"],
                    carbohydrates_100g=row["carbohydrates_100g"],
                    fat_100g=row["fat_100g"],
                    sugars_100g=row["sugars_100g"],
                    fiber_100g=row["fiber_100g"],
                    sodium_100g=row["sodium_100g"]
                ),
                images=ProductImagesModel(
                    url=row["image_url"],
                    small_url=row["image_small_url"]
                )
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error searching by barcode: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/search", response_model=SearchResponse)
async def search_by_name(
    q: str = Query(..., min_length=3, description="Search query (minimum 3 characters)"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results"),
    lang: str = Query(None, description="Optional language preference (e.g., 'en', 'fr', 'de', 'es')"),
    country: str = Query(None, description="Optional country filter (e.g., 'en:france', 'en:united-states')"),
    api_key: str = Security(api_key_header)
):
    """
    Search for products by name or brand using fuzzy text search with optional language preference.
    Requires API key authentication.
    Uses PostgreSQL trigram similarity for typo-tolerant matching.

    If `lang` is specified, product names in that language are prioritized (e.g., 'fr' for French).
    The JSONB data column contains ALL language variants, so any language is supported.
    If `country` is specified, only products sold in that country are returned.
    """
    # Validate API key
    await verify_api_key(api_key)

    # Languages with trigram indexes for fast fuzzy search
    INDEXED_LANGUAGES = {'en', 'fr', 'de', 'es', 'it', 'pt', 'pl', 'nl', 'ja', 'zh', 'ar', 'ru'}

    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            # Build dynamic query based on language preference
            if lang and lang.lower() in INDEXED_LANGUAGES:
                # Use JSONB with indexed language for fast search
                lang_field = f"product_name_{lang.lower()}"
                query = """
                    SELECT code, product_name, brands, image_url,
                           data->>$2 as localized_name,
                           GREATEST(
                               COALESCE(similarity(data->>$2, $1), 0) * 2.0,  -- Boost localized name heavily
                               similarity(product_name, $1),
                               similarity(product_name_en, $1),
                               similarity(brands, $1)
                           ) as relevance_score
                    FROM products
                    WHERE (data->>$2) % $1
                       OR product_name % $1
                       OR product_name_en % $1
                       OR brands % $1
                """
                params = [q, lang_field]
            else:
                # No language preference or unsupported language, use default search
                query = """
                    SELECT code, product_name, brands, image_url,
                           GREATEST(
                               similarity(product_name, $1),
                               similarity(product_name_en, $1),
                               similarity(brands, $1)
                           ) as relevance_score
                    FROM products
                    WHERE product_name % $1
                       OR product_name_en % $1
                       OR brands % $1
                """
                params = [q]

            # Add country filter if specified
            if country:
                params.append(country.lower())
                query += f" AND ${len(params)} = ANY(countries_tags)"

            # Add ordering and limit
            params.append(limit)
            query += f" ORDER BY relevance_score DESC LIMIT ${len(params)}"

            rows = await conn.fetch(query, *params)

            results = [
                ProductSearchResult(
                    code=row["code"],
                    product_name=row["product_name"],
                    brands=row["brands"],
                    image_url=row["image_url"],
                    relevance_score=float(row["relevance_score"]) if row["relevance_score"] else None
                )
                for row in rows
            ]

            return SearchResponse(
                query=q,
                count=len(results),
                results=results
            )

    except Exception as e:
        logger.exception(f"Error searching by name: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

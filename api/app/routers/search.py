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
    api_key: str = Security(api_key_header)
):
    """
    Search for products by name or brand using fuzzy text search.
    Requires API key authentication.
    Uses PostgreSQL trigram similarity for typo-tolerant matching.
    """
    # Validate API key
    await verify_api_key(api_key)

    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
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
                ORDER BY relevance_score DESC
                LIMIT $2
                """,
                q,
                limit
            )

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

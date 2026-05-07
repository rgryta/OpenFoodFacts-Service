"""
Pydantic models for API request/response validation
"""
from typing import Optional, List
from pydantic import BaseModel, Field


class NutrientsModel(BaseModel):
    """Nutritional information per 100g"""
    energy_100g: Optional[float] = None
    energy_kcal_100g: Optional[float] = None
    proteins_100g: Optional[float] = None
    carbohydrates_100g: Optional[float] = None
    fat_100g: Optional[float] = None
    sugars_100g: Optional[float] = None
    fiber_100g: Optional[float] = None
    sodium_100g: Optional[float] = None


class ProductImagesModel(BaseModel):
    """Product image URLs"""
    url: Optional[str] = None
    small_url: Optional[str] = None


class ProductResponse(BaseModel):
    """Single product response"""
    code: str
    product_name: Optional[str] = None
    brands: Optional[str] = None
    quantity: Optional[str] = None
    categories_tags: Optional[List[str]] = None
    nutrients: Optional[NutrientsModel] = None
    images: Optional[ProductImagesModel] = None


class ProductSearchResult(BaseModel):
    """Single search result with relevance score"""
    code: str
    product_name: Optional[str] = None
    brands: Optional[str] = None
    image_url: Optional[str] = None
    relevance_score: Optional[float] = Field(None, description="Trigram similarity score")


class SearchResponse(BaseModel):
    """Search results response"""
    query: str
    count: int
    results: List[ProductSearchResult]


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    database: str
    product_count: int
    last_update: Optional[str] = None


class SyncTriggerResponse(BaseModel):
    """Manual sync trigger response"""
    status: str
    message: str

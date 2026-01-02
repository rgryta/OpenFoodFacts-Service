-- OpenFoodFacts Products Database Schema
-- PostgreSQL 16+ with JSONB and full-text search support

-- Drop table if exists (for clean re-initialization)
DROP TABLE IF EXISTS products CASCADE;

-- Main products table
CREATE TABLE products (
    -- Primary identifier (barcode or internal code)
    code VARCHAR(50) PRIMARY KEY,

    -- Frequently queried fields (denormalized for performance)
    product_name TEXT,
    product_name_en TEXT,
    brands TEXT,
    quantity TEXT,

    -- Nutritional data per 100g (extracted for fast access)
    energy_100g NUMERIC(10, 2),
    energy_kcal_100g NUMERIC(10, 2),
    proteins_100g NUMERIC(10, 2),
    carbohydrates_100g NUMERIC(10, 2),
    fat_100g NUMERIC(10, 2),
    sugars_100g NUMERIC(10, 2),
    fiber_100g NUMERIC(10, 2),
    sodium_100g NUMERIC(10, 2),

    -- Product images
    image_url TEXT,
    image_small_url TEXT,

    -- Full OpenFoodFacts product data (all fields preserved)
    data JSONB NOT NULL,

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for performance

-- Trigram indexes for fuzzy text search (handles typos, partial matches)
CREATE INDEX idx_product_name_trgm ON products USING GIN (product_name gin_trgm_ops);
CREATE INDEX idx_product_name_en_trgm ON products USING GIN (product_name_en gin_trgm_ops);
CREATE INDEX idx_brands_trgm ON products USING GIN (brands gin_trgm_ops);

-- GIN index for JSONB queries (future extensibility)
CREATE INDEX idx_data_gin ON products USING GIN (data);

-- Trigger function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to call update function on row updates
CREATE TRIGGER update_products_updated_at
BEFORE UPDATE ON products
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- Grant permissions (if needed for specific user)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON products TO offuser;

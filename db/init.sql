-- OpenFoodFacts Products Database Schema
-- PostgreSQL 16+ with JSONB and full-text search support

-- Drop table if exists (for clean re-initialization)
DROP TABLE IF EXISTS products CASCADE;

-- Main products table
CREATE TABLE products (
    -- Primary identifier (barcode or internal code)
    code VARCHAR(100) PRIMARY KEY,

    -- Frequently queried fields (denormalized for performance)
    product_name TEXT,
    product_name_en TEXT,
    brands TEXT,
    quantity TEXT,
    countries_tags TEXT[],  -- Array of country tags for localization

    -- Nutritional data per 100g (extracted for fast access)
    -- Using NUMERIC(15,4) to handle outlier values in OpenFoodFacts data
    energy_100g NUMERIC(15, 4),
    energy_kcal_100g NUMERIC(15, 4),
    proteins_100g NUMERIC(15, 4),
    carbohydrates_100g NUMERIC(15, 4),
    fat_100g NUMERIC(15, 4),
    sugars_100g NUMERIC(15, 4),
    fiber_100g NUMERIC(15, 4),
    sodium_100g NUMERIC(15, 4),

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

-- GIN index for country tags array (for country-based filtering)
CREATE INDEX idx_countries_tags ON products USING GIN (countries_tags);

-- GIN index for JSONB queries (enables exact lookups)
CREATE INDEX idx_data_gin ON products USING GIN (data jsonb_path_ops);

-- Functional trigram indexes for common localized product names (extracted from JSONB)
-- These enable fast fuzzy search on language-specific fields
CREATE INDEX idx_data_product_name_fr_trgm ON products USING GIN ((data->>'product_name_fr') gin_trgm_ops);
CREATE INDEX idx_data_product_name_de_trgm ON products USING GIN ((data->>'product_name_de') gin_trgm_ops);
CREATE INDEX idx_data_product_name_es_trgm ON products USING GIN ((data->>'product_name_es') gin_trgm_ops);
CREATE INDEX idx_data_product_name_it_trgm ON products USING GIN ((data->>'product_name_it') gin_trgm_ops);
CREATE INDEX idx_data_product_name_pt_trgm ON products USING GIN ((data->>'product_name_pt') gin_trgm_ops);
CREATE INDEX idx_data_product_name_pl_trgm ON products USING GIN ((data->>'product_name_pl') gin_trgm_ops);
CREATE INDEX idx_data_product_name_nl_trgm ON products USING GIN ((data->>'product_name_nl') gin_trgm_ops);
CREATE INDEX idx_data_product_name_ja_trgm ON products USING GIN ((data->>'product_name_ja') gin_trgm_ops);
CREATE INDEX idx_data_product_name_zh_trgm ON products USING GIN ((data->>'product_name_zh') gin_trgm_ops);
CREATE INDEX idx_data_product_name_ar_trgm ON products USING GIN ((data->>'product_name_ar') gin_trgm_ops);
CREATE INDEX idx_data_product_name_ru_trgm ON products USING GIN ((data->>'product_name_ru') gin_trgm_ops);

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

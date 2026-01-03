-- Migration: Add localization support (countries_tags column and language indexes)
-- Run this if you have an existing database without these features

-- Add countries_tags column if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'products' AND column_name = 'countries_tags'
    ) THEN
        ALTER TABLE products ADD COLUMN countries_tags TEXT[] DEFAULT '{}';
        RAISE NOTICE 'Added countries_tags column';
    ELSE
        RAISE NOTICE 'countries_tags column already exists';
    END IF;
END $$;

-- Populate countries_tags from JSONB data
UPDATE products
SET countries_tags = COALESCE(
    ARRAY(SELECT jsonb_array_elements_text(data->'countries_tags')),
    '{}'
)
WHERE countries_tags = '{}' OR countries_tags IS NULL;

-- Create index for countries_tags if it doesn't exist
CREATE INDEX IF NOT EXISTS idx_countries_tags ON products USING GIN (countries_tags);

-- Create functional trigram indexes for localized product names
-- These allow fast fuzzy search on language-specific fields from JSONB
CREATE INDEX IF NOT EXISTS idx_data_product_name_fr_trgm ON products USING GIN ((data->>'product_name_fr') gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_data_product_name_de_trgm ON products USING GIN ((data->>'product_name_de') gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_data_product_name_es_trgm ON products USING GIN ((data->>'product_name_es') gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_data_product_name_it_trgm ON products USING GIN ((data->>'product_name_it') gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_data_product_name_pt_trgm ON products USING GIN ((data->>'product_name_pt') gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_data_product_name_pl_trgm ON products USING GIN ((data->>'product_name_pl') gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_data_product_name_nl_trgm ON products USING GIN ((data->>'product_name_nl') gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_data_product_name_ja_trgm ON products USING GIN ((data->>'product_name_ja') gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_data_product_name_zh_trgm ON products USING GIN ((data->>'product_name_zh') gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_data_product_name_ar_trgm ON products USING GIN ((data->>'product_name_ar') gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_data_product_name_ru_trgm ON products USING GIN ((data->>'product_name_ru') gin_trgm_ops);

-- Update JSONB index to use jsonb_path_ops for better performance
DROP INDEX IF EXISTS idx_data_gin;
CREATE INDEX idx_data_gin ON products USING GIN (data jsonb_path_ops);

-- Analyze table to update query planner statistics
ANALYZE products;

-- Summary
DO $$
DECLARE
    idx_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO idx_count
    FROM pg_indexes
    WHERE tablename = 'products';

    RAISE NOTICE 'Migration complete!';
    RAISE NOTICE 'Total indexes on products table: %', idx_count;
END $$;

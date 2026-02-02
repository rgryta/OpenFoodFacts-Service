-- Enable PostgreSQL extensions for OpenFoodFacts service
-- This file runs first (00-extensions.sql) before schema creation

-- pg_trgm: Trigram-based text search for fuzzy matching
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- btree_gin: Enables GIN indexes on mixed data types
CREATE EXTENSION IF NOT EXISTS btree_gin;

-- Performance tuning for trigram searches
-- Increase work_mem for faster sorts (default: 4MB)
ALTER SYSTEM SET work_mem = '64MB';

-- Optimize for SSD storage (default: 4, reduce for SSD)
ALTER SYSTEM SET random_page_cost = 1.5;

-- Reload configuration
SELECT pg_reload_conf();

-- Enable PostgreSQL extensions for OpenFoodFacts service
-- This file runs first (00-extensions.sql) before schema creation

-- pg_trgm: Trigram-based text search for fuzzy matching
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- btree_gin: Enables GIN indexes on mixed data types
CREATE EXTENSION IF NOT EXISTS btree_gin;

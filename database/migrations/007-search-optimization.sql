-- Search Optimization Indexes
-- Migration 007: Add indexes specifically for search functionality

-- Player name search indexes (ILIKE optimization)
CREATE INDEX IF NOT EXISTS idx_players_first_name_pattern
ON players(first_name text_pattern_ops)
WHERE first_name IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_players_last_name_pattern
ON players(last_name text_pattern_ops)
WHERE last_name IS NOT NULL;

-- Umpire name search
CREATE INDEX IF NOT EXISTS idx_umpires_name_pattern
ON umpires(name text_pattern_ops)
WHERE name IS NOT NULL;

-- Team search indexes (already have abbreviation, add city and name)
CREATE INDEX IF NOT EXISTS idx_teams_name_pattern
ON teams(name text_pattern_ops)
WHERE name IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_teams_city_pattern
ON teams(city text_pattern_ops)
WHERE city IS NOT NULL;

-- Case-insensitive search using lower() function indexes (alternative approach)
CREATE INDEX IF NOT EXISTS idx_players_full_name_lower
ON players(LOWER(full_name));

CREATE INDEX IF NOT EXISTS idx_players_last_name_lower
ON players(LOWER(last_name));

CREATE INDEX IF NOT EXISTS idx_umpires_name_lower
ON umpires(LOWER(name));

CREATE INDEX IF NOT EXISTS idx_teams_name_lower
ON teams(LOWER(name));

CREATE INDEX IF NOT EXISTS idx_teams_city_lower
ON teams(LOWER(city));

-- Full-text search indexes (PostgreSQL tsvector for advanced search)
-- Players
ALTER TABLE players ADD COLUMN IF NOT EXISTS search_vector tsvector
GENERATED ALWAYS AS (
    to_tsvector('english',
        COALESCE(full_name, '') || ' ' ||
        COALESCE(first_name, '') || ' ' ||
        COALESCE(last_name, '')
    )
) STORED;

CREATE INDEX IF NOT EXISTS idx_players_search_vector
ON players USING gin(search_vector);

-- Teams
ALTER TABLE teams ADD COLUMN IF NOT EXISTS search_vector tsvector
GENERATED ALWAYS AS (
    to_tsvector('english',
        COALESCE(name, '') || ' ' ||
        COALESCE(city, '') || ' ' ||
        COALESCE(abbreviation, '')
    )
) STORED;

CREATE INDEX IF NOT EXISTS idx_teams_search_vector
ON teams USING gin(search_vector);

-- Umpires
ALTER TABLE umpires ADD COLUMN IF NOT EXISTS search_vector tsvector
GENERATED ALWAYS AS (
    to_tsvector('english', COALESCE(name, ''))
) STORED;

CREATE INDEX IF NOT EXISTS idx_umpires_search_vector
ON umpires USING gin(search_vector);

-- Update statistics for query planner
ANALYZE players;
ANALYZE teams;
ANALYZE umpires;
ANALYZE games;

-- Vacuum to reclaim space
VACUUM ANALYZE;

-- Report created indexes
SELECT
    schemaname,
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) as index_size
FROM pg_indexes
JOIN pg_class ON pg_class.relname = indexname
WHERE schemaname = 'public'
    AND indexname LIKE '%search%' OR indexname LIKE '%pattern%' OR indexname LIKE '%lower%'
ORDER BY tablename, indexname;

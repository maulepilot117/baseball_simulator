-- Performance Optimization Indexes
-- Migration 006: Add indexes for common query patterns

-- Player lookups by player_id (used frequently in API)
CREATE INDEX IF NOT EXISTS idx_players_player_id
ON players(player_id)
WHERE player_id IS NOT NULL;

-- Player season aggregates - most common queries
CREATE INDEX IF NOT EXISTS idx_player_season_aggregates_player_season
ON player_season_aggregates(player_id, season, stats_type);

CREATE INDEX IF NOT EXISTS idx_player_season_aggregates_season
ON player_season_aggregates(season)
WHERE season IS NOT NULL;

-- Games by season and date (very common)
CREATE INDEX IF NOT EXISTS idx_games_season_date
ON games(season, game_date DESC);

CREATE INDEX IF NOT EXISTS idx_games_date
ON games(game_date DESC);

CREATE INDEX IF NOT EXISTS idx_games_teams
ON games(home_team_id, away_team_id);

-- Teams lookups
CREATE INDEX IF NOT EXISTS idx_teams_abbreviation
ON teams(abbreviation)
WHERE abbreviation IS NOT NULL;

-- Umpire season stats
CREATE INDEX IF NOT EXISTS idx_umpire_season_stats_season
ON umpire_season_stats(season DESC);

CREATE INDEX IF NOT EXISTS idx_umpire_season_stats_umpire_season
ON umpire_season_stats(umpire_id, season DESC);

-- Simulations by status (for monitoring active simulations)
CREATE INDEX IF NOT EXISTS idx_simulations_status
ON simulations(status, created_at DESC)
WHERE status IN ('pending', 'running');

-- Player stats partitioned tables - add indexes on each partition
-- (These would need to be created for each partition individually in a real system)
-- Example for current season:
DO $$
DECLARE
    current_year INT := EXTRACT(YEAR FROM CURRENT_DATE);
    partition_name TEXT;
BEGIN
    -- Add index to current year partition if it exists
    partition_name := 'player_stats_' || current_year;

    EXECUTE format('CREATE INDEX IF NOT EXISTS idx_%s_player_id
                    ON %I(player_id, stat_type)',
                   partition_name, partition_name);
EXCEPTION
    WHEN undefined_table THEN
        NULL; -- Partition doesn't exist yet, skip
END $$;

-- Composite indexes for complex queries
CREATE INDEX IF NOT EXISTS idx_players_team_position
ON players(team_id, position, status);

-- Covering index for player list queries (avoid table lookups)
CREATE INDEX IF NOT EXISTS idx_players_list_covering
ON players(id, player_id, full_name, position, team_id, status);

-- Text search optimization (if using LIKE queries)
CREATE INDEX IF NOT EXISTS idx_players_full_name_pattern
ON players(full_name text_pattern_ops);

-- Statistics for query planner
ANALYZE players;
ANALYZE player_season_aggregates;
ANALYZE games;
ANALYZE teams;
ANALYZE umpire_season_stats;

-- Vacuum to reclaim space and update statistics
VACUUM ANALYZE;

-- Summary of created indexes
SELECT
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'public'
    AND tablename IN ('players', 'player_season_aggregates', 'games', 'teams', 'umpire_season_stats')
ORDER BY tablename, indexname;

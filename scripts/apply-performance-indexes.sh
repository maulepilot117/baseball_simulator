#!/bin/bash
# Script to apply performance indexes to the database
# Run this when database is not under heavy load

set -e

echo "Applying performance indexes to baseball_sim database..."

docker exec -i baseball-db psql -U baseball_user -d baseball_sim <<'EOF'
-- Performance Optimization Indexes

-- Player lookups
CREATE INDEX IF NOT EXISTS idx_players_player_id ON players(player_id);
CREATE INDEX IF NOT EXISTS idx_player_season_aggregates_player_season ON player_season_aggregates(player_id, season, stats_type);
CREATE INDEX IF NOT EXISTS idx_player_season_aggregates_season ON player_season_aggregates(season);

-- Games indexes
CREATE INDEX IF NOT EXISTS idx_games_season_date ON games(season, game_date DESC);
CREATE INDEX IF NOT EXISTS idx_games_date ON games(game_date DESC);
CREATE INDEX IF NOT EXISTS idx_games_teams ON games(home_team_id, away_team_id);

-- Teams
CREATE INDEX IF NOT EXISTS idx_teams_abbreviation ON teams(abbreviation);

-- Umpires
CREATE INDEX IF NOT EXISTS idx_umpire_season_stats_season ON umpire_season_stats(season DESC);
CREATE INDEX IF NOT EXISTS idx_umpire_season_stats_umpire_season ON umpire_season_stats(umpire_id, season DESC);

-- Composite indexes
CREATE INDEX IF NOT EXISTS idx_players_team_position ON players(team_id, position, status);
CREATE INDEX IF NOT EXISTS idx_players_list_covering ON players(id, player_id, full_name, position, team_id, status);

-- Update statistics
ANALYZE players;
ANALYZE player_season_aggregates;
ANALYZE games;
ANALYZE teams;
ANALYZE umpire_season_stats;

VACUUM ANALYZE;

SELECT 'Indexes created successfully!' as status;
EOF

echo "Performance indexes applied successfully!"
echo ""
echo "To verify indexes, run:"
echo "docker exec baseball-db psql -U baseball_user -d baseball_sim -c \"\\di\""

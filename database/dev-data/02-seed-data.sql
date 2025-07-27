-- Development seed data for baseball simulation
-- This file only runs in development environment

-- Insert sample stadiums
INSERT INTO stadiums (stadium_id, name, location, capacity, dimensions, park_factors, altitude, surface, roof_type) VALUES
('fenway', 'Fenway Park', 'Boston, MA', 37755, 
 '{"left_field": 310, "center_field": 420, "right_field": 302}'::jsonb,
 '{"home_run_factor": 1.05, "doubles_factor": 1.12, "triples_factor": 0.85}'::jsonb,
 20, 'Natural Grass', 'Open'),
('yankee', 'Yankee Stadium', 'Bronx, NY', 47309,
 '{"left_field": 318, "center_field": 408, "right_field": 314}'::jsonb,
 '{"home_run_factor": 1.08, "doubles_factor": 0.98, "triples_factor": 0.75}'::jsonb,
 55, 'Natural Grass', 'Open'),
('wrigley', 'Wrigley Field', 'Chicago, IL', 41649,
 '{"left_field": 355, "center_field": 400, "right_field": 353}'::jsonb,
 '{"home_run_factor": 1.02, "doubles_factor": 1.05, "triples_factor": 1.15}'::jsonb,
 595, 'Natural Grass', 'Open'),
('coors', 'Coors Field', 'Denver, CO', 50398,
 '{"left_field": 347, "center_field": 415, "right_field": 350}'::jsonb,
 '{"home_run_factor": 1.25, "doubles_factor": 1.18, "triples_factor": 1.30}'::jsonb,
 5200, 'Natural Grass', 'Open');

-- Insert sample teams
INSERT INTO teams (team_id, name, abbreviation, league, division, stadium_id) 
SELECT 'BOS', 'Red Sox', 'BOS', 'AL', 'East', s.id FROM stadiums s WHERE s.stadium_id = 'fenway'
UNION ALL
SELECT 'NYY', 'Yankees', 'NYY', 'AL', 'East', s.id FROM stadiums s WHERE s.stadium_id = 'yankee'
UNION ALL
SELECT 'CHC', 'Cubs', 'CHC', 'NL', 'Central', s.id FROM stadiums s WHERE s.stadium_id = 'wrigley'
UNION ALL
SELECT 'COL', 'Rockies', 'COL', 'NL', 'West', s.id FROM stadiums s WHERE s.stadium_id = 'coors';

-- Insert sample players for Red Sox
INSERT INTO players (player_id, first_name, last_name, position, bats, throws, team_id, status)
SELECT 
    'betts_m', 'Mookie', 'Betts', 'OF', 'R', 'R', t.id, 'active'
FROM teams t WHERE t.team_id = 'BOS'
UNION ALL
SELECT 
    'bogaerts_x', 'Xander', 'Bogaerts', 'SS', 'R', 'R', t.id, 'active'
FROM teams t WHERE t.team_id = 'BOS'
UNION ALL
SELECT 
    'devers_r', 'Rafael', 'Devers', '3B', 'L', 'R', t.id, 'active'
FROM teams t WHERE t.team_id = 'BOS'
UNION ALL
SELECT 
    'martinez_jd', 'J.D.', 'Martinez', 'DH', 'R', 'R', t.id, 'active'
FROM teams t WHERE t.team_id = 'BOS'
UNION ALL
SELECT 
    'sale_c', 'Chris', 'Sale', 'P', 'L', 'L', t.id, 'active'
FROM teams t WHERE t.team_id = 'BOS';

-- Insert sample players for Yankees  
INSERT INTO players (player_id, first_name, last_name, position, bats, throws, team_id, status)
SELECT 
    'judge_a', 'Aaron', 'Judge', 'OF', 'R', 'R', t.id, 'active'
FROM teams t WHERE t.team_id = 'NYY'
UNION ALL
SELECT 
    'stanton_g', 'Giancarlo', 'Stanton', 'DH', 'R', 'R', t.id, 'active'
FROM teams t WHERE t.team_id = 'NYY'
UNION ALL
SELECT 
    'torres_g', 'Gleyber', 'Torres', '2B', 'R', 'R', t.id, 'active'
FROM teams t WHERE t.team_id = 'NYY'
UNION ALL
SELECT 
    'cole_g', 'Gerrit', 'Cole', 'P', 'R', 'R', t.id, 'active'
FROM teams t WHERE t.team_id = 'NYY';

-- Insert sample games
INSERT INTO games (game_id, season, game_type, game_date, home_team_id, away_team_id, status, stadium_id)
SELECT 
    'BOS_NYY_20240415', 2024, 'regular', '2024-04-15 19:10:00'::timestamp,
    ht.id, at.id, 'scheduled', s.id
FROM teams ht, teams at, stadiums s
WHERE ht.team_id = 'BOS' AND at.team_id = 'NYY' AND s.stadium_id = 'fenway'
UNION ALL
SELECT 
    'CHC_COL_20240416', 2024, 'regular', '2024-04-16 20:10:00'::timestamp,
    ht.id, at.id, 'scheduled', s.id
FROM teams ht, teams at, stadiums s
WHERE ht.team_id = 'CHC' AND at.team_id = 'COL' AND s.stadium_id = 'wrigley';

-- Insert sample player statistics
INSERT INTO raw_data.player_stats (player_id, season, stats_type, games_played, aggregated_stats)
SELECT 
    p.id, 2024, 'batting', 150,
    jsonb_build_object(
        'avg', 0.295,
        'obp', 0.368,
        'slg', 0.502,
        'ops', 0.870,
        'hr', 25,
        'rbi', 85,
        'runs', 92,
        'hits', 165,
        'doubles', 35,
        'triples', 3,
        'walks', 65,
        'strikeouts', 120
    )
FROM players p WHERE p.player_id = 'betts_m'
UNION ALL
SELECT 
    p.id, 2024, 'batting', 148,
    jsonb_build_object(
        'avg', 0.307,
        'obp', 0.377,
        'slg', 0.506,
        'ops', 0.883,
        'hr', 22,
        'rbi', 73,
        'runs', 84,
        'hits', 167,
        'doubles', 42,
        'triples', 1,
        'walks', 52,
        'strikeouts', 95
    )
FROM players p WHERE p.player_id = 'bogaerts_x'
UNION ALL
SELECT 
    p.id, 2024, 'batting', 162,
    jsonb_build_object(
        'avg', 0.282,
        'obp', 0.354,
        'slg', 0.538,
        'ops', 0.892,
        'hr', 38,
        'rbi', 115,
        'runs', 101,
        'hits', 174,
        'doubles', 37,
        'triples', 2,
        'walks', 78,
        'strikeouts', 155
    )
FROM players p WHERE p.player_id = 'devers_r';

-- Insert sample pitching statistics
INSERT INTO raw_data.player_stats (player_id, season, stats_type, games_played, aggregated_stats)
SELECT 
    p.id, 2024, 'pitching', 32,
    jsonb_build_object(
        'era', 3.25,
        'whip', 1.08,
        'wins', 14,
        'losses', 8,
        'saves', 0,
        'innings_pitched', 195.1,
        'hits_allowed', 165,
        'runs_allowed', 75,
        'earned_runs', 71,
        'walks_allowed', 45,
        'strikeouts', 218,
        'home_runs_allowed', 22
    )
FROM players p WHERE p.player_id = 'sale_c'
UNION ALL
SELECT 
    p.id, 2024, 'pitching', 33,
    jsonb_build_object(
        'era', 2.78,
        'whip', 1.01,
        'wins', 16,
        'losses', 6,
        'saves', 0,
        'innings_pitched', 210.2,
        'hits_allowed', 175,
        'runs_allowed', 68,
        'earned_runs', 65,
        'walks_allowed', 38,
        'strikeouts', 257,
        'home_runs_allowed', 18
    )
FROM players p WHERE p.player_id = 'cole_g';

-- Create some indexes for better performance in development
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_players_team_id ON players(team_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_games_date ON games(game_date);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_games_teams ON games(home_team_id, away_team_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_player_stats_player_season ON raw_data.player_stats(player_id, season);

-- Insert a development notice
INSERT INTO analytics.system_info (key, value, description) VALUES
('environment', 'development', 'Current system environment'),
('seed_data_loaded', 'true', 'Development seed data has been loaded'),
('last_seeded', NOW()::text, 'Timestamp when seed data was last loaded')
ON CONFLICT (key) DO UPDATE SET 
    value = EXCLUDED.value,
    description = EXCLUDED.description,
    updated_at = NOW();
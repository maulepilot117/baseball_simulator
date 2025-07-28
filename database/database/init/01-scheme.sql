-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- Create schemas
CREATE SCHEMA IF NOT EXISTS raw_data;
CREATE SCHEMA IF NOT EXISTS analytics;
CREATE SCHEMA IF NOT EXISTS simulations;

-- System information table for metadata
CREATE TABLE IF NOT EXISTS analytics.system_info (
    key VARCHAR(100) PRIMARY KEY,
    value TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Teams table
CREATE TABLE IF NOT EXISTS teams (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    team_id VARCHAR(10) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    abbreviation VARCHAR(5) NOT NULL,
    league VARCHAR(10),
    division VARCHAR(20),
    stadium_id UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Stadiums table with park factors
CREATE TABLE IF NOT EXISTS stadiums (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    stadium_id VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(200) NOT NULL,
    location VARCHAR(200),
    capacity INTEGER,
    dimensions JSONB, -- left field, center field, right field distances
    park_factors JSONB, -- batting average, home runs, etc.
    altitude INTEGER,
    surface VARCHAR(50),
    roof_type VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Players table
CREATE TABLE IF NOT EXISTS players (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    player_id VARCHAR(50) UNIQUE NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    birth_date DATE,
    position VARCHAR(10),
    bats VARCHAR(10),
    throws VARCHAR(10),
    team_id UUID REFERENCES teams(id),
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Umpires table
CREATE TABLE IF NOT EXISTS umpires (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    umpire_id VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(200) NOT NULL,
    tendencies JSONB, -- strike zone tendencies, K%, BB%, etc.
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Games table
CREATE TABLE IF NOT EXISTS games (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    game_id VARCHAR(50) UNIQUE NOT NULL,
    game_date DATE NOT NULL,
    game_time TIME,
    home_team_id UUID REFERENCES teams(id),
    away_team_id UUID REFERENCES teams(id),
    stadium_id UUID REFERENCES stadiums(id),
    home_plate_umpire_id UUID REFERENCES umpires(id),
    weather_data JSONB, -- temperature, wind, humidity, etc.
    game_number INTEGER DEFAULT 1, -- for doubleheaders
    season INTEGER,
    game_type VARCHAR(20), -- regular, playoff, etc.
    status VARCHAR(20) DEFAULT 'scheduled',
    final_score_home INTEGER,
    final_score_away INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index for common queries
CREATE INDEX idx_games_date ON games(game_date);
CREATE INDEX idx_games_teams ON games(home_team_id, away_team_id);

-- Player statistics table (partitioned by year)
CREATE TABLE IF NOT EXISTS player_stats (
    id UUID DEFAULT uuid_generate_v4(),
    player_id UUID REFERENCES players(id),
    game_id UUID REFERENCES games(id),
    season INTEGER NOT NULL,
    game_date DATE NOT NULL,
    stats_type VARCHAR(20) NOT NULL, -- batting, pitching, fielding
    stats JSONB NOT NULL, -- all statistics as JSON
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (id, season)
) PARTITION BY RANGE (season);

-- Create partitions for player stats (last 5 years + current)
CREATE TABLE IF NOT EXISTS player_stats_2020 PARTITION OF player_stats FOR VALUES FROM (2020) TO (2021);
CREATE TABLE IF NOT EXISTS player_stats_2021 PARTITION OF player_stats FOR VALUES FROM (2021) TO (2022);
CREATE TABLE IF NOT EXISTS player_stats_2022 PARTITION OF player_stats FOR VALUES FROM (2022) TO (2023);
CREATE TABLE IF NOT EXISTS player_stats_2023 PARTITION OF player_stats FOR VALUES FROM (2023) TO (2024);
CREATE TABLE IF NOT EXISTS player_stats_2024 PARTITION OF player_stats FOR VALUES FROM (2024) TO (2025);
CREATE TABLE IF NOT EXISTS player_stats_2025 PARTITION OF player_stats FOR VALUES FROM (2025) TO (2026);

-- Pitch-by-pitch data table (partitioned by month for performance)
CREATE TABLE IF NOT EXISTS pitches (
    id UUID DEFAULT uuid_generate_v4(),
    game_id UUID REFERENCES games(id),
    pitcher_id UUID REFERENCES players(id),
    batter_id UUID REFERENCES players(id),
    game_date DATE NOT NULL,
    inning INTEGER NOT NULL,
    inning_half VARCHAR(10) NOT NULL, -- top/bottom
    pitch_number INTEGER NOT NULL,
    pitch_type VARCHAR(20),
    velocity DECIMAL(4,1),
    spin_rate INTEGER,
    release_point JSONB,
    plate_location JSONB,
    result VARCHAR(50), -- ball, strike, hit, etc.
    exit_velocity DECIMAL(4,1),
    launch_angle DECIMAL(4,1),
    hit_distance INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
) PARTITION BY RANGE (game_date);

-- Create monthly partitions for 2025
DO $$
BEGIN
    FOR i IN 1..11 LOOP
        EXECUTE format(
            'CREATE TABLE IF NOT EXISTS pitches_2025_%s PARTITION OF pitches 
             FOR VALUES FROM (''2025-%s-01'') TO (''2025-%s-01'')',
            lpad(i::text, 2, '0'),
            lpad(i::text, 2, '0'),
            lpad((i+1)::text, 2, '0')
        );
    END LOOP;
    -- December needs special handling (goes to next year)
    EXECUTE 'CREATE TABLE IF NOT EXISTS pitches_2025_12 PARTITION OF pitches 
             FOR VALUES FROM (''2025-12-01'') TO (''2026-01-01'')';
END $$;

-- Simulation runs table
CREATE TABLE IF NOT EXISTS simulation_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    game_id UUID REFERENCES games(id),
    simulation_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    config JSONB, -- simulation parameters
    total_runs INTEGER DEFAULT 1000,
    completed_runs INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'pending',
    created_by VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);

-- Individual simulation results
CREATE TABLE IF NOT EXISTS simulation_results (
    id UUID DEFAULT uuid_generate_v4(),
    run_id UUID REFERENCES simulation_runs(id),
    simulation_number INTEGER NOT NULL,
    home_score INTEGER NOT NULL,
    away_score INTEGER NOT NULL,
    total_pitches INTEGER,
    game_duration_minutes INTEGER,
    key_events JSONB, -- home runs, errors, etc.
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (id, run_id)
) PARTITION BY LIST (run_id);

-- Create initial partition for simulation results
CREATE TABLE IF NOT EXISTS simulation_results_default PARTITION OF simulation_results DEFAULT;

-- Aggregated simulation statistics
CREATE TABLE IF NOT EXISTS simulation_aggregates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_id UUID REFERENCES simulation_runs(id) UNIQUE,
    home_win_probability DECIMAL(5,4),
    away_win_probability DECIMAL(5,4),
    expected_home_score DECIMAL(4,2),
    expected_away_score DECIMAL(4,2),
    home_score_distribution JSONB,
    away_score_distribution JSONB,
    total_score_over_under JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Season aggregated statistics table
CREATE TABLE IF NOT EXISTS player_season_aggregates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    player_id UUID REFERENCES players(id),
    season INTEGER NOT NULL,
    stats_type VARCHAR(20) NOT NULL, -- batting, pitching, fielding
    aggregated_stats JSONB NOT NULL, -- season totals and averages
    games_played INTEGER DEFAULT 0,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(player_id, season, stats_type)
);

-- Fielding plays table for advanced defensive metrics
CREATE TABLE IF NOT EXISTS fielding_plays (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    game_id UUID REFERENCES games(id),
    player_id UUID REFERENCES players(id),
    game_date DATE NOT NULL,
    inning INTEGER NOT NULL,
    inning_half VARCHAR(10) NOT NULL,
    play_type VARCHAR(20) NOT NULL, -- ground_ball, fly_ball, line_drive, popup
    hit_location POINT, -- x, y coordinates on field
    hang_time DECIMAL(3,2), -- seconds for fly balls
    exit_velocity DECIMAL(4,1), -- mph
    result VARCHAR(20) NOT NULL, -- out, hit, error, foul
    difficulty_score DECIMAL(3,2), -- 0.00 to 1.00
    fielding_zone VARCHAR(10), -- zone identifier (1-9, foul, etc)
    assist_player_ids UUID[], -- array of player UUIDs for assists
    runner_advancement JSONB, -- base running data
    outs_on_play INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
) PARTITION BY RANGE (game_date);

-- Create monthly partitions for fielding plays (2025)
DO $$
BEGIN
    FOR i IN 1..11 LOOP
        EXECUTE format(
            'CREATE TABLE IF NOT EXISTS fielding_plays_2025_%s PARTITION OF fielding_plays 
             FOR VALUES FROM (''2025-%s-01'') TO (''2025-%s-01'')',
            lpad(i::text, 2, '0'),
            lpad(i::text, 2, '0'),
            lpad((i+1)::text, 2, '0')
        );
    END LOOP;
    -- December needs special handling
    EXECUTE 'CREATE TABLE IF NOT EXISTS fielding_plays_2025_12 PARTITION OF fielding_plays 
             FOR VALUES FROM (''2025-12-01'') TO (''2026-01-01'')';
END $$;

-- Park factors table for fielding adjustments
CREATE TABLE IF NOT EXISTS park_factors (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    stadium_id UUID REFERENCES stadiums(id),
    season INTEGER NOT NULL,
    factor_type VARCHAR(20) NOT NULL, -- hr, doubles, triples, errors, etc
    factor_value DECIMAL(4,3) NOT NULL, -- 1.000 = neutral
    handedness VARCHAR(5), -- L, R, or NULL for both
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(stadium_id, season, factor_type, handedness)
);

-- Injuries table
CREATE TABLE IF NOT EXISTS injuries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    player_id UUID REFERENCES players(id),
    injury_date DATE NOT NULL,
    return_date DATE,
    injury_type VARCHAR(100),
    severity VARCHAR(20),
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX idx_player_stats_player_season ON player_stats(player_id, season);
CREATE INDEX idx_player_stats_game ON player_stats(game_id);
CREATE INDEX idx_player_stats_type ON player_stats(stats_type);
CREATE INDEX idx_pitches_game ON pitches(game_id);
CREATE INDEX idx_pitches_pitcher ON pitches(pitcher_id);
CREATE INDEX idx_pitches_batter ON pitches(batter_id);
CREATE INDEX idx_simulation_results_run ON simulation_results(run_id);
CREATE INDEX idx_injuries_player_active ON injuries(player_id, status) WHERE status = 'active';
CREATE INDEX idx_player_season_aggregates_player_season ON player_season_aggregates(player_id, season);
CREATE INDEX idx_player_season_aggregates_type ON player_season_aggregates(stats_type);
CREATE INDEX idx_fielding_plays_player ON fielding_plays(player_id);
CREATE INDEX idx_fielding_plays_game ON fielding_plays(game_id);
CREATE INDEX idx_fielding_plays_location ON fielding_plays USING GIST(hit_location);
CREATE INDEX idx_fielding_plays_zone ON fielding_plays(fielding_zone);
CREATE INDEX idx_park_factors_stadium_season ON park_factors(stadium_id, season);

-- Create materialized views for common queries
CREATE MATERIALIZED VIEW IF NOT EXISTS player_season_stats AS
SELECT 
    ps.player_id,
    ps.season,
    ps.stats_type,
    jsonb_agg(ps.stats ORDER BY ps.game_date) as games,
    COUNT(*) as game_count,
    MAX(ps.game_date) as last_game_date
FROM player_stats ps
GROUP BY ps.player_id, ps.season, ps.stats_type;

CREATE INDEX idx_player_season_stats ON player_season_stats(player_id, season);

-- Create view for recent player performance
CREATE OR REPLACE VIEW player_recent_performance AS
SELECT 
    p.player_id,
    p.first_name,
    p.last_name,
    ps.season,
    ps.stats_type,
    ps.stats,
    ps.game_date,
    ROW_NUMBER() OVER (PARTITION BY p.player_id, ps.stats_type ORDER BY ps.game_date DESC) as game_recency
FROM players p
JOIN player_stats ps ON p.id = ps.player_id
WHERE ps.game_date >= CURRENT_DATE - INTERVAL '30 days';

-- Function to refresh materialized views
CREATE OR REPLACE FUNCTION refresh_materialized_views()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY player_season_stats;
END;
$$ LANGUAGE plpgsql;

-- Set up triggers for updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_teams_updated_at BEFORE UPDATE ON teams
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_players_updated_at BEFORE UPDATE ON players
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_games_updated_at BEFORE UPDATE ON games
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
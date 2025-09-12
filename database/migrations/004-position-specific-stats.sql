-- Migration: 004-position-specific-stats.sql
-- Add position-specific statistics tables for catcher and outfielder analytics

-- Catcher Stats Table
CREATE TABLE IF NOT EXISTS catcher_stats (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    player_id UUID NOT NULL REFERENCES players(id),
    season INTEGER NOT NULL,

    -- Framing metrics
    framing_runs DECIMAL(5,2) DEFAULT 0,
    framing_pct_above DECIMAL(6,3) DEFAULT 0,

    -- Blocking metrics
    blocking_runs DECIMAL(5,2) DEFAULT 0,
    blocking_pct_above DECIMAL(6,3) DEFAULT 0,

    -- Arm/Throwing metrics
    arm_runs DECIMAL(5,2) DEFAULT 0,
    pop_time DECIMAL(4,3) DEFAULT 2.0, -- seconds
    exchange_time DECIMAL(4,3) DEFAULT 0.85, -- seconds

    -- Defense metrics
    cs_above_avg DECIMAL(5,2) DEFAULT 0,

    -- Composite metrics
    total_catcher_runs DECIMAL(5,2) DEFAULT 0,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Constraints
    UNIQUE(player_id, season),
    CHECK (season >= 1876 AND season <= 2030)
);

-- Outfielder Stats Table
CREATE TABLE IF NOT EXISTS outfielder_stats (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    player_id UUID NOT NULL REFERENCES players(id),
    season INTEGER NOT NULL,
    position VARCHAR(2) NOT NULL, -- LF, CF, RF

    -- Range metrics
    range_runs DECIMAL(5,2) DEFAULT 0,
    jump_rating DECIMAL(4,1) DEFAULT 20.0, -- 20-80 scouting scale

    -- Arm metrics
    arm_runs DECIMAL(5,2) DEFAULT 0,

    -- Speed metrics
    route_efficiency DECIMAL(4,3) DEFAULT 1.0,
    sprint_speed DECIMAL(4,1) DEFAULT 0.0, -- seconds to home
    max_speed_mph DECIMAL(4,1) DEFAULT 0.0,
    first_step_time DECIMAL(4,3) DEFAULT 0.0, -- seconds

    -- Composite metrics
    total_outfielder_runs DECIMAL(5,2) DEFAULT 0,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Constraints
    UNIQUE(player_id, season, position),
    CHECK (position IN ('LF', 'CF', 'RF')),
    CHECK (season >= 1876 AND season <= 2030),
    CHECK (jump_rating >= 0 AND jump_rating <= 80)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_catcher_stats_player_season ON catcher_stats(player_id, season);
CREATE INDEX IF NOT EXISTS idx_catcher_stats_season ON catcher_stats(season);
CREATE INDEX IF NOT EXISTS idx_outfielder_stats_player_season ON outfielder_stats(player_id, season, position);
CREATE INDEX IF NOT EXISTS idx_outfielder_stats_season_position ON outfielder_stats(season, position);

-- Create trigger functions for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create triggers for automatic updated_at
DROP TRIGGER IF EXISTS update_catcher_stats_updated_at ON catcher_stats;
CREATE TRIGGER update_catcher_stats_updated_at
    BEFORE UPDATE ON catcher_stats
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_outfielder_stats_updated_at ON outfielder_stats;
CREATE TRIGGER update_outfielder_stats_updated_at
    BEFORE UPDATE ON outfielder_stats
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Verify tables were created successfully
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_name = 'catcher_stats'
        AND table_schema = 'public'
    ) THEN
        RAISE EXCEPTION 'catcher_stats table was not created successfully';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_name = 'outfielder_stats'
        AND table_schema = 'public'
    ) THEN
        RAISE EXCEPTION 'outfielder_stats table was not created successfully';
    END IF;

    RAISE NOTICE 'Position-specific stats tables created successfully';
END $$;

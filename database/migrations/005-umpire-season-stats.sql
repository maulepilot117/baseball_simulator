-- Migration: Add umpire season statistics table for historical data
-- Similar to player_season_aggregates, this tracks umpire performance by season

-- Create umpire_season_stats table
CREATE TABLE IF NOT EXISTS umpire_season_stats (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    umpire_id UUID NOT NULL REFERENCES umpires(id) ON DELETE CASCADE,
    season INTEGER NOT NULL,
    games_umped INTEGER DEFAULT 0,
    accuracy_pct NUMERIC(5,2),
    consistency_pct NUMERIC(5,2),
    favor_home NUMERIC(5,2),
    expected_accuracy NUMERIC(5,2),
    expected_consistency NUMERIC(5,2),
    correct_calls INTEGER DEFAULT 0,
    incorrect_calls INTEGER DEFAULT 0,
    total_calls INTEGER DEFAULT 0,
    strike_pct NUMERIC(5,2),
    ball_pct NUMERIC(5,2),
    k_pct_above_avg NUMERIC(5,2),
    bb_pct_above_avg NUMERIC(5,2),
    home_plate_calls_per_game NUMERIC(5,2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Unique constraint: one record per umpire per season
    UNIQUE(umpire_id, season)
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_umpire_season_stats_umpire_id ON umpire_season_stats(umpire_id);
CREATE INDEX IF NOT EXISTS idx_umpire_season_stats_season ON umpire_season_stats(season);
CREATE INDEX IF NOT EXISTS idx_umpire_season_stats_accuracy ON umpire_season_stats(accuracy_pct DESC);

-- Add trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_umpire_season_stats_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_umpire_season_stats_updated_at
    BEFORE UPDATE ON umpire_season_stats
    FOR EACH ROW
    EXECUTE FUNCTION update_umpire_season_stats_updated_at();

-- Comment on table
COMMENT ON TABLE umpire_season_stats IS 'Season-specific umpire performance statistics from umpscorecards.com';

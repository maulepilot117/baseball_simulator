-- Fix typos in players table
ALTER TABLE players DROP COLUMN IF EXISTS weighy;
ALTER TABLE players ADD COLUMN IF NOT EXISTS weight INTEGER;

-- Remove duplicate debut_date column (appears twice in CREATE statement)
-- This is handled by the CREATE TABLE statement already

-- Add umpire scorecard columns
ALTER TABLE umpires ADD COLUMN IF NOT EXISTS games_umped INTEGER DEFAULT 0;
ALTER TABLE umpires ADD COLUMN IF NOT EXISTS accuracy_pct DECIMAL(5,2);
ALTER TABLE umpires ADD COLUMN IF NOT EXISTS consistency_pct DECIMAL(5,2);
ALTER TABLE umpires ADD COLUMN IF NOT EXISTS favor_home DECIMAL(5,2);
ALTER TABLE umpires ADD COLUMN IF NOT EXISTS expected_accuracy DECIMAL(5,2);
ALTER TABLE umpires ADD COLUMN IF NOT EXISTS expected_consistency DECIMAL(5,2);
ALTER TABLE umpires ADD COLUMN IF NOT EXISTS correct_calls INTEGER DEFAULT 0;
ALTER TABLE umpires ADD COLUMN IF NOT EXISTS incorrect_calls INTEGER DEFAULT 0;
ALTER TABLE umpires ADD COLUMN IF NOT EXISTS total_calls INTEGER DEFAULT 0;
ALTER TABLE umpires ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();

-- Add missing foreign key reference
ALTER TABLE teams ADD CONSTRAINT fk_teams_stadium 
    FOREIGN KEY (stadium_id) REFERENCES stadiums(id);

-- Add player_mlb_mapping table (not in original schema)
CREATE TABLE IF NOT EXISTS player_mlb_mapping (
    player_id UUID PRIMARY KEY REFERENCES players(id),
    mlb_id INTEGER UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_player_mlb_mapping_mlb_id ON player_mlb_mapping(mlb_id);

-- Add data_fetch_status table (not in original schema)
CREATE TABLE IF NOT EXISTS data_fetch_status (
    id SERIAL PRIMARY KEY,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR(20),
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
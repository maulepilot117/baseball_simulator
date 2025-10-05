-- Add missing tables that the code expects

-- Create data_fetch_status if not exists
CREATE TABLE IF NOT EXISTS data_fetch_status (
    id SERIAL PRIMARY KEY,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR(20),
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create player_mlb_mapping if not exists
CREATE TABLE IF NOT EXISTS player_mlb_mapping (
    player_id UUID PRIMARY KEY REFERENCES players(id),
    mlb_id INTEGER UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index for performance
CREATE INDEX IF NOT EXISTS idx_player_mlb_mapping_mlb_id ON player_mlb_mapping(mlb_id);

-- Add missing columns to umpires table
ALTER TABLE umpires ADD COLUMN IF NOT EXISTS games_umped INTEGER DEFAULT 0;
ALTER TABLE umpires ADD COLUMN IF NOT EXISTS accuracy_pct DECIMAL(5,2);
ALTER TABLE umpires ADD COLUMN IF NOT EXISTS consistency_pct DECIMAL(5,2);
ALTER TABLE umpires ADD COLUMN IF NOT EXISTS favor_home DECIMAL(5,2);
ALTER TABLE umpires ADD COLUMN IF NOT EXISTS expected_accuracy DECIMAL(5,2);
ALTER TABLE umpires ADD COLUMN IF NOT EXISTS expected_consistency DECIMAL(5,2);
ALTER TABLE umpires ADD COLUMN IF NOT EXISTS correct_calls INTEGER DEFAULT 0;
ALTER TABLE umpires ADD COLUMN IF NOT EXISTS incorrect_calls INTEGER DEFAULT 0;
ALTER TABLE umpires ADD COLUMN IF NOT EXISTS total_calls INTEGER DEFAULT 0;
ALTER TABLE umpires ADD COLUMN IF NOT EXISTS strike_pct DECIMAL(5,2);
ALTER TABLE umpires ADD COLUMN IF NOT EXISTS ball_pct DECIMAL(5,2);
ALTER TABLE umpires ADD COLUMN IF NOT EXISTS k_pct_above_avg DECIMAL(5,2);
ALTER TABLE umpires ADD COLUMN IF NOT EXISTS bb_pct_above_avg DECIMAL(5,2);
ALTER TABLE umpires ADD COLUMN IF NOT EXISTS home_plate_calls_per_game DECIMAL(5,2);
ALTER TABLE umpires ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();

-- Add updated_at trigger to umpires
CREATE TRIGGER update_umpires_updated_at BEFORE UPDATE ON umpires
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
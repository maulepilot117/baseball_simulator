-- Add Box Scores and Play-by-Play Tables
-- Migration 010: Comprehensive game detail support

-- Box scores for batting
CREATE TABLE IF NOT EXISTS game_box_score_batting (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    game_id UUID NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    player_id UUID NOT NULL REFERENCES players(id),
    team_id UUID NOT NULL REFERENCES teams(id),
    batting_order INTEGER,
    position VARCHAR(5),
    at_bats INTEGER DEFAULT 0,
    runs INTEGER DEFAULT 0,
    hits INTEGER DEFAULT 0,
    rbis INTEGER DEFAULT 0,
    walks INTEGER DEFAULT 0,
    strikeouts INTEGER DEFAULT 0,
    doubles INTEGER DEFAULT 0,
    triples INTEGER DEFAULT 0,
    home_runs INTEGER DEFAULT 0,
    stolen_bases INTEGER DEFAULT 0,
    caught_stealing INTEGER DEFAULT 0,
    left_on_base INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(game_id, player_id)
);

CREATE INDEX idx_box_batting_game ON game_box_score_batting(game_id);
CREATE INDEX idx_box_batting_player ON game_box_score_batting(player_id);

-- Box scores for pitching
CREATE TABLE IF NOT EXISTS game_box_score_pitching (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    game_id UUID NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    player_id UUID NOT NULL REFERENCES players(id),
    team_id UUID NOT NULL REFERENCES teams(id),
    innings_pitched NUMERIC(4,1) DEFAULT 0,
    hits_allowed INTEGER DEFAULT 0,
    runs_allowed INTEGER DEFAULT 0,
    earned_runs INTEGER DEFAULT 0,
    walks_allowed INTEGER DEFAULT 0,
    strikeouts INTEGER DEFAULT 0,
    home_runs_allowed INTEGER DEFAULT 0,
    pitches_thrown INTEGER DEFAULT 0,
    strikes INTEGER DEFAULT 0,
    win BOOLEAN DEFAULT FALSE,
    loss BOOLEAN DEFAULT FALSE,
    save BOOLEAN DEFAULT FALSE,
    hold BOOLEAN DEFAULT FALSE,
    blown_save BOOLEAN DEFAULT FALSE,
    era NUMERIC(5,2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(game_id, player_id)
);

CREATE INDEX idx_box_pitching_game ON game_box_score_pitching(game_id);
CREATE INDEX idx_box_pitching_player ON game_box_score_pitching(player_id);

-- Play-by-play events
CREATE TABLE IF NOT EXISTS game_plays (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    game_id UUID NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    play_id VARCHAR(100) NOT NULL,
    inning INTEGER NOT NULL,
    inning_half VARCHAR(10) NOT NULL, -- 'top' or 'bottom'
    outs INTEGER NOT NULL,
    balls INTEGER,
    strikes INTEGER,
    batter_id UUID REFERENCES players(id),
    pitcher_id UUID REFERENCES players(id),
    event_type VARCHAR(50), -- 'single', 'double', 'homerun', 'strikeout', 'walk', etc.
    description TEXT,
    rbi INTEGER DEFAULT 0,
    runs_scored INTEGER DEFAULT 0,
    play_sequence JSONB, -- detailed pitch sequence
    runners_on JSONB, -- base runner positions before play
    runners_after JSONB, -- base runner positions after play
    home_score INTEGER DEFAULT 0,
    away_score INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(game_id, play_id)
);

CREATE INDEX idx_plays_game ON game_plays(game_id);
CREATE INDEX idx_plays_inning ON game_plays(game_id, inning, inning_half);

-- Add stadium dome/roof information
ALTER TABLE stadiums ADD COLUMN IF NOT EXISTS roof_type VARCHAR(20) DEFAULT 'open'; -- 'open', 'dome', 'retractable'
ALTER TABLE stadiums ADD COLUMN IF NOT EXISTS surface_type VARCHAR(20) DEFAULT 'grass'; -- 'grass', 'artificial'
ALTER TABLE stadiums ADD COLUMN IF NOT EXISTS elevation INTEGER; -- feet above sea level

-- Update games weather_data to include more fields
COMMENT ON COLUMN games.weather_data IS 'Weather conditions: {temp, condition, wind, humidity, is_dome, roof_closed}';

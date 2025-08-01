-- Create the update_updated_at_column function if it doesn't exist
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Add missing updated_at column to stadiums table
ALTER TABLE stadiums ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();

-- Add trigger for stadiums updated_at
DROP TRIGGER IF EXISTS update_stadiums_updated_at ON stadiums;
CREATE TRIGGER update_stadiums_updated_at BEFORE UPDATE ON stadiums
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Verify all tables have proper columns
-- Fix any other missing columns while we're at it
ALTER TABLE players ALTER COLUMN status SET DEFAULT 'active';
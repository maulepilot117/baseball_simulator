-- Fix All Team Names - Remove City Prefix
-- Migration 009: Strip city names from all team names

UPDATE teams SET name = 'Diamondbacks' WHERE abbreviation = 'AZ';
UPDATE teams SET name = 'Athletics' WHERE abbreviation = 'ATH';
UPDATE teams SET name = 'Braves' WHERE abbreviation = 'ATL';
UPDATE teams SET name = 'Orioles' WHERE abbreviation = 'BAL';
UPDATE teams SET name = 'Red Sox' WHERE abbreviation = 'BOS';
UPDATE teams SET name = 'Cubs' WHERE abbreviation = 'CHC';
UPDATE teams SET name = 'White Sox' WHERE abbreviation = 'CWS';
UPDATE teams SET name = 'Reds' WHERE abbreviation = 'CIN';
UPDATE teams SET name = 'Guardians' WHERE abbreviation = 'CLE';
UPDATE teams SET name = 'Rockies' WHERE abbreviation = 'COL';
UPDATE teams SET name = 'Tigers' WHERE abbreviation = 'DET';
UPDATE teams SET name = 'Astros' WHERE abbreviation = 'HOU';
UPDATE teams SET name = 'Royals' WHERE abbreviation = 'KC';
UPDATE teams SET name = 'Angels' WHERE abbreviation = 'LAA';
UPDATE teams SET name = 'Dodgers' WHERE abbreviation = 'LAD';
UPDATE teams SET name = 'Marlins' WHERE abbreviation = 'MIA';
UPDATE teams SET name = 'Brewers' WHERE abbreviation = 'MIL';
UPDATE teams SET name = 'Twins' WHERE abbreviation = 'MIN';
UPDATE teams SET name = 'Mets' WHERE abbreviation = 'NYM';
UPDATE teams SET name = 'Yankees' WHERE abbreviation = 'NYY';
UPDATE teams SET name = 'Phillies' WHERE abbreviation = 'PHI';
UPDATE teams SET name = 'Pirates' WHERE abbreviation = 'PIT';
UPDATE teams SET name = 'Padres' WHERE abbreviation = 'SD';
UPDATE teams SET name = 'Mariners' WHERE abbreviation = 'SEA';
UPDATE teams SET name = 'Giants' WHERE abbreviation = 'SF';
UPDATE teams SET name = 'Cardinals' WHERE abbreviation = 'STL';
UPDATE teams SET name = 'Rays' WHERE abbreviation = 'TB';
UPDATE teams SET name = 'Rangers' WHERE abbreviation = 'TEX';
UPDATE teams SET name = 'Blue Jays' WHERE abbreviation = 'TOR';
UPDATE teams SET name = 'Nationals' WHERE abbreviation = 'WSH';

-- Verify the changes
SELECT abbreviation, city, name
FROM teams
ORDER BY abbreviation;

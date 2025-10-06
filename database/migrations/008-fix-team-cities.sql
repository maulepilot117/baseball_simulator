-- Fix Team Cities
-- Migration 008: Extract and populate city names from team names

-- Update cities for teams where city is in the name
UPDATE teams SET city = 'Arizona' WHERE abbreviation = 'AZ';
UPDATE teams SET city = 'Oakland' WHERE abbreviation = 'ATH';
UPDATE teams SET city = 'Atlanta' WHERE abbreviation = 'ATL';
UPDATE teams SET city = 'Baltimore' WHERE abbreviation = 'BAL';
UPDATE teams SET city = 'Boston' WHERE abbreviation = 'BOS';
UPDATE teams SET city = 'Chicago' WHERE abbreviation IN ('CHC', 'CWS');
UPDATE teams SET city = 'Cincinnati' WHERE abbreviation = 'CIN';
UPDATE teams SET city = 'Cleveland' WHERE abbreviation = 'CLE';
UPDATE teams SET city = 'Colorado' WHERE abbreviation = 'COL';
UPDATE teams SET city = 'Detroit' WHERE abbreviation = 'DET';
UPDATE teams SET city = 'Houston' WHERE abbreviation = 'HOU';
UPDATE teams SET city = 'Kansas City' WHERE abbreviation = 'KC';
UPDATE teams SET city = 'Los Angeles' WHERE abbreviation IN ('LAA', 'LAD');
UPDATE teams SET city = 'Miami' WHERE abbreviation = 'MIA';
UPDATE teams SET city = 'Milwaukee' WHERE abbreviation = 'MIL';
UPDATE teams SET city = 'Minnesota' WHERE abbreviation = 'MIN';
UPDATE teams SET city = 'New York' WHERE abbreviation IN ('NYM', 'NYY');
UPDATE teams SET city = 'Philadelphia' WHERE abbreviation = 'PHI';
UPDATE teams SET city = 'Pittsburgh' WHERE abbreviation = 'PIT';
UPDATE teams SET city = 'San Diego' WHERE abbreviation = 'SD';
UPDATE teams SET city = 'Seattle' WHERE abbreviation = 'SEA';
UPDATE teams SET city = 'San Francisco' WHERE abbreviation = 'SF';
UPDATE teams SET city = 'St. Louis' WHERE abbreviation = 'STL';
UPDATE teams SET city = 'Tampa Bay' WHERE abbreviation = 'TB';
UPDATE teams SET city = 'Texas' WHERE abbreviation = 'TEX';
UPDATE teams SET city = 'Toronto' WHERE abbreviation = 'TOR';
UPDATE teams SET city = 'Washington' WHERE abbreviation = 'WSH';

-- Update team names to remove city (keep just the team name)
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
SELECT city, name, abbreviation
FROM teams
ORDER BY city, name;

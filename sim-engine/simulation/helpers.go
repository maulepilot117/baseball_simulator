package simulation

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"sort"
	"strconv"
	"time"

	"sim-engine/models"
)

// loadGameData retrieves game information from the database
func (se *SimulationEngine) loadGameData(ctx context.Context, gameID string) (*GameData, error) {
	var gameData GameData
	var weatherJSON []byte

	query := `
		SELECT g.game_id, g.home_team_id, g.away_team_id, g.game_date, 
		       g.weather_data, s.name as stadium_name
		FROM games g
		LEFT JOIN stadiums s ON g.stadium_id = s.id
		WHERE g.game_id = $1
	`

	err := se.db.QueryRow(ctx, query, gameID).Scan(
		&gameData.GameID,
		&gameData.HomeTeamID,
		&gameData.AwayTeamID,
		&gameData.Date,
		&weatherJSON,
		&gameData.Stadium,
	)

	if err != nil {
		return nil, fmt.Errorf("failed to load game data: %w", err)
	}

	// Parse weather data
	if len(weatherJSON) > 0 {
		if err := json.Unmarshal(weatherJSON, &gameData.Weather); err != nil {
			log.Printf("Failed to parse weather data: %v", err)
			// Use default weather
			gameData.Weather = models.Weather{
				Temperature: 72,
				WindSpeed:   5,
				WindDir:     "calm",
				Humidity:    50,
				Pressure:    29.92,
			}
		}
	} else {
		// Default weather conditions
		gameData.Weather = models.Weather{
			Temperature: 72,
			WindSpeed:   5,
			WindDir:     "calm",
			Humidity:    50,
			Pressure:    29.92,
		}
	}

	return &gameData, nil
}

// loadTeamRosters loads the rosters for both teams
func (se *SimulationEngine) loadTeamRosters(ctx context.Context, homeTeamID, awayTeamID string) (*models.Roster, *models.Roster, error) {
	homeRoster, err := se.loadTeamRoster(ctx, homeTeamID)
	if err != nil {
		return nil, nil, fmt.Errorf("failed to load home roster: %w", err)
	}

	awayRoster, err := se.loadTeamRoster(ctx, awayTeamID)
	if err != nil {
		return nil, nil, fmt.Errorf("failed to load away roster: %w", err)
	}

	return homeRoster, awayRoster, nil
}

// loadTeamRoster loads a single team's roster with statistics
func (se *SimulationEngine) loadTeamRoster(ctx context.Context, teamID string) (*models.Roster, error) {
	// Load players for the team
	playersQuery := `
		SELECT p.id, p.player_id, p.first_name, p.last_name, p.position, 
		       p.bats, p.throws, p.birth_date
		FROM players p
		WHERE p.team_id = $1 AND p.status = 'active'
		ORDER BY p.position, p.last_name
	`

	rows, err := se.db.Query(ctx, playersQuery, teamID)
	if err != nil {
		return nil, fmt.Errorf("failed to query players: %w", err)
	}
	defer rows.Close()

	var players []models.Player
	var playerIDs []string

	for rows.Next() {
		var player models.Player
		var birthDate *time.Time
		var firstName, lastName string

		err := rows.Scan(
			&player.ID,
			&player.ID, // player_id maps to ID for simplicity
			&firstName,
			&lastName,
			&player.Position,
			&player.Hand,
			&player.Hand, // throws maps to hand for simplicity
			&birthDate,
		)

		if err != nil {
			log.Printf("Error scanning player: %v", err)
			continue
		}

		player.Name = fmt.Sprintf("%s %s", firstName, lastName)
		player.TeamID = teamID

		// Calculate age if birth date available
		if birthDate != nil {
			player.Attributes.Age = int(time.Since(*birthDate).Hours() / 24 / 365.25)
		} else {
			player.Attributes.Age = 27 // Default age
		}

		players = append(players, player)
		playerIDs = append(playerIDs, player.ID)
	}

	// Load current season statistics for all players
	currentYear := time.Now().Year()
	if err := se.loadPlayerStatistics(ctx, players, currentYear); err != nil {
		log.Printf("Warning: failed to load player statistics: %v", err)
		// Continue with default stats
		se.setDefaultStatistics(players)
	}

	// Create roster with lineups
	roster := &models.Roster{
		TeamID:  teamID,
		Players: players,
	}

	// Generate lineup orders
	se.generateLineups(roster)

	return roster, nil
}

// loadPlayerStatistics loads current season stats for players
func (se *SimulationEngine) loadPlayerStatistics(ctx context.Context, players []models.Player, season int) error {
	if len(players) == 0 {
		return nil
	}

	// Build player ID list for query
	playerIDs := make([]string, len(players))
	for i, player := range players {
		playerIDs[i] = player.ID
	}

	// Load batting stats
	battingQuery := `
		SELECT player_id, aggregated_stats
		FROM player_season_aggregates
		WHERE player_id = ANY($1) AND season = $2 AND stats_type = 'batting'
	`

	rows, err := se.db.Query(ctx, battingQuery, playerIDs, season)
	if err != nil {
		return fmt.Errorf("failed to query batting stats: %w", err)
	}
	defer rows.Close()

	battingStats := make(map[string]map[string]interface{})
	for rows.Next() {
		var playerID string
		var statsJSON []byte

		if err := rows.Scan(&playerID, &statsJSON); err != nil {
			continue
		}

		var stats map[string]interface{}
		if err := json.Unmarshal(statsJSON, &stats); err != nil {
			continue
		}

		battingStats[playerID] = stats
	}

	// Load pitching stats
	pitchingQuery := `
		SELECT player_id, aggregated_stats
		FROM player_season_aggregates
		WHERE player_id = ANY($1) AND season = $2 AND stats_type = 'pitching'
	`

	rows, err = se.db.Query(ctx, pitchingQuery, playerIDs, season)
	if err != nil {
		return fmt.Errorf("failed to query pitching stats: %w", err)
	}
	defer rows.Close()

	pitchingStats := make(map[string]map[string]interface{})
	for rows.Next() {
		var playerID string
		var statsJSON []byte

		if err := rows.Scan(&playerID, &statsJSON); err != nil {
			continue
		}

		var stats map[string]interface{}
		if err := json.Unmarshal(statsJSON, &stats); err != nil {
			continue
		}

		pitchingStats[playerID] = stats
	}

	// Load fielding stats
	fieldingQuery := `
		SELECT player_id, aggregated_stats
		FROM player_season_aggregates
		WHERE player_id = ANY($1) AND season = $2 AND stats_type = 'fielding'
	`

	rows, err = se.db.Query(ctx, fieldingQuery, playerIDs, season)
	if err != nil {
		return fmt.Errorf("failed to query fielding stats: %w", err)
	}
	defer rows.Close()

	fieldingStats := make(map[string]map[string]interface{})
	for rows.Next() {
		var playerID string
		var statsJSON []byte

		if err := rows.Scan(&playerID, &statsJSON); err != nil {
			continue
		}

		var stats map[string]interface{}
		if err := json.Unmarshal(statsJSON, &stats); err != nil {
			continue
		}

		fieldingStats[playerID] = stats
	}

	// Apply stats to players
	for i := range players {
		playerID := players[i].ID

		// Apply batting stats
		if batting, exists := battingStats[playerID]; exists {
			se.applyBattingStats(&players[i], batting)
		}

		// Apply pitching stats
		if pitching, exists := pitchingStats[playerID]; exists {
			se.applyPitchingStats(&players[i], pitching)
		}

		// Apply fielding stats
		if fielding, exists := fieldingStats[playerID]; exists {
			se.applyFieldingStats(&players[i], fielding)
		}

		// Set default attributes if not loaded
		se.setDefaultAttributes(&players[i])
	}

	return nil
}

// applyBattingStats applies batting statistics to a player
func (se *SimulationEngine) applyBattingStats(player *models.Player, stats map[string]interface{}) {
	player.Batting.AVG = getFloatFromStats(stats, "AVG", 0.250)
	player.Batting.OBP = getFloatFromStats(stats, "OBP", 0.320)
	player.Batting.SLG = getFloatFromStats(stats, "SLG", 0.400)
	player.Batting.OPS = player.Batting.OBP + player.Batting.SLG
	player.Batting.WOBA = getFloatFromStats(stats, "wOBA", 0.320)
	player.Batting.WRCPlus = getIntFromStats(stats, "wRC+", 100)
	player.Batting.ISO = getFloatFromStats(stats, "ISO", 0.150)
	player.Batting.BABIP = getFloatFromStats(stats, "BABIP", 0.300)
	player.Batting.BBPercent = getFloatFromStats(stats, "BB%", 8.5)
	player.Batting.KPercent = getFloatFromStats(stats, "K%", 22.0)

	// Counting stats
	player.Batting.PA = getIntFromStats(stats, "PA", 500)
	player.Batting.AB = getIntFromStats(stats, "AB", 450)
	player.Batting.H = getIntFromStats(stats, "H", 110)
	player.Batting.Doubles = getIntFromStats(stats, "2B", 20)
	player.Batting.Triples = getIntFromStats(stats, "3B", 2)
	player.Batting.HR = getIntFromStats(stats, "HR", 15)
	player.Batting.RBI = getIntFromStats(stats, "RBI", 60)
	player.Batting.SB = getIntFromStats(stats, "SB", 5)
	player.Batting.CS = getIntFromStats(stats, "CS", 2)
}

// applyPitchingStats applies pitching statistics to a player
func (se *SimulationEngine) applyPitchingStats(player *models.Player, stats map[string]interface{}) {
	player.Pitching.ERA = getFloatFromStats(stats, "ERA", 4.50)
	player.Pitching.WHIP = getFloatFromStats(stats, "WHIP", 1.35)
	player.Pitching.FIP = getFloatFromStats(stats, "FIP", 4.20)
	player.Pitching.XFIP = getFloatFromStats(stats, "xFIP", 4.20)
	player.Pitching.ERAPlus = getIntFromStats(stats, "ERA+", 100)
	player.Pitching.KPer9 = getFloatFromStats(stats, "K/9", 8.5)
	player.Pitching.BBPer9 = getFloatFromStats(stats, "BB/9", 3.2)
	player.Pitching.HRPer9 = getFloatFromStats(stats, "HR/9", 1.2)
	player.Pitching.KBBRatio = getFloatFromStats(stats, "K/BB", 2.7)

	// Counting stats
	player.Pitching.IP = getFloatFromStats(stats, "IP", 150.0)
	player.Pitching.H = getIntFromStats(stats, "H", 145)
	player.Pitching.ER = getIntFromStats(stats, "ER", 65)
	player.Pitching.BB = getIntFromStats(stats, "BB", 50)
	player.Pitching.SO = getIntFromStats(stats, "SO", 140)
	player.Pitching.HR = getIntFromStats(stats, "HR", 18)
	player.Pitching.W = getIntFromStats(stats, "W", 8)
	player.Pitching.L = getIntFromStats(stats, "L", 8)

	// Contact management
	player.Pitching.GroundBallPercent = getFloatFromStats(stats, "GB%", 45.0)
	player.Pitching.FlyBallPercent = getFloatFromStats(stats, "FB%", 35.0)
	player.Pitching.LinedrivePercent = getFloatFromStats(stats, "LD%", 20.0)
}

// applyFieldingStats applies fielding statistics to a player
func (se *SimulationEngine) applyFieldingStats(player *models.Player, stats map[string]interface{}) {
	player.Fielding.FPCT = getFloatFromStats(stats, "FPCT", 0.975)
	player.Fielding.Errors = getIntFromStats(stats, "E", 8)
	player.Fielding.PO = getIntFromStats(stats, "PO", 200)
	player.Fielding.A = getIntFromStats(stats, "A", 300)
	player.Fielding.UZR = getFloatFromStats(stats, "UZR", 0.0)
	player.Fielding.DRS = getIntFromStats(stats, "DRS", 0)
	player.Fielding.ARM = getFloatFromStats(stats, "ARM", 50.0)
	player.Fielding.RangeRuns = getFloatFromStats(stats, "RANGE_RUNS", 0.0)

	// Position-specific stats
	if player.Position == "C" {
		player.Fielding.FramingRuns = getFloatFromStats(stats, "FRAMING_RUNS", 0.0)
		player.Fielding.BlockingRuns = getFloatFromStats(stats, "BLOCKING_RUNS", 0.0)
	}

	if player.Position == "LF" || player.Position == "CF" || player.Position == "RF" {
		player.Fielding.JumpRating = getFloatFromStats(stats, "JUMP_RATING", 50.0)
	}
}

// setDefaultAttributes sets default scouting attributes for players
func (se *SimulationEngine) setDefaultAttributes(player *models.Player) {
	// Set defaults based on performance if not already set
	if player.Attributes.Speed == 0 {
		// Base speed on stolen bases and position
		speed := 45 // Default
		if player.Batting.SB > 15 {
			speed = 60
		} else if player.Batting.SB > 5 {
			speed = 55
		}

		// Catchers tend to be slower
		if player.Position == "C" {
			speed = int(float64(speed) * 0.8)
		}

		player.Attributes.Speed = speed
	}

	if player.Attributes.Power == 0 {
		// Base power on home runs and ISO
		power := 45 // Default
		if player.Batting.HR > 25 {
			power = 65
		} else if player.Batting.HR > 15 {
			power = 55
		} else if player.Batting.HR > 8 {
			power = 50
		}

		player.Attributes.Power = power
	}

	if player.Attributes.Contact == 0 {
		// Base contact on strikeout rate and average
		contact := 50
		if player.Batting.KPercent < 15 {
			contact = 60
		} else if player.Batting.KPercent > 25 {
			contact = 40
		}

		if player.Batting.AVG > 0.280 {
			contact += 5
		} else if player.Batting.AVG < 0.240 {
			contact -= 5
		}

		player.Attributes.Contact = contact
	}

	if player.Attributes.Eye == 0 {
		// Base eye on walk rate
		eye := 50
		if player.Batting.BBPercent > 12 {
			eye = 60
		} else if player.Batting.BBPercent < 6 {
			eye = 40
		}

		player.Attributes.Eye = eye
	}

	// Set remaining attributes to league average if not set
	if player.Attributes.ArmStrength == 0 {
		player.Attributes.ArmStrength = 50
	}
	if player.Attributes.Accuracy == 0 {
		player.Attributes.Accuracy = 50
	}
	if player.Attributes.Range == 0 {
		player.Attributes.Range = 50
	}
	if player.Attributes.Hands == 0 {
		player.Attributes.Hands = 50
	}
	if player.Attributes.Height == 0 {
		player.Attributes.Height = 72 // 6'0"
	}
	if player.Attributes.Weight == 0 {
		player.Attributes.Weight = 190
	}
	if player.Attributes.Clutch == 0 {
		player.Attributes.Clutch = 50
	}
	if player.Attributes.Durability == 0 {
		player.Attributes.Durability = 50
	}
	if player.Attributes.Composure == 0 {
		player.Attributes.Composure = 50
	}
}

// setDefaultStatistics sets league average statistics for players without data
func (se *SimulationEngine) setDefaultStatistics(players []models.Player) {
	for i := range players {
		player := &players[i]

		// Set default batting stats
		player.Batting.AVG = 0.250
		player.Batting.OBP = 0.320
		player.Batting.SLG = 0.400
		player.Batting.OPS = 0.720
		player.Batting.WOBA = 0.320
		player.Batting.WRCPlus = 100
		player.Batting.ISO = 0.150
		player.Batting.BABIP = 0.300
		player.Batting.BBPercent = 8.5
		player.Batting.KPercent = 22.0
		player.Batting.PA = 500
		player.Batting.AB = 450
		player.Batting.H = 110
		player.Batting.HR = 15

		// Set default pitching stats
		player.Pitching.ERA = 4.50
		player.Pitching.WHIP = 1.35
		player.Pitching.FIP = 4.20
		player.Pitching.KPer9 = 8.5
		player.Pitching.BBPer9 = 3.2
		player.Pitching.IP = 150

		// Set default fielding stats
		player.Fielding.FPCT = 0.975
		player.Fielding.UZR = 0.0
		player.Fielding.DRS = 0

		// Set default attributes
		se.setDefaultAttributes(player)
	}
}

// Helper functions for extracting values from stats maps
func getFloatFromStats(stats map[string]interface{}, key string, defaultValue float64) float64 {
	if val, exists := stats[key]; exists {
		switch v := val.(type) {
		case float64:
			return v
		case int:
			return float64(v)
		case string:
			// Try to parse string as float
			if parsed, err := parseFloat(v); err == nil {
				return parsed
			}
		}
	}
	return defaultValue
}

func getIntFromStats(stats map[string]interface{}, key string, defaultValue int) int {
	if val, exists := stats[key]; exists {
		switch v := val.(type) {
		case int:
			return v
		case float64:
			return int(v)
		case string:
			// Try to parse string as int
			if parsed, err := parseInt(v); err == nil {
				return parsed
			}
		}
	}
	return defaultValue
}

// parseFloat parses a string to float64
func parseFloat(s string) (float64, error) {
	if f, err := strconv.ParseFloat(s, 64); err == nil {
		return f, nil
	}
	return 0.0, fmt.Errorf("failed to parse float: %s", s)
}

// parseInt parses a string to int
func parseInt(s string) (int, error) {
	if i, err := strconv.Atoi(s); err == nil {
		return i, nil
	}
	return 0, fmt.Errorf("failed to parse int: %s", s)
}

// generateLineups creates batting orders and pitching rotations
func (se *SimulationEngine) generateLineups(roster *models.Roster) {
	// Separate position players and pitchers
	var positionPlayers []models.Player
	var pitchers []models.Player

	for _, player := range roster.Players {
		if player.Position == "P" {
			pitchers = append(pitchers, player)
		} else {
			positionPlayers = append(positionPlayers, player)
		}
	}

	// Create batting lineup based on OPS
	sort.Slice(positionPlayers, func(i, j int) bool {
		return positionPlayers[i].Batting.OPS > positionPlayers[j].Batting.OPS
	})

	// Traditional batting order strategy
	var lineup []string
	if len(positionPlayers) >= 9 {
		// 1. Leadoff - high OBP, speed
		// 2. Contact hitter
		// 3. Best overall hitter
		// 4. Power hitter
		// 5. RBI guy
		// 6-8. Fill out lineup
		// 9. Pitcher or weakest hitter

		for i := 0; i < 9 && i < len(positionPlayers); i++ {
			lineup = append(lineup, positionPlayers[i].ID)
		}
	}

	roster.Lineup = lineup

	// Create pitching rotation (top 5 pitchers by ERA/FIP)
	sort.Slice(pitchers, func(i, j int) bool {
		return pitchers[i].Pitching.FIP < pitchers[j].Pitching.FIP
	})

	var rotation []string
	var bullpen []string

	for i, pitcher := range pitchers {
		if i < 5 { // Starting rotation
			rotation = append(rotation, pitcher.ID)
		} else { // Bullpen
			bullpen = append(bullpen, pitcher.ID)
		}
	}

	roster.Rotation = rotation
	roster.Bullpen = bullpen
}

// createLineup creates the game lineup from roster
func (se *SimulationEngine) createLineup(roster *models.Roster) []models.Player {
	var lineup []models.Player

	// Convert lineup IDs to players
	for _, playerID := range roster.Lineup {
		for _, player := range roster.Players {
			if player.ID == playerID {
				lineup = append(lineup, player)
				break
			}
		}
	}

	// If lineup is incomplete, fill with available position players
	if len(lineup) < 9 {
		for _, player := range roster.Players {
			if player.Position != "P" && len(lineup) < 9 {
				// Check if already in lineup
				found := false
				for _, lineupPlayer := range lineup {
					if lineupPlayer.ID == player.ID {
						found = true
						break
					}
				}
				if !found {
					lineup = append(lineup, player)
				}
			}
		}
	}

	return lineup
}

// getStartingPitcher returns the starting pitcher for the team
func (se *SimulationEngine) getStartingPitcher(roster *models.Roster) *models.Player {
	// Use first pitcher in rotation, or any pitcher if rotation is empty
	if len(roster.Rotation) > 0 {
		for _, player := range roster.Players {
			if player.ID == roster.Rotation[0] {
				return &player
			}
		}
	}

	// Fallback to any pitcher
	for _, player := range roster.Players {
		if player.Position == "P" {
			return &player
		}
	}

	// This shouldn't happen in a valid roster
	return nil
}

// Continue with remaining helper functions...

// Performance monitoring and debug helpers
func (se *SimulationEngine) getActiveRunsCount() int {
	se.mu.RLock()
	defer se.mu.RUnlock()
	return len(se.activeRuns)
}

// runPerformanceCleanup periodically cleans up old runs to prevent memory leaks
func (se *SimulationEngine) runPerformanceCleanup() {
	ticker := time.NewTicker(1 * time.Hour)
	defer ticker.Stop()

	for range ticker.C {
		se.CleanupOldRuns()
		log.Printf("Simulation engine cleanup: %d active runs", se.getActiveRunsCount())
	}
}

// Helper function to validate game configuration
func (se *SimulationEngine) validateGameConfig(config map[string]interface{}) error {
	// Add any custom configuration validation here
	if config == nil {
		return nil // Default config is acceptable
	}

	// Example validations
	if val, exists := config["weather_effects"]; exists {
		if enabled, ok := val.(bool); ok && enabled {
			// Weather effects are enabled, ensure weather data is available
			log.Printf("Weather effects enabled for simulation")
		}
	}

	if val, exists := config["advanced_metrics"]; exists {
		if enabled, ok := val.(bool); ok && enabled {
			log.Printf("Advanced metrics enabled for simulation")
		}
	}

	return nil
}

// StartPerformanceMonitoring starts background cleanup processes
func (se *SimulationEngine) StartPerformanceMonitoring() {
	go se.runPerformanceCleanup()
}

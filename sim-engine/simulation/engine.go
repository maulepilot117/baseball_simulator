package simulation

import (
	"context"
	"log"
	"math/rand"
	"sync"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
	"sim-engine/models"
	"sim-engine/weather"
)

// SimulationEngine handles baseball game simulations
type SimulationEngine struct {
	db             *pgxpool.Pool
	workers        int
	simulationRuns int
	mu             sync.RWMutex
	activeRuns     map[string]*RunStatus
	weatherService WeatherService
}

// WeatherService interface for fetching weather data
type WeatherService interface {
	GetWeatherForGame(ctx context.Context, stadium StadiumInfo, gameTime time.Time) (models.Weather, error)
}

// StadiumInfo matches the weather service stadium info structure
type StadiumInfo = struct {
	Name      string
	Location  string
	Latitude  float64
	Longitude float64
	RoofType  string
	Altitude  int
}

// RunStatus tracks the progress of a simulation run
type RunStatus struct {
	RunID            string
	GameID           string
	TotalRuns        int
	CompletedRuns    int
	Status           string
	StartTime        time.Time
	CompletedTime    *time.Time
	Results          []models.SimulationResult
	AggregatedResult *models.AggregatedResult
}

// NewSimulationEngine creates a new simulation engine
func NewSimulationEngine(db *pgxpool.Pool, workers, simulationRuns int) *SimulationEngine {
	return &SimulationEngine{
		db:             db,
		workers:        workers,
		simulationRuns: simulationRuns,
		activeRuns:     make(map[string]*RunStatus),
		weatherService: nil, // Will be set via SetWeatherService
	}
}

// SetWeatherService sets the weather service for the engine
func (se *SimulationEngine) SetWeatherService(ws WeatherService) {
	se.weatherService = ws
}

// RunSimulation executes a complete simulation run
func (se *SimulationEngine) RunSimulation(runID, gameID string, simulationRuns int, config map[string]interface{}) {
	ctx := context.Background()

	// Update status to running
	se.updateRunStatus(runID, "running")

	// Initialize run status
	se.mu.Lock()
	se.activeRuns[runID] = &RunStatus{
		RunID:         runID,
		GameID:        gameID,
		TotalRuns:     simulationRuns,
		CompletedRuns: 0,
		Status:        "running",
		StartTime:     time.Now(),
		Results:       make([]models.SimulationResult, 0, simulationRuns),
	}
	se.mu.Unlock()

	// Load game data
	gameData, err := se.loadGameData(ctx, gameID)
	if err != nil {
		log.Printf("Failed to load game data for %s: %v", gameID, err)
		se.updateRunStatus(runID, "error")
		return
	}

	// Fetch real-time weather if weather service is available
	if se.weatherService != nil && gameData.Stadium.Name != "" {
		// Convert stadium info for weather service
		stadiumInfo := se.convertToWeatherStadiumInfo(gameData.Stadium)

		weather, err := se.weatherService.GetWeatherForGame(ctx, stadiumInfo, gameData.GameTime)
		if err != nil {
			log.Printf("Failed to fetch weather for %s: %v, using default", gameData.Stadium.Name, err)
		} else {
			gameData.Weather = weather
			log.Printf("Fetched weather for %s: %d°F, wind %d mph %s",
				gameData.Stadium.Name, weather.Temperature, weather.WindSpeed, weather.WindDir)
		}
	}

	// Load team rosters
	homeRoster, awayRoster, err := se.loadTeamRosters(ctx, gameData.HomeTeamID, gameData.AwayTeamID)
	if err != nil {
		log.Printf("Failed to load team rosters for %s: %v", gameID, err)
		se.updateRunStatus(runID, "error")
		return
	}

	// Run simulations concurrently
	resultsChan := make(chan models.SimulationResult, simulationRuns)
	var wg sync.WaitGroup

	// Create worker goroutines
	simulationsPerWorker := simulationRuns / se.workers
	remainder := simulationRuns % se.workers

	for i := 0; i < se.workers; i++ {
		wg.Add(1)

		workerSims := simulationsPerWorker
		if i < remainder {
			workerSims++
		}

		go func(workerID, simCount int) {
			defer wg.Done()

			for j := 0; j < simCount; j++ {
				simNumber := workerID*simulationsPerWorker + j + 1
				result := se.simulateGame(runID, simNumber, gameData, homeRoster, awayRoster, config)
				resultsChan <- result

				// Update progress
				se.updateProgress(runID)
			}
		}(i, workerSims)
	}

	// Collect results
	go func() {
		wg.Wait()
		close(resultsChan)
	}()

	var results []models.SimulationResult
	for result := range resultsChan {
		results = append(results, result)

		// Store individual result in database
		if err := se.storeSimulationResult(ctx, result); err != nil {
			log.Printf("Failed to store simulation result: %v", err)
		}
	}

	// Calculate aggregated results
	aggregated := se.calculateAggregatedResults(runID, results)

	// Store aggregated results
	if err := se.storeAggregatedResults(ctx, aggregated); err != nil {
		log.Printf("Failed to store aggregated results: %v", err)
	}

	// Update final status
	se.mu.Lock()
	if status, exists := se.activeRuns[runID]; exists {
		status.Status = "completed"
		status.CompletedRuns = simulationRuns
		completedTime := time.Now()
		status.CompletedTime = &completedTime
		status.Results = results
		status.AggregatedResult = aggregated
	}
	se.mu.Unlock()

	se.updateRunStatus(runID, "completed")

	log.Printf("Simulation run %s completed: %d simulations in %v",
		runID, simulationRuns, time.Since(se.activeRuns[runID].StartTime))
}

// simulateGame simulates a single baseball game
func (se *SimulationEngine) simulateGame(runID string, simNumber int, gameData *GameData,
	homeRoster, awayRoster *models.Roster, config map[string]interface{}) models.SimulationResult {

	// Initialize game state
	gameState := models.NewGameState(gameData.GameID, runID)
	gameState.Weather = gameData.Weather

	// Initialize lineups
	homeLineup := se.createLineup(homeRoster)
	awayLineup := se.createLineup(awayRoster)

	// Initialize player stat tracking
	batterStats := make(map[string]*models.PlayerBattingStats)
	pitcherStats := make(map[string]*models.PlayerPitchingStats)

	// Initialize stats for all players
	for i := range homeLineup {
		batterStats[homeLineup[i].ID] = &models.PlayerBattingStats{
			PlayerID:   homeLineup[i].ID,
			PlayerName: homeLineup[i].Name,
			Position:   homeLineup[i].Position,
		}
	}
	for i := range awayLineup {
		batterStats[awayLineup[i].ID] = &models.PlayerBattingStats{
			PlayerID:   awayLineup[i].ID,
			PlayerName: awayLineup[i].Name,
			Position:   awayLineup[i].Position,
		}
	}

	var events []models.GameEvent
	pitchCount := 0
	homeBatterIndex := 0
	awayBatterIndex := 0

	// Get starting pitchers
	homePitcher := se.getStartingPitcher(homeRoster)
	awayPitcher := se.getStartingPitcher(awayRoster)
	currentPitcher := awayPitcher // Away team pitches first

	// Initialize pitcher stats
	pitcherStats[homePitcher.ID] = &models.PlayerPitchingStats{
		PlayerID:   homePitcher.ID,
		PlayerName: homePitcher.Name,
	}
	pitcherStats[awayPitcher.ID] = &models.PlayerPitchingStats{
		PlayerID:   awayPitcher.ID,
		PlayerName: awayPitcher.Name,
	}

	// Simulate game
	for !gameState.IsGameOver() {
		// Determine current batter and lineup
		var currentBatter *models.Player
		var currentLineup []models.Player
		var batterIndex *int

		if gameState.InningHalf == "top" {
			currentLineup = awayLineup
			batterIndex = &awayBatterIndex
			currentPitcher = homePitcher
		} else {
			currentLineup = homeLineup
			batterIndex = &homeBatterIndex
			currentPitcher = awayPitcher
		}

		currentBatter = &currentLineup[*batterIndex]

		// Set up at-bat
		gameState.CurrentAB = models.AtBat{
			BatterID:    currentBatter.ID,
			BatterName:  currentBatter.Name,
			PitcherID:   currentPitcher.ID,
			PitcherName: currentPitcher.Name,
			BatterHand:  currentBatter.Hand,
			PitcherHand: currentPitcher.Hand,
			PitchCount:  0,
			Leverage:    gameState.CalculateLeverage(),
		}

		// Simulate at-bat with full context (umpire, park factors, stadium)
		atBatResult := se.simulateAtBatWithContext(currentBatter, currentPitcher, gameState, gameData)
		atBatPitches := rand.Intn(6) + 3 // 3-8 pitches per at-bat
		pitchCount += atBatPitches

		// Process at-bat result
		runs, outs := se.processAtBatResult(gameState, atBatResult)

		// Track batter stats
		se.updateBatterStats(batterStats[currentBatter.ID], atBatResult, runs)

		// Track pitcher stats
		se.updatePitcherStats(pitcherStats[currentPitcher.ID], atBatResult, runs, atBatPitches)

		// Create game event
		event := models.GameEvent{
			Type:        atBatResult.Type,
			Description: atBatResult.Description,
			Inning:      gameState.Inning,
			InningHalf:  gameState.InningHalf,
			BatterID:    currentBatter.ID,
			PitcherID:   currentPitcher.ID,
			Result:      atBatResult.Type,
			Runs:        runs,
			Outs:        outs,
			Leverage:    atBatResult.Leverage,
			Timestamp:   time.Now(),
		}

		// Add to high leverage events if significant
		if atBatResult.Leverage > 1.5 && (runs > 0 || atBatResult.Type == "home_run") {
			events = append(events, event)
		}

		// Update game state
		gameState.Outs += outs
		gameState.AddRuns(runs)

		// Advance batter in lineup
		*batterIndex = (*batterIndex + 1) % len(currentLineup)

		// Check if inning is over
		if gameState.IsInningOver() {
			gameState.AdvanceInning()
		}

		// Reset count for next at-bat
		gameState.Count = models.Count{Balls: 0, Strikes: 0}
	}

	// Determine winner
	winner := "tie"
	if gameState.HomeScore > gameState.AwayScore {
		winner = "home"
	} else if gameState.AwayScore > gameState.HomeScore {
		winner = "away"
	}

	// Calculate game duration (rough estimate)
	baseDuration := 150 + rand.Intn(60) // 150-210 minutes
	if gameState.Inning > 9 {
		baseDuration += (gameState.Inning - 9) * 20 // Extra innings
	}

	gameState.IsComplete = true
	gameState.WinnerTeam = winner

	// Calculate derived stats for all players
	for _, stats := range batterStats {
		se.calculateDerivedBattingStats(stats)
	}
	for _, stats := range pitcherStats {
		se.calculateDerivedPitchingStats(stats)
	}

	// Build player stats by team
	homeBatting := make(map[string]*models.PlayerGameBatting)
	awayBatting := make(map[string]*models.PlayerGameBatting)
	for _, player := range homeLineup {
		if stats, ok := batterStats[player.ID]; ok {
			homeBatting[player.ID] = se.convertToGameBatting(stats)
		}
	}
	for _, player := range awayLineup {
		if stats, ok := batterStats[player.ID]; ok {
			awayBatting[player.ID] = se.convertToGameBatting(stats)
		}
	}

	homePitching := make(map[string]*models.PlayerGamePitching)
	awayPitching := make(map[string]*models.PlayerGamePitching)
	if stats, ok := pitcherStats[homePitcher.ID]; ok {
		homePitching[homePitcher.ID] = se.convertToGamePitching(stats)
	}
	if stats, ok := pitcherStats[awayPitcher.ID]; ok {
		awayPitching[awayPitcher.ID] = se.convertToGamePitching(stats)
	}

	return models.SimulationResult{
		RunID:            runID,
		SimulationNumber: simNumber,
		HomeScore:        gameState.HomeScore,
		AwayScore:        gameState.AwayScore,
		Winner:           winner,
		TotalPitches:     pitchCount,
		GameDuration:     baseDuration,
		KeyEvents:        events,
		FinalState:       *gameState,
		CreatedAt:        time.Now(),
		PlayerStats: &models.GamePlayerStats{
			HomeBatting:  homeBatting,
			AwayBatting:  awayBatting,
			HomePitching: homePitching,
			AwayPitching: awayPitching,
		},
	}
}

// simulateAtBat simulates a single plate appearance (legacy compatibility)
func (se *SimulationEngine) simulateAtBat(batter, pitcher *models.Player, gameState *models.GameState) models.AtBatResult {
	// Use the player model's simulation method
	return batter.SimulateAtBat(pitcher, gameState, gameState.Weather)
}

// simulateAtBatWithContext simulates a plate appearance with full game context
func (se *SimulationEngine) simulateAtBatWithContext(batter, pitcher *models.Player, gameState *models.GameState, gameData *GameData) models.AtBatResult {
	// Apply altitude effect to home run probability
	altitude := gameData.Stadium.Altitude
	if altitude > 1000 {
		altitudeEffect := models.GetAltitudeEffect(altitude)
		// Altitude effect is applied within the hit simulation
		_ = altitudeEffect
	}

	// Call player's at-bat simulation with full context
	return batter.SimulateAtBatWithContext(
		pitcher,
		gameState,
		gameState.Weather,
		&gameData.Umpire.Tendencies,
		&gameData.Stadium.ParkFactors,
		&gameData.Stadium.Dimensions,
	)
}

// convertToWeatherStadiumInfo converts stadium data to weather service format
func (se *SimulationEngine) convertToWeatherStadiumInfo(stadium StadiumData) weather.StadiumInfo {
	return weather.StadiumInfo{
		Name:      stadium.Name,
		Location:  stadium.Location,
		Latitude:  stadium.Latitude,
		Longitude: stadium.Longitude,
		RoofType:  stadium.RoofType,
		Altitude:  stadium.Altitude,
	}
}

// processAtBatResult updates the game state based on the at-bat outcome
func (se *SimulationEngine) processAtBatResult(gameState *models.GameState, result models.AtBatResult) (runs, outs int) {
	switch result.Type {
	case "single":
		return se.processSingle(gameState)
	case "double":
		return se.processDouble(gameState)
	case "triple":
		return se.processTriple(gameState)
	case "home_run":
		return se.processHomeRun(gameState)
	case "walk", "hit_by_pitch":
		return se.processWalk(gameState)
	case "strikeout", "out":
		return 0, 1
	default:
		return 0, 1
	}
}

// processSingle handles a single hit
func (se *SimulationEngine) processSingle(gameState *models.GameState) (runs, outs int) {
	runs = 0

	// Third base scores
	if gameState.Bases.Third != nil {
		runs++
		gameState.Bases.Third = nil
	}

	// Second base scores (usually)
	if gameState.Bases.Second != nil {
		if rand.Float64() < 0.85 { // 85% chance to score from second
			runs++
			gameState.Bases.Second = nil
		} else {
			gameState.Bases.Third = gameState.Bases.Second
			gameState.Bases.Second = nil
		}
	}

	// First base to second (usually) or third
	if gameState.Bases.First != nil {
		if rand.Float64() < 0.15 { // 15% chance to go to third on single
			gameState.Bases.Third = gameState.Bases.First
		} else {
			gameState.Bases.Second = gameState.Bases.First
		}
		gameState.Bases.First = nil
	}

	// Batter goes to first
	gameState.Bases.First = &models.BaseRunner{
		PlayerID: gameState.CurrentAB.BatterID,
		Name:     gameState.CurrentAB.BatterName,
		Speed:    50.0, // Default speed
	}

	return runs, 0
}

// processDouble handles a double hit
func (se *SimulationEngine) processDouble(gameState *models.GameState) (runs, outs int) {
	runs = 0

	// Third and second base score
	if gameState.Bases.Third != nil {
		runs++
		gameState.Bases.Third = nil
	}
	if gameState.Bases.Second != nil {
		runs++
		gameState.Bases.Second = nil
	}

	// First base usually scores
	if gameState.Bases.First != nil {
		if rand.Float64() < 0.75 { // 75% chance to score from first on double
			runs++
		} else {
			gameState.Bases.Third = gameState.Bases.First
		}
		gameState.Bases.First = nil
	}

	// Batter goes to second
	gameState.Bases.Second = &models.BaseRunner{
		PlayerID: gameState.CurrentAB.BatterID,
		Name:     gameState.CurrentAB.BatterName,
		Speed:    50.0,
	}

	return runs, 0
}

// processTriple handles a triple hit
func (se *SimulationEngine) processTriple(gameState *models.GameState) (runs, outs int) {
	runs = 0

	// All runners score
	if gameState.Bases.Third != nil {
		runs++
		gameState.Bases.Third = nil
	}
	if gameState.Bases.Second != nil {
		runs++
		gameState.Bases.Second = nil
	}
	if gameState.Bases.First != nil {
		runs++
		gameState.Bases.First = nil
	}

	// Batter goes to third
	gameState.Bases.Third = &models.BaseRunner{
		PlayerID: gameState.CurrentAB.BatterID,
		Name:     gameState.CurrentAB.BatterName,
		Speed:    50.0,
	}

	return runs, 0
}

// processHomeRun handles a home run
func (se *SimulationEngine) processHomeRun(gameState *models.GameState) (runs, outs int) {
	runs = 1 // Batter scores

	// All runners score
	if gameState.Bases.Third != nil {
		runs++
		gameState.Bases.Third = nil
	}
	if gameState.Bases.Second != nil {
		runs++
		gameState.Bases.Second = nil
	}
	if gameState.Bases.First != nil {
		runs++
		gameState.Bases.First = nil
	}

	return runs, 0
}

// processWalk handles a walk or hit by pitch
func (se *SimulationEngine) processWalk(gameState *models.GameState) (runs, outs int) {
	runs = 0

	// Force runners if bases are loaded
	if gameState.Bases.First != nil && gameState.Bases.Second != nil && gameState.Bases.Third != nil {
		runs++ // Force runner home from third
		gameState.Bases.Third = gameState.Bases.Second
		gameState.Bases.Second = gameState.Bases.First
	} else if gameState.Bases.First != nil && gameState.Bases.Second != nil {
		// Force runner to third
		gameState.Bases.Third = gameState.Bases.Second
		gameState.Bases.Second = gameState.Bases.First
	} else if gameState.Bases.First != nil {
		// Force runner to second
		gameState.Bases.Second = gameState.Bases.First
	}

	// Batter goes to first
	gameState.Bases.First = &models.BaseRunner{
		PlayerID: gameState.CurrentAB.BatterID,
		Name:     gameState.CurrentAB.BatterName,
		Speed:    50.0,
	}

	return runs, 0
}

// GameData represents the basic game information needed for simulation
type GameData struct {
	GameID       string
	HomeTeamID   string
	AwayTeamID   string
	Weather      models.Weather
	Date         time.Time
	GameTime     time.Time
	Stadium      StadiumData
	Umpire       UmpireData
}

// StadiumData contains stadium information for simulation
type StadiumData struct {
	ID           string
	Name         string
	Location     string
	Latitude     float64
	Longitude    float64
	RoofType     string
	Altitude     int
	Surface      string
	Dimensions   models.StadiumDimensions
	ParkFactors  models.ParkFactors
}

// UmpireData contains umpire information and tendencies
type UmpireData struct {
	ID         string
	Name       string
	Tendencies models.UmpireTendencies
}

// updateBatterStats updates batting statistics based on at-bat result
func (se *SimulationEngine) updateBatterStats(stats *models.PlayerBattingStats, result models.AtBatResult, runsScored int) {
	stats.PA++ // Every at-bat is a plate appearance

	switch result.Type {
	case "single":
		stats.AB++
		stats.H++
		stats.Singles++
		stats.RBI += float64(runsScored)
	case "double":
		stats.AB++
		stats.H++
		stats.Doubles++
		stats.RBI += float64(runsScored)
	case "triple":
		stats.AB++
		stats.H++
		stats.Triples++
		stats.RBI += float64(runsScored)
	case "home_run":
		stats.AB++
		stats.H++
		stats.HR++
		stats.RBI += float64(runsScored)
		stats.R++ // Batter scores on home run
	case "walk", "hit_by_pitch":
		// Walks don't count as at-bats
		stats.BB++
	case "strikeout":
		stats.AB++
		stats.K++
	case "out":
		stats.AB++
	}
}

// updatePitcherStats updates pitching statistics based on at-bat result
func (se *SimulationEngine) updatePitcherStats(stats *models.PlayerPitchingStats, result models.AtBatResult, runsAllowed int, pitches int) {
	stats.Pitches += float64(pitches)

	switch result.Type {
	case "single", "double", "triple", "home_run":
		stats.H++
		if result.Type == "home_run" {
			stats.HR++
		}
	case "walk", "hit_by_pitch":
		stats.BB++
	case "strikeout", "out":
		// Recorded an out - increment IP by 1/3
		stats.IP += 1.0 / 3.0
		if result.Type == "strikeout" {
			stats.K++
		}
	}

	// Track runs allowed (these are assumed to be earned)
	stats.R += float64(runsAllowed)
	stats.ER += float64(runsAllowed)
}

// calculateDerivedBattingStats calculates AVG, OBP, SLG from counting stats
func (se *SimulationEngine) calculateDerivedBattingStats(stats *models.PlayerBattingStats) {
	if stats.AB > 0 {
		stats.AVG = stats.H / stats.AB

		// Calculate total bases for SLG
		totalBases := stats.Singles + (stats.Doubles * 2) + (stats.Triples * 3) + (stats.HR * 4)
		stats.SLG = totalBases / stats.AB
	}

	if stats.PA > 0 {
		// OBP = (H + BB) / PA
		stats.OBP = (stats.H + stats.BB) / stats.PA
	}
}

// calculateDerivedPitchingStats calculates ERA and WHIP from counting stats
func (se *SimulationEngine) calculateDerivedPitchingStats(stats *models.PlayerPitchingStats) {
	if stats.IP > 0 {
		// ERA = (ER * 9) / IP
		stats.ERA = (stats.ER * 9) / stats.IP

		// WHIP = (H + BB) / IP
		stats.WHIP = (stats.H + stats.BB) / stats.IP
	}
}

// convertToGameBatting converts PlayerBattingStats to PlayerGameBatting (integer counts)
func (se *SimulationEngine) convertToGameBatting(stats *models.PlayerBattingStats) *models.PlayerGameBatting {
	return &models.PlayerGameBatting{
		PlayerID: stats.PlayerID,
		PA:       int(stats.PA),
		AB:       int(stats.AB),
		H:        int(stats.H),
		Singles:  int(stats.Singles),
		Doubles:  int(stats.Doubles),
		Triples:  int(stats.Triples),
		HR:       int(stats.HR),
		RBI:      int(stats.RBI),
		R:        int(stats.R),
		BB:       int(stats.BB),
		K:        int(stats.K),
	}
}

// convertToGamePitching converts PlayerPitchingStats to PlayerGamePitching (integer counts)
func (se *SimulationEngine) convertToGamePitching(stats *models.PlayerPitchingStats) *models.PlayerGamePitching {
	return &models.PlayerGamePitching{
		PlayerID: stats.PlayerID,
		Outs:     int(stats.IP * 3), // Convert IP to outs
		H:        int(stats.H),
		R:        int(stats.R),
		ER:       int(stats.ER),
		BB:       int(stats.BB),
		K:        int(stats.K),
		HR:       int(stats.HR),
		Pitches:  int(stats.Pitches),
	}
}

// Helper functions for simulation setup and management would go here
// (loadGameData, loadTeamRosters, createLineup, etc.)
// Implementation continues in next part...

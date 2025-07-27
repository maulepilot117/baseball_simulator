package simulation

import (
	"context"
	"log"
	"math/rand"
	"sync"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
	"sim-engine/models"
)

// SimulationEngine handles baseball game simulations
type SimulationEngine struct {
	db             *pgxpool.Pool
	workers        int
	simulationRuns int
	mu             sync.RWMutex
	activeRuns     map[string]*RunStatus
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
	}
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

	var events []models.GameEvent
	pitchCount := 0
	homeBatterIndex := 0
	awayBatterIndex := 0

	// Get starting pitchers
	homePitcher := se.getStartingPitcher(homeRoster)
	awayPitcher := se.getStartingPitcher(awayRoster)
	currentPitcher := awayPitcher // Away team pitches first

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

		// Simulate at-bat
		atBatResult := se.simulateAtBat(currentBatter, currentPitcher, gameState)
		pitchCount += rand.Intn(6) + 3 // 3-8 pitches per at-bat

		// Process at-bat result
		runs, outs := se.processAtBatResult(gameState, atBatResult)

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
	}
}

// simulateAtBat simulates a single plate appearance
func (se *SimulationEngine) simulateAtBat(batter, pitcher *models.Player, gameState *models.GameState) models.AtBatResult {
	// Use the player model's simulation method
	return batter.SimulateAtBat(pitcher, gameState, gameState.Weather)
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
	GameID     string
	HomeTeamID string
	AwayTeamID string
	Weather    models.Weather
	Date       time.Time
	Stadium    string
}

// Helper functions for simulation setup and management would go here
// (loadGameData, loadTeamRosters, createLineup, etc.)
// Implementation continues in next part...

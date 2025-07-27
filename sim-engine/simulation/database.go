package simulation

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"time"

	"sim-engine/models"
)

// updateRunStatus updates the simulation run status in the database
func (se *SimulationEngine) updateRunStatus(runID, status string) {
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	query := `
		UPDATE simulation_runs 
		SET status = $2, updated_at = NOW()
		WHERE id = $1
	`

	if _, err := se.db.Exec(ctx, query, runID, status); err != nil {
		log.Printf("Failed to update run status for %s: %v", runID, err)
	}
}

// updateProgress updates the completed runs count
func (se *SimulationEngine) updateProgress(runID string) {
	se.mu.Lock()
	defer se.mu.Unlock()

	if status, exists := se.activeRuns[runID]; exists {
		status.CompletedRuns++

		// Update database every 100 completed runs or when done
		if status.CompletedRuns%100 == 0 || status.CompletedRuns == status.TotalRuns {
			go func() {
				ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
				defer cancel()

				query := `
					UPDATE simulation_runs 
					SET completed_runs = $2, updated_at = NOW()
					WHERE id = $1
				`

				if _, err := se.db.Exec(ctx, query, runID, status.CompletedRuns); err != nil {
					log.Printf("Failed to update progress for %s: %v", runID, err)
				}
			}()
		}
	}
}

// storeSimulationResult stores an individual simulation result
func (se *SimulationEngine) storeSimulationResult(ctx context.Context, result models.SimulationResult) error {
	keyEventsJSON, err := json.Marshal(result.KeyEvents)
	if err != nil {
		return fmt.Errorf("failed to marshal key events: %w", err)
	}

	finalStateJSON, err := json.Marshal(result.FinalState)
	if err != nil {
		return fmt.Errorf("failed to marshal final state: %w", err)
	}

	query := `
		INSERT INTO simulation_results (
			id, run_id, simulation_number, home_score, away_score, 
			total_pitches, game_duration_minutes, key_events, 
			final_state, created_at
		) VALUES (
			uuid_generate_v4(), $1, $2, $3, $4, $5, $6, $7, $8, $9
		)
	`

	_, err = se.db.Exec(ctx, query,
		result.RunID,
		result.SimulationNumber,
		result.HomeScore,
		result.AwayScore,
		result.TotalPitches,
		result.GameDuration,
		keyEventsJSON,
		finalStateJSON,
		result.CreatedAt,
	)

	if err != nil {
		return fmt.Errorf("failed to store simulation result: %w", err)
	}

	return nil
}

// storeAggregatedResults stores the aggregated simulation results
func (se *SimulationEngine) storeAggregatedResults(ctx context.Context, result *models.AggregatedResult) error {
	homeScoreDistJSON, err := json.Marshal(result.HomeScoreDistribution)
	if err != nil {
		return fmt.Errorf("failed to marshal home score distribution: %w", err)
	}

	awayScoreDistJSON, err := json.Marshal(result.AwayScoreDistribution)
	if err != nil {
		return fmt.Errorf("failed to marshal away score distribution: %w", err)
	}

	highLeverageEventsJSON, err := json.Marshal(result.HighLeverageEvents)
	if err != nil {
		return fmt.Errorf("failed to marshal high leverage events: %w", err)
	}

	statisticsJSON, err := json.Marshal(result.Statistics)
	if err != nil {
		return fmt.Errorf("failed to marshal statistics: %w", err)
	}

	query := `
		INSERT INTO simulation_aggregates (
			id, run_id, home_win_probability, away_win_probability,
			expected_home_score, expected_away_score, 
			home_score_distribution, away_score_distribution,
			total_score_over_under, created_at
		) VALUES (
			uuid_generate_v4(), $1, $2, $3, $4, $5, $6, $7, $8, NOW()
		)
		ON CONFLICT (run_id) DO UPDATE SET
			home_win_probability = EXCLUDED.home_win_probability,
			away_win_probability = EXCLUDED.away_win_probability,
			expected_home_score = EXCLUDED.expected_home_score,
			expected_away_score = EXCLUDED.expected_away_score,
			home_score_distribution = EXCLUDED.home_score_distribution,
			away_score_distribution = EXCLUDED.away_score_distribution,
			total_score_over_under = EXCLUDED.total_score_over_under
	`

	// Calculate total score over/under probabilities
	totalScoreOverUnder := make(map[string]interface{})
	totalScoreOverUnder["average"] = result.ExpectedHomeScore + result.ExpectedAwayScore
	totalScoreOverUnder["over_8_5"] = se.calculateOverUnderProbability(result, 8.5)
	totalScoreOverUnder["over_9_5"] = se.calculateOverUnderProbability(result, 9.5)
	totalScoreOverUnder["over_10_5"] = se.calculateOverUnderProbability(result, 10.5)

	totalScoreOverUnderJSON, _ := json.Marshal(totalScoreOverUnder)

	_, err = se.db.Exec(ctx, query,
		result.RunID,
		result.HomeWinProbability,
		result.AwayWinProbability,
		result.ExpectedHomeScore,
		result.ExpectedAwayScore,
		homeScoreDistJSON,
		awayScoreDistJSON,
		totalScoreOverUnderJSON,
	)

	if err != nil {
		return fmt.Errorf("failed to store aggregated results: %w", err)
	}

	// Also store additional metadata in a separate table if needed
	return se.storeSimulationMetadata(ctx, result, highLeverageEventsJSON, statisticsJSON)
}

// storeSimulationMetadata stores additional simulation metadata
func (se *SimulationEngine) storeSimulationMetadata(ctx context.Context, result *models.AggregatedResult,
	highLeverageEventsJSON, statisticsJSON []byte) error {

	// Create or update metadata table
	createTableQuery := `
		CREATE TABLE IF NOT EXISTS simulation_metadata (
			run_id UUID PRIMARY KEY REFERENCES simulation_runs(id),
			total_simulations INTEGER,
			home_wins INTEGER,
			away_wins INTEGER,
			ties INTEGER,
			average_game_duration DECIMAL(5,2),
			average_pitches DECIMAL(5,1),
			high_leverage_events JSONB,
			statistics JSONB,
			created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
			updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
		)
	`

	if _, err := se.db.Exec(ctx, createTableQuery); err != nil {
		log.Printf("Warning: failed to create metadata table: %v", err)
	}

	metadataQuery := `
		INSERT INTO simulation_metadata (
			run_id, total_simulations, home_wins, away_wins, ties,
			average_game_duration, average_pitches, high_leverage_events, 
			statistics
		) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
		ON CONFLICT (run_id) DO UPDATE SET
			total_simulations = EXCLUDED.total_simulations,
			home_wins = EXCLUDED.home_wins,
			away_wins = EXCLUDED.away_wins,
			ties = EXCLUDED.ties,
			average_game_duration = EXCLUDED.average_game_duration,
			average_pitches = EXCLUDED.average_pitches,
			high_leverage_events = EXCLUDED.high_leverage_events,
			statistics = EXCLUDED.statistics,
			updated_at = NOW()
	`

	_, err := se.db.Exec(ctx, metadataQuery,
		result.RunID,
		result.TotalSimulations,
		result.HomeWins,
		result.AwayWins,
		result.Ties,
		result.AverageGameDuration,
		result.AveragePitches,
		highLeverageEventsJSON,
		statisticsJSON,
	)

	return err
}

// calculateAggregatedResults processes all simulation results into aggregated statistics
func (se *SimulationEngine) calculateAggregatedResults(runID string, results []models.SimulationResult) *models.AggregatedResult {
	if len(results) == 0 {
		return &models.AggregatedResult{RunID: runID}
	}

	aggregated := &models.AggregatedResult{
		RunID:                 runID,
		TotalSimulations:      len(results),
		HomeScoreDistribution: make(map[int]int),
		AwayScoreDistribution: make(map[int]int),
		Statistics:            make(map[string]float64),
	}

	var totalHomeScore, totalAwayScore float64
	var totalDuration, totalPitches float64
	var allHighLeverageEvents []models.GameEvent

	// Process each result
	for _, result := range results {
		// Count wins
		switch result.Winner {
		case "home":
			aggregated.HomeWins++
		case "away":
			aggregated.AwayWins++
		case "tie":
			aggregated.Ties++
		}

		// Score distributions
		aggregated.HomeScoreDistribution[result.HomeScore]++
		aggregated.AwayScoreDistribution[result.AwayScore]++

		// Running totals
		totalHomeScore += float64(result.HomeScore)
		totalAwayScore += float64(result.AwayScore)
		totalDuration += float64(result.GameDuration)
		totalPitches += float64(result.TotalPitches)

		// Collect high leverage events
		for _, event := range result.KeyEvents {
			if event.Leverage > 2.0 { // Very high leverage
				allHighLeverageEvents = append(allHighLeverageEvents, event)
			}
		}
	}

	// Calculate probabilities
	totalSims := float64(aggregated.TotalSimulations)
	aggregated.HomeWinProbability = float64(aggregated.HomeWins) / totalSims
	aggregated.AwayWinProbability = float64(aggregated.AwayWins) / totalSims
	aggregated.TieProbability = float64(aggregated.Ties) / totalSims

	// Calculate averages
	aggregated.ExpectedHomeScore = totalHomeScore / totalSims
	aggregated.ExpectedAwayScore = totalAwayScore / totalSims
	aggregated.AverageGameDuration = totalDuration / totalSims
	aggregated.AveragePitches = totalPitches / totalSims

	// Additional statistics
	aggregated.Statistics["total_runs_average"] = aggregated.ExpectedHomeScore + aggregated.ExpectedAwayScore
	aggregated.Statistics["score_variance"] = se.calculateScoreVariance(results, aggregated.ExpectedHomeScore, aggregated.ExpectedAwayScore)
	aggregated.Statistics["blowout_percentage"] = se.calculateBlowoutPercentage(results)
	aggregated.Statistics["one_run_game_percentage"] = se.calculateOneRunGamePercentage(results)
	aggregated.Statistics["shutout_percentage"] = se.calculateShutoutPercentage(results)
	aggregated.Statistics["high_scoring_percentage"] = se.calculateHighScoringPercentage(results)

	// Limit high leverage events to most significant
	if len(allHighLeverageEvents) > 50 {
		// Sort by leverage and take top 50
		allHighLeverageEvents = se.selectTopLeverageEvents(allHighLeverageEvents, 50)
	}
	aggregated.HighLeverageEvents = allHighLeverageEvents

	return aggregated
}

// calculateOverUnderProbability calculates the probability of the total score going over a threshold
func (se *SimulationEngine) calculateOverUnderProbability(result *models.AggregatedResult, threshold float64) float64 {
	overCount := 0
	totalCount := 0

	for homeScore, homeCount := range result.HomeScoreDistribution {
		for awayScore, awayCount := range result.AwayScoreDistribution {
			totalScore := float64(homeScore + awayScore)
			if totalScore > threshold {
				overCount += homeCount * awayCount
			}
			totalCount += homeCount * awayCount
		}
	}

	if totalCount == 0 {
		return 0.0
	}

	return float64(overCount) / float64(totalCount)
}

// calculateScoreVariance calculates the variance in total scoring
func (se *SimulationEngine) calculateScoreVariance(results []models.SimulationResult, expectedHome, expectedAway float64) float64 {
	expectedTotal := expectedHome + expectedAway
	var sumSquaredDiffs float64

	for _, result := range results {
		totalScore := float64(result.HomeScore + result.AwayScore)
		diff := totalScore - expectedTotal
		sumSquaredDiffs += diff * diff
	}

	return sumSquaredDiffs / float64(len(results))
}

// calculateBlowoutPercentage calculates percentage of games with margin ≥ 7 runs
func (se *SimulationEngine) calculateBlowoutPercentage(results []models.SimulationResult) float64 {
	blowouts := 0
	for _, result := range results {
		margin := result.HomeScore - result.AwayScore
		if margin < 0 {
			margin = -margin
		}
		if margin >= 7 {
			blowouts++
		}
	}
	return float64(blowouts) / float64(len(results)) * 100.0
}

// calculateOneRunGamePercentage calculates percentage of one-run games
func (se *SimulationEngine) calculateOneRunGamePercentage(results []models.SimulationResult) float64 {
	oneRunGames := 0
	for _, result := range results {
		margin := result.HomeScore - result.AwayScore
		if margin < 0 {
			margin = -margin
		}
		if margin == 1 {
			oneRunGames++
		}
	}
	return float64(oneRunGames) / float64(len(results)) * 100.0
}

// calculateShutoutPercentage calculates percentage of shutout games
func (se *SimulationEngine) calculateShutoutPercentage(results []models.SimulationResult) float64 {
	shutouts := 0
	for _, result := range results {
		if result.HomeScore == 0 || result.AwayScore == 0 {
			shutouts++
		}
	}
	return float64(shutouts) / float64(len(results)) * 100.0
}

// calculateHighScoringPercentage calculates percentage of high-scoring games (total ≥ 12 runs)
func (se *SimulationEngine) calculateHighScoringPercentage(results []models.SimulationResult) float64 {
	highScoring := 0
	for _, result := range results {
		totalRuns := result.HomeScore + result.AwayScore
		if totalRuns >= 12 {
			highScoring++
		}
	}
	return float64(highScoring) / float64(len(results)) * 100.0
}

// selectTopLeverageEvents selects the highest leverage events
func (se *SimulationEngine) selectTopLeverageEvents(events []models.GameEvent, limit int) []models.GameEvent {
	if len(events) <= limit {
		return events
	}

	// Sort by leverage (descending)
	for i := 0; i < len(events)-1; i++ {
		for j := i + 1; j < len(events); j++ {
			if events[i].Leverage < events[j].Leverage {
				events[i], events[j] = events[j], events[i]
			}
		}
	}

	return events[:limit]
}

// GetRunStatus returns the current status of a simulation run
func (se *SimulationEngine) GetRunStatus(runID string) (*RunStatus, bool) {
	se.mu.RLock()
	defer se.mu.RUnlock()

	status, exists := se.activeRuns[runID]
	return status, exists
}

// GetRunResult returns the completed result of a simulation run
func (se *SimulationEngine) GetRunResult(ctx context.Context, runID string) (*models.AggregatedResult, error) {
	// First check if it's in memory
	se.mu.RLock()
	if status, exists := se.activeRuns[runID]; exists && status.AggregatedResult != nil {
		se.mu.RUnlock()
		return status.AggregatedResult, nil
	}
	se.mu.RUnlock()

	// Load from database
	var result models.AggregatedResult
	var homeScoreDist, awayScoreDist, totalScoreOverUnder []byte

	query := `
		SELECT sa.run_id, sa.home_win_probability, sa.away_win_probability,
		       sa.expected_home_score, sa.expected_away_score,
		       sa.home_score_distribution, sa.away_score_distribution,
		       sa.total_score_over_under,
		       COALESCE(sm.total_simulations, 0) as total_simulations,
		       COALESCE(sm.home_wins, 0) as home_wins,
		       COALESCE(sm.away_wins, 0) as away_wins,
		       COALESCE(sm.ties, 0) as ties,
		       COALESCE(sm.average_game_duration, 0) as average_game_duration,
		       COALESCE(sm.average_pitches, 0) as average_pitches,
		       COALESCE(sm.high_leverage_events, '[]'::jsonb) as high_leverage_events,
		       COALESCE(sm.statistics, '{}'::jsonb) as statistics
		FROM simulation_aggregates sa
		LEFT JOIN simulation_metadata sm ON sa.run_id = sm.run_id
		WHERE sa.run_id = $1
	`

	var highLeverageEventsJSON, statisticsJSON []byte

	err := se.db.QueryRow(ctx, query, runID).Scan(
		&result.RunID,
		&result.HomeWinProbability,
		&result.AwayWinProbability,
		&result.ExpectedHomeScore,
		&result.ExpectedAwayScore,
		&homeScoreDist,
		&awayScoreDist,
		&totalScoreOverUnder,
		&result.TotalSimulations,
		&result.HomeWins,
		&result.AwayWins,
		&result.Ties,
		&result.AverageGameDuration,
		&result.AveragePitches,
		&highLeverageEventsJSON,
		&statisticsJSON,
	)

	if err != nil {
		return nil, fmt.Errorf("failed to load simulation result: %w", err)
	}

	// Parse JSON fields
	if err := json.Unmarshal(homeScoreDist, &result.HomeScoreDistribution); err != nil {
		log.Printf("Failed to parse home score distribution: %v", err)
		result.HomeScoreDistribution = make(map[int]int)
	}

	if err := json.Unmarshal(awayScoreDist, &result.AwayScoreDistribution); err != nil {
		log.Printf("Failed to parse away score distribution: %v", err)
		result.AwayScoreDistribution = make(map[int]int)
	}

	if err := json.Unmarshal(highLeverageEventsJSON, &result.HighLeverageEvents); err != nil {
		log.Printf("Failed to parse high leverage events: %v", err)
		result.HighLeverageEvents = []models.GameEvent{}
	}

	if err := json.Unmarshal(statisticsJSON, &result.Statistics); err != nil {
		log.Printf("Failed to parse statistics: %v", err)
		result.Statistics = make(map[string]float64)
	}

	// Calculate tie probability
	result.TieProbability = 1.0 - result.HomeWinProbability - result.AwayWinProbability

	return &result, nil
}

// CleanupOldRuns removes old simulation runs from memory
func (se *SimulationEngine) CleanupOldRuns() {
	se.mu.Lock()
	defer se.mu.Unlock()

	cutoff := time.Now().Add(-24 * time.Hour) // Keep for 24 hours

	for runID, status := range se.activeRuns {
		if status.StartTime.Before(cutoff) {
			delete(se.activeRuns, runID)
		}
	}
}

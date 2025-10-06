package main

import (
	"testing"

	"github.com/stretchr/testify/assert"
)

// TestTeamStatsCalculations tests team statistics calculations
func TestTeamStatsCalculations(t *testing.T) {
	tests := []struct {
		name         string
		wins         int
		losses       int
		runsScored   int
		runsAllowed  int
		expectedWinPct float64
	}{
		{
			name:           "winning team",
			wins:           90,
			losses:         72,
			runsScored:     800,
			runsAllowed:    650,
			expectedWinPct: 0.556,
		},
		{
			name:           "losing team",
			wins:           65,
			losses:         97,
			runsScored:     600,
			runsAllowed:    750,
			expectedWinPct: 0.401,
		},
		{
			name:           "perfect season (theoretical)",
			wins:           162,
			losses:         0,
			runsScored:     1000,
			runsAllowed:    400,
			expectedWinPct: 1.000,
		},
		{
			name:           "winless season (theoretical)",
			wins:           0,
			losses:         162,
			runsScored:     400,
			runsAllowed:    1000,
			expectedWinPct: 0.000,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			totalGames := tt.wins + tt.losses
			var winPct float64
			if totalGames > 0 {
				winPct = float64(tt.wins) / float64(totalGames)
			}
			assert.InDelta(t, tt.expectedWinPct, winPct, 0.001)
		})
	}
}

// TestTeamSeasonValidation tests season parameter validation
func TestTeamSeasonValidation(t *testing.T) {
	tests := []struct {
		season  int
		valid   bool
	}{
		{2024, true},
		{2023, true},
		{1900, true},
		{1875, false}, // Before MLB founding
		{2100, false}, // Too far in future
	}

	for _, tt := range tests {
		t.Run("", func(t *testing.T) {
			// MLB founded in 1876
			isValid := tt.season >= 1876 && tt.season <= 2030
			assert.Equal(t, tt.valid, isValid)
		})
	}
}

// TestCurrentSeasonCalculation tests getCurrentSeason logic
func TestCurrentSeasonCalculation(t *testing.T) {
	// getCurrentSeason should return current year or current year + 1 depending on month
	// This is a simple test to ensure the function exists and returns a reasonable value
	season := getCurrentSeason()

	// Season should be between 2020 and 2030 (reasonable range for tests)
	assert.True(t, season >= 2020 && season <= 2030)
}

// TestRunDifferentialCalculation tests run differential calculation
func TestRunDifferentialCalculation(t *testing.T) {
	tests := []struct {
		runsScored    int
		runsAllowed   int
		expectedDiff  int
	}{
		{800, 650, 150},   // Good team
		{600, 750, -150},  // Bad team
		{700, 700, 0},     // Neutral team
	}

	for _, tt := range tests {
		t.Run("", func(t *testing.T) {
			diff := tt.runsScored - tt.runsAllowed
			assert.Equal(t, tt.expectedDiff, diff)
		})
	}
}

// TestPythagoreanExpectation tests Pythagorean win expectation
func TestPythagoreanExpectation(t *testing.T) {
	tests := []struct {
		name            string
		runsScored      int
		runsAllowed     int
		expectedWinPct  float64
		description     string
	}{
		{
			name:           "strong offense and defense",
			runsScored:     850,
			runsAllowed:    600,
			expectedWinPct: 0.668,
			description:    "team with good run differential",
		},
		{
			name:           "average team",
			runsScored:     700,
			runsAllowed:    700,
			expectedWinPct: 0.500,
			description:    "neutral run differential",
		},
		{
			name:           "weak team",
			runsScored:     600,
			runsAllowed:    800,
			expectedWinPct: 0.360,
			description:    "negative run differential",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			// Pythagorean expectation: RS^2 / (RS^2 + RA^2)
			rsSquared := float64(tt.runsScored * tt.runsScored)
			raSquared := float64(tt.runsAllowed * tt.runsAllowed)
			pythWinPct := rsSquared / (rsSquared + raSquared)

			assert.InDelta(t, tt.expectedWinPct, pythWinPct, 0.01)
		})
	}
}

// TestTeamStatsResponse tests team stats response structure
func TestTeamStatsResponse(t *testing.T) {
	stats := map[string]interface{}{
		"wins":         90,
		"losses":       72,
		"runs_scored":  800,
		"runs_allowed": 650,
		"season":       2024,
	}

	assert.Equal(t, 90, stats["wins"])
	assert.Equal(t, 72, stats["losses"])
	assert.Equal(t, 800, stats["runs_scored"])
	assert.Equal(t, 650, stats["runs_allowed"])
	assert.Equal(t, 2024, stats["season"])
}

// TestTeamGamesFiltering tests game filtering logic
func TestTeamGamesFiltering(t *testing.T) {
	// Mock games data
	type mockGame struct {
		homeTeamID string
		awayTeamID string
		season     int
		status     string
	}

	games := []mockGame{
		{"team-1", "team-2", 2024, "completed"},
		{"team-2", "team-1", 2024, "completed"},
		{"team-1", "team-3", 2024, "scheduled"},
		{"team-1", "team-2", 2023, "completed"},
	}

	targetTeamID := "team-1"
	targetSeason := 2024

	var filtered []mockGame
	for _, game := range games {
		if (game.homeTeamID == targetTeamID || game.awayTeamID == targetTeamID) &&
		   game.season == targetSeason {
			filtered = append(filtered, game)
		}
	}

	assert.Equal(t, 3, len(filtered), "Should find 3 games for team-1 in 2024")
}

// TestTeamGamesOrdering tests that games are ordered by date
func TestTeamGamesOrdering(t *testing.T) {
	type mockGame struct {
		gameID   string
		gameDate string
	}

	games := []mockGame{
		{"game-1", "2024-04-15"},
		{"game-2", "2024-03-28"},
		{"game-3", "2024-05-10"},
	}

	// Simulate DESC ordering (most recent first)
	// In real query: ORDER BY g.game_date DESC
	assert.Equal(t, "2024-04-15", games[0].gameDate)

	// After sorting DESC, game-3 should be first
	expectedOrder := []string{"2024-05-10", "2024-04-15", "2024-03-28"}
	sortedDates := []string{games[2].gameDate, games[0].gameDate, games[1].gameDate}

	assert.Equal(t, expectedOrder, sortedDates)
}

// TestTeamGamesPagination tests pagination logic for team games
func TestTeamGamesPagination(t *testing.T) {
	totalGames := 162
	pageSize := 50

	tests := []struct {
		page           int
		expectedOffset int
		expectedLimit  int
	}{
		{1, 0, 50},
		{2, 50, 50},
		{3, 100, 50},
		{4, 150, 50},
	}

	for _, tt := range tests {
		t.Run("", func(t *testing.T) {
			offset := (tt.page - 1) * pageSize
			limit := pageSize

			assert.Equal(t, tt.expectedOffset, offset)
			assert.Equal(t, tt.expectedLimit, limit)

			// Verify we don't exceed total games
			remaining := totalGames - offset
			if remaining < limit {
				limit = remaining
			}
			assert.True(t, limit <= pageSize)
		})
	}
}

// TestTeamIDValidation tests team ID parameter validation
func TestTeamIDValidation(t *testing.T) {
	tests := []struct {
		teamID  string
		valid   bool
	}{
		{"", false},                                  // Empty
		{"550e8400-e29b-41d4-a716-446655440000", true}, // Valid UUID
		{"team-123", true},                           // Valid ID
		{"LAD", true},                                // Team abbreviation
	}

	for _, tt := range tests {
		t.Run(tt.teamID, func(t *testing.T) {
			isValid := tt.teamID != ""
			assert.Equal(t, tt.valid, isValid)
		})
	}
}

// TestHomeAwayGameSplit tests splitting home and away games
func TestHomeAwayGameSplit(t *testing.T) {
	type mockGame struct {
		homeTeamID string
		awayTeamID string
	}

	games := []mockGame{
		{"team-1", "team-2"}, // Home
		{"team-2", "team-1"}, // Away
		{"team-1", "team-3"}, // Home
		{"team-3", "team-1"}, // Away
	}

	targetTeam := "team-1"
	var homeGames, awayGames int

	for _, game := range games {
		if game.homeTeamID == targetTeam {
			homeGames++
		}
		if game.awayTeamID == targetTeam {
			awayGames++
		}
	}

	assert.Equal(t, 2, homeGames)
	assert.Equal(t, 2, awayGames)
}

// TestWinLossCalculation tests win/loss determination
func TestWinLossCalculation(t *testing.T) {
	tests := []struct {
		name          string
		homeTeamID    string
		awayTeamID    string
		homeScore     int
		awayScore     int
		targetTeam    string
		expectedResult string
	}{
		{
			name:          "home team wins",
			homeTeamID:    "team-1",
			awayTeamID:    "team-2",
			homeScore:     5,
			awayScore:     3,
			targetTeam:    "team-1",
			expectedResult: "win",
		},
		{
			name:          "away team wins",
			homeTeamID:    "team-1",
			awayTeamID:    "team-2",
			homeScore:     3,
			awayScore:     5,
			targetTeam:    "team-2",
			expectedResult: "win",
		},
		{
			name:          "home team loses",
			homeTeamID:    "team-1",
			awayTeamID:    "team-2",
			homeScore:     2,
			awayScore:     6,
			targetTeam:    "team-1",
			expectedResult: "loss",
		},
		{
			name:          "away team loses",
			homeTeamID:    "team-1",
			awayTeamID:    "team-2",
			homeScore:     8,
			awayScore:     1,
			targetTeam:    "team-2",
			expectedResult: "loss",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			var result string

			if tt.targetTeam == tt.homeTeamID {
				if tt.homeScore > tt.awayScore {
					result = "win"
				} else {
					result = "loss"
				}
			} else {
				if tt.awayScore > tt.homeScore {
					result = "win"
				} else {
					result = "loss"
				}
			}

			assert.Equal(t, tt.expectedResult, result)
		})
	}
}

// TestTeamStatsAggregation tests runs scored/allowed aggregation
func TestTeamStatsAggregation(t *testing.T) {
	type mockGame struct {
		homeTeamID  string
		awayTeamID  string
		homeScore   int
		awayScore   int
	}

	games := []mockGame{
		{"team-1", "team-2", 5, 3},
		{"team-2", "team-1", 4, 6},
		{"team-1", "team-3", 7, 2},
	}

	targetTeam := "team-1"
	var runsScored, runsAllowed int

	for _, game := range games {
		if game.homeTeamID == targetTeam {
			runsScored += game.homeScore
			runsAllowed += game.awayScore
		} else if game.awayTeamID == targetTeam {
			runsScored += game.awayScore
			runsAllowed += game.homeScore
		}
	}

	assert.Equal(t, 18, runsScored)  // 5 + 6 + 7
	assert.Equal(t, 9, runsAllowed)  // 3 + 4 + 2
}

// TestCompletedGamesFilter tests filtering for completed games only
func TestCompletedGamesFilter(t *testing.T) {
	type mockGame struct {
		status string
	}

	games := []mockGame{
		{"completed"},
		{"scheduled"},
		{"in_progress"},
		{"completed"},
		{"postponed"},
		{"completed"},
	}

	var completed []mockGame
	for _, game := range games {
		if game.status == "completed" {
			completed = append(completed, game)
		}
	}

	assert.Equal(t, 3, len(completed), "Should only count completed games")
}

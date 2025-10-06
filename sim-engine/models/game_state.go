package models

import (
	"time"
)

// GameState represents the current state of a baseball game
type GameState struct {
	GameID     string    `json:"game_id"`
	RunID      string    `json:"run_id"`
	Inning     int       `json:"inning"`
	InningHalf string    `json:"inning_half"` // "top" or "bottom"
	Outs       int       `json:"outs"`
	HomeScore  int       `json:"home_score"`
	AwayScore  int       `json:"away_score"`
	Bases      BaseState `json:"bases"`
	Count      Count     `json:"count"`
	CurrentAB  AtBat     `json:"current_at_bat"`
	Weather    Weather   `json:"weather"`
	CreatedAt  time.Time `json:"created_at"`
	IsComplete bool      `json:"is_complete"`
	WinnerTeam string    `json:"winner_team,omitempty"`
}

// BaseState represents which bases are occupied
type BaseState struct {
	First  *BaseRunner `json:"first,omitempty"`
	Second *BaseRunner `json:"second,omitempty"`
	Third  *BaseRunner `json:"third,omitempty"`
}

// BaseRunner represents a player on base
type BaseRunner struct {
	PlayerID string  `json:"player_id"`
	Name     string  `json:"name"`
	Speed    float64 `json:"speed"` // 0-100 scale
}

// Count represents balls and strikes
type Count struct {
	Balls   int `json:"balls"`
	Strikes int `json:"strikes"`
}

// AtBat represents the current plate appearance
type AtBat struct {
	BatterID    string  `json:"batter_id"`
	BatterName  string  `json:"batter_name"`
	PitcherID   string  `json:"pitcher_id"`
	PitcherName string  `json:"pitcher_name"`
	BatterHand  string  `json:"batter_hand"`  // "L" or "R"
	PitcherHand string  `json:"pitcher_hand"` // "L" or "R"
	PitchCount  int     `json:"pitch_count"`
	Leverage    float64 `json:"leverage"` // Leverage index
}

// Weather represents game conditions
type Weather struct {
	Temperature int     `json:"temperature"` // Fahrenheit
	WindSpeed   int     `json:"wind_speed"`  // MPH
	WindDir     string  `json:"wind_dir"`    // "in", "out", "left", "right"
	Humidity    int     `json:"humidity"`    // Percentage
	Pressure    float64 `json:"pressure"`    // Inches of mercury
}

// GameEvent represents something that happened in the game
type GameEvent struct {
	Type        string                 `json:"type"`
	Description string                 `json:"description"`
	Inning      int                    `json:"inning"`
	InningHalf  string                 `json:"inning_half"`
	BatterID    string                 `json:"batter_id"`
	PitcherID   string                 `json:"pitcher_id"`
	Result      string                 `json:"result"`
	Bases       map[string]interface{} `json:"bases,omitempty"`
	Runs        int                    `json:"runs,omitempty"`
	RBI         int                    `json:"rbi,omitempty"`
	Outs        int                    `json:"outs,omitempty"`
	Leverage    float64                `json:"leverage"`
	Timestamp   time.Time              `json:"timestamp"`
}

// SimulationResult represents the final result of one simulation
type SimulationResult struct {
	RunID            string      `json:"run_id"`
	SimulationNumber int         `json:"simulation_number"`
	HomeScore        int         `json:"home_score"`
	AwayScore        int         `json:"away_score"`
	Winner           string      `json:"winner"`
	TotalPitches     int         `json:"total_pitches"`
	GameDuration     int         `json:"game_duration_minutes"`
	KeyEvents        []GameEvent `json:"key_events"`
	FinalState       GameState   `json:"final_state"`
	CreatedAt        time.Time   `json:"created_at"`
	PlayerStats      *GamePlayerStats `json:"player_stats,omitempty"`
}

// GamePlayerStats tracks player performance for a single simulated game
type GamePlayerStats struct {
	HomeBatting  map[string]*PlayerGameBatting  `json:"home_batting"`
	AwayBatting  map[string]*PlayerGameBatting  `json:"away_batting"`
	HomePitching map[string]*PlayerGamePitching `json:"home_pitching"`
	AwayPitching map[string]*PlayerGamePitching `json:"away_pitching"`
}

// PlayerGameBatting tracks batting stats for one game
type PlayerGameBatting struct {
	PlayerID string
	PA       int // Plate appearances
	AB       int // At bats
	H        int // Hits
	Singles  int
	Doubles  int
	Triples  int
	HR       int
	RBI      int
	R        int // Runs scored
	BB       int
	K        int
}

// PlayerGamePitching tracks pitching stats for one game
type PlayerGamePitching struct {
	PlayerID    string
	Outs        int // Outs recorded (IP = Outs/3)
	H           int // Hits allowed
	R           int // Runs allowed
	ER          int // Earned runs
	BB          int
	K           int
	HR          int
	Pitches     int
}

// AggregatedResult represents the combined results of all simulations
type AggregatedResult struct {
	RunID                 string             `json:"run_id"`
	TotalSimulations      int                `json:"total_simulations"`
	HomeWins              int                `json:"home_wins"`
	AwayWins              int                `json:"away_wins"`
	Ties                  int                `json:"ties"`
	HomeWinProbability    float64            `json:"home_win_probability"`
	AwayWinProbability    float64            `json:"away_win_probability"`
	TieProbability        float64            `json:"tie_probability"`
	ExpectedHomeScore     float64            `json:"expected_home_score"`
	ExpectedAwayScore     float64            `json:"expected_away_score"`
	HomeScoreDistribution map[int]int        `json:"home_score_distribution"`
	AwayScoreDistribution map[int]int        `json:"away_score_distribution"`
	AverageGameDuration   float64            `json:"average_game_duration"`
	AveragePitches        float64            `json:"average_pitches"`
	HighLeverageEvents    []GameEvent        `json:"high_leverage_events"`
	Statistics            map[string]float64 `json:"statistics"`
	PlayerPerformance     *AggregatedPlayerPerformance `json:"player_performance,omitempty"`
}

// AggregatedPlayerPerformance contains averaged player statistics across all simulations
type AggregatedPlayerPerformance struct {
	HomeTeam TeamPerformance `json:"home_team"`
	AwayTeam TeamPerformance `json:"away_team"`
}

// TeamPerformance contains batting and pitching stats for a team
type TeamPerformance struct {
	TeamID   string                       `json:"team_id"`
	TeamName string                       `json:"team_name"`
	Batting  map[string]PlayerBattingStats `json:"batting"` // keyed by player ID
	Pitching map[string]PlayerPitchingStats `json:"pitching"` // keyed by player ID
}

// PlayerBattingStats represents average batting performance across simulations
type PlayerBattingStats struct {
	PlayerID   string  `json:"player_id"`
	PlayerName string  `json:"player_name"`
	Position   string  `json:"position"`
	PA         float64 `json:"pa"`   // Plate appearances (avg per game)
	AB         float64 `json:"ab"`   // At bats
	H          float64 `json:"h"`    // Hits
	Singles    float64 `json:"1b"`   // Singles
	Doubles    float64 `json:"2b"`   // Doubles
	Triples    float64 `json:"3b"`   // Triples
	HR         float64 `json:"hr"`   // Home runs
	RBI        float64 `json:"rbi"`  // Runs batted in
	R          float64 `json:"r"`    // Runs scored
	BB         float64 `json:"bb"`   // Walks
	K          float64 `json:"k"`    // Strikeouts
	AVG        float64 `json:"avg"`  // Batting average (H/AB)
	OBP        float64 `json:"obp"`  // On-base percentage
	SLG        float64 `json:"slg"`  // Slugging percentage
}

// PlayerPitchingStats represents average pitching performance across simulations
type PlayerPitchingStats struct {
	PlayerID    string  `json:"player_id"`
	PlayerName  string  `json:"player_name"`
	IP          float64 `json:"ip"`   // Innings pitched
	H           float64 `json:"h"`    // Hits allowed
	R           float64 `json:"r"`    // Runs allowed
	ER          float64 `json:"er"`   // Earned runs
	BB          float64 `json:"bb"`   // Walks allowed
	K           float64 `json:"k"`    // Strikeouts
	HR          float64 `json:"hr"`   // Home runs allowed
	Pitches     float64 `json:"pitches"` // Total pitches
	ERA         float64 `json:"era"`  // Earned run average
	WHIP        float64 `json:"whip"` // Walks + Hits per inning pitched
}

// NewGameState creates a new game state for simulation
func NewGameState(gameID, runID string) *GameState {
	return &GameState{
		GameID:     gameID,
		RunID:      runID,
		Inning:     1,
		InningHalf: "top",
		Outs:       0,
		HomeScore:  0,
		AwayScore:  0,
		Bases:      BaseState{},
		Count:      Count{Balls: 0, Strikes: 0},
		CreatedAt:  time.Now(),
		IsComplete: false,
	}
}

// IsInningOver checks if the current half-inning is over
func (gs *GameState) IsInningOver() bool {
	return gs.Outs >= 3
}

// IsGameOver checks if the game has ended
func (gs *GameState) IsGameOver() bool {
	// Game ends after 9 innings if not tied
	if gs.Inning >= 9 && gs.InningHalf == "bottom" {
		if gs.HomeScore != gs.AwayScore {
			return true
		}
		// Or if home team takes the lead in bottom of 9th or later
		if gs.HomeScore > gs.AwayScore {
			return true
		}
	}

	// Extra innings - game ends when inning is complete and not tied
	if gs.Inning > 9 && gs.InningHalf == "bottom" && gs.HomeScore != gs.AwayScore {
		return true
	}

	return false
}

// AdvanceInning moves to the next half-inning or inning
func (gs *GameState) AdvanceInning() {
	gs.Outs = 0
	gs.Count = Count{Balls: 0, Strikes: 0}
	gs.Bases = BaseState{} // Clear bases

	if gs.InningHalf == "top" {
		gs.InningHalf = "bottom"
	} else {
		gs.InningHalf = "top"
		gs.Inning++
	}
}

// AddRuns adds runs to the appropriate team's score
func (gs *GameState) AddRuns(runs int) {
	if gs.InningHalf == "top" {
		gs.AwayScore += runs
	} else {
		gs.HomeScore += runs
	}
}

// GetBaseRunners returns a slice of all base runners
func (bs *BaseState) GetBaseRunners() []*BaseRunner {
	var runners []*BaseRunner
	if bs.First != nil {
		runners = append(runners, bs.First)
	}
	if bs.Second != nil {
		runners = append(runners, bs.Second)
	}
	if bs.Third != nil {
		runners = append(runners, bs.Third)
	}
	return runners
}

// IsEmpty checks if all bases are empty
func (bs *BaseState) IsEmpty() bool {
	return bs.First == nil && bs.Second == nil && bs.Third == nil
}

// GetBaseCount returns the number of runners on base
func (bs *BaseState) GetBaseCount() int {
	count := 0
	if bs.First != nil {
		count++
	}
	if bs.Second != nil {
		count++
	}
	if bs.Third != nil {
		count++
	}
	return count
}

// ClearBases removes all base runners
func (bs *BaseState) ClearBases() {
	bs.First = nil
	bs.Second = nil
	bs.Third = nil
}

// CalculateLeverage calculates the leverage index for the current situation
func (gs *GameState) CalculateLeverage() float64 {
	// Simplified leverage calculation
	// Real leverage index is more complex, considering inning, score differential, runners, outs

	baseLeverage := 1.0

	// Inning multiplier
	if gs.Inning >= 7 {
		baseLeverage += float64(gs.Inning-6) * 0.3
	}

	// Score differential impact
	scoreDiff := abs(gs.HomeScore - gs.AwayScore)
	if scoreDiff <= 3 {
		baseLeverage += (4 - float64(scoreDiff)) * 0.2
	}

	// Runners on base
	runners := gs.Bases.GetBaseCount()
	baseLeverage += float64(runners) * 0.1

	// Out situation
	if gs.Outs == 2 {
		baseLeverage += 0.3
	}

	// Late inning bonus
	if gs.Inning >= 9 {
		baseLeverage += 0.5
	}

	return baseLeverage
}

func abs(x int) int {
	if x < 0 {
		return -x
	}
	return x
}

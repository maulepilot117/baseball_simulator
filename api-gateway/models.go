package main

import (
	"time"
)

// Team represents a baseball team
type Team struct {
	ID           string    `json:"id" db:"id"`
	TeamID       string    `json:"team_id" db:"team_id"`
	Name         string    `json:"name" db:"name"`
	Abbreviation string    `json:"abbreviation" db:"abbreviation"`
	League       string    `json:"league" db:"league"`
	Division     string    `json:"division" db:"division"`
	Stadium      string    `json:"stadium_id,omitempty" db:"stadium_id"`
	CreatedAt    time.Time `json:"created_at" db:"created_at"`
	UpdatedAt    time.Time `json:"updated_at" db:"updated_at"`
}

// Player represents a baseball player
type Player struct {
	ID           string     `json:"id" db:"id"`
	PlayerID     string     `json:"player_id" db:"player_id"`
	FirstName    string     `json:"first_name" db:"first_name"`
	LastName     string     `json:"last_name" db:"last_name"`
	FullName     string     `json:"full_name" db:"full_name"`
	Position     string     `json:"position" db:"position"`
	TeamID       string     `json:"team_id" db:"team_id"`
	JerseyNumber string       `json:"jersey_number,omitempty" db:"jersey_number"`
	Height       string     `json:"height,omitempty" db:"height"`
	Weight       *int       `json:"weight,omitempty" db:"weight"`
	BirthDate    *time.Time `json:"birth_date,omitempty" db:"birth_date"`
	BirthCity    string     `json:"birth_city,omitempty" db:"birth_city"`
	BirthCountry string     `json:"birth_country,omitempty" db:"birth_country"`
	Bats         string     `json:"bats" db:"bats"`
	Throws       string     `json:"throws" db:"throws"`
	DebutDate    *time.Time `json:"debut_date,omitempty" db:"debut_date"`
	Status       string     `json:"status" db:"status"`
	CreatedAt    time.Time  `json:"created_at" db:"created_at"`
	UpdatedAt    time.Time  `json:"updated_at" db:"updated_at"`
}

// PlayerWithTeam represents a player with team information
type PlayerWithTeam struct {
	Player
	Team *Team `json:"team,omitempty"`
}

// Game represents a baseball game
type Game struct {
	ID           string    `json:"id" db:"id"`
	GameID       string    `json:"game_id" db:"game_id"`
	Season       int       `json:"season" db:"season"`
	GameType     string    `json:"game_type" db:"game_type"`
	GameDate     time.Time `json:"game_date" db:"game_date"`
	HomeTeamID   string    `json:"home_team_id" db:"home_team_id"`
	AwayTeamID   string    `json:"away_team_id" db:"away_team_id"`
	HomeScore    *int      `json:"home_score,omitempty" db:"home_score"`
	AwayScore    *int      `json:"away_score,omitempty" db:"away_score"`
	Status       string    `json:"status" db:"status"`
	Inning       *int      `json:"inning,omitempty" db:"inning"`
	InningHalf   string    `json:"inning_half,omitempty" db:"inning_half"`
	StadiumID    string    `json:"stadium_id,omitempty" db:"stadium_id"`
	WeatherData  *string   `json:"weather_data,omitempty" db:"weather_data"`
	Attendance   *int      `json:"attendance,omitempty" db:"attendance"`
	GameDuration *int      `json:"game_duration,omitempty" db:"game_duration"`
	CreatedAt    time.Time `json:"created_at" db:"created_at"`
	UpdatedAt    time.Time `json:"updated_at" db:"updated_at"`
}

// GameWithTeams represents a game with team information
type GameWithTeams struct {
	Game
	HomeTeam *Team    `json:"home_team,omitempty"`
	AwayTeam *Team    `json:"away_team,omitempty"`
	Stadium  *Stadium `json:"stadium,omitempty"`
}

// Stadium represents a baseball stadium
type Stadium struct {
	ID        string    `json:"id" db:"id"`
	Name      string    `json:"name" db:"name"`
	City      string    `json:"city" db:"city"`
	State     string    `json:"state" db:"state"`
	Country   string    `json:"country" db:"country"`
	Capacity  *int      `json:"capacity,omitempty" db:"capacity"`
	Opened    *int      `json:"opened,omitempty" db:"opened"`
	Surface   string    `json:"surface,omitempty" db:"surface"`
	CreatedAt time.Time `json:"created_at" db:"created_at"`
	UpdatedAt time.Time `json:"updated_at" db:"updated_at"`
}

// PlayerStats represents aggregated player statistics
type PlayerStats struct {
	PlayerID        string                 `json:"player_id" db:"player_id"`
	Season          int                    `json:"season" db:"season"`
	StatsType       string                 `json:"stats_type" db:"stats_type"` // batting, pitching, fielding
	AggregatedStats map[string]interface{} `json:"aggregated_stats" db:"aggregated_stats"`
	GamesPlayed     int                    `json:"games_played" db:"games_played"`
	UpdatedAt       time.Time              `json:"updated_at" db:"updated_at"`
}

// SimulationRun represents a simulation run
type SimulationRun struct {
	ID            string                 `json:"id" db:"id"`
	GameID        string                 `json:"game_id" db:"game_id"`
	Status        string                 `json:"status" db:"status"`
	TotalRuns     int                    `json:"total_runs" db:"total_runs"`
	CompletedRuns int                    `json:"completed_runs" db:"completed_runs"`
	Config        map[string]interface{} `json:"config" db:"config"`
	CreatedAt     time.Time              `json:"created_at" db:"created_at"`
	UpdatedAt     time.Time              `json:"updated_at" db:"updated_at"`
	CompletedAt   *time.Time             `json:"completed_at,omitempty" db:"completed_at"`
}

// SimulationResult represents the aggregated results of a simulation
type SimulationResult struct {
	RunID                 string                 `json:"run_id"`
	HomeWinProbability    float64                `json:"home_win_probability"`
	AwayWinProbability    float64                `json:"away_win_probability"`
	ExpectedHomeScore     float64                `json:"expected_home_score"`
	ExpectedAwayScore     float64                `json:"expected_away_score"`
	HomeScoreDistribution map[int]int            `json:"home_score_distribution"`
	AwayScoreDistribution map[int]int            `json:"away_score_distribution"`
	Metadata              map[string]interface{} `json:"metadata"`
}

// DataStatus represents the status of data in the system
type DataStatus struct {
	LastUpdate    time.Time `json:"last_update"`
	TotalTeams    int       `json:"total_teams"`
	TotalPlayers  int       `json:"total_players"`
	TotalGames    int       `json:"total_games"`
	CurrentSeason int       `json:"current_season"`
	Status        string    `json:"status"`
}

// APIError represents an API error response
type APIError struct {
	Error   string                 `json:"error"`
	Code    string                 `json:"code,omitempty"`
	Details map[string]interface{} `json:"details,omitempty"`
}

// PaginatedResponse represents a paginated API response
type PaginatedResponse struct {
	Data       interface{} `json:"data"`
	Total      int         `json:"total"`
	Page       int         `json:"page"`
	PageSize   int         `json:"page_size"`
	TotalPages int         `json:"total_pages"`
}

// QueryParams represents common query parameters
type QueryParams struct {
	Page     int    `json:"page"`
	PageSize int    `json:"page_size"`
	Season   *int   `json:"season,omitempty"`
	Team     string `json:"team,omitempty"`
	Position string `json:"position,omitempty"`
	Status   string `json:"status,omitempty"`
	Date     string `json:"date,omitempty"`
	Sort     string `json:"sort,omitempty"`
	Order    string `json:"order,omitempty"`
}

// SimulationRequest represents a request to create a simulation
type SimulationRequest struct {
	GameID         string                 `json:"game_id"`
	SimulationRuns int                    `json:"simulation_runs,omitempty"`
	Config         map[string]interface{} `json:"config,omitempty"`
}

// ServiceHealth represents the health status of external services
type ServiceHealth struct {
	Database      string `json:"database"`
	SimEngine     string `json:"sim_engine"`
	DataFetcher   string `json:"data_fetcher"`
	OverallStatus string `json:"overall_status"`
}

// Umpire represents an umpire with performance metrics
type Umpire struct {
	ID                       string     `json:"id" db:"id"`
	UmpireID                 string     `json:"umpire_id" db:"umpire_id"`
	Name                     string     `json:"name" db:"name"`
	GamesUmped               int        `json:"games_umped" db:"games_umped"`
	AccuracyPct              *float64   `json:"accuracy_pct,omitempty" db:"accuracy_pct"`
	ConsistencyPct           *float64   `json:"consistency_pct,omitempty" db:"consistency_pct"`
	FavorHome                *float64   `json:"favor_home,omitempty" db:"favor_home"`
	ExpectedAccuracy         *float64   `json:"expected_accuracy,omitempty" db:"expected_accuracy"`
	ExpectedConsistency      *float64   `json:"expected_consistency,omitempty" db:"expected_consistency"`
	CorrectCalls             int        `json:"correct_calls" db:"correct_calls"`
	IncorrectCalls           int        `json:"incorrect_calls" db:"incorrect_calls"`
	TotalCalls               int        `json:"total_calls" db:"total_calls"`
	StrikePct                *float64   `json:"strike_pct,omitempty" db:"strike_pct"`
	BallPct                  *float64   `json:"ball_pct,omitempty" db:"ball_pct"`
	KPctAboveAvg             *float64   `json:"k_pct_above_avg,omitempty" db:"k_pct_above_avg"`
	BBPctAboveAvg            *float64   `json:"bb_pct_above_avg,omitempty" db:"bb_pct_above_avg"`
	HomePlateCallsPerGame    *float64   `json:"home_plate_calls_per_game,omitempty" db:"home_plate_calls_per_game"`
	CreatedAt                time.Time  `json:"created_at" db:"created_at"`
	UpdatedAt                time.Time  `json:"updated_at" db:"updated_at"`
}

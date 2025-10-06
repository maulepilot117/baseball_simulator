package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"runtime"
	"syscall"
	"time"

	"github.com/google/uuid"
	"github.com/gorilla/mux"
	"github.com/jackc/pgx/v5/pgxpool"

	"sim-engine/simulation"
	"sim-engine/weather"
)

type Server struct {
	db         *pgxpool.Pool
	router     *mux.Router
	httpServer *http.Server
	config     *Config
	simEngine  *simulation.SimulationEngine
}

type Config struct {
	Port           string
	DBHost         string
	DBPort         string
	DBUser         string
	DBPassword     string
	DBName         string
	Workers        int
	SimulationRuns int
}

// Remove the local definition since we're importing from simulation package

type SimulationRequest struct {
	GameID         string                 `json:"game_id"`
	SimulationRuns int                    `json:"simulation_runs,omitempty"`
	Config         map[string]interface{} `json:"config,omitempty"`
}

type SimulationResponse struct {
	RunID     string    `json:"run_id"`
	Status    string    `json:"status"`
	Message   string    `json:"message"`
	CreatedAt time.Time `json:"created_at"`
}

type SimulationStatus struct {
	RunID         string     `json:"run_id"`
	GameID        string     `json:"game_id"`
	Status        string     `json:"status"`
	TotalRuns     int        `json:"total_runs"`
	CompletedRuns int        `json:"completed_runs"`
	Progress      float64    `json:"progress"`
	CreatedAt     time.Time  `json:"created_at"`
	CompletedAt   *time.Time `json:"completed_at,omitempty"`
}

type SimulationResult struct {
	RunID                 string                 `json:"run_id"`
	GameID                string                 `json:"game_id"`
	HomeTeam              string                 `json:"home_team"`
	AwayTeam              string                 `json:"away_team"`
	TotalSimulations      int                    `json:"total_simulations"`
	HomeWins              int                    `json:"home_wins"`
	AwayWins              int                    `json:"away_wins"`
	HomeWinProbability    float64                `json:"home_win_probability"`
	AwayWinProbability    float64                `json:"away_win_probability"`
	ExpectedHomeScore     float64                `json:"expected_home_score"`
	ExpectedAwayScore     float64                `json:"expected_away_score"`
	HomeScoreDistribution map[int]int            `json:"home_score_distribution"`
	AwayScoreDistribution map[int]int            `json:"away_score_distribution"`
	PlayerPerformance     interface{}            `json:"player_performance,omitempty"`
	Weather               map[string]interface{} `json:"weather,omitempty"`
	ParkFactors           map[string]interface{} `json:"park_factors,omitempty"`
	Umpire                map[string]interface{} `json:"umpire,omitempty"`
	Metadata              map[string]interface{} `json:"metadata,omitempty"`
}

func NewConfig() *Config {
	workers := runtime.NumCPU()
	if envWorkers := os.Getenv("WORKERS"); envWorkers != "" {
		fmt.Sscanf(envWorkers, "%d", &workers)
	}

	simulationRuns := 1000
	if envRuns := os.Getenv("SIMULATION_RUNS"); envRuns != "" {
		fmt.Sscanf(envRuns, "%d", &simulationRuns)
	}

	return &Config{
		Port:           getEnv("PORT", "8081"),
		DBHost:         getEnv("DB_HOST", "localhost"),
		DBPort:         getEnv("DB_PORT", "5432"),
		DBUser:         getEnv("DB_USER", "baseball_user"),
		DBPassword:     getEnv("DB_PASSWORD", "baseball_pass"),
		DBName:         getEnv("DB_NAME", "baseball_sim"),
		Workers:        workers,
		SimulationRuns: simulationRuns,
	}
}

func NewServer(config *Config) (*Server, error) {
	// Database connection
	dbURL := fmt.Sprintf("postgresql://%s:%s@%s:%s/%s",
		config.DBUser, config.DBPassword, config.DBHost, config.DBPort, config.DBName)

	dbConfig, err := pgxpool.ParseConfig(dbURL)
	if err != nil {
		return nil, fmt.Errorf("failed to parse db config: %w", err)
	}

	// Connection pool settings
	dbConfig.MaxConns = int32(config.Workers * 2)
	dbConfig.MinConns = int32(config.Workers / 2)
	dbConfig.MaxConnLifetime = time.Hour
	dbConfig.MaxConnIdleTime = time.Minute * 30

	db, err := pgxpool.NewWithConfig(context.Background(), dbConfig)
	if err != nil {
		return nil, fmt.Errorf("failed to connect to database: %w", err)
	}

	// Test connection
	if err := db.Ping(context.Background()); err != nil {
		return nil, fmt.Errorf("failed to ping database: %w", err)
	}

	simEngine := simulation.NewSimulationEngine(db, config.Workers, config.SimulationRuns)
	simEngine.StartPerformanceMonitoring()

	// Initialize weather service if API key is configured
	weatherAPIKey := os.Getenv("OPENWEATHER_API_KEY")
	if weatherAPIKey != "" {
		weatherService := weather.NewService(weatherAPIKey)
		weatherService.StartCacheCleanup()

		// Validate API key
		ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		if err := weatherService.ValidateAPIKey(ctx); err != nil {
			log.Printf("Warning: Weather API key validation failed: %v", err)
			log.Printf("Simulations will use default weather conditions")
		} else {
			log.Printf("Weather service initialized successfully")
			// Wrap weather service with adapter
			adapter := simulation.NewWeatherServiceAdapter(weatherService)
			simEngine.SetWeatherService(adapter)
		}
		cancel()
	} else {
		log.Printf("No OPENWEATHER_API_KEY configured, simulations will use default weather")
	}

	s := &Server{
		db:        db,
		config:    config,
		router:    mux.NewRouter(),
		simEngine: simEngine,
	}

	s.setupRoutes()
	return s, nil
}

func (s *Server) setupRoutes() {
	// Health check
	s.router.HandleFunc("/health", s.healthHandler).Methods("GET")

	// Simulation endpoints
	s.router.HandleFunc("/simulate", s.simulateHandler).Methods("POST")
	s.router.HandleFunc("/simulation/{id}/status", s.simulationStatusHandler).Methods("GET")
	s.router.HandleFunc("/simulation/{id}/result", s.simulationResultHandler).Methods("GET")

	// Daily simulation endpoint
	s.router.HandleFunc("/simulate/daily", s.simulateDailyHandler).Methods("POST")

	// Apply middleware
	s.router.Use(s.loggingMiddleware)
	s.router.Use(s.recoveryMiddleware)
}

func (s *Server) Start() error {
	s.httpServer = &http.Server{
		Addr:         ":" + s.config.Port,
		Handler:      s.router,
		ReadTimeout:  15 * time.Second,
		WriteTimeout: 60 * time.Second, // Longer timeout for simulations
		IdleTimeout:  120 * time.Second,
	}

	log.Printf("Starting Simulation Engine on port %s with %d workers",
		s.config.Port, s.config.Workers)
	return s.httpServer.ListenAndServe()
}

func (s *Server) Shutdown(ctx context.Context) error {
	log.Println("Shutting down Simulation Engine...")

	// Close database connection
	s.db.Close()

	// Shutdown HTTP server
	return s.httpServer.Shutdown(ctx)
}

// Handlers
func (s *Server) healthHandler(w http.ResponseWriter, r *http.Request) {
	health := map[string]interface{}{
		"status":   "healthy",
		"time":     time.Now().UTC(),
		"workers":  s.config.Workers,
		"database": "connected",
	}

	// Check database connection
	ctx, cancel := context.WithTimeout(r.Context(), 2*time.Second)
	defer cancel()

	if err := s.db.Ping(ctx); err != nil {
		health["database"] = "disconnected"
		health["status"] = "unhealthy"
		w.WriteHeader(http.StatusServiceUnavailable)
	}

	writeJSON(w, health)
}

func (s *Server) simulateHandler(w http.ResponseWriter, r *http.Request) {
	var req SimulationRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid request body", http.StatusBadRequest)
		return
	}

	// Validate game exists
	var gameExists bool
	err := s.db.QueryRow(r.Context(),
		"SELECT EXISTS(SELECT 1 FROM games WHERE game_id = $1)",
		req.GameID).Scan(&gameExists)

	if err != nil {
		log.Printf("Database error: %v", err)
		http.Error(w, "Internal server error", http.StatusInternalServerError)
		return
	}

	if !gameExists {
		http.Error(w, "Game not found", http.StatusNotFound)
		return
	}

	// Create simulation run
	runID := uuid.New().String()
	simulationRuns := req.SimulationRuns
	if simulationRuns == 0 {
		simulationRuns = s.config.SimulationRuns
	}

	configJSON, _ := json.Marshal(req.Config)

	_, err = s.db.Exec(r.Context(), `
		INSERT INTO simulation_runs (id, game_id, config, total_runs, status)
		VALUES ($1, (SELECT id FROM games WHERE game_id = $2), $3, $4, 'pending')
	`, runID, req.GameID, configJSON, simulationRuns)

	if err != nil {
		log.Printf("Failed to create simulation run: %v", err)
		http.Error(w, "Failed to create simulation", http.StatusInternalServerError)
		return
	}

	// Start simulation in background
	go s.simEngine.RunSimulation(runID, req.GameID, simulationRuns, req.Config)

	response := SimulationResponse{
		RunID:     runID,
		Status:    "started",
		Message:   fmt.Sprintf("Simulation started with %d runs", simulationRuns),
		CreatedAt: time.Now().UTC(),
	}

	writeJSON(w, response)
}

func (s *Server) simulationStatusHandler(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	runID := vars["id"]

	// First check in-memory status
	if runStatus, exists := s.simEngine.GetRunStatus(runID); exists {
		status := SimulationStatus{
			RunID:         runStatus.RunID,
			GameID:        runStatus.GameID,
			Status:        runStatus.Status,
			TotalRuns:     runStatus.TotalRuns,
			CompletedRuns: runStatus.CompletedRuns,
			Progress:      float64(runStatus.CompletedRuns) / float64(runStatus.TotalRuns),
			CreatedAt:     runStatus.StartTime,
			CompletedAt:   runStatus.CompletedTime,
		}
		writeJSON(w, status)
		return
	}

	// Fallback to database lookup
	var status SimulationStatus
	var gameID string
	var config json.RawMessage

	err := s.db.QueryRow(r.Context(), `
		SELECT sr.id, g.game_id, sr.status, sr.total_runs, sr.completed_runs, 
		       sr.created_at, sr.completed_at, sr.config
		FROM simulation_runs sr
		JOIN games g ON sr.game_id = g.id
		WHERE sr.id = $1
	`, runID).Scan(&status.RunID, &gameID, &status.Status, &status.TotalRuns,
		&status.CompletedRuns, &status.CreatedAt, &status.CompletedAt, &config)

	if err != nil {
		http.Error(w, "Simulation not found", http.StatusNotFound)
		return
	}

	status.GameID = gameID
	status.Progress = float64(status.CompletedRuns) / float64(status.TotalRuns)

	writeJSON(w, status)
}

func (s *Server) simulationResultHandler(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	runID := vars["id"]

	// Check if simulation is complete
	var status string
	err := s.db.QueryRow(r.Context(),
		"SELECT status FROM simulation_runs WHERE id = $1", runID).Scan(&status)

	if err != nil {
		http.Error(w, "Simulation not found", http.StatusNotFound)
		return
	}

	if status != "completed" {
		http.Error(w, "Simulation not yet complete", http.StatusAccepted)
		return
	}

	// Get aggregated results using the simulation engine
	aggregatedResult, err := s.simEngine.GetRunResult(r.Context(), runID)
	if err != nil {
		log.Printf("Failed to get simulation results: %v", err)
		http.Error(w, "Results not available", http.StatusInternalServerError)
		return
	}

	// Get game context (weather, stadium, umpire, teams) used in the simulation
	var gameID string
	var homeTeamName, awayTeamName string
	var weatherJSON, parkFactorsJSON, umpireTendenciesJSON []byte
	var stadiumName, stadiumLocation, umpireName *string
	var stadiumAltitude *int

	contextQuery := `
		SELECT g.game_id,
		       ht.name as home_team_name,
		       at.name as away_team_name,
		       g.weather_data,
		       s.name, s.location, s.altitude, s.park_factors,
		       u.name, u.tendencies
		FROM simulation_runs sr
		JOIN games g ON sr.game_id = g.id
		JOIN teams ht ON g.home_team_id = ht.id
		JOIN teams at ON g.away_team_id = at.id
		LEFT JOIN stadiums s ON g.stadium_id = s.id
		LEFT JOIN umpires u ON g.home_plate_umpire_id = u.id
		WHERE sr.id = $1
	`

	err = s.db.QueryRow(r.Context(), contextQuery, runID).Scan(
		&gameID,
		&homeTeamName,
		&awayTeamName,
		&weatherJSON,
		&stadiumName,
		&stadiumLocation,
		&stadiumAltitude,
		&parkFactorsJSON,
		&umpireName,
		&umpireTendenciesJSON,
	)

	// Convert to response format with defaults if game query failed
	result := SimulationResult{
		RunID:                 aggregatedResult.RunID,
		GameID:                gameID,
		HomeTeam:              homeTeamName,
		AwayTeam:              awayTeamName,
		TotalSimulations:      aggregatedResult.TotalSimulations,
		HomeWins:              aggregatedResult.HomeWins,
		AwayWins:              aggregatedResult.AwayWins,
		HomeWinProbability:    aggregatedResult.HomeWinProbability,
		AwayWinProbability:    aggregatedResult.AwayWinProbability,
		ExpectedHomeScore:     aggregatedResult.ExpectedHomeScore,
		ExpectedAwayScore:     aggregatedResult.ExpectedAwayScore,
		HomeScoreDistribution: aggregatedResult.HomeScoreDistribution,
		AwayScoreDistribution: aggregatedResult.AwayScoreDistribution,
		PlayerPerformance:     aggregatedResult.PlayerPerformance,
		Metadata: map[string]interface{}{
			"average_game_duration": aggregatedResult.AverageGameDuration,
			"average_pitches":       aggregatedResult.AveragePitches,
			"high_leverage_events":  len(aggregatedResult.HighLeverageEvents),
			"statistics":            aggregatedResult.Statistics,
		},
	}

	// Add simulation context (weather, park, umpire) if available
	if err == nil {
		// Parse and add weather
		if len(weatherJSON) > 0 {
			var weather map[string]interface{}
			if json.Unmarshal(weatherJSON, &weather) == nil {
				result.Weather = weather
			}
		}

		// Parse and add park factors
		if len(parkFactorsJSON) > 0 {
			var parkFactors map[string]interface{}
			if json.Unmarshal(parkFactorsJSON, &parkFactors) == nil {
				result.ParkFactors = parkFactors
			}
		}

		// Add stadium info if available
		if stadiumName != nil {
			if result.Metadata == nil {
				result.Metadata = make(map[string]interface{})
			}
			result.Metadata["stadium"] = map[string]interface{}{
				"name":     *stadiumName,
				"location": stadiumLocation,
				"altitude": stadiumAltitude,
			}
		}

		// Parse and add umpire info
		if umpireName != nil {
			umpireInfo := map[string]interface{}{
				"name": *umpireName,
			}
			if len(umpireTendenciesJSON) > 0 {
				var tendencies map[string]interface{}
				if json.Unmarshal(umpireTendenciesJSON, &tendencies) == nil {
					umpireInfo["tendencies"] = tendencies
				}
			}
			result.Umpire = umpireInfo
		}
	} else {
		log.Printf("Warning: Failed to load game context: %v", err)
	}

	writeJSON(w, result)
}

// DailySimulationRequest for batch simulating multiple games
type DailySimulationRequest struct {
	Date           string                 `json:"date"`            // YYYY-MM-DD format, defaults to today
	SimulationRuns int                    `json:"simulation_runs"` // Optional override
	Config         map[string]interface{} `json:"config,omitempty"`
}

// DailySimulationResponse contains all simulations for the day
type DailySimulationResponse struct {
	Date         string              `json:"date"`
	GamesCount   int                 `json:"games_count"`
	Simulations  []GameSimulation    `json:"simulations"`
	StartedAt    time.Time           `json:"started_at"`
	Message      string              `json:"message"`
}

// GameSimulation represents a single game's simulation in the batch
type GameSimulation struct {
	GameID     string `json:"game_id"`
	HomeTeam   string `json:"home_team"`
	AwayTeam   string `json:"away_team"`
	RunID      string `json:"run_id"`
	Status     string `json:"status"`
	Error      string `json:"error,omitempty"`
}

func (s *Server) simulateDailyHandler(w http.ResponseWriter, r *http.Request) {
	var req DailySimulationRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		// Allow empty body - use defaults
		req.Date = time.Now().Format("2006-01-02")
	}

	// Parse or default date
	var targetDate time.Time
	var err error
	if req.Date == "" {
		targetDate = time.Now()
	} else {
		targetDate, err = time.Parse("2006-01-02", req.Date)
		if err != nil {
			http.Error(w, "Invalid date format, use YYYY-MM-DD", http.StatusBadRequest)
			return
		}
	}

	// Query scheduled games for the target date
	query := `
		SELECT g.game_id, ht.name as home_team, at.name as away_team
		FROM games g
		JOIN teams ht ON g.home_team_id = ht.id
		JOIN teams at ON g.away_team_id = at.id
		WHERE g.game_date = $1 AND g.status = 'scheduled'
		ORDER BY g.game_time
	`

	rows, err := s.db.Query(r.Context(), query, targetDate)
	if err != nil {
		log.Printf("Failed to query games: %v", err)
		http.Error(w, "Failed to query games", http.StatusInternalServerError)
		return
	}
	defer rows.Close()

	var games []struct {
		GameID   string
		HomeTeam string
		AwayTeam string
	}

	for rows.Next() {
		var game struct {
			GameID   string
			HomeTeam string
			AwayTeam string
		}
		if err := rows.Scan(&game.GameID, &game.HomeTeam, &game.AwayTeam); err != nil {
			log.Printf("Error scanning game: %v", err)
			continue
		}
		games = append(games, game)
	}

	if len(games) == 0 {
		response := DailySimulationResponse{
			Date:        targetDate.Format("2006-01-02"),
			GamesCount:  0,
			Simulations: []GameSimulation{},
			StartedAt:   time.Now(),
			Message:     "No scheduled games found for this date",
		}
		writeJSON(w, response)
		return
	}

	// Start simulations for all games
	simulationRuns := req.SimulationRuns
	if simulationRuns == 0 {
		simulationRuns = s.config.SimulationRuns
	}

	var simulations []GameSimulation

	for _, game := range games {
		// Create simulation run for this game
		runID := uuid.New().String()

		// Validate game exists in database
		var gameExists bool
		err := s.db.QueryRow(r.Context(),
			"SELECT EXISTS(SELECT 1 FROM games WHERE game_id = $1)",
			game.GameID).Scan(&gameExists)

		if err != nil || !gameExists {
			simulations = append(simulations, GameSimulation{
				GameID:   game.GameID,
				HomeTeam: game.HomeTeam,
				AwayTeam: game.AwayTeam,
				RunID:    runID,
				Status:   "error",
				Error:    "Game not found in database",
			})
			continue
		}

		// Insert simulation run
		configJSON, _ := json.Marshal(req.Config)
		_, err = s.db.Exec(r.Context(), `
			INSERT INTO simulation_runs (id, game_id, config, total_runs, status)
			VALUES ($1, (SELECT id FROM games WHERE game_id = $2), $3, $4, 'pending')
		`, runID, game.GameID, configJSON, simulationRuns)

		if err != nil {
			log.Printf("Failed to create simulation run for game %s: %v", game.GameID, err)
			simulations = append(simulations, GameSimulation{
				GameID:   game.GameID,
				HomeTeam: game.HomeTeam,
				AwayTeam: game.AwayTeam,
				RunID:    runID,
				Status:   "error",
				Error:    fmt.Sprintf("Failed to create simulation: %v", err),
			})
			continue
		}

		// Start simulation in background
		go s.simEngine.RunSimulation(runID, game.GameID, simulationRuns, req.Config)

		simulations = append(simulations, GameSimulation{
			GameID:   game.GameID,
			HomeTeam: game.HomeTeam,
			AwayTeam: game.AwayTeam,
			RunID:    runID,
			Status:   "started",
		})

		log.Printf("Started simulation for game %s (%s vs %s)", game.GameID, game.AwayTeam, game.HomeTeam)
	}

	response := DailySimulationResponse{
		Date:        targetDate.Format("2006-01-02"),
		GamesCount:  len(games),
		Simulations: simulations,
		StartedAt:   time.Now(),
		Message:     fmt.Sprintf("Started simulations for %d games", len(simulations)),
	}

	writeJSON(w, response)
}

// Middleware
func (s *Server) loggingMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		start := time.Now()

		// Create a custom response writer to capture status code
		lrw := &loggingResponseWriter{ResponseWriter: w, statusCode: http.StatusOK}

		next.ServeHTTP(lrw, r)

		duration := time.Since(start)
		log.Printf("%s %s %d %v", r.Method, r.RequestURI, lrw.statusCode, duration)
	})
}

func (s *Server) recoveryMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		defer func() {
			if err := recover(); err != nil {
				log.Printf("Panic recovered: %v", err)
				http.Error(w, "Internal Server Error", http.StatusInternalServerError)
			}
		}()
		next.ServeHTTP(w, r)
	})
}

// Helper types and functions
type loggingResponseWriter struct {
	http.ResponseWriter
	statusCode int
}

func (lrw *loggingResponseWriter) WriteHeader(code int) {
	lrw.statusCode = code
	lrw.ResponseWriter.WriteHeader(code)
}

func writeJSON(w http.ResponseWriter, data interface{}) {
	w.Header().Set("Content-Type", "application/json")
	if err := json.NewEncoder(w).Encode(data); err != nil {
		log.Printf("Error encoding JSON: %v", err)
		http.Error(w, "Internal Server Error", http.StatusInternalServerError)
	}
}

func getEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}

func main() {
	config := NewConfig()

	server, err := NewServer(config)
	if err != nil {
		log.Fatal("Failed to create server:", err)
	}

	// Graceful shutdown
	go func() {
		sigChan := make(chan os.Signal, 1)
		signal.Notify(sigChan, os.Interrupt, syscall.SIGTERM)
		<-sigChan

		ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
		defer cancel()

		if err := server.Shutdown(ctx); err != nil {
			log.Fatal("Server shutdown failed:", err)
		}
		log.Println("Server shutdown complete")
	}()

	if err := server.Start(); err != nil && err != http.ErrServerClosed {
		log.Fatal("Server failed to start:", err)
	}
}

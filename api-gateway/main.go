package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"strconv"
	"strings"
	"syscall"
	"time"

	"github.com/gorilla/mux"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/rs/cors"
)

type Server struct {
	db         *pgxpool.Pool
	router     *mux.Router
	httpServer *http.Server
	config     *Config
}

type Config struct {
	Port           string
	DBHost         string
	DBPort         string
	DBUser         string
	DBPassword     string
	DBName         string
	SimEngineURL   string
	DataFetcherURL string
}

func NewConfig() *Config {
	return &Config{
		Port:           getEnv("PORT", "8080"),
		DBHost:         getEnv("DB_HOST", "localhost"),
		DBPort:         getEnv("DB_PORT", "5432"),
		DBUser:         getEnv("DB_USER", "baseball_user"),
		DBPassword:     getEnv("DB_PASSWORD", "baseball_pass"),
		DBName:         getEnv("DB_NAME", "baseball_sim"),
		SimEngineURL:   getEnv("SIM_ENGINE_URL", "http://localhost:8081"),
		DataFetcherURL: getEnv("DATA_FETCHER_URL", "http://localhost:8082"),
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
	dbConfig.MaxConns = 25
	dbConfig.MinConns = 5
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

	s := &Server{
		db:     db,
		config: config,
		router: mux.NewRouter(),
	}

	s.setupRoutes()
	return s, nil
}

func (s *Server) setupRoutes() {
	// Root endpoint for API documentation
	s.router.HandleFunc("/", s.rootHandler).Methods("GET")
	
	// API version prefix
	api := s.router.PathPrefix("/api/v1").Subrouter()

	// Health check
	api.HandleFunc("/health", s.healthHandler).Methods("GET")

	// Teams endpoints
	api.HandleFunc("/teams", s.getTeamsHandler).Methods("GET")
	api.HandleFunc("/teams/{id}", s.getTeamHandler).Methods("GET")

	// Players endpoints
	api.HandleFunc("/players", s.getPlayersHandler).Methods("GET")
	api.HandleFunc("/players/{id}", s.getPlayerHandler).Methods("GET")
	api.HandleFunc("/players/{id}/stats", s.getPlayerStatsHandler).Methods("GET")

	// Games endpoints
	api.HandleFunc("/games", s.getGamesHandler).Methods("GET")
	api.HandleFunc("/games/{id}", s.getGameHandler).Methods("GET")
	api.HandleFunc("/games/date/{date}", s.getGamesByDateHandler).Methods("GET")

	// Simulation endpoints
	api.HandleFunc("/simulations", s.createSimulationHandler).Methods("POST")
	api.HandleFunc("/simulations/{id}", s.getSimulationHandler).Methods("GET")
	api.HandleFunc("/simulations/{id}/status", s.getSimulationStatusHandler).Methods("GET")

	// Data update endpoints
	api.HandleFunc("/data/refresh", s.refreshDataHandler).Methods("POST")
	api.HandleFunc("/data/status", s.dataStatusHandler).Methods("GET")
	
	// API status endpoint
	api.HandleFunc("/status", s.apiStatusHandler).Methods("GET")

	// Apply middleware
	s.router.Use(s.loggingMiddleware)
	s.router.Use(s.recoveryMiddleware)
}

func (s *Server) Start() error {
	// Setup CORS
	c := cors.New(cors.Options{
		AllowedOrigins: []string{"http://localhost:3000", "http://localhost:8080"},
		AllowedMethods: []string{"GET", "POST", "PUT", "DELETE", "OPTIONS"},
		AllowedHeaders: []string{"*"},
		MaxAge:         86400,
	})

	handler := c.Handler(s.router)

	s.httpServer = &http.Server{
		Addr:         ":" + s.config.Port,
		Handler:      handler,
		ReadTimeout:  15 * time.Second,
		WriteTimeout: 15 * time.Second,
		IdleTimeout:  60 * time.Second,
	}

	log.Printf("Starting API Gateway on port %s", s.config.Port)
	return s.httpServer.ListenAndServe()
}

func (s *Server) Shutdown(ctx context.Context) error {
	log.Println("Shutting down API Gateway...")

	// Close database connection
	s.db.Close()

	// Shutdown HTTP server
	return s.httpServer.Shutdown(ctx)
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

// Handlers
func (s *Server) rootHandler(w http.ResponseWriter, r *http.Request) {
	apiInfo := map[string]interface{}{
		"service": "Baseball Simulation API Gateway",
		"version": "2.0.0",
		"status":  "online",
		"time":    time.Now().UTC(),
		"endpoints": map[string]interface{}{
			"health":     "/api/v1/health",
			"teams":      "/api/v1/teams",
			"players":    "/api/v1/players",
			"games":      "/api/v1/games",
			"simulations": "/api/v1/simulations",
		},
		"documentation": "Baseball simulation system with MLB data integration and Monte Carlo predictions",
		"frontend":      "http://localhost:3000",
	}

	// Check database connection for status
	ctx, cancel := context.WithTimeout(r.Context(), 2*time.Second)
	defer cancel()

	if err := s.db.Ping(ctx); err != nil {
		apiInfo["status"] = "degraded"
		apiInfo["database"] = "disconnected"
	} else {
		apiInfo["database"] = "connected"
	}

	writeJSON(w, apiInfo)
}

func (s *Server) healthHandler(w http.ResponseWriter, r *http.Request) {
	health := map[string]interface{}{
		"status":   "healthy",
		"time":     time.Now().UTC(),
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

// Teams handlers
func (s *Server) getTeamsHandler(w http.ResponseWriter, r *http.Request) {
	ctx, cancel := contextWithTimeout(r.Context())
	defer cancel()

	params := parseQueryParams(r)

	// Build base query
	baseQuery := `
		SELECT t.id, t.team_id, t.name, t.abbreviation, t.league, 
		       t.division, t.stadium_id, t.created_at, t.updated_at
		FROM teams t`

	// Count query for pagination
	countQuery := "SELECT COUNT(*) FROM teams t"

	// Build WHERE clause
	whereClause, args := buildWhereClause(params, "t")

	// Get total count
	var total int
	err := s.db.QueryRow(ctx, countQuery+whereClause, args...).Scan(&total)
	if err != nil {
		writeError(w, "Failed to count teams", http.StatusInternalServerError)
		return
	}

	// Build ORDER and LIMIT clause
	orderClause := buildOrderClause(params, "t", "name")
	offset := calculateOffset(params.Page, params.PageSize)
	limitClause := fmt.Sprintf(" LIMIT %d OFFSET %d", params.PageSize, offset)

	// Execute main query
	finalQuery := baseQuery + whereClause + orderClause + limitClause
	rows, err := s.db.Query(ctx, finalQuery, args...)
	if err != nil {
		writeError(w, "Failed to query teams", http.StatusInternalServerError)
		return
	}
	defer rows.Close()

	var teams []Team
	for rows.Next() {
		var team Team
		err := rows.Scan(
			&team.ID, &team.TeamID, &team.Name, &team.Abbreviation,
			&team.League, &team.Division, &team.Stadium, &team.CreatedAt, &team.UpdatedAt,
		)
		if err != nil {
			writeError(w, "Failed to scan team", http.StatusInternalServerError)
			return
		}
		teams = append(teams, team)
	}

	response := buildPaginatedResponse(teams, total, params.Page, params.PageSize)
	writeJSON(w, response)
}

func (s *Server) getTeamHandler(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	teamID := vars["id"]

	if teamID == "" {
		writeError(w, "Team ID is required", http.StatusBadRequest)
		return
	}

	ctx, cancel := contextWithTimeout(r.Context())
	defer cancel()

	query := `
		SELECT t.id, t.team_id, t.name, t.abbreviation, t.league, 
		       t.division, t.stadium_id, t.created_at, t.updated_at
		FROM teams t
		WHERE t.id = $1 OR t.team_id = $1`

	var team Team
	err := s.db.QueryRow(ctx, query, teamID).Scan(
		&team.ID, &team.TeamID, &team.Name, &team.Abbreviation,
		&team.League, &team.Division, &team.Stadium, &team.CreatedAt, &team.UpdatedAt,
	)

	if err != nil {
		if err.Error() == "no rows in result set" {
			writeError(w, "Team not found", http.StatusNotFound)
		} else {
			writeError(w, "Failed to query team", http.StatusInternalServerError)
		}
		return
	}

	writeJSON(w, team)
}

// Players handlers
func (s *Server) getPlayersHandler(w http.ResponseWriter, r *http.Request) {
	ctx, cancel := contextWithTimeout(r.Context())
	defer cancel()

	params := parseQueryParams(r)

	// Build base query with team information
	baseQuery := `
		SELECT p.id, p.player_id, p.first_name, p.last_name, 
		       COALESCE(p.full_name, CONCAT(p.first_name, ' ', p.last_name)) as full_name,
		       p.position, p.team_id, p.jersey_number, p.height, p.weight,
		       p.birth_date, p.birth_city, p.birth_country, p.bats, p.throws,
		       p.debut_date, p.status, p.created_at, p.updated_at,
		       t.name as team_name, t.city as team_city, t.abbreviation as team_abbreviation
		FROM players p
		LEFT JOIN teams t ON p.team_id = t.id`

	// Count query
	countQuery := `
		SELECT COUNT(*) 
		FROM players p 
		LEFT JOIN teams t ON p.team_id = t.id`

	// Build WHERE clause
	whereClause, args := buildPlayersWhereClause(params)

	// Get total count
	var total int
	err := s.db.QueryRow(ctx, countQuery+whereClause, args...).Scan(&total)
	if err != nil {
		writeError(w, "Failed to count players", http.StatusInternalServerError)
		return
	}

	// Build ORDER and LIMIT clause
	orderClause := buildOrderClause(params, "p", "last_name")
	offset := calculateOffset(params.Page, params.PageSize)
	limitClause := fmt.Sprintf(" LIMIT %d OFFSET %d", params.PageSize, offset)

	// Execute main query
	finalQuery := baseQuery + whereClause + orderClause + limitClause
	rows, err := s.db.Query(ctx, finalQuery, args...)
	if err != nil {
		writeError(w, "Failed to query players", http.StatusInternalServerError)
		return
	}
	defer rows.Close()

	var players []PlayerWithTeam
	for rows.Next() {
		var p PlayerWithTeam
		var teamName, teamCity, teamAbbr *string

		err := rows.Scan(
			&p.ID, &p.PlayerID, &p.FirstName, &p.LastName, &p.FullName,
			&p.Position, &p.TeamID, &p.JerseyNumber, &p.Height, &p.Weight,
			&p.BirthDate, &p.BirthCity, &p.BirthCountry, &p.Bats, &p.Throws,
			&p.DebutDate, &p.Status, &p.CreatedAt, &p.UpdatedAt,
			&teamName, &teamCity, &teamAbbr,
		)
		if err != nil {
			log.Printf("Failed to scan player: %v", err)
			log.Printf("Query: %s", finalQuery)
			writeError(w, fmt.Sprintf("Failed to scan player: %v", err), http.StatusInternalServerError)
			return
		}

		// Add team information if available
		if teamName != nil {
			p.Team = &Team{
				ID:           p.TeamID,
				Name:         *teamName,
				Abbreviation: *teamAbbr,
			}
		}

		players = append(players, p)
	}

	response := buildPaginatedResponse(players, total, params.Page, params.PageSize)
	writeJSON(w, response)
}

func (s *Server) getPlayerHandler(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	playerID := vars["id"]

	if playerID == "" {
		writeError(w, "Player ID is required", http.StatusBadRequest)
		return
	}

	ctx, cancel := contextWithTimeout(r.Context())
	defer cancel()

	query := `
		SELECT p.id, p.player_id, p.first_name, p.last_name, 
		       COALESCE(p.full_name, CONCAT(p.first_name, ' ', p.last_name)) as full_name,
		       p.position, p.team_id, p.jersey_number, p.height, p.weight,
		       p.birth_date, p.birth_city, p.birth_country, p.bats, p.throws,
		       p.debut_date, p.status, p.created_at, p.updated_at,
		       t.id as team_internal_id, t.team_id, t.name as team_name, 
		       t.city as team_city, t.abbreviation as team_abbreviation
		FROM players p
		LEFT JOIN teams t ON p.team_id = t.id
		WHERE p.id = $1 OR p.player_id = $1`

	var p PlayerWithTeam
	var teamInternalID, teamID, teamName, teamCity, teamAbbr *string

	err := s.db.QueryRow(ctx, query, playerID).Scan(
		&p.ID, &p.PlayerID, &p.FirstName, &p.LastName, &p.FullName,
		&p.Position, &p.TeamID, &p.JerseyNumber, &p.Height, &p.Weight,
		&p.BirthDate, &p.BirthCity, &p.BirthCountry, &p.Bats, &p.Throws,
		&p.DebutDate, &p.Status, &p.CreatedAt, &p.UpdatedAt,
		&teamInternalID, &teamID, &teamName, &teamCity, &teamAbbr,
	)

	if err != nil {
		if err.Error() == "no rows in result set" {
			writeError(w, "Player not found", http.StatusNotFound)
		} else {
			writeError(w, "Failed to query player", http.StatusInternalServerError)
		}
		return
	}

	// Add team information if available
	if teamName != nil {
		p.Team = &Team{
			ID:           *teamInternalID,
			TeamID:       *teamID,
			Name:         *teamName,
			Abbreviation: *teamAbbr,
		}
	}

	writeJSON(w, p)
}

func (s *Server) getPlayerStatsHandler(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	playerID := vars["id"]

	if playerID == "" {
		writeError(w, "Player ID is required", http.StatusBadRequest)
		return
	}

	ctx, cancel := contextWithTimeout(r.Context())
	defer cancel()

	// Get season parameter, default to current season
	season := getCurrentSeason()
	if seasonStr := r.URL.Query().Get("season"); seasonStr != "" {
		if parsedSeason, err := strconv.Atoi(seasonStr); err == nil {
			season = parsedSeason
		}
	}

	query := `
		SELECT player_id, season, stats_type, aggregated_stats, games_played, updated_at
		FROM player_season_aggregates
		WHERE player_id = (SELECT id FROM players WHERE id = $1 OR player_id = $1)
		AND season = $2
		ORDER BY stats_type`

	rows, err := s.db.Query(ctx, query, playerID, season)
	if err != nil {
		writeError(w, "Failed to query player stats", http.StatusInternalServerError)
		return
	}
	defer rows.Close()

	var stats []PlayerStats
	for rows.Next() {
		var stat PlayerStats
		var aggregatedStatsJSON []byte

		err := rows.Scan(
			&stat.PlayerID, &stat.Season, &stat.StatsType,
			&aggregatedStatsJSON, &stat.GamesPlayed, &stat.UpdatedAt,
		)
		if err != nil {
			writeError(w, "Failed to scan player stats", http.StatusInternalServerError)
			return
		}

		// Parse aggregated stats JSON
		if len(aggregatedStatsJSON) > 0 {
			if err := json.Unmarshal(aggregatedStatsJSON, &stat.AggregatedStats); err != nil {
				log.Printf("Failed to parse aggregated stats: %v", err)
				stat.AggregatedStats = make(map[string]interface{})
			}
		} else {
			stat.AggregatedStats = make(map[string]interface{})
		}

		stats = append(stats, stat)
	}

	if len(stats) == 0 {
		writeError(w, "No stats found for player", http.StatusNotFound)
		return
	}

	writeJSON(w, map[string]interface{}{
		"player_id": playerID,
		"season":    season,
		"stats":     stats,
	})
}

// Games handlers
func (s *Server) getGamesHandler(w http.ResponseWriter, r *http.Request) {
	ctx, cancel := contextWithTimeout(r.Context())
	defer cancel()

	params := parseQueryParams(r)

	// Build base query with team information
	baseQuery := `
		SELECT g.id, g.game_id, g.season, g.game_type, g.game_date,
		       g.home_team_id, g.away_team_id, g.home_score, g.away_score,
		       g.status, g.inning, g.inning_half, g.stadium_id, g.weather_data,
		       g.attendance, g.game_duration, g.created_at, g.updated_at,
		       ht.name as home_team_name, ht.city as home_team_city, ht.abbreviation as home_team_abbr,
		       at.name as away_team_name, at.city as away_team_city, at.abbreviation as away_team_abbr,
		       s.name as stadium_name, s.city as stadium_city
		FROM games g
		LEFT JOIN teams ht ON g.home_team_id = ht.id
		LEFT JOIN teams at ON g.away_team_id = at.id
		LEFT JOIN stadiums s ON g.stadium_id = s.id`

	// Count query
	countQuery := `
		SELECT COUNT(*) 
		FROM games g
		LEFT JOIN teams ht ON g.home_team_id = ht.id
		LEFT JOIN teams at ON g.away_team_id = at.id`

	// Build WHERE clause
	whereClause, args := buildGamesWhereClause(params)

	// Get total count
	var total int
	err := s.db.QueryRow(ctx, countQuery+whereClause, args...).Scan(&total)
	if err != nil {
		writeError(w, "Failed to count games", http.StatusInternalServerError)
		return
	}

	// Build ORDER and LIMIT clause
	orderClause := buildOrderClause(params, "g", "game_date")
	offset := calculateOffset(params.Page, params.PageSize)
	limitClause := fmt.Sprintf(" LIMIT %d OFFSET %d", params.PageSize, offset)

	// Execute main query
	finalQuery := baseQuery + whereClause + orderClause + limitClause
	rows, err := s.db.Query(ctx, finalQuery, args...)
	if err != nil {
		writeError(w, "Failed to query games", http.StatusInternalServerError)
		return
	}
	defer rows.Close()

	var games []GameWithTeams
	for rows.Next() {
		var g GameWithTeams
		var homeTeamName, homeTeamCity, homeTeamAbbr *string
		var awayTeamName, awayTeamCity, awayTeamAbbr *string
		var stadiumName, stadiumCity *string

		err := rows.Scan(
			&g.ID, &g.GameID, &g.Season, &g.GameType, &g.GameDate,
			&g.HomeTeamID, &g.AwayTeamID, &g.HomeScore, &g.AwayScore,
			&g.Status, &g.Inning, &g.InningHalf, &g.StadiumID, &g.WeatherData,
			&g.Attendance, &g.GameDuration, &g.CreatedAt, &g.UpdatedAt,
			&homeTeamName, &homeTeamCity, &homeTeamAbbr,
			&awayTeamName, &awayTeamCity, &awayTeamAbbr,
			&stadiumName, &stadiumCity,
		)
		if err != nil {
			writeError(w, "Failed to scan game", http.StatusInternalServerError)
			return
		}

		// Add team information
		if homeTeamName != nil {
			g.HomeTeam = &Team{
				ID:           g.HomeTeamID,
				Name:         *homeTeamName,
				Abbreviation: *homeTeamAbbr,
			}
		}
		if awayTeamName != nil {
			g.AwayTeam = &Team{
				ID:           g.AwayTeamID,
				Name:         *awayTeamName,
				Abbreviation: *awayTeamAbbr,
			}
		}
		if stadiumName != nil {
			g.Stadium = &Stadium{
				ID:   g.StadiumID,
				Name: *stadiumName,
			}
		}

		games = append(games, g)
	}

	response := buildPaginatedResponse(games, total, params.Page, params.PageSize)
	writeJSON(w, response)
}

func (s *Server) getGameHandler(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	gameID := vars["id"]

	if gameID == "" {
		writeError(w, "Game ID is required", http.StatusBadRequest)
		return
	}

	ctx, cancel := contextWithTimeout(r.Context())
	defer cancel()

	query := `
		SELECT g.id, g.game_id, g.season, g.game_type, g.game_date,
		       g.home_team_id, g.away_team_id, g.home_score, g.away_score,
		       g.status, g.inning, g.inning_half, g.stadium_id, g.weather_data,
		       g.attendance, g.game_duration, g.created_at, g.updated_at,
		       ht.team_id as home_team_external_id, ht.name as home_team_name, 
		       ht.city as home_team_city, ht.abbreviation as home_team_abbr,
		       at.team_id as away_team_external_id, at.name as away_team_name, 
		       at.city as away_team_city, at.abbreviation as away_team_abbr,
		       s.name as stadium_name, s.city as stadium_city, s.capacity as stadium_capacity
		FROM games g
		LEFT JOIN teams ht ON g.home_team_id = ht.id
		LEFT JOIN teams at ON g.away_team_id = at.id
		LEFT JOIN stadiums s ON g.stadium_id = s.id
		WHERE g.id = $1 OR g.game_id = $1`

	var g GameWithTeams
	var homeTeamExternalID, homeTeamName, homeTeamCity, homeTeamAbbr *string
	var awayTeamExternalID, awayTeamName, awayTeamCity, awayTeamAbbr *string
	var stadiumName, stadiumCity *string
	var stadiumCapacity *int

	err := s.db.QueryRow(ctx, query, gameID).Scan(
		&g.ID, &g.GameID, &g.Season, &g.GameType, &g.GameDate,
		&g.HomeTeamID, &g.AwayTeamID, &g.HomeScore, &g.AwayScore,
		&g.Status, &g.Inning, &g.InningHalf, &g.StadiumID, &g.WeatherData,
		&g.Attendance, &g.GameDuration, &g.CreatedAt, &g.UpdatedAt,
		&homeTeamExternalID, &homeTeamName, &homeTeamCity, &homeTeamAbbr,
		&awayTeamExternalID, &awayTeamName, &awayTeamCity, &awayTeamAbbr,
		&stadiumName, &stadiumCity, &stadiumCapacity,
	)

	if err != nil {
		if err.Error() == "no rows in result set" {
			writeError(w, "Game not found", http.StatusNotFound)
		} else {
			writeError(w, "Failed to query game", http.StatusInternalServerError)
		}
		return
	}

	// Add team and stadium information
	if homeTeamName != nil {
		g.HomeTeam = &Team{
			ID:           g.HomeTeamID,
			TeamID:       *homeTeamExternalID,
			Name:         *homeTeamName,
			Abbreviation: *homeTeamAbbr,
		}
	}
	if awayTeamName != nil {
		g.AwayTeam = &Team{
			ID:           g.AwayTeamID,
			TeamID:       *awayTeamExternalID,
			Name:         *awayTeamName,
			Abbreviation: *awayTeamAbbr,
		}
	}
	if stadiumName != nil {
		g.Stadium = &Stadium{
			ID:       g.StadiumID,
			Name:     *stadiumName,
			Capacity: stadiumCapacity,
		}
	}

	writeJSON(w, g)
}

func (s *Server) getGamesByDateHandler(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	dateStr := vars["date"]

	if !validateDateFormat(dateStr) {
		writeError(w, "Invalid date format, use YYYY-MM-DD", http.StatusBadRequest)
		return
	}

	ctx, cancel := contextWithTimeout(r.Context())
	defer cancel()

	date, _ := time.Parse("2006-01-02", dateStr)
	nextDate := date.AddDate(0, 0, 1)

	query := `
		SELECT g.id, g.game_id, g.season, g.game_type, g.game_date,
		       g.home_team_id, g.away_team_id, g.home_score, g.away_score,
		       g.status, g.inning, g.inning_half, g.stadium_id, g.weather_data,
		       g.attendance, g.game_duration, g.created_at, g.updated_at,
		       ht.name as home_team_name, ht.city as home_team_city, ht.abbreviation as home_team_abbr,
		       at.name as away_team_name, at.city as away_team_city, at.abbreviation as away_team_abbr
		FROM games g
		LEFT JOIN teams ht ON g.home_team_id = ht.id
		LEFT JOIN teams at ON g.away_team_id = at.id
		WHERE g.game_date >= $1 AND g.game_date < $2
		ORDER BY g.game_date ASC`

	rows, err := s.db.Query(ctx, query, date, nextDate)
	if err != nil {
		writeError(w, "Failed to query games", http.StatusInternalServerError)
		return
	}
	defer rows.Close()

	var games []GameWithTeams
	for rows.Next() {
		var g GameWithTeams
		var homeTeamName, homeTeamCity, homeTeamAbbr *string
		var awayTeamName, awayTeamCity, awayTeamAbbr *string

		err := rows.Scan(
			&g.ID, &g.GameID, &g.Season, &g.GameType, &g.GameDate,
			&g.HomeTeamID, &g.AwayTeamID, &g.HomeScore, &g.AwayScore,
			&g.Status, &g.Inning, &g.InningHalf, &g.StadiumID, &g.WeatherData,
			&g.Attendance, &g.GameDuration, &g.CreatedAt, &g.UpdatedAt,
			&homeTeamName, &homeTeamCity, &homeTeamAbbr,
			&awayTeamName, &awayTeamCity, &awayTeamAbbr,
		)
		if err != nil {
			writeError(w, "Failed to scan game", http.StatusInternalServerError)
			return
		}

		// Add team information
		if homeTeamName != nil {
			g.HomeTeam = &Team{
				ID:           g.HomeTeamID,
				Name:         *homeTeamName,
				Abbreviation: *homeTeamAbbr,
			}
		}
		if awayTeamName != nil {
			g.AwayTeam = &Team{
				ID:           g.AwayTeamID,
				Name:         *awayTeamName,
				Abbreviation: *awayTeamAbbr,
			}
		}

		games = append(games, g)
	}

	writeJSON(w, map[string]interface{}{
		"date":  dateStr,
		"games": games,
		"count": len(games),
	})
}

// Simulation proxy handlers
func (s *Server) createSimulationHandler(w http.ResponseWriter, r *http.Request) {
	var req SimulationRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeError(w, "Invalid request body", http.StatusBadRequest)
		return
	}

	if req.GameID == "" {
		writeError(w, "Game ID is required", http.StatusBadRequest)
		return
	}

	// Forward request to simulation engine
	reqBody, _ := json.Marshal(req)
	resp, err := http.Post(s.config.SimEngineURL+"/simulate", "application/json", strings.NewReader(string(reqBody)))
	if err != nil {
		writeError(w, "Failed to communicate with simulation engine", http.StatusServiceUnavailable)
		return
	}
	defer resp.Body.Close()

	// Forward response status and body
	w.WriteHeader(resp.StatusCode)
	w.Header().Set("Content-Type", "application/json")

	var result map[string]interface{}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		writeError(w, "Failed to parse simulation response", http.StatusInternalServerError)
		return
	}

	writeJSON(w, result)
}

func (s *Server) getSimulationHandler(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	simID := vars["id"]

	if simID == "" {
		writeError(w, "Simulation ID is required", http.StatusBadRequest)
		return
	}

	// Forward request to simulation engine
	resp, err := http.Get(s.config.SimEngineURL + "/simulation/" + simID + "/result")
	if err != nil {
		writeError(w, "Failed to communicate with simulation engine", http.StatusServiceUnavailable)
		return
	}
	defer resp.Body.Close()

	// Forward response status and body
	w.WriteHeader(resp.StatusCode)
	w.Header().Set("Content-Type", "application/json")

	var result map[string]interface{}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		writeError(w, "Failed to parse simulation response", http.StatusInternalServerError)
		return
	}

	writeJSON(w, result)
}

func (s *Server) getSimulationStatusHandler(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	simID := vars["id"]

	if simID == "" {
		writeError(w, "Simulation ID is required", http.StatusBadRequest)
		return
	}

	// Forward request to simulation engine
	resp, err := http.Get(s.config.SimEngineURL + "/simulation/" + simID + "/status")
	if err != nil {
		writeError(w, "Failed to communicate with simulation engine", http.StatusServiceUnavailable)
		return
	}
	defer resp.Body.Close()

	// Forward response status and body
	w.WriteHeader(resp.StatusCode)
	w.Header().Set("Content-Type", "application/json")

	var result map[string]interface{}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		writeError(w, "Failed to parse simulation response", http.StatusInternalServerError)
		return
	}

	writeJSON(w, result)
}

// Data management handlers
func (s *Server) refreshDataHandler(w http.ResponseWriter, r *http.Request) {
	// Forward request to data fetcher
	resp, err := http.Post(s.config.DataFetcherURL+"/fetch", "application/json", nil)
	if err != nil {
		writeError(w, "Failed to communicate with data fetcher", http.StatusServiceUnavailable)
		return
	}
	defer resp.Body.Close()

	// Forward response status and body
	w.WriteHeader(resp.StatusCode)
	w.Header().Set("Content-Type", "application/json")

	var result map[string]interface{}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		writeError(w, "Failed to parse data fetcher response", http.StatusInternalServerError)
		return
	}

	writeJSON(w, result)
}

func (s *Server) dataStatusHandler(w http.ResponseWriter, r *http.Request) {
	ctx, cancel := contextWithTimeout(r.Context())
	defer cancel()

	// Get data statistics from database
	var status DataStatus

	// Get current season
	status.CurrentSeason = getCurrentSeason()

	// Get counts
	countQueries := map[string]string{
		"teams":   "SELECT COUNT(*) FROM teams",
		"players": "SELECT COUNT(*) FROM players WHERE status = 'active'",
		"games":   "SELECT COUNT(*) FROM games WHERE season = $1",
	}

	// Get team count
	err := s.db.QueryRow(ctx, countQueries["teams"]).Scan(&status.TotalTeams)
	if err != nil {
		log.Printf("Failed to get team count: %v", err)
	}

	// Get player count
	err = s.db.QueryRow(ctx, countQueries["players"]).Scan(&status.TotalPlayers)
	if err != nil {
		log.Printf("Failed to get player count: %v", err)
	}

	// Get games count for current season
	err = s.db.QueryRow(ctx, countQueries["games"], status.CurrentSeason).Scan(&status.TotalGames)
	if err != nil {
		log.Printf("Failed to get games count: %v", err)
	}

	// Get last update timestamp
	lastUpdateQuery := `
		SELECT MAX(updated_at) as last_update
		FROM (
			SELECT updated_at FROM teams
			UNION ALL
			SELECT updated_at FROM players
			UNION ALL
			SELECT updated_at FROM games
		) combined`

	err = s.db.QueryRow(ctx, lastUpdateQuery).Scan(&status.LastUpdate)
	if err != nil {
		log.Printf("Failed to get last update: %v", err)
		status.LastUpdate = time.Now()
	}

	// Set status based on data availability
	if status.TotalTeams > 0 && status.TotalPlayers > 0 && status.TotalGames > 0 {
		status.Status = "healthy"
	} else {
		status.Status = "incomplete"
	}

	// Also try to get status from data fetcher
	dataFetcherStatus := make(map[string]interface{})
	resp, err := http.Get(s.config.DataFetcherURL + "/status")
	if err == nil {
		defer resp.Body.Close()
		json.NewDecoder(resp.Body).Decode(&dataFetcherStatus)
	}

	writeJSON(w, map[string]interface{}{
		"database_status":     status,
		"data_fetcher_status": dataFetcherStatus,
	})
}

func (s *Server) apiStatusHandler(w http.ResponseWriter, r *http.Request) {
	ctx, cancel := contextWithTimeout(r.Context())
	defer cancel()

	status := map[string]interface{}{
		"service": "Baseball Simulation API Gateway", 
		"version": "2.0.0",
		"status":  "online",
		"time":    time.Now().UTC(),
	}

	// Check database connection
	if err := s.db.Ping(ctx); err != nil {
		status["database"] = "disconnected"
		status["status"] = "degraded"
	} else {
		status["database"] = "connected"
	}

	// Check external services
	services := map[string]string{
		"sim_engine":   s.config.SimEngineURL + "/health",
		"data_fetcher": s.config.DataFetcherURL + "/health",
	}

	for name, url := range services {
		_, err := http.Get(url)
		if err != nil {
			status[name] = "offline"
		} else {
			status[name] = "online"
		}
	}

	writeJSON(w, status)
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

package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
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
	Port            string
	DBHost          string
	DBPort          string
	DBUser          string
	DBPassword      string
	DBName          string
	SimEngineURL    string
	DataFetcherURL  string
}

func NewConfig() *Config {
	return &Config{
		Port:            getEnv("PORT", "8080"),
		DBHost:          getEnv("DB_HOST", "localhost"),
		DBPort:          getEnv("DB_PORT", "5432"),
		DBUser:          getEnv("DB_USER", "baseball_user"),
		DBPassword:      getEnv("DB_PASSWORD", "baseball_pass"),
		DBName:          getEnv("DB_NAME", "baseball_sim"),
		SimEngineURL:    getEnv("SIM_ENGINE_URL", "http://localhost:8081"),
		DataFetcherURL:  getEnv("DATA_FETCHER_URL", "http://localhost:8082"),
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
func (s *Server) healthHandler(w http.ResponseWriter, r *http.Request) {
	health := map[string]interface{}{
		"status": "healthy",
		"time":   time.Now().UTC(),
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

// Placeholder handlers - to be implemented
func (s *Server) getTeamsHandler(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, map[string]string{"message": "Get teams endpoint"})
}

func (s *Server) getTeamHandler(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	writeJSON(w, map[string]string{"message": "Get team endpoint", "id": vars["id"]})
}

func (s *Server) getPlayersHandler(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, map[string]string{"message": "Get players endpoint"})
}

func (s *Server) getPlayerHandler(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	writeJSON(w, map[string]string{"message": "Get player endpoint", "id": vars["id"]})
}

func (s *Server) getPlayerStatsHandler(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	writeJSON(w, map[string]string{"message": "Get player stats endpoint", "id": vars["id"]})
}

func (s *Server) getGamesHandler(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, map[string]string{"message": "Get games endpoint"})
}

func (s *Server) getGameHandler(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	writeJSON(w, map[string]string{"message": "Get game endpoint", "id": vars["id"]})
}

func (s *Server) getGamesByDateHandler(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	writeJSON(w, map[string]string{"message": "Get games by date endpoint", "date": vars["date"]})
}

func (s *Server) createSimulationHandler(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, map[string]string{"message": "Create simulation endpoint"})
}

func (s *Server) getSimulationHandler(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	writeJSON(w, map[string]string{"message": "Get simulation endpoint", "id": vars["id"]})
}

func (s *Server) getSimulationStatusHandler(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	writeJSON(w, map[string]string{"message": "Get simulation status endpoint", "id": vars["id"]})
}

func (s *Server) refreshDataHandler(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, map[string]string{"message": "Refresh data endpoint"})
}

func (s *Server) dataStatusHandler(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, map[string]string{"message": "Data status endpoint"})
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
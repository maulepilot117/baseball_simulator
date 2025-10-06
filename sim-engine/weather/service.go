package weather

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"net/url"
	"sync"
	"time"

	"sim-engine/models"
)

const (
	// OpenWeatherMap API endpoint
	openWeatherAPIURL = "https://api.openweathermap.org/data/2.5/forecast"

	// Cache duration for weather forecasts
	cacheDuration = 30 * time.Minute

	// Timeout for API requests
	requestTimeout = 10 * time.Second
)

// Service handles weather data fetching and caching
type Service struct {
	apiKey     string
	httpClient *http.Client
	cache      *forecastCache
	mu         sync.RWMutex
}

// forecastCache stores weather forecasts with expiration
type forecastCache struct {
	data      map[string]*cachedForecast
	mu        sync.RWMutex
}

type cachedForecast struct {
	weather   models.Weather
	expiresAt time.Time
}

// OpenWeatherResponse represents the API response
type OpenWeatherResponse struct {
	List []struct {
		Dt   int64 `json:"dt"`
		Main struct {
			Temp     float64 `json:"temp"`
			Pressure float64 `json:"pressure"`
			Humidity int     `json:"humidity"`
		} `json:"main"`
		Weather []struct {
			Main        string `json:"main"`
			Description string `json:"description"`
		} `json:"weather"`
		Wind struct {
			Speed float64 `json:"speed"`
			Deg   int     `json:"deg"`
		} `json:"wind"`
		Clouds struct {
			All int `json:"all"`
		} `json:"clouds"`
		Pop  float64 `json:"pop"` // Probability of precipitation
		Rain *struct {
			ThreeH float64 `json:"3h"`
		} `json:"rain,omitempty"`
	} `json:"list"`
	City struct {
		Name    string `json:"name"`
		Country string `json:"country"`
		Coord   struct {
			Lat float64 `json:"lat"`
			Lon float64 `json:"lon"`
		} `json:"coord"`
	} `json:"city"`
}

// StadiumInfo contains stadium data needed for weather decisions
type StadiumInfo struct {
	Name      string
	Location  string
	Latitude  float64
	Longitude float64
	RoofType  string
	Altitude  int
}

// NewService creates a new weather service
func NewService(apiKey string) *Service {
	return &Service{
		apiKey: apiKey,
		httpClient: &http.Client{
			Timeout: requestTimeout,
		},
		cache: &forecastCache{
			data: make(map[string]*cachedForecast),
		},
	}
}

// GetWeatherForGame fetches weather data for a specific game
func (s *Service) GetWeatherForGame(ctx context.Context, stadium StadiumInfo, gameTime time.Time) (models.Weather, error) {
	// Check if stadium has dome or retractable roof (closed by default in bad weather)
	if s.isDome(stadium.RoofType) {
		log.Printf("Stadium %s has dome/indoor roof, using controlled conditions", stadium.Name)
		return s.getControlledConditions(), nil
	}

	// Check cache first
	cacheKey := s.getCacheKey(stadium, gameTime)
	if cached, ok := s.getCachedForecast(cacheKey); ok {
		log.Printf("Using cached weather for %s", stadium.Name)
		return cached, nil
	}

	// Validate coordinates
	if stadium.Latitude == 0 && stadium.Longitude == 0 {
		log.Printf("Warning: No coordinates for stadium %s, using default weather", stadium.Name)
		return s.getDefaultWeather(stadium), nil
	}

	// Fetch forecast from OpenWeatherMap
	weather, err := s.fetchForecast(ctx, stadium, gameTime)
	if err != nil {
		log.Printf("Failed to fetch weather for %s: %v, using default", stadium.Name, err)
		return s.getDefaultWeather(stadium), nil
	}

	// Cache the result
	s.cacheForecast(cacheKey, weather)

	return weather, nil
}

// isDome checks if the stadium is domed or indoor
func (s *Service) isDome(roofType string) bool {
	switch roofType {
	case "dome", "indoor", "fixed_roof", "closed":
		return true
	case "retractable":
		// Retractable roofs are typically closed in bad weather
		// For simulation purposes, we'll treat as outdoor since we want realistic conditions
		return false
	case "outdoor", "open", "":
		return false
	default:
		// Unknown roof type, assume outdoor
		return false
	}
}

// getControlledConditions returns ideal conditions for domed stadiums
func (s *Service) getControlledConditions() models.Weather {
	return models.Weather{
		Temperature: 72, // Perfect 72°F
		WindSpeed:   0,  // No wind indoors
		WindDir:     "calm",
		Humidity:    50, // Controlled humidity
		Pressure:    29.92,
	}
}

// getDefaultWeather returns reasonable outdoor default conditions
func (s *Service) getDefaultWeather(stadium StadiumInfo) models.Weather {
	// Adjust temperature based on season (rough estimate)
	now := time.Now()
	month := now.Month()

	temp := 72
	if month >= 4 && month <= 9 { // Spring/Summer
		temp = 75
	} else if month >= 10 || month <= 3 { // Fall/Winter
		temp = 55
	}

	// Altitude affects air pressure
	pressure := 29.92
	if stadium.Altitude > 0 {
		// Drop ~1 inHg per 1000 feet
		pressure -= float64(stadium.Altitude) / 1000.0
	}

	return models.Weather{
		Temperature: temp,
		WindSpeed:   8,
		WindDir:     "varies",
		Humidity:    55,
		Pressure:    pressure,
	}
}

// fetchForecast calls OpenWeatherMap API
func (s *Service) fetchForecast(ctx context.Context, stadium StadiumInfo, gameTime time.Time) (models.Weather, error) {
	if s.apiKey == "" {
		return models.Weather{}, fmt.Errorf("weather API key not configured")
	}

	// Build API URL
	params := url.Values{}
	params.Add("lat", fmt.Sprintf("%.4f", stadium.Latitude))
	params.Add("lon", fmt.Sprintf("%.4f", stadium.Longitude))
	params.Add("appid", s.apiKey)
	params.Add("units", "imperial") // Fahrenheit, mph
	params.Add("cnt", "40")         // 5 days of 3-hour forecasts

	apiURL := fmt.Sprintf("%s?%s", openWeatherAPIURL, params.Encode())

	// Create request with context
	req, err := http.NewRequestWithContext(ctx, "GET", apiURL, nil)
	if err != nil {
		return models.Weather{}, fmt.Errorf("failed to create request: %w", err)
	}

	// Execute request
	resp, err := s.httpClient.Do(req)
	if err != nil {
		return models.Weather{}, fmt.Errorf("API request failed: %w", err)
	}
	defer resp.Body.Close()

	// Check status code
	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return models.Weather{}, fmt.Errorf("API returned status %d: %s", resp.StatusCode, string(body))
	}

	// Parse response
	var weatherResp OpenWeatherResponse
	if err := json.NewDecoder(resp.Body).Decode(&weatherResp); err != nil {
		return models.Weather{}, fmt.Errorf("failed to parse response: %w", err)
	}

	// Find closest forecast to game time
	weather, err := s.findClosestForecast(weatherResp, gameTime, stadium)
	if err != nil {
		return models.Weather{}, err
	}

	return weather, nil
}

// findClosestForecast finds the forecast entry closest to game time
func (s *Service) findClosestForecast(resp OpenWeatherResponse, gameTime time.Time, stadium StadiumInfo) (models.Weather, error) {
	if len(resp.List) == 0 {
		return models.Weather{}, fmt.Errorf("no forecast data available")
	}

	// Find entry closest to game time
	var closestEntry *struct {
		Dt   int64 `json:"dt"`
		Main struct {
			Temp     float64 `json:"temp"`
			Pressure float64 `json:"pressure"`
			Humidity int     `json:"humidity"`
		} `json:"main"`
		Weather []struct {
			Main        string `json:"main"`
			Description string `json:"description"`
		} `json:"weather"`
		Wind struct {
			Speed float64 `json:"speed"`
			Deg   int     `json:"deg"`
		} `json:"wind"`
		Clouds struct {
			All int `json:"all"`
		} `json:"clouds"`
		Pop  float64 `json:"pop"`
		Rain *struct {
			ThreeH float64 `json:"3h"`
		} `json:"rain,omitempty"`
	}

	minDiff := time.Duration(1<<63 - 1) // Max duration

	for i := range resp.List {
		entry := &resp.List[i]
		forecastTime := time.Unix(entry.Dt, 0)
		diff := gameTime.Sub(forecastTime)
		if diff < 0 {
			diff = -diff
		}

		if diff < minDiff {
			minDiff = diff
			closestEntry = entry
		}
	}

	if closestEntry == nil {
		return models.Weather{}, fmt.Errorf("could not find suitable forecast")
	}

	// Convert to our weather model
	weather := models.Weather{
		Temperature: int(closestEntry.Main.Temp),
		WindSpeed:   int(closestEntry.Wind.Speed),
		WindDir:     s.degreesToDirection(closestEntry.Wind.Deg),
		Humidity:    closestEntry.Main.Humidity,
		Pressure:    closestEntry.Main.Pressure,
	}

	// Adjust pressure for altitude if needed
	if stadium.Altitude > 0 {
		weather.Pressure -= float64(stadium.Altitude) / 1000.0
	}

	return weather, nil
}

// degreesToDirection converts wind direction in degrees to cardinal direction
func (s *Service) degreesToDirection(degrees int) string {
	// Normalize to 0-360
	degrees = degrees % 360
	if degrees < 0 {
		degrees += 360
	}

	// Determine general direction for baseball purposes
	// "out" = blowing toward outfield (helps hitters)
	// "in" = blowing toward infield (hurts hitters)
	// "left"/"right" = cross winds

	switch {
	case degrees >= 338 || degrees < 23:
		return "out" // Wind from home plate toward center field
	case degrees >= 23 && degrees < 68:
		return "right" // Wind from 1B toward 3B
	case degrees >= 68 && degrees < 113:
		return "right" // Wind from 1B toward 3B
	case degrees >= 113 && degrees < 158:
		return "in" // Wind from outfield toward home plate
	case degrees >= 158 && degrees < 203:
		return "in" // Wind from outfield toward home plate
	case degrees >= 203 && degrees < 248:
		return "left" // Wind from 3B toward 1B
	case degrees >= 248 && degrees < 293:
		return "left" // Wind from 3B toward 1B
	case degrees >= 293 && degrees < 338:
		return "out" // Wind from home plate toward center field
	default:
		return "varies"
	}
}

// getCacheKey generates a cache key for a stadium and time
func (s *Service) getCacheKey(stadium StadiumInfo, gameTime time.Time) string {
	// Round to nearest hour for cache efficiency
	rounded := gameTime.Round(time.Hour)
	return fmt.Sprintf("%s_%s", stadium.Name, rounded.Format("2006-01-02T15"))
}

// getCachedForecast retrieves cached forecast if not expired
func (s *Service) getCachedForecast(key string) (models.Weather, bool) {
	s.cache.mu.RLock()
	defer s.cache.mu.RUnlock()

	if cached, ok := s.cache.data[key]; ok {
		if time.Now().Before(cached.expiresAt) {
			return cached.weather, true
		}
		// Expired, will be cleaned up later
	}

	return models.Weather{}, false
}

// cacheForecast stores a forecast in the cache
func (s *Service) cacheForecast(key string, weather models.Weather) {
	s.cache.mu.Lock()
	defer s.cache.mu.Unlock()

	s.cache.data[key] = &cachedForecast{
		weather:   weather,
		expiresAt: time.Now().Add(cacheDuration),
	}
}

// CleanExpiredCache removes expired entries from cache
func (s *Service) CleanExpiredCache() {
	s.cache.mu.Lock()
	defer s.cache.mu.Unlock()

	now := time.Now()
	for key, cached := range s.cache.data {
		if now.After(cached.expiresAt) {
			delete(s.cache.data, key)
		}
	}
}

// StartCacheCleanup starts a background goroutine to clean expired cache entries
func (s *Service) StartCacheCleanup() {
	go func() {
		ticker := time.NewTicker(15 * time.Minute)
		defer ticker.Stop()

		for range ticker.C {
			s.CleanExpiredCache()
			log.Printf("Weather cache cleaned: %d entries remaining", len(s.cache.data))
		}
	}()
}

// GetCacheStats returns cache statistics for monitoring
func (s *Service) GetCacheStats() map[string]interface{} {
	s.cache.mu.RLock()
	defer s.cache.mu.RUnlock()

	return map[string]interface{}{
		"entries": len(s.cache.data),
		"size":    len(s.cache.data),
	}
}

// ValidateAPIKey checks if the API key is valid by making a test request
func (s *Service) ValidateAPIKey(ctx context.Context) error {
	if s.apiKey == "" {
		return fmt.Errorf("API key is empty")
	}

	// Make test request to a known location (NYC)
	params := url.Values{}
	params.Add("lat", "40.7128")
	params.Add("lon", "-74.0060")
	params.Add("appid", s.apiKey)
	params.Add("cnt", "1")

	apiURL := fmt.Sprintf("%s?%s", openWeatherAPIURL, params.Encode())
	log.Printf("Validating weather API key with URL: %s", apiURL)

	req, err := http.NewRequestWithContext(ctx, "GET", apiURL, nil)
	if err != nil {
		log.Printf("Failed to create validation request: %v", err)
		return err
	}

	resp, err := s.httpClient.Do(req)
	if err != nil {
		log.Printf("Weather API validation request error: %v", err)
		return fmt.Errorf("API key validation request failed: %w", err)
	}
	defer resp.Body.Close()

	body, _ := io.ReadAll(resp.Body)
	log.Printf("Weather API validation response: status=%d, body=%s", resp.StatusCode, string(body))

	if resp.StatusCode == 401 {
		return fmt.Errorf("invalid API key")
	} else if resp.StatusCode != 200 {
		return fmt.Errorf("API key validation failed with status %d: %s", resp.StatusCode, string(body))
	}

	log.Printf("Weather API key validated successfully")
	return nil
}

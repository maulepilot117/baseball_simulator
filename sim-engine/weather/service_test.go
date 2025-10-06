package weather

import (
	"context"
	"testing"
	"time"

	"sim-engine/models"
)

// TestNewService tests service initialization
func TestNewService(t *testing.T) {
	apiKey := "test_key_123"
	service := NewService(apiKey)

	if service.apiKey != apiKey {
		t.Errorf("Expected API key %s, got %s", apiKey, service.apiKey)
	}

	if service.cache == nil {
		t.Error("Cache should be initialized")
	}

	if service.httpClient == nil {
		t.Error("HTTP client should be initialized")
	}
}

// TestIsDome tests stadium roof type detection
func TestIsDome(t *testing.T) {
	service := NewService("test_key")

	tests := []struct {
		roofType string
		expected bool
	}{
		{"dome", true},
		{"indoor", true},
		{"fixed_roof", true},
		{"closed", true},
		{"retractable", false}, // Treated as outdoor for realistic weather
		{"outdoor", false},
		{"open", false},
		{"", false},
		{"unknown", false},
	}

	for _, tt := range tests {
		t.Run(tt.roofType, func(t *testing.T) {
			result := service.isDome(tt.roofType)
			if result != tt.expected {
				t.Errorf("isDome(%s) = %v, want %v", tt.roofType, result, tt.expected)
			}
		})
	}
}

// TestGetControlledConditions tests indoor stadium conditions
func TestGetControlledConditions(t *testing.T) {
	service := NewService("test_key")
	weather := service.getControlledConditions()

	if weather.Temperature != 72 {
		t.Errorf("Expected temperature 72, got %d", weather.Temperature)
	}

	if weather.WindSpeed != 0 {
		t.Errorf("Expected wind speed 0, got %d", weather.WindSpeed)
	}

	if weather.WindDir != "calm" {
		t.Errorf("Expected wind direction 'calm', got %s", weather.WindDir)
	}

	if weather.Humidity != 50 {
		t.Errorf("Expected humidity 50, got %d", weather.Humidity)
	}
}

// TestGetDefaultWeather tests default weather generation
func TestGetDefaultWeather(t *testing.T) {
	service := NewService("test_key")

	tests := []struct {
		name     string
		stadium  StadiumInfo
		checkAlt bool
	}{
		{
			name: "sea level stadium",
			stadium: StadiumInfo{
				Name:     "Test Stadium",
				Altitude: 0,
			},
			checkAlt: false,
		},
		{
			name: "high altitude stadium",
			stadium: StadiumInfo{
				Name:     "Coors Field",
				Altitude: 5280,
			},
			checkAlt: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			weather := service.getDefaultWeather(tt.stadium)

			if weather.Temperature < 50 || weather.Temperature > 80 {
				t.Errorf("Temperature %d out of reasonable range", weather.Temperature)
			}

			if tt.checkAlt && weather.Pressure >= 29.92 {
				t.Errorf("High altitude stadium should have lower pressure, got %f", weather.Pressure)
			}
		})
	}
}

// TestDegreesToDirection tests wind direction conversion
func TestDegreesToDirection(t *testing.T) {
	service := NewService("test_key")

	tests := []struct {
		degrees  int
		expected string
	}{
		{0, "out"},
		{45, "right"},
		{90, "right"},
		{135, "in"},
		{180, "in"},
		{225, "left"},
		{270, "left"},
		{315, "out"},
		{360, "out"},
		{315, "out"}, // Should be "out" not "left"
	}

	for _, tt := range tests {
		t.Run("", func(t *testing.T) {
			result := service.degreesToDirection(tt.degrees)
			if result != tt.expected {
				t.Errorf("degreesToDirection(%d) = %s, want %s", tt.degrees, result, tt.expected)
			}
		})
	}
}

// TestGetWeatherForGame_DomeStadium tests dome stadium handling
func TestGetWeatherForGame_DomeStadium(t *testing.T) {
	service := NewService("") // No API key needed for dome test
	ctx := context.Background()

	stadium := StadiumInfo{
		Name:     "Tropicana Field",
		RoofType: "dome",
	}

	gameTime := time.Now().Add(24 * time.Hour)

	weather, err := service.GetWeatherForGame(ctx, stadium, gameTime)
	if err != nil {
		t.Fatalf("Unexpected error: %v", err)
	}

	if weather.Temperature != 72 {
		t.Errorf("Expected controlled temp 72, got %d", weather.Temperature)
	}

	if weather.WindSpeed != 0 {
		t.Errorf("Expected no wind in dome, got %d", weather.WindSpeed)
	}
}

// TestGetWeatherForGame_NoCoordinates tests fallback with no coordinates
func TestGetWeatherForGame_NoCoordinates(t *testing.T) {
	service := NewService("") // No API key
	ctx := context.Background()

	stadium := StadiumInfo{
		Name:      "Unknown Stadium",
		RoofType:  "outdoor",
		Latitude:  0,
		Longitude: 0,
	}

	gameTime := time.Now().Add(24 * time.Hour)

	weather, err := service.GetWeatherForGame(ctx, stadium, gameTime)
	if err != nil {
		t.Fatalf("Unexpected error: %v", err)
	}

	// Should return default weather
	if weather.Temperature == 0 {
		t.Error("Expected non-zero temperature from default weather")
	}
}

// TestCacheKey tests cache key generation
func TestCacheKey(t *testing.T) {
	service := NewService("test_key")

	stadium := StadiumInfo{
		Name: "Fenway Park",
	}

	gameTime1 := time.Date(2024, 10, 6, 19, 0, 0, 0, time.UTC)
	gameTime2 := time.Date(2024, 10, 6, 20, 0, 0, 0, time.UTC)

	key1 := service.getCacheKey(stadium, gameTime1)
	key2 := service.getCacheKey(stadium, gameTime2)

	// Different hours should have different keys
	if key1 == key2 {
		t.Errorf("Expected different cache keys for different hours: %s vs %s", key1, key2)
	}
}

// TestCacheOperations tests cache get/set operations
func TestCacheOperations(t *testing.T) {
	service := NewService("test_key")

	key := "test_key_123"
	weather := models.Weather{
		Temperature: 75,
		WindSpeed:   10,
		WindDir:     "out",
		Humidity:    60,
		Pressure:    29.92,
	}

	// Cache should be empty initially
	if _, ok := service.getCachedForecast(key); ok {
		t.Error("Cache should be empty initially")
	}

	// Store in cache
	service.cacheForecast(key, weather)

	// Should retrieve from cache
	cached, ok := service.getCachedForecast(key)
	if !ok {
		t.Error("Should retrieve cached forecast")
	}

	if cached.Temperature != weather.Temperature {
		t.Errorf("Expected temperature %d, got %d", weather.Temperature, cached.Temperature)
	}
}

// TestCacheExpiration tests cache expiration
func TestCacheExpiration(t *testing.T) {
	service := NewService("test_key")

	key := "expiring_key"
	weather := models.Weather{Temperature: 70}

	// Manually insert expired entry
	service.cache.mu.Lock()
	service.cache.data[key] = &cachedForecast{
		weather:   weather,
		expiresAt: time.Now().Add(-1 * time.Hour), // Already expired
	}
	service.cache.mu.Unlock()

	// Should not retrieve expired forecast
	if _, ok := service.getCachedForecast(key); ok {
		t.Error("Should not retrieve expired forecast")
	}
}

// TestCleanExpiredCache tests cache cleanup
func TestCleanExpiredCache(t *testing.T) {
	service := NewService("test_key")

	// Add valid entry
	service.cache.mu.Lock()
	service.cache.data["valid"] = &cachedForecast{
		weather:   models.Weather{Temperature: 70},
		expiresAt: time.Now().Add(1 * time.Hour),
	}

	// Add expired entry
	service.cache.data["expired"] = &cachedForecast{
		weather:   models.Weather{Temperature: 65},
		expiresAt: time.Now().Add(-1 * time.Hour),
	}
	service.cache.mu.Unlock()

	// Clean cache
	service.CleanExpiredCache()

	service.cache.mu.RLock()
	defer service.cache.mu.RUnlock()

	if _, ok := service.cache.data["expired"]; ok {
		t.Error("Expired entry should be removed")
	}

	if _, ok := service.cache.data["valid"]; !ok {
		t.Error("Valid entry should remain")
	}
}

// TestGetCacheStats tests cache statistics
func TestGetCacheStats(t *testing.T) {
	service := NewService("test_key")

	// Add some entries
	service.cacheForecast("key1", models.Weather{Temperature: 70})
	service.cacheForecast("key2", models.Weather{Temperature: 75})

	stats := service.GetCacheStats()

	if entries, ok := stats["entries"].(int); !ok || entries != 2 {
		t.Errorf("Expected 2 cache entries, got %v", stats["entries"])
	}
}

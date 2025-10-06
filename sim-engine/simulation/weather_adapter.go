package simulation

import (
	"context"
	"time"

	"sim-engine/models"
	"sim-engine/weather"
)

// WeatherServiceAdapter adapts the weather service to match the simulation interface
type WeatherServiceAdapter struct {
	service *weather.Service
}

// NewWeatherServiceAdapter creates a new adapter
func NewWeatherServiceAdapter(service *weather.Service) *WeatherServiceAdapter {
	return &WeatherServiceAdapter{
		service: service,
	}
}

// GetWeatherForGame implements the WeatherService interface
func (w *WeatherServiceAdapter) GetWeatherForGame(ctx context.Context, stadium StadiumInfo, gameTime time.Time) (models.Weather, error) {
	// Convert simulation.StadiumInfo to weather.StadiumInfo
	weatherStadiumInfo := weather.StadiumInfo{
		Name:      stadium.Name,
		Location:  stadium.Location,
		Latitude:  stadium.Latitude,
		Longitude: stadium.Longitude,
		RoofType:  stadium.RoofType,
		Altitude:  stadium.Altitude,
	}

	return w.service.GetWeatherForGame(ctx, weatherStadiumInfo, gameTime)
}

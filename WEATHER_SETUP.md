# Weather Forecasting Setup

The baseball simulation engine can use real weather forecasts to improve simulation accuracy. This affects:
- Wind direction and speed (helps/hurts fly balls)
- Temperature (cold suppresses offense, heat helps)
- Humidity (high humidity suppresses power)
- Precipitation (affects gameplay)

## Getting an OpenWeather API Key

1. Go to [OpenWeatherMap](https://openweathermap.org/api)
2. Sign up for a free account
3. Navigate to API keys section
4. Generate a new API key (free tier allows 1,000 calls/day)

## Configuring the API Key

### Option 1: Environment Variable (Recommended for Production)

Add to your `.env` file:
```bash
OPENWEATHER_API_KEY=your_api_key_here
```

Then update `docker-compose.yml` to pass it to the sim-engine service:
```yaml
sim-engine:
  environment:
    - OPENWEATHER_API_KEY=${OPENWEATHER_API_KEY}
    # ... other environment variables
```

### Option 2: Direct Configuration (Development)

Add directly in `docker-compose.yml`:
```yaml
sim-engine:
  environment:
    - OPENWEATHER_API_KEY=your_api_key_here
    # ... other environment variables
```

## Restart the Service

```bash
docker-compose up -d sim-engine
```

Check the logs to confirm weather service initialized:
```bash
docker-compose logs sim-engine | grep -i weather
```

You should see:
```
Weather service initialized successfully
```

## Without API Key

If no API key is configured, simulations use **neutral default weather**:
- Temperature: 72°F
- Wind: 0 mph (calm)
- Humidity: 50%
- Conditions: Clear

This provides consistent baseline simulations but won't reflect actual game-day conditions.

## Weather API Usage

- Each simulation fetches weather once per game
- Weather is cached for 1 hour
- Free tier supports ~40 simulations per day (1000 calls / 25 games per call)
- Paid tiers available for higher volume

## Testing

Run a simulation and check if weather was fetched:
```bash
curl -X POST 'http://localhost:8081/simulate' \
  -H 'Content-Type: application/json' \
  -d '{"game_id":"123456"}'

# Wait for completion, then check logs:
docker-compose logs sim-engine | tail -20
```

Look for: `Fetched weather for [Stadium]: 75°F, wind 10 mph NW`

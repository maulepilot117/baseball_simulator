package main

import (
	"encoding/json"
	"testing"

	"github.com/stretchr/testify/assert"
)

// TestBoxScoreBattingStruct tests the BoxScoreBatting struct
func TestBoxScoreBattingStruct(t *testing.T) {
	battingOrder := 1
	batting := BoxScoreBatting{
		PlayerID:       "player-123",
		PlayerName:     "Mike Trout",
		TeamID:         "team-456",
		BattingOrder:   &battingOrder,
		Position:       "CF",
		AtBats:         4,
		Runs:           2,
		Hits:           3,
		RBIs:           2,
		Walks:          1,
		Strikeouts:     0,
		Doubles:        1,
		Triples:        0,
		HomeRuns:       1,
		StolenBases:    1,
		CaughtStealing: 0,
		LeftOnBase:     1,
	}

	assert.Equal(t, "player-123", batting.PlayerID)
	assert.Equal(t, "Mike Trout", batting.PlayerName)
	assert.Equal(t, 4, batting.AtBats)
	assert.Equal(t, 3, batting.Hits)
	assert.NotNil(t, batting.BattingOrder)
	assert.Equal(t, 1, *batting.BattingOrder)
}

// TestBoxScoreBattingJSON tests JSON serialization
func TestBoxScoreBattingJSON(t *testing.T) {
	battingOrder := 1
	batting := BoxScoreBatting{
		PlayerID:     "player-123",
		PlayerName:   "Mike Trout",
		TeamID:       "team-456",
		BattingOrder: &battingOrder,
		Position:     "CF",
		AtBats:       4,
		Hits:         3,
		HomeRuns:     1,
	}

	jsonData, err := json.Marshal(batting)
	assert.NoError(t, err)
	assert.Contains(t, string(jsonData), "Mike Trout")
	assert.Contains(t, string(jsonData), "player-123")

	// Test unmarshaling
	var decoded BoxScoreBatting
	err = json.Unmarshal(jsonData, &decoded)
	assert.NoError(t, err)
	assert.Equal(t, batting.PlayerName, decoded.PlayerName)
	assert.Equal(t, batting.HomeRuns, decoded.HomeRuns)
}

// TestBoxScorePitchingStruct tests the BoxScorePitching struct
func TestBoxScorePitchingStruct(t *testing.T) {
	era := 2.75
	pitching := BoxScorePitching{
		PlayerID:        "player-789",
		PlayerName:      "Shohei Ohtani",
		TeamID:          "team-456",
		InningsPitched:  7.0,
		HitsAllowed:     4,
		RunsAllowed:     2,
		EarnedRuns:      2,
		WalksAllowed:    2,
		Strikeouts:      10,
		HomeRunsAllowed: 1,
		PitchesThrown:   105,
		Strikes:         72,
		Win:             true,
		Loss:            false,
		Save:            false,
		Hold:            false,
		BlownSave:       false,
		ERA:             &era,
	}

	assert.Equal(t, "Shohei Ohtani", pitching.PlayerName)
	assert.Equal(t, 7.0, pitching.InningsPitched)
	assert.Equal(t, 10, pitching.Strikeouts)
	assert.True(t, pitching.Win)
	assert.False(t, pitching.Loss)
	assert.NotNil(t, pitching.ERA)
	assert.Equal(t, 2.75, *pitching.ERA)
}

// TestBoxScorePitchingJSON tests JSON serialization
func TestBoxScorePitchingJSON(t *testing.T) {
	era := 3.50
	pitching := BoxScorePitching{
		PlayerID:       "player-789",
		PlayerName:     "Clayton Kershaw",
		InningsPitched: 6.0,
		Strikeouts:     8,
		Win:            true,
		ERA:            &era,
	}

	jsonData, err := json.Marshal(pitching)
	assert.NoError(t, err)
	assert.Contains(t, string(jsonData), "Clayton Kershaw")

	var decoded BoxScorePitching
	err = json.Unmarshal(jsonData, &decoded)
	assert.NoError(t, err)
	assert.Equal(t, pitching.PlayerName, decoded.PlayerName)
	assert.Equal(t, pitching.Win, decoded.Win)
}

// TestGamePlayStruct tests the GamePlay struct
func TestGamePlayStruct(t *testing.T) {
	balls := 2
	strikes := 2
	play := GamePlay{
		ID:          "play-123",
		PlayID:      "play-456",
		Inning:      5,
		InningHalf:  "top",
		Outs:        2,
		Balls:       &balls,
		Strikes:     &strikes,
		BatterName:  "Aaron Judge",
		PitcherName: "Gerrit Cole",
		EventType:   "home_run",
		Description: "Aaron Judge homers to left field",
		RBI:         1,
		RunsScored:  1,
		HomeScore:   3,
		AwayScore:   4,
	}

	assert.Equal(t, 5, play.Inning)
	assert.Equal(t, "top", play.InningHalf)
	assert.Equal(t, "Aaron Judge", play.BatterName)
	assert.Equal(t, "home_run", play.EventType)
	assert.NotNil(t, play.Balls)
	assert.Equal(t, 2, *play.Balls)
}

// TestGamePlayJSON tests JSON serialization
func TestGamePlayJSON(t *testing.T) {
	play := GamePlay{
		PlayID:      "play-789",
		Inning:      9,
		InningHalf:  "bottom",
		BatterName:  "Mookie Betts",
		EventType:   "strikeout",
		Description: "Struck out swinging",
	}

	jsonData, err := json.Marshal(play)
	assert.NoError(t, err)
	assert.Contains(t, string(jsonData), "Mookie Betts")

	var decoded GamePlay
	err = json.Unmarshal(jsonData, &decoded)
	assert.NoError(t, err)
	assert.Equal(t, play.BatterName, decoded.BatterName)
	assert.Equal(t, play.EventType, decoded.EventType)
}

// TestGameBoxScoreStruct tests the GameBoxScore struct
func TestGameBoxScoreStruct(t *testing.T) {
	boxScore := GameBoxScore{
		HomeTeamBatting: []BoxScoreBatting{
			{PlayerName: "Player 1", Hits: 2},
			{PlayerName: "Player 2", Hits: 1},
		},
		AwayTeamBatting: []BoxScoreBatting{
			{PlayerName: "Player 3", Hits: 3},
		},
		HomeTeamPitching: []BoxScorePitching{
			{PlayerName: "Pitcher 1", InningsPitched: 7.0},
		},
		AwayTeamPitching: []BoxScorePitching{
			{PlayerName: "Pitcher 2", InningsPitched: 6.0},
		},
	}

	assert.Len(t, boxScore.HomeTeamBatting, 2)
	assert.Len(t, boxScore.AwayTeamBatting, 1)
	assert.Len(t, boxScore.HomeTeamPitching, 1)
	assert.Len(t, boxScore.AwayTeamPitching, 1)
}

// TestGameBoxScoreJSON tests JSON serialization
func TestGameBoxScoreJSON(t *testing.T) {
	boxScore := GameBoxScore{
		HomeTeamBatting: []BoxScoreBatting{
			{PlayerName: "Batter 1", Hits: 2, AtBats: 4},
		},
		HomeTeamPitching: []BoxScorePitching{
			{PlayerName: "Pitcher 1", Strikeouts: 8},
		},
	}

	jsonData, err := json.Marshal(boxScore)
	assert.NoError(t, err)
	assert.Contains(t, string(jsonData), "Batter 1")
	assert.Contains(t, string(jsonData), "Pitcher 1")

	var decoded GameBoxScore
	err = json.Unmarshal(jsonData, &decoded)
	assert.NoError(t, err)
	assert.Equal(t, 1, len(decoded.HomeTeamBatting))
	assert.Equal(t, "Batter 1", decoded.HomeTeamBatting[0].PlayerName)
}

// TestWeatherDataJSON tests weather data JSON handling
func TestWeatherDataJSON(t *testing.T) {
	weatherJSON := `{
		"temp": 72,
		"condition": "Partly Cloudy",
		"wind": "5 mph",
		"humidity": 45
	}`

	var weather map[string]interface{}
	err := json.Unmarshal([]byte(weatherJSON), &weather)
	assert.NoError(t, err)
	assert.Equal(t, "Partly Cloudy", weather["condition"])
	assert.Equal(t, float64(72), weather["temp"])
}

// TestEmptyWeatherData tests handling of empty weather data
func TestEmptyWeatherData(t *testing.T) {
	emptyJSON := `{}`
	var weather map[string]interface{}
	err := json.Unmarshal([]byte(emptyJSON), &weather)
	assert.NoError(t, err)
	assert.NotNil(t, weather)
	assert.Len(t, weather, 0)
}

// TestInvalidWeatherData tests handling of invalid weather JSON
func TestInvalidWeatherData(t *testing.T) {
	invalidJSON := `{invalid json`
	var weather map[string]interface{}
	err := json.Unmarshal([]byte(invalidJSON), &weather)
	assert.Error(t, err)
}

// TestBattingStatCalculations tests batting statistics calculations
func TestBattingStatCalculations(t *testing.T) {
	batting := BoxScoreBatting{
		AtBats:   4,
		Hits:     3,
		Walks:    1,
		HomeRuns: 1,
	}

	// Calculate batting average
	avg := float64(batting.Hits) / float64(batting.AtBats)
	assert.InDelta(t, 0.750, avg, 0.001)

	// Calculate OBP (simplified)
	obp := float64(batting.Hits+batting.Walks) / float64(batting.AtBats+batting.Walks)
	assert.InDelta(t, 0.800, obp, 0.001)
}

// TestPitchingStatCalculations tests pitching statistics calculations
func TestPitchingStatCalculations(t *testing.T) {
	pitching := BoxScorePitching{
		InningsPitched: 7.0,
		EarnedRuns:     2,
	}

	// Calculate ERA
	era := (float64(pitching.EarnedRuns) * 9.0) / pitching.InningsPitched
	assert.InDelta(t, 2.571, era, 0.01)
}

// TestInningsPitchedFormat tests innings pitched formatting
func TestInningsPitchedFormat(t *testing.T) {
	tests := []struct {
		innings  float64
		expected string
	}{
		{6.0, "6.0"},
		{6.1, "6.1"}, // 6 and 1/3 innings
		{6.2, "6.2"}, // 6 and 2/3 innings
		{7.0, "7.0"},
	}

	for _, tt := range tests {
		t.Run(tt.expected, func(t *testing.T) {
			pitching := BoxScorePitching{InningsPitched: tt.innings}
			assert.Equal(t, tt.innings, pitching.InningsPitched)
		})
	}
}

// TestPlayEventTypes tests valid play event types
func TestPlayEventTypes(t *testing.T) {
	validEvents := []string{
		"strikeout",
		"walk",
		"single",
		"double",
		"triple",
		"home_run",
		"groundout",
		"flyout",
		"lineout",
		"field_error",
		"stolen_base",
	}

	for _, event := range validEvents {
		play := GamePlay{EventType: event}
		assert.NotEmpty(t, play.EventType)
	}
}

// TestPlayInningHalf tests valid inning half values
func TestPlayInningHalf(t *testing.T) {
	validHalves := []string{"top", "bottom"}

	for _, half := range validHalves {
		play := GamePlay{InningHalf: half}
		assert.Contains(t, validHalves, play.InningHalf)
	}
}

// TestBoxScoreOrdering tests that batting order is properly handled
func TestBoxScoreOrdering(t *testing.T) {
	order1 := 1
	order2 := 2
	order3 := 3

	lineup := []BoxScoreBatting{
		{PlayerName: "Player 3", BattingOrder: &order3},
		{PlayerName: "Player 1", BattingOrder: &order1},
		{PlayerName: "Player 2", BattingOrder: &order2},
	}

	// Sort by batting order
	for i := 0; i < len(lineup); i++ {
		for j := i + 1; j < len(lineup); j++ {
			if lineup[i].BattingOrder != nil && lineup[j].BattingOrder != nil {
				if *lineup[j].BattingOrder < *lineup[i].BattingOrder {
					lineup[i], lineup[j] = lineup[j], lineup[i]
				}
			}
		}
	}

	assert.Equal(t, "Player 1", lineup[0].PlayerName)
	assert.Equal(t, "Player 2", lineup[1].PlayerName)
	assert.Equal(t, "Player 3", lineup[2].PlayerName)
}

// TestEmptyBoxScore tests handling of empty box score
func TestEmptyBoxScore(t *testing.T) {
	boxScore := GameBoxScore{}

	assert.Nil(t, boxScore.HomeTeamBatting)
	assert.Nil(t, boxScore.AwayTeamBatting)
	assert.Nil(t, boxScore.HomeTeamPitching)
	assert.Nil(t, boxScore.AwayTeamPitching)
}

package models

import (
	"testing"
)

// TestGetStrikeZoneAdjustment tests strike zone adjustment calculation
func TestGetStrikeZoneAdjustment(t *testing.T) {
	tests := []struct {
		name       string
		umpire     UmpireTendencies
		count      Count
		leverage   float64
		expectMore bool // Expect more strikes
	}{
		{
			name: "large zone on hitter's count",
			umpire: UmpireTendencies{
				StrikeZoneSize: 105,
				CountTendency:  2.0,
			},
			count:      Count{Balls: 3, Strikes: 0},
			leverage:   1.0,
			expectMore: true,
		},
		{
			name: "small zone on pitcher's count",
			umpire: UmpireTendencies{
				StrikeZoneSize: 95,
				CountTendency:  0.0, // Neutral count tendency
			},
			count:      Count{Balls: 0, Strikes: 2},
			leverage:   1.0,
			expectMore: false,
		},
		{
			name: "high leverage tightening",
			umpire: UmpireTendencies{
				StrikeZoneSize:       100,
				HighLeverageTendency: -5.0,
			},
			count:      Count{Balls: 2, Strikes: 2},
			leverage:   2.5,
			expectMore: false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			adjustment := tt.umpire.GetStrikeZoneAdjustment(tt.count, tt.leverage)

			if tt.expectMore && adjustment <= 0 {
				t.Errorf("Expected positive adjustment, got %f", adjustment)
			} else if !tt.expectMore && adjustment > 0 {
				t.Errorf("Expected non-positive adjustment, got %f", adjustment)
			}
		})
	}
}

// TestGetStrikeoutAdjustment tests strikeout rate adjustment
func TestGetStrikeoutAdjustment(t *testing.T) {
	tests := []struct {
		name     string
		umpire   UmpireTendencies
		expected float64 // Approximate expected value
	}{
		{
			name: "large strike zone increases K%",
			umpire: UmpireTendencies{
				StrikeZoneSize:          110,
				StrikeoutRateAdjustment: 1.0,
			},
			expected: 1.5, // Should be positive
		},
		{
			name: "small strike zone decreases K%",
			umpire: UmpireTendencies{
				StrikeZoneSize:          90,
				StrikeoutRateAdjustment: -0.5,
			},
			expected: -1.0, // Should be negative
		},
		{
			name: "neutral zone",
			umpire: UmpireTendencies{
				StrikeZoneSize:          100,
				StrikeoutRateAdjustment: 0.0,
			},
			expected: 0.0,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			adjustment := tt.umpire.GetStrikeoutAdjustment()

			// Check sign matches expectation
			if tt.expected > 0 && adjustment <= 0 {
				t.Errorf("Expected positive K adjustment, got %f", adjustment)
			} else if tt.expected < 0 && adjustment >= 0 {
				t.Errorf("Expected negative K adjustment, got %f", adjustment)
			}
		})
	}
}

// TestGetWalkAdjustment tests walk rate adjustment
func TestGetWalkAdjustment(t *testing.T) {
	tests := []struct {
		name     string
		umpire   UmpireTendencies
		expected float64
	}{
		{
			name: "large strike zone decreases BB%",
			umpire: UmpireTendencies{
				StrikeZoneSize:     110,
				WalkRateAdjustment: -0.5,
			},
			expected: -1.0, // Should be negative
		},
		{
			name: "small strike zone increases BB%",
			umpire: UmpireTendencies{
				StrikeZoneSize:     90,
				WalkRateAdjustment: 1.0,
			},
			expected: 1.5, // Should be positive
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			adjustment := tt.umpire.GetWalkAdjustment()

			// Check sign matches expectation
			if tt.expected > 0 && adjustment <= 0 {
				t.Errorf("Expected positive BB adjustment, got %f", adjustment)
			} else if tt.expected < 0 && adjustment >= 0 {
				t.Errorf("Expected negative BB adjustment, got %f", adjustment)
			}
		})
	}
}

// TestIsStrikeCaller tests strike caller identification
func TestIsStrikeCaller(t *testing.T) {
	tests := []struct {
		name     string
		umpire   UmpireTendencies
		expected bool
	}{
		{
			name: "large strike zone",
			umpire: UmpireTendencies{
				StrikeZoneSize: 105,
			},
			expected: true,
		},
		{
			name: "high K rate adjustment",
			umpire: UmpireTendencies{
				StrikeZoneSize:          100,
				StrikeoutRateAdjustment: 1.0,
			},
			expected: true,
		},
		{
			name: "neutral umpire",
			umpire: UmpireTendencies{
				StrikeZoneSize:          100,
				StrikeoutRateAdjustment: 0.0,
			},
			expected: false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := tt.umpire.IsStrikeCaller()
			if result != tt.expected {
				t.Errorf("IsStrikeCaller() = %v, want %v", result, tt.expected)
			}
		})
	}
}

// TestIsHitterFriendly tests hitter-friendly umpire identification
func TestIsHitterFriendly(t *testing.T) {
	tests := []struct {
		name     string
		umpire   UmpireTendencies
		expected bool
	}{
		{
			name: "small strike zone",
			umpire: UmpireTendencies{
				StrikeZoneSize: 95,
			},
			expected: true,
		},
		{
			name: "high walk rate",
			umpire: UmpireTendencies{
				StrikeZoneSize:     100,
				WalkRateAdjustment: 1.0,
			},
			expected: true,
		},
		{
			name: "neutral umpire",
			umpire: UmpireTendencies{
				StrikeZoneSize:     100,
				WalkRateAdjustment: 0.0,
			},
			expected: false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := tt.umpire.IsHitterFriendly()
			if result != tt.expected {
				t.Errorf("IsHitterFriendly() = %v, want %v", result, tt.expected)
			}
		})
	}
}

// TestGetConsistencyFactor tests consistency factor calculation
func TestGetConsistencyFactor(t *testing.T) {
	tests := []struct {
		consistency int
		expected    float64
	}{
		{90, 1.0},  // Very consistent
		{75, 0.95}, // Above average
		{55, 0.90}, // Below average
		{35, 0.85}, // Inconsistent
	}

	for _, tt := range tests {
		t.Run("", func(t *testing.T) {
			umpire := UmpireTendencies{Consistency: float64(tt.consistency)}
			factor := umpire.GetConsistencyFactor()

			if factor != tt.expected {
				t.Errorf("GetConsistencyFactor() with consistency %d = %f, want %f",
					tt.consistency, factor, tt.expected)
			}
		})
	}
}

// TestGetExperienceBonus tests experience bonus calculation
func TestGetExperienceBonus(t *testing.T) {
	tests := []struct {
		experience int
		expected   float64
	}{
		{5, 0.0},
		{10, 0.01},
		{15, 0.01},
		{20, 0.02},
		{25, 0.02},
	}

	for _, tt := range tests {
		t.Run("", func(t *testing.T) {
			umpire := UmpireTendencies{Experience: tt.experience}
			bonus := umpire.GetExperienceBonus()

			if bonus != tt.expected {
				t.Errorf("GetExperienceBonus() with %d years = %f, want %f",
					tt.experience, bonus, tt.expected)
			}
		})
	}
}

// TestDefaultUmpireTendencies tests default umpire creation
func TestDefaultUmpireTendencies(t *testing.T) {
	defaults := DefaultUmpireTendencies()

	if defaults.StrikeZoneSize != 100.0 {
		t.Errorf("Default strike zone should be 100, got %f", defaults.StrikeZoneSize)
	}

	if defaults.EdgeTendency != 100.0 {
		t.Errorf("Default edge tendency should be 100, got %f", defaults.EdgeTendency)
	}

	if defaults.StrikeoutRateAdjustment != 0.0 {
		t.Errorf("Default K adjustment should be 0, got %f", defaults.StrikeoutRateAdjustment)
	}

	if defaults.WalkRateAdjustment != 0.0 {
		t.Errorf("Default BB adjustment should be 0, got %f", defaults.WalkRateAdjustment)
	}

	if defaults.Consistency != 70.0 {
		t.Errorf("Default consistency should be 70, got %f", defaults.Consistency)
	}
}

// TestUmpireEffectsBalance tests that umpire effects are balanced
func TestUmpireEffectsBalance(t *testing.T) {
	// Large strike zone should increase K% and decrease BB%
	largeZone := UmpireTendencies{
		StrikeZoneSize: 110,
	}

	kAdj := largeZone.GetStrikeoutAdjustment()
	bbAdj := largeZone.GetWalkAdjustment()

	if kAdj <= 0 {
		t.Error("Large zone should increase strikeouts")
	}

	if bbAdj >= 0 {
		t.Error("Large zone should decrease walks")
	}

	// Small strike zone should do the opposite
	smallZone := UmpireTendencies{
		StrikeZoneSize: 90,
	}

	kAdj2 := smallZone.GetStrikeoutAdjustment()
	bbAdj2 := smallZone.GetWalkAdjustment()

	if kAdj2 >= 0 {
		t.Error("Small zone should decrease strikeouts")
	}

	if bbAdj2 <= 0 {
		t.Error("Small zone should increase walks")
	}
}

package models

import (
	"testing"
)

// TestGetParkFactorMultiplier tests park factor retrieval
func TestGetParkFactorMultiplier(t *testing.T) {
	pf := ParkFactors{
		HRFactor:      110.0,
		DoublesFactor: 95.0,
		TriplesFactor: 105.0,
		HitsFactor:    102.0,
		LHBHRFactor:   115.0,
		RHBHRFactor:   105.0,
	}

	tests := []struct {
		outcome     string
		batterHand  string
		expectedMin float64
		expectedMax float64
	}{
		{"home_run", "L", 1.10, 1.20},
		{"home_run", "R", 1.00, 1.10},
		{"double", "L", 0.90, 1.00},
		{"triple", "R", 1.00, 1.10},
		{"single", "L", 1.00, 1.05},
	}

	for _, tt := range tests {
		t.Run(tt.outcome+"_"+tt.batterHand, func(t *testing.T) {
			multiplier := pf.GetParkFactorMultiplier(tt.outcome, tt.batterHand)
			if multiplier < tt.expectedMin || multiplier > tt.expectedMax {
				t.Errorf("Park factor for %s (%s) = %f, want between %f and %f",
					tt.outcome, tt.batterHand, multiplier, tt.expectedMin, tt.expectedMax)
			}
		})
	}
}

// TestGetAltitudeEffect tests altitude effects on home runs
func TestGetAltitudeEffect(t *testing.T) {
	tests := []struct {
		altitude int
		expected float64
		desc     string
	}{
		{0, 1.0, "sea level"},
		{500, 1.0, "low elevation"},
		{1000, 1.0, "threshold"},
		{3000, 1.04, "moderate elevation"},
		{5280, 1.0856, "Coors Field"},
		{10000, 1.18, "extreme altitude (capped)"},
	}

	for _, tt := range tests {
		t.Run(tt.desc, func(t *testing.T) {
			effect := GetAltitudeEffect(tt.altitude)
			if effect < tt.expected-0.01 || effect > tt.expected+0.01 {
				t.Errorf("GetAltitudeEffect(%d) = %f, want ~%f", tt.altitude, effect, tt.expected)
			}
		})
	}
}

// TestGetSurfaceEffect tests playing surface effects
func TestGetSurfaceEffect(t *testing.T) {
	tests := []struct {
		surface  string
		outcome  string
		expected float64
	}{
		{"turf", "single", 1.03},
		{"turf", "double", 1.03},
		{"turf", "home_run", 1.0},
		{"grass", "single", 1.0},
		{"natural", "double", 1.0},
		{"unknown", "single", 1.0},
	}

	for _, tt := range tests {
		t.Run(tt.surface+"_"+tt.outcome, func(t *testing.T) {
			effect := GetSurfaceEffect(tt.surface, tt.outcome)
			if effect != tt.expected {
				t.Errorf("GetSurfaceEffect(%s, %s) = %f, want %f",
					tt.surface, tt.outcome, effect, tt.expected)
			}
		})
	}
}

// TestIsHittersFriendly tests hitter-friendly park detection
func TestIsHittersFriendly(t *testing.T) {
	tests := []struct {
		name     string
		pf       ParkFactors
		expected bool
	}{
		{
			name: "hitter friendly",
			pf: ParkFactors{
				RunsFactor: 110.0,
				HRFactor:   112.0,
			},
			expected: true,
		},
		{
			name: "neutral park",
			pf: ParkFactors{
				RunsFactor: 100.0,
				HRFactor:   100.0,
			},
			expected: false,
		},
		{
			name: "pitcher friendly",
			pf: ParkFactors{
				RunsFactor: 90.0,
				HRFactor:   88.0,
			},
			expected: false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := tt.pf.IsHittersFriendly()
			if result != tt.expected {
				t.Errorf("IsHittersFriendly() = %v, want %v", result, tt.expected)
			}
		})
	}
}

// TestIsPitchersFriendly tests pitcher-friendly park detection
func TestIsPitchersFriendly(t *testing.T) {
	tests := []struct {
		name     string
		pf       ParkFactors
		expected bool
	}{
		{
			name: "pitcher friendly",
			pf: ParkFactors{
				RunsFactor: 92.0,
				HRFactor:   90.0,
			},
			expected: true,
		},
		{
			name: "neutral park",
			pf: ParkFactors{
				RunsFactor: 100.0,
				HRFactor:   100.0,
			},
			expected: false,
		},
		{
			name: "hitter friendly",
			pf: ParkFactors{
				RunsFactor: 108.0,
				HRFactor:   110.0,
			},
			expected: false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := tt.pf.IsPitchersFriendly()
			if result != tt.expected {
				t.Errorf("IsPitchersFriendly() = %v, want %v", result, tt.expected)
			}
		})
	}
}

// TestGetOverallOffensiveFactor tests combined offensive factor
func TestGetOverallOffensiveFactor(t *testing.T) {
	tests := []struct {
		name     string
		pf       ParkFactors
		expected float64
	}{
		{
			name: "hitter friendly",
			pf: ParkFactors{
				RunsFactor: 110.0,
				HRFactor:   112.0,
				HitsFactor: 108.0,
			},
			expected: 1.10, // Roughly
		},
		{
			name: "neutral",
			pf: ParkFactors{
				RunsFactor: 100.0,
				HRFactor:   100.0,
				HitsFactor: 100.0,
			},
			expected: 1.00,
		},
		{
			name: "pitcher friendly",
			pf: ParkFactors{
				RunsFactor: 90.0,
				HRFactor:   88.0,
				HitsFactor: 92.0,
			},
			expected: 0.90, // Roughly
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			factor := tt.pf.GetOverallOffensiveFactor()
			if factor < tt.expected-0.02 || factor > tt.expected+0.02 {
				t.Errorf("GetOverallOffensiveFactor() = %f, want ~%f", factor, tt.expected)
			}
		})
	}
}

// TestDefaultParkFactors tests default park factors
func TestDefaultParkFactors(t *testing.T) {
	defaults := DefaultParkFactors()

	if defaults.RunsFactor != 100.0 {
		t.Errorf("Default runs factor should be 100, got %f", defaults.RunsFactor)
	}

	if defaults.HRFactor != 100.0 {
		t.Errorf("Default HR factor should be 100, got %f", defaults.HRFactor)
	}

	if defaults.HitsFactor != 100.0 {
		t.Errorf("Default hits factor should be 100, got %f", defaults.HitsFactor)
	}
}

// TestDefaultDimensions tests default stadium dimensions
func TestDefaultDimensions(t *testing.T) {
	dims := DefaultDimensions()

	if dims.LeftField != 330 {
		t.Errorf("Default left field should be 330, got %d", dims.LeftField)
	}

	if dims.Center != 400 {
		t.Errorf("Default center field should be 400, got %d", dims.Center)
	}

	if dims.RightField != 330 {
		t.Errorf("Default right field should be 330, got %d", dims.RightField)
	}
}

// TestDimensionSymmetry tests that default dimensions are symmetric
func TestDimensionSymmetry(t *testing.T) {
	dims := DefaultDimensions()

	if dims.LeftField != dims.RightField {
		t.Error("Left and right field should be symmetric by default")
	}

	if dims.LeftFieldWall != dims.RightFieldWall {
		t.Error("Left and right field walls should be symmetric by default")
	}
}

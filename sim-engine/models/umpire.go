package models

// UmpireTendencies represents an umpire's historical strike zone and game management tendencies
type UmpireTendencies struct {
	// Strike zone size relative to average (100 = average, >100 = larger zone, <100 = smaller zone)
	StrikeZoneSize float64 `json:"strike_zone_size"`

	// Edge tendency (100 = average, >100 = calls more strikes on edges, <100 = tighter zone)
	EdgeTendency float64 `json:"edge_tendency"`

	// Rate adjustments (positive = favors pitchers, negative = favors hitters)
	StrikeoutRateAdjustment float64 `json:"strikeout_rate_adjustment"` // % points
	WalkRateAdjustment      float64 `json:"walk_rate_adjustment"`      // % points

	// Consistency (0-100 scale, higher = more consistent calls)
	Consistency float64 `json:"consistency"`

	// Favorable count tendency (>0 = calls more strikes in hitter counts, <0 = vice versa)
	CountTendency float64 `json:"count_tendency"`

	// Experience level (years in MLB)
	Experience int `json:"experience"`

	// Historical stats
	GamesUmpired     int     `json:"games_umpired"`
	AvgStrikePercent float64 `json:"avg_strike_percent"`
	AvgCallsPerGame  int     `json:"avg_calls_per_game"`

	// High/low leverage tendencies
	HighLeverageTendency float64 `json:"high_leverage_tendency"` // How zone changes in high leverage
}

// GetStrikeZoneAdjustment returns the strike zone modifier for count probabilities
func (ut *UmpireTendencies) GetStrikeZoneAdjustment(count Count, leverage float64) float64 {
	// Base adjustment from zone size
	baseAdjust := (ut.StrikeZoneSize - 100.0) / 100.0 * 0.05

	// Apply count tendency
	countAdjust := 0.0
	if count.Balls > count.Strikes {
		// Hitter's count
		countAdjust = ut.CountTendency * 0.01
	} else if count.Strikes > count.Balls {
		// Pitcher's count
		countAdjust = -ut.CountTendency * 0.01
	}

	// Apply leverage adjustment
	leverageAdjust := 0.0
	if leverage > 1.5 {
		// High leverage situation - some umps tighten zone
		leverageAdjust = ut.HighLeverageTendency * 0.01
	}

	return baseAdjust + countAdjust + leverageAdjust
}

// GetStrikeoutAdjustment returns the K% adjustment from this umpire
func (ut *UmpireTendencies) GetStrikeoutAdjustment() float64 {
	// Larger zone = more strikeouts
	adjustment := ut.StrikeoutRateAdjustment

	// Factor in zone size
	if ut.StrikeZoneSize > 100 {
		adjustment += (ut.StrikeZoneSize - 100.0) * 0.05
	} else if ut.StrikeZoneSize < 100 {
		adjustment += (ut.StrikeZoneSize - 100.0) * 0.05
	}

	return adjustment
}

// GetWalkAdjustment returns the BB% adjustment from this umpire
func (ut *UmpireTendencies) GetWalkAdjustment() float64 {
	// Smaller zone = more walks
	adjustment := ut.WalkRateAdjustment

	// Factor in zone size (inverse relationship)
	if ut.StrikeZoneSize > 100 {
		adjustment -= (ut.StrikeZoneSize - 100.0) * 0.05
	} else if ut.StrikeZoneSize < 100 {
		adjustment -= (ut.StrikeZoneSize - 100.0) * 0.05
	}

	return adjustment
}

// IsStrikeCaller returns true if umpire tends to call more strikes than average
func (ut *UmpireTendencies) IsStrikeCaller() bool {
	return ut.StrikeZoneSize > 102 || ut.StrikeoutRateAdjustment > 0.5
}

// IsHitterFriendly returns true if umpire tends to favor hitters
func (ut *UmpireTendencies) IsHitterFriendly() bool {
	return ut.StrikeZoneSize < 98 || ut.WalkRateAdjustment > 0.5
}

// GetConsistencyFactor returns how consistent the umpire is (0.8-1.2 range)
func (ut *UmpireTendencies) GetConsistencyFactor() float64 {
	// High consistency = less variance in calls
	// Low consistency = more variance (random noise)
	if ut.Consistency >= 80 {
		return 1.0 // Very consistent
	} else if ut.Consistency >= 60 {
		return 0.95
	} else if ut.Consistency >= 40 {
		return 0.90
	} else {
		return 0.85 // Inconsistent
	}
}

// GetExperienceBonus returns a small adjustment for veteran umpires
func (ut *UmpireTendencies) GetExperienceBonus() float64 {
	if ut.Experience >= 20 {
		return 0.02 // Very experienced, slightly more accurate
	} else if ut.Experience >= 10 {
		return 0.01
	}
	return 0.0
}

// DefaultUmpireTendencies returns league average umpire tendencies
func DefaultUmpireTendencies() UmpireTendencies {
	return UmpireTendencies{
		StrikeZoneSize:          100.0,
		EdgeTendency:            100.0,
		StrikeoutRateAdjustment: 0.0,
		WalkRateAdjustment:      0.0,
		Consistency:             70.0,
		CountTendency:           0.0,
		Experience:              10,
		GamesUmpired:            500,
		AvgStrikePercent:        50.0,
		AvgCallsPerGame:         150,
		HighLeverageTendency:    0.0,
	}
}

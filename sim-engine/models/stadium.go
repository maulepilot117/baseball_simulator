package models

// StadiumDimensions represents the physical dimensions of a ballpark
type StadiumDimensions struct {
	LeftField       int `json:"left_field"`        // Distance in feet
	LeftCenter      int `json:"left_center"`       // Distance in feet
	Center          int `json:"center"`            // Distance in feet
	RightCenter     int `json:"right_center"`      // Distance in feet
	RightField      int `json:"right_field"`       // Distance in feet
	LeftFieldWall   int `json:"left_field_wall"`   // Wall height in feet
	CenterFieldWall int `json:"center_field_wall"` // Wall height in feet
	RightFieldWall  int `json:"right_field_wall"`  // Wall height in feet
}

// ParkFactors represents how a stadium affects different outcomes
type ParkFactors struct {
	// Overall factors (100 = neutral, >100 = favors offense, <100 = favors pitchers)
	RunsFactor   float64 `json:"runs_factor"`
	HRFactor     float64 `json:"hr_factor"`
	HitsFactor   float64 `json:"hits_factor"`
	DoublesFactor float64 `json:"doubles_factor"`
	TriplesFactor float64 `json:"triples_factor"`

	// Handedness splits
	LHBHRFactor float64 `json:"lhb_hr_factor"`
	RHBHRFactor float64 `json:"rhb_hr_factor"`

	// Additional factors
	BABIPFactor float64 `json:"babip_factor"`
	StrikeoutFactor float64 `json:"strikeout_factor"`
	WalkFactor   float64 `json:"walk_factor"`
}

// GetParkFactorMultiplier returns the park factor for a specific outcome
func (pf *ParkFactors) GetParkFactorMultiplier(outcomeType string, batterHand string) float64 {
	switch outcomeType {
	case "home_run":
		// Apply handedness-specific HR factor if available
		if batterHand == "L" && pf.LHBHRFactor > 0 {
			return pf.LHBHRFactor / 100.0
		} else if batterHand == "R" && pf.RHBHRFactor > 0 {
			return pf.RHBHRFactor / 100.0
		}
		return pf.HRFactor / 100.0
	case "double":
		if pf.DoublesFactor > 0 {
			return pf.DoublesFactor / 100.0
		}
		return 1.0
	case "triple":
		if pf.TriplesFactor > 0 {
			return pf.TriplesFactor / 100.0
		}
		return 1.0
	case "single", "hit":
		if pf.HitsFactor > 0 {
			return pf.HitsFactor / 100.0
		}
		return 1.0
	case "walk":
		if pf.WalkFactor > 0 {
			return pf.WalkFactor / 100.0
		}
		return 1.0
	case "strikeout":
		if pf.StrikeoutFactor > 0 {
			return pf.StrikeoutFactor / 100.0
		}
		return 1.0
	default:
		return 1.0
	}
}

// GetAltitudeEffect returns the home run boost from altitude
// High altitude stadiums like Coors Field (5280 ft) see ~10-15% boost
func GetAltitudeEffect(altitude int) float64 {
	if altitude <= 1000 {
		return 1.0 // No effect at sea level or low elevation
	}

	// Linear increase: ~2% per 1000 feet above 1000 feet
	// Capped at 20% boost
	boost := float64(altitude-1000) / 1000.0 * 0.02
	if boost > 0.20 {
		boost = 0.20
	}

	return 1.0 + boost
}

// GetSurfaceEffect returns the effect of playing surface on hits/speed
func GetSurfaceEffect(surface string, outcomeType string) float64 {
	switch surface {
	case "turf", "artificial":
		// Turf tends to speed up ground balls, slightly more hits
		if outcomeType == "single" || outcomeType == "double" {
			return 1.03 // 3% boost
		}
		return 1.0
	case "grass", "natural":
		return 1.0 // Baseline
	default:
		return 1.0
	}
}

// IsHittersFriendly returns true if the park significantly favors hitters
func (pf *ParkFactors) IsHittersFriendly() bool {
	return pf.RunsFactor >= 105 && pf.HRFactor >= 105
}

// IsPitchersFriendly returns true if the park significantly favors pitchers
func (pf *ParkFactors) IsPitchersFriendly() bool {
	return pf.RunsFactor <= 95 && pf.HRFactor <= 95
}

// GetOverallOffensiveFactor returns a combined offensive factor
func (pf *ParkFactors) GetOverallOffensiveFactor() float64 {
	// Weight different factors
	return (pf.RunsFactor*0.4 + pf.HRFactor*0.3 + pf.HitsFactor*0.3) / 100.0
}

// DefaultParkFactors returns neutral park factors
func DefaultParkFactors() ParkFactors {
	return ParkFactors{
		RunsFactor:      100.0,
		HRFactor:        100.0,
		HitsFactor:      100.0,
		DoublesFactor:   100.0,
		TriplesFactor:   100.0,
		LHBHRFactor:     100.0,
		RHBHRFactor:     100.0,
		BABIPFactor:     100.0,
		StrikeoutFactor: 100.0,
		WalkFactor:      100.0,
	}
}

// DefaultDimensions returns typical MLB field dimensions
func DefaultDimensions() StadiumDimensions {
	return StadiumDimensions{
		LeftField:       330,
		LeftCenter:      375,
		Center:          400,
		RightCenter:     375,
		RightField:      330,
		LeftFieldWall:   8,
		CenterFieldWall: 8,
		RightFieldWall:  8,
	}
}

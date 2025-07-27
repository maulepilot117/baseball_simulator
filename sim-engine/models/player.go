package models

import (
	"math"
	"math/rand"
)

// Player represents a baseball player with performance statistics
type Player struct {
	ID        string          `json:"id"`
	Name      string          `json:"name"`
	Position  string          `json:"position"`
	TeamID    string          `json:"team_id"`
	Hand      string          `json:"hand"` // "L" or "R"
	Batting   BattingStats    `json:"batting"`
	Pitching  PitchingStats   `json:"pitching"`
	Fielding  FieldingStats   `json:"fielding"`
	Attributes PlayerAttributes `json:"attributes"`
}

// BattingStats contains offensive statistics
type BattingStats struct {
	// Basic stats
	AVG    float64 `json:"avg"`
	OBP    float64 `json:"obp"`
	SLG    float64 `json:"slg"`
	OPS    float64 `json:"ops"`
	
	// Advanced stats
	WOBA   float64 `json:"woba"`
	WRCPlus int    `json:"wrc_plus"`
	ISO    float64 `json:"iso"`
	BABIP  float64 `json:"babip"`
	
	// Rate stats
	BBPercent float64 `json:"bb_percent"`
	KPercent  float64 `json:"k_percent"`
	
	// Counting stats
	PA     int `json:"pa"`
	AB     int `json:"ab"`
	H      int `json:"h"`
	Doubles int `json:"doubles"`
	Triples int `json:"triples"`
	HR     int `json:"hr"`
	RBI    int `json:"rbi"`
	SB     int `json:"sb"`
	CS     int `json:"cs"`
	
	// Situational splits
	VsLHP  SplitStats `json:"vs_lhp"`
	VsRHP  SplitStats `json:"vs_rhp"`
	RISP   SplitStats `json:"risp"` // Runners in scoring position
	Clutch SplitStats `json:"clutch"` // High leverage situations
}

// PitchingStats contains pitching statistics
type PitchingStats struct {
	// Basic stats
	ERA    float64 `json:"era"`
	WHIP   float64 `json:"whip"`
	
	// Advanced stats
	FIP    float64 `json:"fip"`
	XFIP   float64 `json:"xfip"`
	ERAPlus int    `json:"era_plus"`
	
	// Rate stats
	KPer9   float64 `json:"k_per_9"`
	BBPer9  float64 `json:"bb_per_9"`
	HRPer9  float64 `json:"hr_per_9"`
	KBBRatio float64 `json:"k_bb_ratio"`
	
	// Counting stats
	IP      float64 `json:"ip"`
	H       int     `json:"h"`
	ER      int     `json:"er"`
	BB      int     `json:"bb"`
	SO      int     `json:"so"`
	HR      int     `json:"hr"`
	W       int     `json:"w"`
	L       int     `json:"l"`
	SV      int     `json:"sv"`
	
	// Contact management
	GroundBallPercent float64 `json:"gb_percent"`
	FlyBallPercent    float64 `json:"fb_percent"`
	LinedrivePercent  float64 `json:"ld_percent"`
	
	// Situational splits
	VsLHB  SplitStats `json:"vs_lhb"`
	VsRHB  SplitStats `json:"vs_rhb"`
	RISP   SplitStats `json:"risp"`
	Clutch SplitStats `json:"clutch"`
	
	// Pitch mix
	PitchMix PitchMix `json:"pitch_mix"`
}

// FieldingStats contains defensive statistics
type FieldingStats struct {
	// Traditional stats
	FPCT   float64 `json:"fpct"`
	Errors int     `json:"errors"`
	PO     int     `json:"po"`
	A      int     `json:"a"`
	
	// Advanced stats
	UZR    float64 `json:"uzr"`
	DRS    int     `json:"drs"`
	ARM    float64 `json:"arm"`
	RangeRuns float64 `json:"range_runs"`
	
	// Position-specific (if applicable)
	FramingRuns  float64 `json:"framing_runs,omitempty"`   // Catchers
	BlockingRuns float64 `json:"blocking_runs,omitempty"`  // Catchers
	ArmRuns      float64 `json:"arm_runs,omitempty"`       // All positions
	JumpRating   float64 `json:"jump_rating,omitempty"`    // Outfielders
}

// SplitStats contains situation-specific performance
type SplitStats struct {
	AVG  float64 `json:"avg"`
	OBP  float64 `json:"obp"`
	SLG  float64 `json:"slg"`
	OPS  float64 `json:"ops"`
	WOBA float64 `json:"woba"`
	PA   int     `json:"pa"`
}

// PitchMix contains pitch type usage
type PitchMix struct {
	Fastball   float64 `json:"fastball"`
	Slider     float64 `json:"slider"`
	Changeup   float64 `json:"changeup"`
	Curveball  float64 `json:"curveball"`
	Cutter     float64 `json:"cutter"`
	Sinker     float64 `json:"sinker"`
	Knuckleball float64 `json:"knuckleball"`
	Other      float64 `json:"other"`
}

// PlayerAttributes contains scouting/physical attributes
type PlayerAttributes struct {
	Speed       int `json:"speed"`        // 20-80 scale
	Power       int `json:"power"`        // 20-80 scale
	Contact     int `json:"contact"`      // 20-80 scale
	Eye         int `json:"eye"`          // 20-80 scale (plate discipline)
	ArmStrength int `json:"arm_strength"` // 20-80 scale
	Accuracy    int `json:"accuracy"`     // 20-80 scale
	Range       int `json:"range"`        // 20-80 scale
	Hands       int `json:"hands"`        // 20-80 scale (fielding)
	
	// Physical
	Height int `json:"height"` // inches
	Weight int `json:"weight"` // pounds
	Age    int `json:"age"`
	
	// Mental/Intangibles
	Clutch     int `json:"clutch"`      // 20-80 scale
	Durability int `json:"durability"`  // 20-80 scale
	Composure  int `json:"composure"`   // 20-80 scale
}

// Roster represents a team's roster
type Roster struct {
	TeamID   string   `json:"team_id"`
	Players  []Player `json:"players"`
	Lineup   []string `json:"lineup"`     // Player IDs in batting order
	Rotation []string `json:"rotation"`   // Starting pitcher IDs
	Bullpen  []string `json:"bullpen"`    // Relief pitcher IDs
}

// GetSplitStats returns appropriate split stats for the situation
func (bs *BattingStats) GetSplitStats(pitcherHand string, risp bool, highLeverage bool) SplitStats {
	var split SplitStats
	
	// Start with overall stats
	split = SplitStats{
		AVG:  bs.AVG,
		OBP:  bs.OBP,
		SLG:  bs.SLG,
		OPS:  bs.OPS,
		WOBA: bs.WOBA,
		PA:   bs.PA,
	}
	
	// Apply platoon split
	var platoonSplit SplitStats
	if pitcherHand == "L" && bs.VsLHP.PA > 0 {
		platoonSplit = bs.VsLHP
	} else if pitcherHand == "R" && bs.VsRHP.PA > 0 {
		platoonSplit = bs.VsRHP
	}
	
	if platoonSplit.PA > 0 {
		split = platoonSplit
	}
	
	// Apply situational adjustments
	if risp && bs.RISP.PA > 20 { // Minimum sample size
		// Blend RISP performance with overall
		weight := math.Min(float64(bs.RISP.PA)/100.0, 0.3) // Max 30% weight
		split.WOBA = split.WOBA*(1-weight) + bs.RISP.WOBA*weight
	}
	
	if highLeverage && bs.Clutch.PA > 20 {
		// Blend clutch performance
		weight := math.Min(float64(bs.Clutch.PA)/100.0, 0.2) // Max 20% weight
		split.WOBA = split.WOBA*(1-weight) + bs.Clutch.WOBA*weight
	}
	
	return split
}

// GetSplitStats returns appropriate pitching splits for the situation
func (ps *PitchingStats) GetSplitStats(batterHand string, risp bool, highLeverage bool) SplitStats {
	var split SplitStats
	
	// Convert pitching stats to "offensive" equivalent for easier calculation
	// Higher ERA/WHIP = worse for pitcher = better wOBA equivalent for batter
	baseWOBA := 0.320 + (ps.FIP-3.70)*0.03 // Rough conversion
	
	split = SplitStats{
		WOBA: math.Max(0.200, math.Min(0.500, baseWOBA)),
		PA:   int(ps.IP * 4), // Rough PA estimate
	}
	
	// Apply platoon adjustments
	if batterHand == "L" && ps.VsLHB.PA > 0 {
		split.WOBA = ps.VsLHB.WOBA
	} else if batterHand == "R" && ps.VsRHB.PA > 0 {
		split.WOBA = ps.VsRHB.WOBA
	}
	
	// Apply situational adjustments
	if risp && ps.RISP.PA > 20 {
		weight := math.Min(float64(ps.RISP.PA)/100.0, 0.3)
		split.WOBA = split.WOBA*(1-weight) + ps.RISP.WOBA*weight
	}
	
	if highLeverage && ps.Clutch.PA > 20 {
		weight := math.Min(float64(ps.Clutch.PA)/100.0, 0.2)
		split.WOBA = split.WOBA*(1-weight) + ps.Clutch.WOBA*weight
	}
	
	return split
}

// SimulateAtBat simulates a plate appearance outcome
func (p *Player) SimulateAtBat(pitcher *Player, gameState *GameState, weather Weather) AtBatResult {
	// Get situational stats
	risp := gameState.Bases.Second != nil || gameState.Bases.Third != nil
	highLeverage := gameState.CalculateLeverage() > 1.5
	
	batterSplit := p.Batting.GetSplitStats(pitcher.Hand, risp, highLeverage)
	pitcherSplit := pitcher.Pitching.GetSplitStats(p.Hand, risp, highLeverage)
	
	// Calculate matchup advantage
	// Average the batter's expected performance with pitcher's expected performance
	expectedWOBA := (batterSplit.WOBA + (0.320*2-pitcherSplit.WOBA)) / 2
	
	// Apply count effects
	countAdjustment := getCountAdjustment(gameState.Count)
	expectedWOBA += countAdjustment
	
	// Apply weather effects
	weatherAdjustment := getWeatherAdjustment(weather)
	expectedWOBA += weatherAdjustment
	
	// Ensure realistic bounds
	expectedWOBA = math.Max(0.200, math.Min(0.500, expectedWOBA))
	
	// Simulate outcome based on expected wOBA
	return simulateOutcome(expectedWOBA, p, pitcher, gameState)
}

// AtBatResult represents the outcome of a plate appearance
type AtBatResult struct {
	Type        string  `json:"type"`        // "single", "double", "triple", "home_run", "walk", "strikeout", "out", "hit_by_pitch"
	Description string  `json:"description"` // Detailed description
	Bases       int     `json:"bases"`       // 0=out, 1=single, 2=double, 3=triple, 4=HR
	IsHit       bool    `json:"is_hit"`
	IsOut       bool    `json:"is_out"`
	Outs        int     `json:"outs"`        // Outs made on this play
	Advancement map[string]int `json:"advancement"` // How runners advance
	Leverage    float64 `json:"leverage"`
	WPA         float64 `json:"wpa"`         // Win Probability Added
}

func getCountAdjustment(count Count) float64 {
	// Hitter's counts favor the batter, pitcher's counts favor the pitcher
	switch {
	case count.Balls == 3 && count.Strikes == 0:
		return 0.080  // 3-0 count
	case count.Balls == 3 && count.Strikes == 1:
		return 0.060  // 3-1 count
	case count.Balls == 2 && count.Strikes == 0:
		return 0.040  // 2-0 count
	case count.Balls == 0 && count.Strikes == 2:
		return -0.060 // 0-2 count
	case count.Balls == 1 && count.Strikes == 2:
		return -0.040 // 1-2 count
	case count.Balls == 2 && count.Strikes == 2:
		return -0.020 // 2-2 count
	default:
		return 0.0    // Even counts
	}
}

func getWeatherAdjustment(weather Weather) float64 {
	adjustment := 0.0
	
	// Wind effects
	switch weather.WindDir {
	case "out":
		adjustment += float64(weather.WindSpeed) * 0.001 // Helps fly balls
	case "in":
		adjustment -= float64(weather.WindSpeed) * 0.001 // Hurts fly balls
	}
	
	// Temperature effects (cold weather hurts offense)
	if weather.Temperature < 50 {
		adjustment -= 0.010
	} else if weather.Temperature > 80 {
		adjustment += 0.005
	}
	
	// Humidity effects (high humidity hurts fly balls slightly)
	if weather.Humidity > 80 {
		adjustment -= 0.005
	}
	
	return adjustment
}

func simulateOutcome(expectedWOBA float64, batter *Player, pitcher *Player, gameState *GameState) AtBatResult {
	// Use wOBA to determine outcome probabilities
	// These are rough estimates based on league averages
	
	roll := rand.Float64()
	
	// Walk probability increases with higher wOBA
	walkProb := batter.Batting.BBPercent/100.0 * (1.0 + (expectedWOBA-0.320)*2.0)
	if roll < walkProb {
		return AtBatResult{
			Type:        "walk",
			Description: "Walk",
			Bases:       0,
			IsHit:       false,
			IsOut:       false,
			Outs:        0,
			Leverage:    gameState.CalculateLeverage(),
		}
	}
	
	// Strikeout probability decreases with higher wOBA
	kProb := walkProb + (batter.Batting.KPercent/100.0 * (1.0 - (expectedWOBA-0.320)*2.0))
	if roll < kProb {
		return AtBatResult{
			Type:        "strikeout",
			Description: "Strikeout",
			Bases:       0,
			IsHit:       false,
			IsOut:       true,
			Outs:        1,
			Leverage:    gameState.CalculateLeverage(),
		}
	}
	
	// Hit probability based on wOBA
	hitProb := kProb + (expectedWOBA * 1.2) // Rough conversion
	if roll < hitProb {
		// Determine hit type
		return simulateHitType(expectedWOBA, batter, pitcher)
	}
	
	// Otherwise it's an out
	return AtBatResult{
		Type:        "out",
		Description: "Groundout",
		Bases:       0,
		IsHit:       false,
		IsOut:       true,
		Outs:        1,
		Leverage:    gameState.CalculateLeverage(),
	}
}

func simulateHitType(expectedWOBA float64, batter *Player, pitcher *Player) AtBatResult {
	roll := rand.Float64()
	
	// Power factor influences extra base hits
	powerFactor := float64(batter.Attributes.Power) / 50.0 // Normalize to ~1.0
	
	// Home run probability
	hrProb := math.Min(0.15, (expectedWOBA-0.250)*0.3*powerFactor)
	if roll < hrProb {
		return AtBatResult{
			Type:        "home_run",
			Description: "Home Run",
			Bases:       4,
			IsHit:       true,
			IsOut:       false,
			Outs:        0,
		}
	}
	
	// Triple probability (rare)
	tripleProb := hrProb + math.Min(0.03, (expectedWOBA-0.300)*0.1)
	if roll < tripleProb {
		return AtBatResult{
			Type:        "triple",
			Description: "Triple",
			Bases:       3,
			IsHit:       true,
			IsOut:       false,
			Outs:        0,
		}
	}
	
	// Double probability
	doubleProb := tripleProb + math.Min(0.25, (expectedWOBA-0.250)*0.5*powerFactor)
	if roll < doubleProb {
		return AtBatResult{
			Type:        "double",
			Description: "Double",
			Bases:       2,
			IsHit:       true,
			IsOut:       false,
			Outs:        0,
		}
	}
	
	// Otherwise single
	return AtBatResult{
		Type:        "single",
		Description: "Single",
		Bases:       1,
		IsHit:       true,
		IsOut:       false,
		Outs:        0,
	}
}
package main

import (
	"context"
	"encoding/json"
	"net/http"
	"time"

	"github.com/gorilla/mux"
)

// BoxScoreBatting represents a batting line in the box score
type BoxScoreBatting struct {
	PlayerID      string `json:"player_id" db:"player_id"`
	PlayerName    string `json:"player_name" db:"player_name"`
	TeamID        string `json:"team_id" db:"team_id"`
	BattingOrder  *int   `json:"batting_order,omitempty" db:"batting_order"`
	Position      string `json:"position" db:"position"`
	AtBats        int    `json:"at_bats" db:"at_bats"`
	Runs          int    `json:"runs" db:"runs"`
	Hits          int    `json:"hits" db:"hits"`
	RBIs          int    `json:"rbis" db:"rbis"`
	Walks         int    `json:"walks" db:"walks"`
	Strikeouts    int    `json:"strikeouts" db:"strikeouts"`
	Doubles       int    `json:"doubles" db:"doubles"`
	Triples       int    `json:"triples" db:"triples"`
	HomeRuns      int    `json:"home_runs" db:"home_runs"`
	StolenBases   int    `json:"stolen_bases" db:"stolen_bases"`
	CaughtStealing int   `json:"caught_stealing" db:"caught_stealing"`
	LeftOnBase    int    `json:"left_on_base" db:"left_on_base"`
}

// BoxScorePitching represents a pitching line in the box score
type BoxScorePitching struct {
	PlayerID        string  `json:"player_id" db:"player_id"`
	PlayerName      string  `json:"player_name" db:"player_name"`
	TeamID          string  `json:"team_id" db:"team_id"`
	InningsPitched  float64 `json:"innings_pitched" db:"innings_pitched"`
	HitsAllowed     int     `json:"hits_allowed" db:"hits_allowed"`
	RunsAllowed     int     `json:"runs_allowed" db:"runs_allowed"`
	EarnedRuns      int     `json:"earned_runs" db:"earned_runs"`
	WalksAllowed    int     `json:"walks_allowed" db:"walks_allowed"`
	Strikeouts      int     `json:"strikeouts" db:"strikeouts"`
	HomeRunsAllowed int     `json:"home_runs_allowed" db:"home_runs_allowed"`
	PitchesThrown   int     `json:"pitches_thrown" db:"pitches_thrown"`
	Strikes         int     `json:"strikes" db:"strikes"`
	Win             bool    `json:"win" db:"win"`
	Loss            bool    `json:"loss" db:"loss"`
	Save            bool    `json:"save" db:"save"`
	Hold            bool    `json:"hold" db:"hold"`
	BlownSave       bool    `json:"blown_save" db:"blown_save"`
	ERA             *float64 `json:"era,omitempty" db:"era"`
}

// GamePlay represents a play-by-play event
type GamePlay struct {
	ID           string                 `json:"id" db:"id"`
	PlayID       string                 `json:"play_id" db:"play_id"`
	Inning       int                    `json:"inning" db:"inning"`
	InningHalf   string                 `json:"inning_half" db:"inning_half"`
	Outs         int                    `json:"outs" db:"outs"`
	Balls        *int                   `json:"balls,omitempty" db:"balls"`
	Strikes      *int                   `json:"strikes,omitempty" db:"strikes"`
	BatterName   string                 `json:"batter_name" db:"batter_name"`
	PitcherName  string                 `json:"pitcher_name" db:"pitcher_name"`
	EventType    string                 `json:"event_type" db:"event_type"`
	Description  string                 `json:"description" db:"description"`
	RBI          int                    `json:"rbi" db:"rbi"`
	RunsScored   int                    `json:"runs_scored" db:"runs_scored"`
	HomeScore    int                    `json:"home_score" db:"home_score"`
	AwayScore    int                    `json:"away_score" db:"away_score"`
}

// GameBoxScore combines batting and pitching box scores
type GameBoxScore struct {
	HomeTeamBatting []BoxScoreBatting  `json:"home_team_batting"`
	AwayTeamBatting []BoxScoreBatting  `json:"away_team_batting"`
	HomeTeamPitching []BoxScorePitching `json:"home_team_pitching"`
	AwayTeamPitching []BoxScorePitching `json:"away_team_pitching"`
}

// getGameBoxScore handles GET /api/v1/games/{id}/boxscore
func (s *Server) getGameBoxScore(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	gameID := vars["id"]

	ctx, cancel := context.WithTimeout(r.Context(), 10*time.Second)
	defer cancel()

	// Get home and away team IDs
	var homeTeamID, awayTeamID string
	err := s.db.QueryRow(ctx, `
		SELECT home_team_id, away_team_id
		FROM games
		WHERE id = $1
	`, gameID).Scan(&homeTeamID, &awayTeamID)

	if err != nil {
		writeError(w, "Game not found", http.StatusNotFound)
		return
	}

	boxScore := GameBoxScore{}

	// Fetch home team batting
	rows, err := s.db.Query(ctx, `
		SELECT
			p.player_id,
			p.full_name as player_name,
			b.team_id,
			b.batting_order,
			b.position,
			b.at_bats,
			b.runs,
			b.hits,
			b.rbis,
			b.walks,
			b.strikeouts,
			b.doubles,
			b.triples,
			b.home_runs,
			b.stolen_bases,
			b.caught_stealing,
			b.left_on_base
		FROM game_box_score_batting b
		JOIN players p ON b.player_id = p.id
		WHERE b.game_id = $1 AND b.team_id = $2
		ORDER BY b.batting_order NULLS LAST
	`, gameID, homeTeamID)

	if err == nil {
		defer rows.Close()
		for rows.Next() {
			var bat BoxScoreBatting
			if err := rows.Scan(
				&bat.PlayerID, &bat.PlayerName, &bat.TeamID, &bat.BattingOrder, &bat.Position,
				&bat.AtBats, &bat.Runs, &bat.Hits, &bat.RBIs, &bat.Walks, &bat.Strikeouts,
				&bat.Doubles, &bat.Triples, &bat.HomeRuns, &bat.StolenBases,
				&bat.CaughtStealing, &bat.LeftOnBase,
			); err == nil {
				boxScore.HomeTeamBatting = append(boxScore.HomeTeamBatting, bat)
			}
		}
	}

	// Fetch away team batting
	rows, err = s.db.Query(ctx, `
		SELECT
			p.player_id,
			p.full_name as player_name,
			b.team_id,
			b.batting_order,
			b.position,
			b.at_bats,
			b.runs,
			b.hits,
			b.rbis,
			b.walks,
			b.strikeouts,
			b.doubles,
			b.triples,
			b.home_runs,
			b.stolen_bases,
			b.caught_stealing,
			b.left_on_base
		FROM game_box_score_batting b
		JOIN players p ON b.player_id = p.id
		WHERE b.game_id = $1 AND b.team_id = $2
		ORDER BY b.batting_order NULLS LAST
	`, gameID, awayTeamID)

	if err == nil {
		defer rows.Close()
		for rows.Next() {
			var bat BoxScoreBatting
			if err := rows.Scan(
				&bat.PlayerID, &bat.PlayerName, &bat.TeamID, &bat.BattingOrder, &bat.Position,
				&bat.AtBats, &bat.Runs, &bat.Hits, &bat.RBIs, &bat.Walks, &bat.Strikeouts,
				&bat.Doubles, &bat.Triples, &bat.HomeRuns, &bat.StolenBases,
				&bat.CaughtStealing, &bat.LeftOnBase,
			); err == nil {
				boxScore.AwayTeamBatting = append(boxScore.AwayTeamBatting, bat)
			}
		}
	}

	// Fetch home team pitching
	rows, err = s.db.Query(ctx, `
		SELECT
			p.player_id,
			p.full_name as player_name,
			pt.team_id,
			pt.innings_pitched,
			pt.hits_allowed,
			pt.runs_allowed,
			pt.earned_runs,
			pt.walks_allowed,
			pt.strikeouts,
			pt.home_runs_allowed,
			pt.pitches_thrown,
			pt.strikes,
			pt.win,
			pt.loss,
			pt.save,
			pt.hold,
			pt.blown_save,
			pt.era
		FROM game_box_score_pitching pt
		JOIN players p ON pt.player_id = p.id
		WHERE pt.game_id = $1 AND pt.team_id = $2
		ORDER BY pt.innings_pitched DESC
	`, gameID, homeTeamID)

	if err == nil {
		defer rows.Close()
		for rows.Next() {
			var pitch BoxScorePitching
			if err := rows.Scan(
				&pitch.PlayerID, &pitch.PlayerName, &pitch.TeamID, &pitch.InningsPitched,
				&pitch.HitsAllowed, &pitch.RunsAllowed, &pitch.EarnedRuns, &pitch.WalksAllowed,
				&pitch.Strikeouts, &pitch.HomeRunsAllowed, &pitch.PitchesThrown, &pitch.Strikes,
				&pitch.Win, &pitch.Loss, &pitch.Save, &pitch.Hold, &pitch.BlownSave, &pitch.ERA,
			); err == nil {
				boxScore.HomeTeamPitching = append(boxScore.HomeTeamPitching, pitch)
			}
		}
	}

	// Fetch away team pitching
	rows, err = s.db.Query(ctx, `
		SELECT
			p.player_id,
			p.full_name as player_name,
			pt.team_id,
			pt.innings_pitched,
			pt.hits_allowed,
			pt.runs_allowed,
			pt.earned_runs,
			pt.walks_allowed,
			pt.strikeouts,
			pt.home_runs_allowed,
			pt.pitches_thrown,
			pt.strikes,
			pt.win,
			pt.loss,
			pt.save,
			pt.hold,
			pt.blown_save,
			pt.era
		FROM game_box_score_pitching pt
		JOIN players p ON pt.player_id = p.id
		WHERE pt.game_id = $1 AND pt.team_id = $2
		ORDER BY pt.innings_pitched DESC
	`, gameID, awayTeamID)

	if err == nil {
		defer rows.Close()
		for rows.Next() {
			var pitch BoxScorePitching
			if err := rows.Scan(
				&pitch.PlayerID, &pitch.PlayerName, &pitch.TeamID, &pitch.InningsPitched,
				&pitch.HitsAllowed, &pitch.RunsAllowed, &pitch.EarnedRuns, &pitch.WalksAllowed,
				&pitch.Strikeouts, &pitch.HomeRunsAllowed, &pitch.PitchesThrown, &pitch.Strikes,
				&pitch.Win, &pitch.Loss, &pitch.Save, &pitch.Hold, &pitch.BlownSave, &pitch.ERA,
			); err == nil {
				boxScore.AwayTeamPitching = append(boxScore.AwayTeamPitching, pitch)
			}
		}
	}

	writeJSON(w, boxScore)
}

// getGamePlays handles GET /api/v1/games/{id}/plays
func (s *Server) getGamePlays(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	gameID := vars["id"]

	ctx, cancel := context.WithTimeout(r.Context(), 10*time.Second)
	defer cancel()

	rows, err := s.db.Query(ctx, `
		SELECT
			gp.id,
			gp.play_id,
			gp.inning,
			gp.inning_half,
			gp.outs,
			gp.balls,
			gp.strikes,
			COALESCE(b.full_name, 'Unknown') as batter_name,
			COALESCE(p.full_name, 'Unknown') as pitcher_name,
			gp.event_type,
			gp.description,
			gp.rbi,
			gp.runs_scored,
			gp.home_score,
			gp.away_score
		FROM game_plays gp
		LEFT JOIN players b ON gp.batter_id = b.id
		LEFT JOIN players p ON gp.pitcher_id = p.id
		WHERE gp.game_id = $1
		ORDER BY gp.inning, gp.inning_half DESC, gp.play_id
	`, gameID)

	if err != nil {
		writeError(w, "Failed to fetch plays", http.StatusInternalServerError)
		return
	}
	defer rows.Close()

	plays := []GamePlay{}
	for rows.Next() {
		var play GamePlay
		if err := rows.Scan(
			&play.ID, &play.PlayID, &play.Inning, &play.InningHalf, &play.Outs,
			&play.Balls, &play.Strikes, &play.BatterName, &play.PitcherName,
			&play.EventType, &play.Description, &play.RBI, &play.RunsScored,
			&play.HomeScore, &play.AwayScore,
		); err == nil {
			plays = append(plays, play)
		}
	}

	writeJSON(w, plays)
}

// getGameWeather handles GET /api/v1/games/{id}/weather
func (s *Server) getGameWeather(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	gameID := vars["id"]

	ctx, cancel := context.WithTimeout(r.Context(), 10*time.Second)
	defer cancel()

	var weatherData []byte
	err := s.db.QueryRow(ctx, `
		SELECT COALESCE(weather_data, '{}'::jsonb)
		FROM games
		WHERE id = $1
	`, gameID).Scan(&weatherData)

	if err != nil {
		writeError(w, "Game not found", http.StatusNotFound)
		return
	}

	var weather map[string]interface{}
	if err := json.Unmarshal(weatherData, &weather); err != nil {
		writeError(w, "Invalid weather data", http.StatusInternalServerError)
		return
	}

	writeJSON(w, weather)
}

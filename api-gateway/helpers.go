package main

import (
	"context"
	"fmt"
	"net/http"
	"strconv"
	"strings"
	"time"
)

// parseQueryParams extracts common query parameters from HTTP request
func parseQueryParams(r *http.Request) QueryParams {
	params := QueryParams{
		Page:     1,
		PageSize: 50,
	}

	if pageStr := r.URL.Query().Get("page"); pageStr != "" {
		if page, err := strconv.Atoi(pageStr); err == nil && page > 0 {
			params.Page = page
		}
	}

	if pageSizeStr := r.URL.Query().Get("page_size"); pageSizeStr != "" {
		if pageSize, err := strconv.Atoi(pageSizeStr); err == nil && pageSize > 0 && pageSize <= 200 {
			params.PageSize = pageSize
		}
	}

	if seasonStr := r.URL.Query().Get("season"); seasonStr != "" {
		if season, err := strconv.Atoi(seasonStr); err == nil {
			params.Season = &season
		}
	}

	params.Team = r.URL.Query().Get("team")
	params.Position = r.URL.Query().Get("position")
	params.Status = r.URL.Query().Get("status")
	params.Date = r.URL.Query().Get("date")
	params.Sort = r.URL.Query().Get("sort")
	params.Order = r.URL.Query().Get("order")

	// Default order to ASC if not specified
	if params.Order != "desc" {
		params.Order = "asc"
	}

	return params
}

// calculateOffset calculates SQL offset for pagination
func calculateOffset(page, pageSize int) int {
	return (page - 1) * pageSize
}

// buildPaginatedResponse creates a paginated response
func buildPaginatedResponse(data interface{}, total, page, pageSize int) PaginatedResponse {
	totalPages := (total + pageSize - 1) / pageSize
	return PaginatedResponse{
		Data:       data,
		Total:      total,
		Page:       page,
		PageSize:   pageSize,
		TotalPages: totalPages,
	}
}

// writeError writes an error response
func writeError(w http.ResponseWriter, message string, statusCode int) {
	w.WriteHeader(statusCode)
	writeJSON(w, APIError{Error: message})
}

// writeErrorWithDetails writes an error response with additional details
func writeErrorWithDetails(w http.ResponseWriter, message, code string, details map[string]interface{}, statusCode int) {
	w.WriteHeader(statusCode)
	writeJSON(w, APIError{
		Error:   message,
		Code:    code,
		Details: details,
	})
}

// buildWhereClause builds SQL WHERE clause from query parameters
func buildWhereClause(params QueryParams, tableName string) (string, []interface{}) {
	var conditions []string
	var args []interface{}
	argIndex := 1

	if params.Season != nil {
		conditions = append(conditions, tableName+".season = $"+strconv.Itoa(argIndex))
		args = append(args, *params.Season)
		argIndex++
	}

	if params.Team != "" {
		conditions = append(conditions, "("+tableName+".home_team_id = $"+strconv.Itoa(argIndex)+" OR "+tableName+".away_team_id = $"+strconv.Itoa(argIndex)+")")
		args = append(args, params.Team)
		argIndex++
	}

	if params.Position != "" {
		conditions = append(conditions, tableName+".position = $"+strconv.Itoa(argIndex))
		args = append(args, params.Position)
		argIndex++
	}

	if params.Status != "" {
		conditions = append(conditions, tableName+".status = $"+strconv.Itoa(argIndex))
		args = append(args, params.Status)
		argIndex++
	}

	if params.Date != "" {
		// Parse date and create date range
		if date, err := time.Parse("2006-01-02", params.Date); err == nil {
			conditions = append(conditions, tableName+".game_date >= $"+strconv.Itoa(argIndex)+" AND "+tableName+".game_date < $"+strconv.Itoa(argIndex+1))
			args = append(args, date)
			args = append(args, date.AddDate(0, 0, 1))
			argIndex += 2
		}
	}

	whereClause := ""
	if len(conditions) > 0 {
		whereClause = " WHERE " + strings.Join(conditions, " AND ")
	}

	return whereClause, args
}

// buildOrderClause builds SQL ORDER BY clause
func buildOrderClause(params QueryParams, tableName string, defaultSort string) string {
	sortField := defaultSort
	if params.Sort != "" {
		// Validate sort field to prevent SQL injection
		allowedSorts := map[string]bool{
			"name":          true,
			"created_at":    true,
			"updated_at":    true,
			"game_date":     true,
			"season":        true,
			"position":      true,
			"last_name":     true,
			"first_name":    true,
			"jersey_number": true,
			"team_id":       true,
		}
		if allowedSorts[params.Sort] {
			sortField = params.Sort
		}
	}

	return " ORDER BY " + tableName + "." + sortField + " " + strings.ToUpper(params.Order)
}

// contextWithTimeout creates a context with a default timeout
func contextWithTimeout(parent context.Context) (context.Context, context.CancelFunc) {
	return context.WithTimeout(parent, 10*time.Second)
}

// validateDateFormat validates date string format
func validateDateFormat(dateStr string) bool {
	_, err := time.Parse("2006-01-02", dateStr)
	return err == nil
}

// formatPlayerName formats a player's full name
func formatPlayerName(firstName, lastName string) string {
	return strings.TrimSpace(firstName + " " + lastName)
}

// getCurrentSeason returns the current MLB season year
func getCurrentSeason() int {
	now := time.Now()
	// MLB season runs from March to October/November
	if now.Month() < 3 {
		return now.Year() - 1
	}
	return now.Year()
}

// validateUUID validates UUID format (simple check)
func validateUUID(id string) bool {
	// Simple UUID format validation
	return len(id) == 36 && strings.Count(id, "-") == 4
}

// sanitizeStringParam sanitizes string parameters
func sanitizeStringParam(param string) string {
	// Basic sanitization - remove potentially harmful characters
	param = strings.TrimSpace(param)
	param = strings.ReplaceAll(param, "'", "")
	param = strings.ReplaceAll(param, "\"", "")
	param = strings.ReplaceAll(param, ";", "")
	param = strings.ReplaceAll(param, "--", "")
	param = strings.ReplaceAll(param, "/*", "")
	param = strings.ReplaceAll(param, "*/", "")
	param = strings.ReplaceAll(param, "xp_", "")
	param = strings.ReplaceAll(param, "sp_", "")
	param = strings.ReplaceAll(param, "<script", "")
	param = strings.ReplaceAll(param, "</script", "")
	return param
}

// validateSeasonParam validates season parameter
func validateSeasonParam(season int) error {
	currentYear := time.Now().Year()
	if season < 1876 || season > currentYear+1 {
		return fmt.Errorf("invalid season: must be between 1876 and %d", currentYear+1)
	}
	return nil
}

// validatePageParams validates pagination parameters
func validatePageParams(page, pageSize int) error {
	if page < 1 {
		return fmt.Errorf("invalid page: must be >= 1")
	}
	if pageSize < 1 || pageSize > 200 {
		return fmt.Errorf("invalid page_size: must be between 1 and 200")
	}
	return nil
}

// validateUUIDParam validates UUID format
func validateUUIDParam(id string) error {
	if id == "" {
		return fmt.Errorf("id cannot be empty")
	}
	// Basic UUID validation
	if len(id) != 36 {
		return fmt.Errorf("invalid UUID format")
	}
	if strings.Count(id, "-") != 4 {
		return fmt.Errorf("invalid UUID format")
	}
	return nil
}

// parseIntParam safely parses integer parameter
func parseIntParam(param string, defaultValue int) int {
	if param == "" {
		return defaultValue
	}
	if val, err := strconv.Atoi(param); err == nil {
		return val
	}
	return defaultValue
}

// formatGameStatus formats game status for display
func formatGameStatus(status string) string {
	switch strings.ToUpper(status) {
	case "SCHEDULED":
		return "Scheduled"
	case "LIVE":
		return "Live"
	case "FINAL":
		return "Final"
	case "POSTPONED":
		return "Postponed"
	case "CANCELLED":
		return "Cancelled"
	default:
		return status
	}
}

// isValidPosition validates baseball position
func isValidPosition(position string) bool {
	validPositions := map[string]bool{
		"P":  true, // Pitcher
		"C":  true, // Catcher
		"1B": true, // First Base
		"2B": true, // Second Base
		"3B": true, // Third Base
		"SS": true, // Shortstop
		"LF": true, // Left Field
		"CF": true, // Center Field
		"RF": true, // Right Field
		"DH": true, // Designated Hitter
		"OF": true, // Outfield (general)
		"IF": true, // Infield (general)
	}
	return validPositions[strings.ToUpper(position)]
}

// formatTeamName formats team name for display
func formatTeamName(city, name string) string {
	if city != "" && name != "" {
		return city + " " + name
	}
	if name != "" {
		return name
	}
	return city
}

// buildPlayersWhereClause builds SQL WHERE clause specifically for players queries
func buildPlayersWhereClause(params QueryParams) (string, []interface{}) {
	var conditions []string
	var args []interface{}
	argIndex := 1

	if params.Position != "" && isValidPosition(params.Position) {
		conditions = append(conditions, "p.position = $"+strconv.Itoa(argIndex))
		args = append(args, params.Position)
		argIndex++
	}

	if params.Team != "" {
		conditions = append(conditions, "(t.id = $"+strconv.Itoa(argIndex)+" OR t.team_id = $"+strconv.Itoa(argIndex)+" OR t.abbreviation = $"+strconv.Itoa(argIndex)+")")
		args = append(args, params.Team)
		argIndex++
	}

	if params.Status != "" {
		conditions = append(conditions, "p.status = $"+strconv.Itoa(argIndex))
		args = append(args, params.Status)
		argIndex++
	}

	whereClause := ""
	if len(conditions) > 0 {
		whereClause = " WHERE " + strings.Join(conditions, " AND ")
	}

	return whereClause, args
}

// buildGamesWhereClause builds SQL WHERE clause specifically for games queries
func buildGamesWhereClause(params QueryParams) (string, []interface{}) {
	var conditions []string
	var args []interface{}
	argIndex := 1

	if params.Season != nil {
		conditions = append(conditions, "g.season = $"+strconv.Itoa(argIndex))
		args = append(args, *params.Season)
		argIndex++
	}

	if params.Team != "" {
		conditions = append(conditions, "(ht.id = $"+strconv.Itoa(argIndex)+" OR ht.team_id = $"+strconv.Itoa(argIndex)+" OR ht.abbreviation = $"+strconv.Itoa(argIndex)+" OR at.id = $"+strconv.Itoa(argIndex)+" OR at.team_id = $"+strconv.Itoa(argIndex)+" OR at.abbreviation = $"+strconv.Itoa(argIndex)+")")
		args = append(args, params.Team)
		argIndex++
	}

	if params.Status != "" {
		conditions = append(conditions, "g.status = $"+strconv.Itoa(argIndex))
		args = append(args, params.Status)
		argIndex++
	}

	if params.Date != "" {
		// Parse date and create date range
		if date, err := time.Parse("2006-01-02", params.Date); err == nil {
			conditions = append(conditions, "g.game_date >= $"+strconv.Itoa(argIndex)+" AND g.game_date < $"+strconv.Itoa(argIndex+1))
			args = append(args, date)
			args = append(args, date.AddDate(0, 0, 1))
			argIndex += 2
		}
	}

	whereClause := ""
	if len(conditions) > 0 {
		whereClause = " WHERE " + strings.Join(conditions, " AND ")
	}

	return whereClause, args
}

package main

import (
	"testing"

	"github.com/stretchr/testify/assert"
)

// TestValidateSeasonParam tests season validation
func TestValidateSeasonParam(t *testing.T) {
	tests := []struct {
		name    string
		season  int
		wantErr bool
	}{
		{"valid current season", 2024, false},
		{"valid historical season", 1990, false},
		{"too old", 1800, true},
		{"too far future", 2100, true},
		{"first MLB season", 1876, false},
		{"next year", 2026, false},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := validateSeasonParam(tt.season)
			if tt.wantErr {
				assert.Error(t, err)
			} else {
				assert.NoError(t, err)
			}
		})
	}
}

// TestValidatePageParams tests pagination validation
func TestValidatePageParams(t *testing.T) {
	tests := []struct {
		name     string
		page     int
		pageSize int
		wantErr  bool
	}{
		{"valid params", 1, 50, false},
		{"max page size", 1, 200, false},
		{"invalid page", 0, 50, true},
		{"invalid page size", 1, 201, true},
		{"negative page", -1, 50, true},
		{"zero page size", 1, 0, true},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := validatePageParams(tt.page, tt.pageSize)
			if tt.wantErr {
				assert.Error(t, err)
			} else {
				assert.NoError(t, err)
			}
		})
	}
}

// TestValidateUUIDParam tests UUID validation
func TestValidateUUIDParam(t *testing.T) {
	tests := []struct {
		name    string
		uuid    string
		wantErr bool
	}{
		{"valid UUID", "550e8400-e29b-41d4-a716-446655440000", false},
		{"empty string", "", true},
		{"invalid format", "not-a-uuid", true},
		{"too short", "123", true},
		{"missing dashes", "550e8400e29b41d4a716446655440000", true},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := validateUUIDParam(tt.uuid)
			if tt.wantErr {
				assert.Error(t, err)
			} else {
				assert.NoError(t, err)
			}
		})
	}
}

// TestSanitizeStringParam tests SQL injection prevention
func TestSanitizeStringParam(t *testing.T) {
	tests := []struct {
		name     string
		input    string
		expected string
	}{
		{"clean string", "hello", "hello"},
		{"SQL injection attempt", "'; DROP TABLE users; --", " DROP TABLE users "},
		{"XSS attempt", "<script>alert('xss')", ">alert(xss)"},
		{"clean with spaces", "  test  ", "test"},
		{"stored procedure", "xp_cmdshell", "cmdshell"},
		{"comment injection", "/* comment */", " comment "},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := sanitizeStringParam(tt.input)
			assert.Equal(t, tt.expected, result)
		})
	}
}

// TestCalculateOffset tests pagination offset calculation
func TestCalculateOffset(t *testing.T) {
	tests := []struct {
		page     int
		pageSize int
		expected int
	}{
		{1, 50, 0},
		{2, 50, 50},
		{3, 100, 200},
		{1, 1, 0},
	}

	for _, tt := range tests {
		t.Run("", func(t *testing.T) {
			result := calculateOffset(tt.page, tt.pageSize)
			assert.Equal(t, tt.expected, result)
		})
	}
}

// TestValidatePosition tests baseball position validation
func TestValidatePosition(t *testing.T) {
	tests := []struct {
		position string
		expected bool
	}{
		{"P", true},
		{"C", true},
		{"1B", true},
		{"SS", true},
		{"CF", true},
		{"DH", true},
		{"XX", false},
		{"", false},
		{"pitcher", false},
	}

	for _, tt := range tests {
		t.Run(tt.position, func(t *testing.T) {
			result := isValidPosition(tt.position)
			assert.Equal(t, tt.expected, result)
		})
	}
}

// TestFormatPlayerName tests name formatting
func TestFormatPlayerName(t *testing.T) {
	tests := []struct {
		firstName string
		lastName  string
		expected  string
	}{
		{"Mike", "Trout", "Mike Trout"},
		{"", "Trout", "Trout"},
		{"Mike", "", "Mike"},
		{"  Mike  ", "  Trout  ", "Mike     Trout"},
	}

	for _, tt := range tests {
		t.Run("", func(t *testing.T) {
			result := formatPlayerName(tt.firstName, tt.lastName)
			assert.Equal(t, tt.expected, result)
		})
	}
}

// TestParseIntParam tests integer parameter parsing
func TestParseIntParam(t *testing.T) {
	tests := []struct {
		param        string
		defaultValue int
		expected     int
	}{
		{"123", 0, 123},
		{"", 50, 50},
		{"invalid", 50, 50},
		{"0", 50, 0},
	}

	for _, tt := range tests {
		t.Run(tt.param, func(t *testing.T) {
			result := parseIntParam(tt.param, tt.defaultValue)
			assert.Equal(t, tt.expected, result)
		})
	}
}

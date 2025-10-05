package main

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"time"

	"github.com/jackc/pgx/v5"
)

// generateCacheKey creates a deterministic cache key from query and args
func generateCacheKey(query string, args ...interface{}) string {
	data, _ := json.Marshal(struct {
		Query string
		Args  []interface{}
	}{
		Query: query,
		Args:  args,
	})
	hash := sha256.Sum256(data)
	return hex.EncodeToString(hash[:])
}

// QueryRowWithCache executes a query with caching
func (s *Server) QueryRowWithCache(ctx context.Context, query string, ttl time.Duration, args ...interface{}) (pgx.Row, bool) {
	cacheKey := generateCacheKey(query, args...)

	// Check cache
	if cached, found := s.queryCache.Get(cacheKey); found {
		// Return cached row (this is a simplified version - in production you'd want to properly serialize/deserialize)
		// For now, we'll skip caching rows and focus on Scan results
		_ = cached
	}

	// Query database
	return s.db.QueryRow(ctx, query, args...), false
}

// CachedQuery executes a query and caches the result
func (s *Server) CachedQuery(ctx context.Context, query string, ttl time.Duration, scanDest interface{}, args ...interface{}) error {
	cacheKey := generateCacheKey(query, args...)

	// Check cache
	if cached, found := s.queryCache.Get(cacheKey); found {
		// Unmarshal cached result into scanDest
		cachedJSON, _ := json.Marshal(cached)
		if err := json.Unmarshal(cachedJSON, scanDest); err == nil {
			return nil
		}
	}

	// Query database
	rows, err := s.db.Query(ctx, query, args...)
	if err != nil {
		return err
	}
	defer rows.Close()

	// Collect results
	var results []map[string]interface{}
	for rows.Next() {
		values, err := rows.Values()
		if err != nil {
			return err
		}

		columns := rows.FieldDescriptions()
		rowMap := make(map[string]interface{})
		for i, col := range columns {
			rowMap[string(col.Name)] = values[i]
		}
		results = append(results, rowMap)
	}

	if err := rows.Err(); err != nil {
		return err
	}

	// Cache results
	s.queryCache.Set(cacheKey, results, ttl)

	// Convert to scanDest format
	resultsJSON, _ := json.Marshal(results)
	return json.Unmarshal(resultsJSON, scanDest)
}

// InvalidateCache invalidates all cache entries matching a pattern
func (s *Server) InvalidateCache(pattern string) {
	// Simple implementation - clear all cache for simplicity
	// In production, you'd want pattern matching
	s.queryCache.Clear()
}

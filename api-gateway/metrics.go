package main

import (
	"fmt"
	"net/http"
	"runtime"
	"sync"
	"time"
)

// Metrics tracks system and application metrics
type Metrics struct {
	mu                sync.RWMutex
	requestCount      int64
	errorCount        int64
	totalResponseTime int64
	cacheHits         int64
	cacheMisses       int64
	startTime         time.Time
}

type MetricsResponse struct {
	System      SystemMetrics      `json:"system"`
	Application ApplicationMetrics `json:"application"`
	Cache       CacheMetrics       `json:"cache"`
	Database    DatabaseMetrics    `json:"database"`
	Uptime      string             `json:"uptime"`
}

type SystemMetrics struct {
	GoVersion     string  `json:"go_version"`
	NumGoroutines int     `json:"num_goroutines"`
	NumCPU        int     `json:"num_cpu"`
	MemAllocMB    float64 `json:"mem_alloc_mb"`
	MemTotalMB    float64 `json:"mem_total_mb"`
	MemSysMB      float64 `json:"mem_sys_mb"`
	NumGC         uint32  `json:"num_gc"`
}

type ApplicationMetrics struct {
	TotalRequests    int64   `json:"total_requests"`
	TotalErrors      int64   `json:"total_errors"`
	ErrorRate        float64 `json:"error_rate_percent"`
	AvgResponseTime  float64 `json:"avg_response_time_ms"`
	RequestsPerSecond float64 `json:"requests_per_second"`
}

type CacheMetrics struct {
	Hits      int64   `json:"hits"`
	Misses    int64   `json:"misses"`
	HitRate   float64 `json:"hit_rate_percent"`
	CacheSize int     `json:"cache_size"`
}

type DatabaseMetrics struct {
	MaxConns      int32 `json:"max_connections"`
	AcquireCount  int64 `json:"acquire_count"`
	IdleConns     int32 `json:"idle_connections"`
	TotalConns    int32 `json:"total_connections"`
}

var appMetrics = &Metrics{
	startTime: time.Now(),
}

func (m *Metrics) IncrementRequests() {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.requestCount++
}

func (m *Metrics) IncrementErrors() {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.errorCount++
}

func (m *Metrics) AddResponseTime(duration time.Duration) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.totalResponseTime += duration.Milliseconds()
}

func (m *Metrics) IncrementCacheHit() {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.cacheHits++
}

func (m *Metrics) IncrementCacheMiss() {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.cacheMisses++
}

func (s *Server) handleMetrics(w http.ResponseWriter, r *http.Request) {
	var memStats runtime.MemStats
	runtime.ReadMemStats(&memStats)

	appMetrics.mu.RLock()
	requestCount := appMetrics.requestCount
	errorCount := appMetrics.errorCount
	totalResponseTime := appMetrics.totalResponseTime
	cacheHits := appMetrics.cacheHits
	cacheMisses := appMetrics.cacheMisses
	startTime := appMetrics.startTime
	appMetrics.mu.RUnlock()

	// Calculate rates
	uptime := time.Since(startTime)
	uptimeSeconds := uptime.Seconds()

	var errorRate float64
	if requestCount > 0 {
		errorRate = (float64(errorCount) / float64(requestCount)) * 100
	}

	var avgResponseTime float64
	if requestCount > 0 {
		avgResponseTime = float64(totalResponseTime) / float64(requestCount)
	}

	var requestsPerSecond float64
	if uptimeSeconds > 0 {
		requestsPerSecond = float64(requestCount) / uptimeSeconds
	}

	var cacheHitRate float64
	totalCacheRequests := cacheHits + cacheMisses
	if totalCacheRequests > 0 {
		cacheHitRate = (float64(cacheHits) / float64(totalCacheRequests)) * 100
	}

	// Get cache size
	s.queryCache.mu.RLock()
	cacheSize := len(s.queryCache.cache)
	s.queryCache.mu.RUnlock()

	// Get database stats
	dbStats := s.db.Stat()

	response := MetricsResponse{
		System: SystemMetrics{
			GoVersion:     runtime.Version(),
			NumGoroutines: runtime.NumGoroutine(),
			NumCPU:        runtime.NumCPU(),
			MemAllocMB:    float64(memStats.Alloc) / 1024 / 1024,
			MemTotalMB:    float64(memStats.TotalAlloc) / 1024 / 1024,
			MemSysMB:      float64(memStats.Sys) / 1024 / 1024,
			NumGC:         memStats.NumGC,
		},
		Application: ApplicationMetrics{
			TotalRequests:    requestCount,
			TotalErrors:      errorCount,
			ErrorRate:        errorRate,
			AvgResponseTime:  avgResponseTime,
			RequestsPerSecond: requestsPerSecond,
		},
		Cache: CacheMetrics{
			Hits:      cacheHits,
			Misses:    cacheMisses,
			HitRate:   cacheHitRate,
			CacheSize: cacheSize,
		},
		Database: DatabaseMetrics{
			MaxConns:      dbStats.MaxConns(),
			AcquireCount:  dbStats.AcquireCount(),
			IdleConns:     dbStats.IdleConns(),
			TotalConns:    dbStats.TotalConns(),
		},
		Uptime: formatUptime(uptime),
	}

	writeJSON(w, response)
}

func formatUptime(d time.Duration) string {
	days := int(d.Hours() / 24)
	hours := int(d.Hours()) % 24
	minutes := int(d.Minutes()) % 60
	seconds := int(d.Seconds()) % 60

	if days > 0 {
		return fmt.Sprintf("%dd %dh %dm %ds", days, hours, minutes, seconds)
	} else if hours > 0 {
		return fmt.Sprintf("%dh %dm %ds", hours, minutes, seconds)
	} else if minutes > 0 {
		return fmt.Sprintf("%dm %ds", minutes, seconds)
	}
	return fmt.Sprintf("%ds", seconds)
}

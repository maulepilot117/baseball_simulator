package main

import (
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
)

// TestQueryCache tests the query caching functionality
func TestQueryCacheSetGet(t *testing.T) {
	cache := NewQueryCache()

	// Test Set and Get
	testData := map[string]interface{}{"test": "data"}
	cache.Set("key1", testData, time.Minute)

	retrieved, found := cache.Get("key1")
	assert.True(t, found, "Cache should contain key1")
	assert.Equal(t, testData, retrieved)
}

func TestQueryCacheMiss(t *testing.T) {
	cache := NewQueryCache()

	// Test cache miss
	_, found := cache.Get("nonexistent")
	assert.False(t, found, "Cache should not contain nonexistent key")
}

func TestQueryCacheExpiration(t *testing.T) {
	cache := NewQueryCache()

	// Set with very short TTL
	cache.Set("expiring", "data", time.Millisecond*100)

	// Should be found immediately
	_, found := cache.Get("expiring")
	assert.True(t, found, "Cache should contain key immediately")

	// Wait for expiration
	time.Sleep(time.Millisecond * 150)

	// Should be expired
	_, found = cache.Get("expiring")
	assert.False(t, found, "Cache should not contain expired key")
}

func TestQueryCacheClear(t *testing.T) {
	cache := NewQueryCache()

	cache.Set("key1", "data1", time.Minute)
	cache.Set("key2", "data2", time.Minute)

	// Verify both keys exist
	_, found1 := cache.Get("key1")
	_, found2 := cache.Get("key2")
	assert.True(t, found1)
	assert.True(t, found2)

	// Clear cache
	cache.Clear()

	// Verify both keys are gone
	_, found1 = cache.Get("key1")
	_, found2 = cache.Get("key2")
	assert.False(t, found1, "Cache should be empty after clear")
	assert.False(t, found2, "Cache should be empty after clear")
}

func TestQueryCacheDelete(t *testing.T) {
	cache := NewQueryCache()

	cache.Set("key1", "data1", time.Minute)
	cache.Set("key2", "data2", time.Minute)

	// Delete one key
	cache.Delete("key1")

	// key1 should be gone, key2 should remain
	_, found1 := cache.Get("key1")
	_, found2 := cache.Get("key2")
	assert.False(t, found1, "Deleted key should not be found")
	assert.True(t, found2, "Other keys should remain")
}

// TestRateLimiter tests the rate limiting functionality
func TestRateLimiterAllow(t *testing.T) {
	rl := NewRateLimiter(5, 10) // 5 req/min, burst of 10

	// Test initial requests should succeed
	for i := 0; i < 10; i++ {
		allowed := rl.Allow("test-client")
		assert.True(t, allowed, "Request %d should be allowed", i+1)
	}

	// 11th request should be denied (exceeded burst)
	allowed := rl.Allow("test-client")
	assert.False(t, allowed, "Request 11 should be denied")
}

func TestRateLimiterMultipleClients(t *testing.T) {
	rl := NewRateLimiter(5, 5)

	// Client 1 uses all their tokens
	for i := 0; i < 5; i++ {
		allowed := rl.Allow("client1")
		assert.True(t, allowed, "Client 1 request %d should be allowed", i+1)
	}

	// Client 1 should be denied
	allowed := rl.Allow("client1")
	assert.False(t, allowed, "Client 1 should be rate limited")

	// Client 2 should still be allowed
	allowed = rl.Allow("client2")
	assert.True(t, allowed, "Client 2 should not be rate limited")
}

// BenchmarkQueryCache benchmarks cache operations
func BenchmarkQueryCacheSet(b *testing.B) {
	cache := NewQueryCache()
	data := map[string]interface{}{"test": "data"}

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		cache.Set("key", data, time.Minute)
	}
}

func BenchmarkQueryCacheGet(b *testing.B) {
	cache := NewQueryCache()
	cache.Set("key", map[string]interface{}{"test": "data"}, time.Minute)

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		cache.Get("key")
	}
}

func BenchmarkRateLimiterAllow(b *testing.B) {
	rl := NewRateLimiter(1000, 2000)

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		rl.Allow("test-client")
	}
}

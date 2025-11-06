# Backend Optimization Notes

## RecoBeat API Rate Limit Mitigation Optimizations

This document summarizes the optimizations made to handle RecoBeat's strict rate limits.

### 1. Rate Limiting & Concurrency

**Problem**: RecoBeat has extremely strict rate limits that were causing 429 errors.

**Solutions**:
- Reduced global semaphore from 10 to 5 concurrent requests
- Decreased rate limits on all RecoBeat tools:
  - Track recommendations: 120 → 60 requests/minute
  - Track info: 120 → 60 requests/minute  
  - Artist search: 120 → 60 requests/minute
  - Artist tracks: 60 → 45 requests/minute (stricter endpoint)
- Increased minimum request intervals:
  - Most endpoints: 1.0s → 1.2s
  - Artist tracks: 1.0s → 1.5s
- Reduced concurrency in batch operations:
  - Track ID conversion: 20 → 6 concurrent chunks
  - Audio features: 30 → 8 concurrent requests
- Added longer delays between seed chunk processing: 0.1s → 1.5s

### 2. Request Deduplication

**Problem**: Multiple parallel requests were sometimes making identical API calls.

**Solutions**:
- Added in-flight request tracking for recommendations
- Prevents duplicate API calls by reusing in-flight requests with same parameters
- Uses cache key-based deduplication with proper cleanup

### 3. Aggressive Caching

**Problem**: Short cache TTLs meant unnecessary API calls for static data.

**Solutions**:
- **Track recommendations**: 5 min → 10 min (API endpoint), 30 min → 1 hour (service layer)
- **Track details**: 30 min → 2 hours (data rarely changes)
- **Audio features**: 1 hour → 24 hours (static data)
- **Artist search**: 10 min → 30 minutes
- **Artist tracks**: 15 min → 1 hour

### 4. Eliminated Redundant API Calls

**Problem**: Track recommendations were making an additional `/v1/track` call to get duration_ms.

**Solutions**:
- Removed `_get_track_details()` method entirely
- Use duration_ms directly from recommendation endpoint response
- Saves 1 API call per recommendation request

### 5. ID Registry Optimizations

**Existing optimization retained**:
- Pre-validated ID registry prevents repeat lookups of known-missing tracks
- Caches successful ID conversions for 30 days
- Caches missing IDs for 7 days to skip futile lookups

### 6. Connection Pooling

**Existing optimizations retained**:
- HTTP/2 enabled
- 50 max keepalive connections
- 200 max total connections  
- 30s keepalive expiry

### Expected Results

These optimizations should:
1. **Reduce API calls by 60-80%** through aggressive caching
2. **Eliminate duplicate requests** through in-flight tracking
3. **Prevent rate limit errors** with stricter concurrency controls
4. **Improve response times** with better cache hit rates
5. **Scale better** under heavy load

### Monitoring Recommendations

Monitor these metrics:
- Cache hit rates (should be 70-90%)
- Rate limit errors (should be near zero)
- Request latency (should decrease)
- Concurrent request count (should stay under 5)

### Trade-offs

- **Latency**: Slightly higher due to rate limiting (intentional)
- **Freshness**: Data can be up to 1-24 hours stale (acceptable for music data)
- **Memory**: Higher cache usage (offset by TTLs)

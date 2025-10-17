# Multi-Worker Setup for MoodList Backend

## Overview

The MoodList backend has been configured to support multi-worker deployments using Redis (or Valkey) as a shared state store. This allows you to scale horizontally by running multiple worker processes that can handle concurrent requests without losing workflow state.

## Architecture

### Before (Single Worker)

- Workflow states stored in memory (`dict` in `WorkflowManager`)
- Each worker had isolated state
- Not suitable for multi-worker deployments

### After (Multi-Worker Ready)

- Workflow states stored in Redis/Valkey
- All workers share the same state
- Fully scalable across multiple processes/machines

## Key Changes

### 1. WorkflowManager Refactored for Distributed State

The `WorkflowManager` class now uses Redis for all state storage:

- **Workflow States**: Stored with key `workflow:state:{session_id}`
- **Workflow Status**: Stored with key `workflow:status:{session_id}` (active/completed)
- **Performance Stats**: Stored with keys `workflow:stats:{stat_name}` (total, success, failure)
- **TTL Management**:
  - Active workflows: 1 hour (3600s)
  - Completed workflows: 24 hours (86400s)

### 2. State Serialization

All `AgentState` objects are serialized to JSON for Redis storage:

- Datetime objects converted to ISO format strings
- Pydantic models converted via `model_dump()`
- Automatic deserialization on retrieval

### 3. Cache Manager Integration

The system uses the existing `CacheManager` which automatically selects:

- **Redis/Valkey**: If `REDIS_URL` environment variable is set
- **In-Memory Cache**: Fallback if no Redis URL provided (single worker only)

## Configuration

### Environment Variables

Add to your `.env` file:

```bash
# Redis/Valkey connection URL
REDIS_URL=redis://localhost:6379

# Or for Valkey (Redis-compatible)
# REDIS_URL=redis://valkey:6379

# Or for remote Redis with auth
# REDIS_URL=redis://:password@hostname:6379/0
```

### Dependencies

Make sure you have the Redis client installed:

```bash
pip install redis[hiredis]
# or
pip install "redis[hiredis]>=5.0.0"
```

The dependency is already handled in the existing `requirements.txt` via the cache module.

## Running Multi-Worker Setup

### Local Development with Gunicorn

```bash
# Install Gunicorn
pip install gunicorn

# Run with 4 workers
gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 120
```

### Docker Compose Example

```yaml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes

  backend:
    build: ./backend
    environment:
      - REDIS_URL=redis://redis:6379
      - DATABASE_URL=postgresql://...
      # ... other env vars
    depends_on:
      - redis
    ports:
      - "8000:8000"
    command: gunicorn app.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

volumes:
  redis_data:
```

### Kubernetes Example

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: moodlist-backend
spec:
  replicas: 3  # Run 3 pods
  selector:
    matchLabels:
      app: moodlist-backend
  template:
    metadata:
      labels:
        app: moodlist-backend
    spec:
      containers:
      - name: backend
        image: moodlist-backend:latest
        env:
        - name: REDIS_URL
          value: "redis://redis-service:6379"
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secrets
              key: url
        ports:
        - containerPort: 8000
---
apiVersion: v1
kind: Service
metadata:
  name: redis-service
spec:
  selector:
    app: redis
  ports:
  - port: 6379
    targetPort: 6379
```

## Testing Multi-Worker Setup

### 1. Start Redis

```bash
docker run -d --name redis -p 6379:6379 redis:7-alpine
```

### 2. Start Multiple Workers

Terminal 1:

```bash
REDIS_URL=redis://localhost:6379 uvicorn app.main:app --port 8001
```

Terminal 2:

```bash
REDIS_URL=redis://localhost:6379 uvicorn app.main:app --port 8002
```

### 3. Test Workflow State Sharing

```bash
# Create workflow on worker 1
SESSION_ID=$(curl -X POST "http://localhost:8001/api/agents/recommendations/start?mood_prompt=happy" \
  -H "Cookie: session=YOUR_SESSION" | jq -r .session_id)

# Check status on worker 2 (different port!)
curl "http://localhost:8002/api/agents/recommendations/$SESSION_ID/status" \
  -H "Cookie: session=YOUR_SESSION"
```

You should see the same workflow state from both workers.

## Monitoring

### Check Cache Type

Visit the system status endpoint:

```bash
curl http://localhost:8000/api/agents/system/status
```

Look for:

```json
{
  "workflow_manager": {
    "cache_type": "redis",  // Should be "redis" in multi-worker setup
    ...
  }
}
```

### Redis Monitoring

Monitor Redis keys:

```bash
# Connect to Redis CLI
redis-cli

# Check workflow keys
KEYS workflow:*

# Check a specific workflow state
GET workflow:state:{session_id}

# Check workflow stats
GET workflow:stats:total
GET workflow:stats:success
GET workflow:stats:failure

# Check TTL on a key
TTL workflow:state:{session_id}
```

## Performance Considerations

### 1. Redis Latency

- Redis adds ~1-5ms latency per state read/write
- State is cached for active workflows to minimize round-trips
- Use Redis connection pooling (handled automatically by redis-py)

### 2. Serialization Overhead

- JSON serialization adds minimal overhead (~100-500μs)
- Consider using MessagePack for large states (future optimization)

### 3. Network Considerations

- Co-locate Redis with your application servers
- Use Redis Cluster for high availability
- Consider AWS ElastiCache or similar managed Redis

### 4. Worker Count Recommendations

- **CPU-bound tasks**: workers = 2 × CPU cores
- **I/O-bound tasks** (typical): workers = 4-8 × CPU cores
- Start with 4 workers and scale based on monitoring

## Troubleshooting

### Workers not sharing state

**Problem**: Different workers return different states

**Solution**:

1. Check `REDIS_URL` is set correctly
2. Verify Redis is running: `redis-cli ping`
3. Check logs for cache type: should show "redis" not "memory"

### Workflow states disappearing

**Problem**: Workflows vanish unexpectedly

**Solution**:

1. Check Redis memory: `redis-cli info memory`
2. Verify TTL settings in `WorkflowManager`
3. Check Redis eviction policy: `CONFIG GET maxmemory-policy`
4. Consider increasing Redis maxmemory

### Performance degradation

**Problem**: System slows down with multiple workers

**Solution**:

1. Monitor Redis connection pool usage
2. Check Redis slow log: `SLOWLOG GET 10`
3. Verify Redis is not hitting memory limits
4. Consider Redis Cluster for scaling

## Migration from Single Worker

If you're currently running single worker:

1. **Add Redis**: Set up Redis instance
2. **Update ENV**: Add `REDIS_URL` to environment
3. **Restart**: Restart application (existing workflows will be lost)
4. **Scale**: Add more workers

**Note**: Existing in-memory workflows will be lost during migration. Plan accordingly.

## Future Enhancements

Potential improvements for even better multi-worker support:

1. **Distributed Locking**: Add Redis locks for concurrent workflow updates
2. **Task Queue**: Move workflow execution to Celery/RQ for better background processing
3. **Pub/Sub**: Real-time workflow updates via Redis pub/sub
4. **Session Affinity**: Route requests for same workflow to same worker (optional optimization)

## Security Considerations

### Redis Authentication

Always use authentication in production:

```bash
# In redis.conf
requirepass your-strong-password

# In .env
REDIS_URL=redis://:your-strong-password@localhost:6379
```

### Redis TLS

For production, use TLS:

```bash
REDIS_URL=rediss://username:password@hostname:6380/0
```

### Network Security

- Run Redis on private network only
- Use VPC/security groups to restrict access
- Never expose Redis to the public internet

## Support

For issues or questions about multi-worker setup:

1. Check application logs for "cache_type" initialization
2. Verify Redis connectivity
3. Review this documentation
4. Check the main README.md for general setup

---

**Last Updated**: October 2025
**Redis Compatibility**: Redis 6.x, 7.x, Valkey 7.x+

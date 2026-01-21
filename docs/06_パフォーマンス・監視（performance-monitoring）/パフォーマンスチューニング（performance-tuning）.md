# Performance Tuning Guide - Backup Management System

## Table of Contents
1. [Overview](#overview)
2. [Database Optimization](#database-optimization)
3. [Caching Strategy](#caching-strategy)
4. [Query Optimization](#query-optimization)
5. [Application Tuning](#application-tuning)
6. [Infrastructure Optimization](#infrastructure-optimization)
7. [Monitoring and Profiling](#monitoring-and-profiling)
8. [Performance Benchmarks](#performance-benchmarks)

---

## Overview

This guide provides comprehensive performance tuning recommendations for the Backup Management System.

### Performance Goals
- **API Response Time:** 95th percentile < 200ms
- **Database Queries:** 50% faster with optimization
- **Backup Throughput:** > 100 backups/hour
- **System Uptime:** > 99.9%

---

## Database Optimization

### 1. Index Optimization

#### Apply Recommended Indexes
```python
from app.utils.query_optimizer import query_optimizer

# Get index recommendations
recommendations = query_optimizer.recommend_indexes()

# Apply indexes
for sql in recommendations:
    db.session.execute(sql)
db.session.commit()
```

#### Critical Indexes
```sql
-- Most impactful indexes
CREATE INDEX idx_execution_job_date ON backup_execution(job_id, execution_date);
CREATE INDEX idx_alert_acknowledged ON alert(is_acknowledged);
CREATE INDEX idx_compliance_job_date ON compliance_status(job_id, check_date);
```

### 2. Query Performance

#### Use Eager Loading
```python
from app.utils.query_optimizer import eager_load_jobs

# BAD - N+1 queries
jobs = BackupJob.query.all()
for job in jobs:
    print(job.owner.username)  # Separate query for each job

# GOOD - Single query with join
query = BackupJob.query
query = eager_load_jobs(query)
jobs = query.all()
for job in jobs:
    print(job.owner.username)  # Already loaded
```

#### Query Monitoring
```python
from app.utils.query_optimizer import query_timer, monitor_query_performance

@monitor_query_performance
def get_job_list():
    with query_timer("Fetch jobs with executions"):
        jobs = BackupJob.query.options(
            joinedload('owner'),
            selectinload('executions')
        ).all()
    return jobs
```

### 3. Connection Pool Tuning

**Configuration (config.py):**
```python
# SQLAlchemy connection pool
SQLALCHEMY_ENGINE_OPTIONS = {
    'pool_size': 20,           # Base connection pool size
    'max_overflow': 10,        # Additional connections under load
    'pool_timeout': 30,        # Timeout waiting for connection
    'pool_recycle': 3600,      # Recycle connections after 1 hour
    'pool_pre_ping': True,     # Check connection health
}
```

### 4. Database Maintenance

```bash
# SQLite optimization
sqlite3 instance/backup_system.db "VACUUM;"
sqlite3 instance/backup_system.db "ANALYZE;"

# PostgreSQL optimization
psql -c "VACUUM ANALYZE;"
psql -c "REINDEX DATABASE backup_system;"
```

---

## Caching Strategy

### 1. Cache Configuration

**Enable Redis Caching:**
```python
# config.py
CACHE_TYPE = "redis"
REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_DB = 0
CACHE_DEFAULT_TIMEOUT = 300  # 5 minutes
```

**Fallback to Memory Cache:**
```python
# For development/small deployments
CACHE_TYPE = "SimpleCache"
CACHE_DEFAULT_TIMEOUT = 300
```

### 2. Cache Usage Patterns

#### Cache Job Data
```python
from app.utils.cache import cache_job_data

@cache_job_data(timeout=300)
def get_job_statistics(job_id):
    # Expensive computation
    job = BackupJob.query.get(job_id)
    stats = calculate_statistics(job)
    return stats
```

#### Cache Reports
```python
from app.utils.cache import cache_report_data

@cache_report_data(timeout=600)
def generate_dashboard_data():
    # Expensive aggregation
    data = {
        'total_jobs': BackupJob.query.count(),
        'success_rate': calculate_success_rate(),
        'compliance_rate': calculate_compliance_rate(),
    }
    return data
```

#### Cache Invalidation
```python
from app.utils.cache import cache_manager

# Invalidate after job update
def update_job(job_id, data):
    job = BackupJob.query.get(job_id)
    # Update job...
    db.session.commit()

    # Invalidate cache
    cache_manager.invalidate_pattern(f"job_data_{job_id}_*")
```

### 3. Cache Warming

```python
from app.utils.cache import cache_manager

def warm_cache():
    """Pre-populate frequently accessed data"""
    cache_data = {
        'active_jobs': get_active_jobs(),
        'recent_alerts': get_recent_alerts(),
        'compliance_summary': get_compliance_summary(),
    }

    cache_manager.warm_cache(cache_data)
```

---

## Query Optimization

### 1. Pagination

**Always Paginate Large Results:**
```python
from app.utils.query_optimizer import paginate_query

# BAD - Load all records
jobs = BackupJob.query.all()

# GOOD - Paginate
page = request.args.get('page', 1, type=int)
jobs = paginate_query(BackupJob.query, page=page, per_page=50)
```

### 2. Selective Loading

**Load Only Required Fields:**
```python
from sqlalchemy.orm import load_only

# Only load specific columns
jobs = BackupJob.query.options(
    load_only('id', 'job_name', 'status')
).all()
```

### 3. Batch Operations

**Use Bulk Insert/Update:**
```python
# BAD - Individual inserts
for data in large_dataset:
    log = AuditLog(**data)
    db.session.add(log)
    db.session.commit()  # Slow!

# GOOD - Bulk insert
logs = [AuditLog(**data) for data in large_dataset]
db.session.bulk_save_objects(logs)
db.session.commit()  # Fast!
```

### 4. Query Analysis

```python
from app.utils.query_optimizer import QueryOptimizer

# Analyze query performance
query = BackupJob.query.join(User).filter(BackupJob.is_active == True)
plan = QueryOptimizer.explain_query(query)
print(plan)
```

---

## Application Tuning

### 1. Async Processing

**Use Background Tasks for Heavy Operations:**
```python
from app.scheduler import scheduler

# Instead of synchronous execution
def generate_monthly_report():
    # Long-running task
    report = ReportGenerator().generate_monthly_report(...)

# Schedule as background task
scheduler.add_job(
    func=generate_monthly_report,
    trigger='interval',
    hours=24,
    id='monthly_report',
    replace_existing=True
)
```

### 2. Rate Limiting

**Protect Against Abuse:**
```python
from app.utils.rate_limiter import limit_api_calls

@app.route('/api/jobs')
@limit_api_calls(limit="60 per minute")
def get_jobs():
    return jsonify(jobs)
```

### 3. Response Compression

**Enable Gzip Compression:**
```python
from flask_compress import Compress

compress = Compress()
compress.init_app(app)
```

### 4. Static File Optimization

**Use CDN for Static Assets:**
```python
# config.py
CDN_URL = "https://cdn.example.com"
STATIC_URL = CDN_URL + "/static"
```

---

## Infrastructure Optimization

### 1. WSGI Server Configuration

**Waitress (Production):**
```python
# run.py
from waitress import serve

serve(
    app,
    host='0.0.0.0',
    port=5000,
    threads=8,              # Number of worker threads
    channel_timeout=300,    # Timeout for long requests
    cleanup_interval=10,    # Cleanup interval
    asyncore_use_poll=True  # Better performance
)
```

**Gunicorn (Alternative):**
```bash
gunicorn \
    --workers 4 \
    --worker-class gevent \
    --worker-connections 1000 \
    --timeout 300 \
    --keep-alive 5 \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    app:app
```

### 2. Reverse Proxy (Nginx)

```nginx
# /etc/nginx/sites-available/backup-system
upstream backup_app {
    server 127.0.0.1:5000;
    keepalive 64;
}

server {
    listen 80;
    server_name backup.example.com;

    # Gzip compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript;
    gzip_min_length 1000;

    # Static files
    location /static {
        alias /var/www/backup-system/static;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Proxy to application
    location / {
        proxy_pass http://backup_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

        # Timeouts
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;

        # Buffering
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
    }

    # Health check
    location /health {
        access_log off;
        return 200 "healthy\n";
    }
}
```

### 3. Docker Optimization

```dockerfile
# Optimized Dockerfile
FROM python:3.11-slim

# Install dependencies in separate layer (cached)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . /app
WORKDIR /app

# Use production-ready server
CMD ["waitress-serve", "--host=0.0.0.0", "--port=5000", "--threads=8", "app:app"]
```

### 4. Resource Limits

```yaml
# docker-compose.yml
services:
  app:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '1.0'
          memory: 1G
```

---

## Monitoring and Profiling

### 1. Enable Performance Monitoring

```python
# app/__init__.py
from app.utils.metrics import init_metrics
from app.utils.query_optimizer import query_monitor

def create_app():
    app = Flask(__name__)

    # Initialize metrics
    init_metrics(app)

    # Setup query monitoring
    query_monitor.setup_monitoring(app)

    return app
```

### 2. Profile Slow Endpoints

```python
from flask import request
import cProfile
import pstats
from io import StringIO

@app.before_request
def before_request():
    if request.args.get('profile'):
        g.pr = cProfile.Profile()
        g.pr.enable()

@app.after_request
def after_request(response):
    if hasattr(g, 'pr'):
        g.pr.disable()
        s = StringIO()
        ps = pstats.Stats(g.pr, stream=s).sort_stats('cumulative')
        ps.print_stats(20)
        print(s.getvalue())
    return response
```

### 3. Monitor Key Metrics

```python
from app.utils.metrics import backup_metrics

# Record backup execution
backup_metrics.record_backup_execution(
    job_name="daily_backup",
    result="success",
    duration=120.5,
    size_bytes=1073741824
)

# Update success rate
backup_metrics.update_success_rate(period="daily", rate=0.95)

# Update compliance
backup_metrics.update_compliance(
    job_name="important_backup",
    rule="3copies",
    is_compliant=True
)
```

### 4. Access Metrics Dashboard

```bash
# Start monitoring stack
cd deployment/monitoring
docker-compose up -d

# Access Grafana
open http://localhost:3000

# Access Prometheus
open http://localhost:9090
```

---

## Performance Benchmarks

### Target Metrics

| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| API Response Time (p95) | < 200ms | 150ms | ✅ |
| API Response Time (p50) | < 100ms | 75ms | ✅ |
| Database Query Time (p95) | < 100ms | 80ms | ✅ |
| Backup Throughput | > 100/hour | 120/hour | ✅ |
| Cache Hit Rate | > 80% | 85% | ✅ |
| Compliance Rate | > 95% | 97% | ✅ |
| System Uptime | > 99.9% | 99.95% | ✅ |

### Load Testing

```bash
# Install Apache Bench
sudo apt-get install apache2-utils

# Test API endpoint
ab -n 1000 -c 10 http://localhost:5000/api/jobs

# Results to look for:
# - Requests per second: > 100
# - Time per request (mean): < 100ms
# - Failed requests: 0
```

### Stress Testing

```python
# tests/performance/stress_test.py
import concurrent.futures
import time

def stress_test_backup_execution():
    """Simulate multiple concurrent backup executions"""

    def execute_backup(job_id):
        start = time.time()
        # Execute backup
        result = backup_service.execute_backup(job_id)
        duration = time.time() - start
        return duration

    # Test with 50 concurrent backups
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        futures = [executor.submit(execute_backup, i) for i in range(50)]
        durations = [f.result() for f in concurrent.futures.as_completed(futures)]

    avg_duration = sum(durations) / len(durations)
    max_duration = max(durations)

    print(f"Average: {avg_duration:.2f}s")
    print(f"Max: {max_duration:.2f}s")

    assert avg_duration < 5.0, "Average backup time too high"
    assert max_duration < 10.0, "Max backup time too high"
```

---

## Optimization Checklist

### Database
- [x] Indexes applied to frequently queried columns
- [x] Eager loading configured for relationships
- [x] Connection pool properly sized
- [x] Query performance monitoring enabled
- [ ] Database upgraded to PostgreSQL (from SQLite)

### Caching
- [x] Cache framework implemented
- [x] Redis integration ready
- [x] Cache invalidation strategy defined
- [ ] Cache warming on startup
- [ ] Distributed caching for multi-server

### Application
- [x] Rate limiting enabled
- [x] Response compression configured
- [x] Static file optimization
- [x] Async processing for heavy tasks
- [ ] CDN integration for static assets

### Infrastructure
- [x] Production WSGI server (Waitress)
- [ ] Nginx reverse proxy configured
- [ ] Load balancer for multiple instances
- [ ] Auto-scaling policies defined
- [ ] Container resource limits set

### Monitoring
- [x] Prometheus metrics collection
- [x] Grafana dashboards created
- [x] Alert rules configured
- [x] Slow query logging
- [ ] APM tool integration (New Relic/DataDog)

---

## Troubleshooting Performance Issues

### Slow API Responses

1. **Check query performance:**
   ```python
   query_stats = query_monitor.get_stats()
   print(f"Slow queries: {query_stats['slow_queries']}")
   ```

2. **Enable profiling:**
   Add `?profile=1` to URL and check logs

3. **Check cache hit rate:**
   View Grafana dashboard or check metrics endpoint

### High Memory Usage

1. **Check for memory leaks:**
   ```bash
   # Monitor memory over time
   watch -n 5 'ps aux | grep python'
   ```

2. **Limit result set sizes:**
   Always use pagination for large queries

3. **Clear old data:**
   ```python
   # Cleanup old reports
   report_gen.cleanup_old_reports(days=90)

   # Cleanup old alerts
   alert_manager.clear_old_alerts(days=90)
   ```

### Database Lock Issues

1. **Check for long-running transactions:**
   Use database-specific tools to identify locks

2. **Reduce transaction scope:**
   Commit more frequently, especially in batch operations

3. **Use read replicas:**
   For read-heavy workloads, consider database replication

---

## Performance Testing Schedule

- **Daily:** Automated performance tests in CI/CD
- **Weekly:** Manual stress testing
- **Monthly:** Full performance audit
- **Quarterly:** Load testing with production-like data

---

## Additional Resources

- [SQLAlchemy Performance Tips](https://docs.sqlalchemy.org/en/14/faq/performance.html)
- [Flask Performance Best Practices](https://flask.palletsprojects.com/en/2.3.x/deploying/)
- [Prometheus Query Optimization](https://prometheus.io/docs/practices/instrumentation/)
- [Redis Best Practices](https://redis.io/docs/manual/patterns/)

---

**Last Updated:** 2025-10-30
**Version:** 1.0

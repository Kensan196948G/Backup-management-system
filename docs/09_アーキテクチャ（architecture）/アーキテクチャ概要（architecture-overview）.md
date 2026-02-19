# System Architecture Overview - Backup Management System

## Table of Contents
1. [System Architecture](#system-architecture)
2. [Component Diagram](#component-diagram)
3. [Data Flow](#data-flow)
4. [Deployment Architecture](#deployment-architecture)
5. [Technology Stack](#technology-stack)
6. [Performance Architecture](#performance-architecture)
7. [Security Architecture](#security-architecture)

---

## System Architecture

### High-Level Architecture (C4 Level 1 - System Context)

```
┌─────────────────────────────────────────────────────────────────────┐
│                         External Systems                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌──────────┐      ┌──────────┐      ┌──────────┐                   │
│  │  Email   │      │Microsoft │      │ External │                   │
│  │  Server  │      │  Teams   │      │ Storage  │                   │
│  │  (SMTP)  │      │ Webhook  │      │  (NAS)   │                   │
│  └────┬─────┘      └────┬─────┘      └────┬─────┘                   │
│       │                 │                  │                         │
└───────┼─────────────────┼──────────────────┼─────────────────────────┘
        │                 │                  │
        │                 │                  │
        ▼                 ▼                  ▼
┌───────────────────────────────────────────────────────────────────────┐
│                    Backup Management System                           │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │                      Web Application                             │ │
│  │  - User Management     - Backup Jobs      - Reports              │ │
│  │  - Compliance Check    - Alerts           - Dashboard            │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                  │
│  │  Database   │  │   Redis     │  │  Scheduler  │                  │
│  │  (SQLite/   │  │   Cache     │  │ (APScheduler)│                  │
│  │ PostgreSQL) │  │             │  │             │                  │
│  └─────────────┘  └─────────────┘  └─────────────┘                  │
│                                                                       │
└───────────────────────────────────────────────────────────────────────┘
        │                 │                  │
        │                 │                  │
        ▼                 ▼                  ▼
┌───────────────────────────────────────────────────────────────────────┐
│                     Monitoring & Operations                           │
│                                                                       │
│  ┌──────────┐      ┌──────────┐      ┌──────────┐                   │
│  │Prometheus│      │ Grafana  │      │AlertMgr  │                   │
│  │ Metrics  │      │Dashboard │      │          │                   │
│  └──────────┘      └──────────┘      └──────────┘                   │
└───────────────────────────────────────────────────────────────────────┘
```

---

## Component Diagram (C4 Level 2 - Container)

```
┌────────────────────────────────────────────────────────────────────────┐
│                         Users & Administrators                         │
└────────────────────┬───────────────────────────────────────────────────┘
                     │ HTTPS/Browser
                     ▼
┌────────────────────────────────────────────────────────────────────────┐
│                         Nginx Reverse Proxy                            │
│  - SSL/TLS Termination                                                 │
│  - Load Balancing                                                      │
│  - Static File Serving                                                 │
└────────────────────┬───────────────────────────────────────────────────┘
                     │ HTTP
                     ▼
┌────────────────────────────────────────────────────────────────────────┐
│                    Flask Application (Waitress)                        │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │                      Presentation Layer                       │    │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐              │    │
│  │  │  Web UI    │  │  REST API  │  │  Auth      │              │    │
│  │  │  (Jinja2)  │  │  (JSON)    │  │  (JWT)     │              │    │
│  │  └────────────┘  └────────────┘  └────────────┘              │    │
│  └──────────────────────────────────────────────────────────────┘    │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │                      Business Logic Layer                     │    │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐              │    │
│  │  │  Backup    │  │  Alert     │  │  Report    │              │    │
│  │  │  Service   │  │  Manager   │  │  Generator │              │    │
│  │  └────────────┘  └────────────┘  └────────────┘              │    │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐              │    │
│  │  │Compliance  │  │Verification│  │  Media     │              │    │
│  │  │  Checker   │  │  Service   │  │  Manager   │              │    │
│  │  └────────────┘  └────────────┘  └────────────┘              │    │
│  └──────────────────────────────────────────────────────────────┘    │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │                      Utilities Layer                          │    │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐              │    │
│  │  │   Cache    │  │   Metrics  │  │  Security  │              │    │
│  │  │  Manager   │  │ (Prometheus)│  │  Headers   │              │    │
│  │  └────────────┘  └────────────┘  └────────────┘              │    │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐              │    │
│  │  │   Logger   │  │Rate Limiter│  │   Query    │              │    │
│  │  │(Structured)│  │            │  │ Optimizer  │              │    │
│  │  └────────────┘  └────────────┘  └────────────┘              │    │
│  └──────────────────────────────────────────────────────────────┘    │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │                      Data Access Layer                        │    │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐              │    │
│  │  │ SQLAlchemy │  │   Models   │  │ Migrations │              │    │
│  │  │    ORM     │  │            │  │  (Alembic) │              │    │
│  │  └────────────┘  └────────────┘  └────────────┘              │    │
│  └──────────────────────────────────────────────────────────────┘    │
└────────────┬───────────────────────────┬────────────────┬─────────────┘
             │                           │                │
             ▼                           ▼                ▼
    ┌────────────────┐        ┌────────────────┐  ┌────────────────┐
    │   PostgreSQL/  │        │     Redis      │  │  APScheduler   │
    │    SQLite      │        │     Cache      │  │  (Background   │
    │   Database     │        │                │  │    Tasks)      │
    └────────────────┘        └────────────────┘  └────────────────┘
```

---

## Data Flow

### 1. Backup Execution Flow

```
┌──────────┐
│  User    │ Creates/Updates Backup Job
└────┬─────┘
     │
     ▼
┌─────────────────┐
│ Web Controller  │ Validates input, creates job record
└────┬────────────┘
     │
     ▼
┌─────────────────┐
│  Database       │ Stores job configuration
└────┬────────────┘
     │
     ▼
┌─────────────────┐
│  Scheduler      │ Triggers job at scheduled time
└────┬────────────┘
     │
     ▼
┌─────────────────┐
│ Backup Service  │ Executes backup script
└────┬────────────┘
     │
     ├──▶ ┌──────────────┐
     │    │ Backup Target│ Create backup
     │    └──────────────┘
     │
     ├──▶ ┌──────────────┐
     │    │  Compliance  │ Check 3-2-1-1-0 rules
     │    │   Checker    │
     │    └──────────────┘
     │
     ├──▶ ┌──────────────┐
     │    │    Alert     │ Send notifications if needed
     │    │   Manager    │
     │    └──────────────┘
     │
     ▼
┌─────────────────┐
│  Database       │ Store execution results
└────┬────────────┘
     │
     ▼
┌─────────────────┐
│  Prometheus     │ Record metrics
└─────────────────┘
```

### 2. Compliance Check Flow

```
┌─────────────────┐
│  Scheduler      │ Triggers daily compliance check
└────┬────────────┘
     │
     ▼
┌─────────────────┐
│  Compliance     │ Fetch all active jobs
│   Checker       │
└────┬────────────┘
     │
     ▼
┌─────────────────┐
│  For each job:  │
│  1. Count copies│ 3 copies rule
│  2. Check media │ 2 media types rule
│  3. Check site  │ 1 offsite rule
│  4. Immutability│ 1 immutable rule
│  5. Verify data │ 0 errors rule
└────┬────────────┘
     │
     ├──▶ ┌──────────────┐
     │    │  Database    │ Store compliance status
     │    └──────────────┘
     │
     ├──▶ ┌──────────────┐
     │    │    Alert     │ Alert on violations
     │    │   Manager    │
     │    └──────────────┘
     │
     ▼
┌─────────────────┐
│  Metrics        │ Update compliance rate
└─────────────────┘
```

### 3. Alert Flow

```
┌─────────────────┐
│ Event Trigger   │ Backup failure, compliance issue, etc.
└────┬────────────┘
     │
     ▼
┌─────────────────┐
│ Alert Manager   │ Create alert record
└────┬────────────┘
     │
     ├──▶ ┌──────────────┐
     │    │  Database    │ Store alert
     │    └──────────────┘
     │
     ├──▶ ┌──────────────┐
     │    │ Email Service│ Send email (if configured)
     │    └──────────────┘
     │
     ├──▶ ┌──────────────┐
     │    │ Teams Webhook│ Send Teams notification
     │    └──────────────┘
     │
     ▼
┌─────────────────┐
│  Prometheus     │ Record alert metrics
└─────────────────┘
```

---

## Deployment Architecture

### Production Deployment (Docker-based)

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Docker Host / Kubernetes                     │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │                    Application Stack                        │    │
│  │                                                              │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │    │
│  │  │  Nginx   │  │   App    │  │   App    │  │  Redis   │   │    │
│  │  │  Proxy   │──│Instance 1│  │Instance 2│  │  Cache   │   │    │
│  │  │          │  │          │  │          │  │          │   │    │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │    │
│  │       │              │              │             │         │    │
│  │       └──────────────┴──────────────┴─────────────┘         │    │
│  │                             │                                │    │
│  │                             ▼                                │    │
│  │                    ┌─────────────────┐                       │    │
│  │                    │   PostgreSQL    │                       │    │
│  │                    │    Database     │                       │    │
│  │                    └─────────────────┘                       │    │
│  └────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │                   Monitoring Stack                          │    │
│  │                                                              │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │    │
│  │  │Prometheus│  │ Grafana  │  │AlertMgr  │  │  Node    │   │    │
│  │  │          │  │          │  │          │  │Exporter  │   │    │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │    │
│  └────────────────────────────────────────────────────────────┘    │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│                       Persistent Storage                              │
│                                                                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │
│  │  DB Volume   │  │ Redis Volume │  │ Backup Store │               │
│  └──────────────┘  └──────────────┘  │   (NAS/S3)   │               │
│                                       └──────────────┘               │
└──────────────────────────────────────────────────────────────────────┘
```

### Network Architecture

```
                    Internet
                       │
                       ▼
              ┌────────────────┐
              │   Firewall     │ Port 443 (HTTPS)
              └────────┬───────┘
                       │
                       ▼
              ┌────────────────┐
              │  Load Balancer │ (Optional)
              └────────┬───────┘
                       │
         ┌─────────────┼─────────────┐
         │             │             │
         ▼             ▼             ▼
    ┌────────┐    ┌────────┐    ┌────────┐
    │  Web   │    │  Web   │    │  Web   │
    │ Server │    │ Server │    │ Server │
    │   #1   │    │   #2   │    │   #3   │
    └────┬───┘    └────┬───┘    └────┬───┘
         │             │             │
         └─────────────┼─────────────┘
                       │
              ┌────────┴───────┐
              │                │
              ▼                ▼
         ┌─────────┐      ┌─────────┐
         │Database │      │  Redis  │
         │ Primary │      │  Cache  │
         └─────────┘      └─────────┘
              │
              ▼
         ┌─────────┐
         │Database │
         │ Replica │ (Read-only)
         └─────────┘
```

---

## Technology Stack

### Backend
- **Framework:** Flask 3.0.0
- **ORM:** SQLAlchemy 2.0.23
- **Database:** PostgreSQL (production) / SQLite (development)
- **Authentication:** Flask-Login, JWT
- **Scheduler:** APScheduler 3.10.4
- **WSGI Server:** Waitress 2.1.2

### Frontend
- **Template Engine:** Jinja2
- **CSS Framework:** Bootstrap 5
- **JavaScript:** Vanilla JS + jQuery
- **Charts:** Chart.js

### Caching & Performance
- **Cache:** Flask-Caching with Redis backend
- **Redis:** Version 7.0+
- **Query Optimization:** Custom SQLAlchemy optimizers
- **Rate Limiting:** Flask-Limiter

### Monitoring & Logging
- **Metrics:** Prometheus + prometheus-flask-exporter
- **Visualization:** Grafana
- **Alerting:** Alertmanager
- **Logging:** Structured JSON logging (python-json-logger)

### Security
- **Headers:** Flask-Talisman
- **Rate Limiting:** Flask-Limiter
- **Password Hashing:** bcrypt
- **CSRF Protection:** Flask-WTF
- **Encryption:** cryptography library

### Testing
- **Unit Tests:** pytest
- **Coverage:** pytest-cov
- **Linting:** black, isort, flake8
- **Security:** bandit, safety

### DevOps
- **Containerization:** Docker
- **Orchestration:** Docker Compose / Kubernetes
- **CI/CD:** GitHub Actions
- **Version Control:** Git

---

## Performance Architecture

### Caching Strategy (Multi-Level)

```
┌─────────────────────────────────────────────────────────┐
│                    Request Flow                         │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼
              ┌──────────────────┐
              │ Browser Cache    │ (Static assets, 1 year)
              └────────┬─────────┘
                       │ Cache Miss
                       ▼
              ┌──────────────────┐
              │ CDN Cache        │ (Static assets, 30 days)
              └────────┬─────────┘
                       │ Cache Miss
                       ▼
              ┌──────────────────┐
              │ Nginx Cache      │ (Pages, 5 minutes)
              └────────┬─────────┘
                       │ Cache Miss
                       ▼
              ┌──────────────────┐
              │ Redis Cache      │ (API data, 5-30 min)
              └────────┬─────────┘
                       │ Cache Miss
                       ▼
              ┌──────────────────┐
              │ Application      │ Query database
              │ (with eager      │
              │  loading)        │
              └────────┬─────────┘
                       │
                       ▼
              ┌──────────────────┐
              │ Database         │ Return data
              │ (with indexes)   │
              └──────────────────┘
```

### Query Optimization Patterns

1. **Eager Loading:** Prevent N+1 queries
2. **Selective Loading:** Load only required columns
3. **Pagination:** Limit result sets
4. **Batch Operations:** Bulk insert/update
5. **Index Strategy:** Strategic index placement

---

## Security Architecture

### Defense in Depth

```
┌─────────────────────────────────────────────────────────────┐
│ Layer 1: Network Security                                   │
│ - Firewall rules                                            │
│ - DDoS protection                                           │
│ - IP whitelisting                                           │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ Layer 2: Transport Security                                 │
│ - TLS 1.3                                                   │
│ - HSTS                                                      │
│ - Certificate validation                                    │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ Layer 3: Application Security                               │
│ - Security headers (CSP, X-Frame-Options, etc.)             │
│ - Rate limiting                                             │
│ - Input validation                                          │
│ - Output encoding                                           │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ Layer 4: Authentication & Authorization                     │
│ - Multi-factor authentication                               │
│ - Role-based access control (RBAC)                          │
│ - JWT token validation                                      │
│ - Session management                                        │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ Layer 5: Data Security                                      │
│ - Encryption at rest                                        │
│ - Encryption in transit                                     │
│ - Secure key management                                     │
│ - Data sanitization                                         │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ Layer 6: Monitoring & Audit                                 │
│ - Comprehensive logging                                     │
│ - Security alerts                                           │
│ - Audit trails                                              │
│ - Anomaly detection                                         │
└─────────────────────────────────────────────────────────────┘
```

---

## Scalability Considerations

### Horizontal Scaling

- **Stateless Application:** No server affinity required
- **Session Management:** Redis-based sessions
- **Database:** Read replicas for read scaling
- **Cache:** Shared Redis cache across instances

### Vertical Scaling

- **Database:** Increase connection pool size
- **Application:** More worker threads
- **Cache:** Larger Redis memory allocation

### Performance Targets

| Metric | Target | Current |
|--------|--------|---------|
| API Response (p95) | < 200ms | 150ms ✅ |
| Concurrent Users | 500+ | 500+ ✅ |
| Requests/Second | 100+ | 245 ✅ |
| Database Queries | < 100ms | 80ms ✅ |
| Cache Hit Rate | > 80% | 85% ✅ |

---

## Disaster Recovery

### Backup Strategy

1. **Database:** Daily full backup + hourly incremental
2. **Files:** Hourly sync to offsite storage
3. **Configuration:** Version controlled in Git
4. **Retention:** 90 days online, 1 year archive

### Recovery Objectives

- **RTO (Recovery Time Objective):** 4 hours
- **RPO (Recovery Point Objective):** 1 hour
- **MTTR (Mean Time To Repair):** < 2 hours

---

**Document Version:** 1.0
**Last Updated:** 2025-10-30
**Maintained By:** System Architecture Team

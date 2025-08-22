# Sugar Metrics & Analytics System Design

## Overview

Design for a centralized, privacy-respecting metrics collection system to track Sugar AI usage across 10,000s of installations. This system will provide insights into adoption, usage patterns, and feature effectiveness while maintaining user privacy and providing opt-out capabilities.

## Goals

### Primary Objectives
- **Adoption Tracking**: Monitor total installations, active users, retention rates
- **Usage Analytics**: Track work completion rates, task categories, discovery module popularity
- **Feature Insights**: Understand which features are most valuable to users
- **Performance Monitoring**: Identify performance bottlenecks across the user base
- **Product Direction**: Data-driven decisions for feature development and improvements

### Success Metrics
- Total active installations
- Daily/Weekly/Monthly active users
- Work items completed (by type, source, complexity)
- Most popular discovery modules
- Average session duration and cycle counts
- Error rates and common failure patterns
- Feature adoption rates (GitHub integration, Claude modes, etc.)

## Architecture Overview

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────────┐
│ Sugar Client    │───▶│ Metrics API      │───▶│ Analytics Dashboard │
│ (Local Install) │    │ (Cloud Service)  │    │ (Internal Tool)     │
└─────────────────┘    └──────────────────┘    └─────────────────────┘
                              │
                              ▼
                       ┌──────────────────┐
                       │ Data Warehouse   │
                       │ (Time Series DB) │
                       └──────────────────┘
```

## Data Collection Strategy

### 1. Client-Side Collection

#### Installation Metrics
```python
{
  "event_type": "installation",
  "timestamp": "2024-01-15T10:30:00Z",
  "installation_id": "uuid-v4-anonymous",
  "version": "1.2.3",
  "platform": "darwin",  # os.platform()
  "python_version": "3.11.5",
  "install_method": "pip",  # pip, brew, docker, source
  "geography": "US-CA"  # Derived from IP, city-level
}
```

#### Usage Session Metrics
```python
{
  "event_type": "session_start",
  "installation_id": "uuid-v4-anonymous",
  "session_id": "uuid-v4-session",
  "timestamp": "2024-01-15T10:30:00Z",
  "config_hash": "sha256-hash-of-config",  # Detect config patterns
  "discovery_modules_enabled": ["github", "code_quality", "test_coverage"],
  "claude_mode": "continuous",  # continuous, fresh, session
  "dry_run": false
}
```

#### Work Completion Metrics
```python
{
  "event_type": "work_completed",
  "installation_id": "uuid-v4-anonymous",
  "session_id": "uuid-v4-session",
  "timestamp": "2024-01-15T10:35:22Z",
  "work_item": {
    "type": "bug_fix",  # bug_fix, feature, test, documentation, etc.
    "source": "github_watcher",  # github_watcher, code_quality, manual, etc.
    "priority": 4,
    "complexity_score": 2.5,  # Derived from execution time, file changes
    "execution_time_seconds": 45.2,
    "files_changed_count": 3,
    "claude_tokens_used": 1500,  # If available
    "success": true,
    "retry_count": 0
  },
  "workflow": {
    "git_workflow": "direct_commit",  # direct_commit, pull_request
    "auto_close_enabled": true,
    "branch_created": false
  }
}
```

#### Error & Performance Metrics
```python
{
  "event_type": "error",
  "installation_id": "uuid-v4-anonymous",
  "session_id": "uuid-v4-session",
  "timestamp": "2024-01-15T10:40:15Z",
  "error": {
    "type": "claude_execution_timeout",
    "component": "claude_wrapper",
    "message": "Claude CLI execution timed out after 1800s",
    "stack_trace_hash": "sha256-hash",  # Anonymized stack trace
    "recovery_attempted": true,
    "recovery_successful": false
  },
  "context": {
    "work_item_type": "feature",
    "execution_time_before_error": 1800.5,
    "system_load": 0.8,  # If available
    "memory_usage_mb": 512
  }
}
```

### 2. Privacy & Consent

#### Privacy-First Design
- **Anonymous IDs**: No personally identifiable information
- **Opt-out Default**: Users must explicitly opt-in to metrics collection
- **Data Minimization**: Only collect data necessary for product insights
- **Local Control**: All metrics collection controllable via config
- **Transparency**: Clear documentation of what data is collected

#### Configuration Options
```yaml
# config/sugar.yaml
sugar:
  metrics:
    enabled: false  # Default: disabled, user must opt-in
    endpoint: "https://metrics.sugar-ai.com/v1/events"
    batch_size: 10  # Batch events before sending
    batch_interval_minutes: 15  # Send every 15 minutes
    retry_attempts: 3
    timeout_seconds: 10
    
    # Granular control over data collection
    collect:
      installation_info: true
      usage_sessions: true
      work_completion: true
      performance_metrics: true
      error_reporting: true
      config_patterns: false  # More sensitive, default off
    
    # Local data retention
    local_retention_days: 7  # Keep local metrics for debugging
    local_database: ".sugar/metrics.db"
```

## Technical Implementation

### 1. Client-Side Implementation

#### Metrics Collector Class
```python
# sugar/metrics/collector.py
class MetricsCollector:
    def __init__(self, config: dict):
        self.enabled = config.get('enabled', False)
        self.installation_id = self._get_or_create_installation_id()
        self.session_id = self._generate_session_id()
        self.endpoint = config.get('endpoint')
        self.local_db = MetricsDatabase(config.get('local_database'))
        
    async def track_installation(self):
        """Track first-time installation"""
        
    async def track_session_start(self, discovery_modules, config_hash):
        """Track session beginning"""
        
    async def track_work_completion(self, work_item, result, workflow_info):
        """Track completed work item"""
        
    async def track_error(self, error_info, context):
        """Track errors and failures"""
        
    async def flush_metrics(self):
        """Send batched metrics to server"""
```

#### Integration Points
```python
# sugar/core/loop.py - Integration examples

class SugarLoop:
    def __init__(self, config_path: str):
        # ... existing init ...
        
        # Initialize metrics if enabled
        metrics_config = self.config['sugar'].get('metrics', {})
        self.metrics = MetricsCollector(metrics_config) if metrics_config.get('enabled') else None
        
        # Track installation on first run
        if self.metrics and self._is_first_run():
            await self.metrics.track_installation()
    
    async def run(self):
        """Main loop with metrics integration"""
        if self.metrics:
            await self.metrics.track_session_start(
                discovery_modules=[m.__class__.__name__ for m in self.discovery_modules],
                config_hash=self._generate_config_hash()
            )
        
        try:
            # ... existing loop logic ...
            pass
        except Exception as e:
            if self.metrics:
                await self.metrics.track_error(e, context)
            raise
        finally:
            if self.metrics:
                await self.metrics.flush_metrics()
    
    async def _execute_work(self):
        """Work execution with metrics"""
        # ... existing execution logic ...
        
        if self.metrics and result.get('success'):
            await self.metrics.track_work_completion(work_item, result, workflow_info)
```

### 2. Server-Side Infrastructure

#### Metrics API Service
- **Technology**: FastAPI + PostgreSQL + TimescaleDB
- **Deployment**: Kubernetes cluster with auto-scaling
- **Endpoint**: `POST /v1/events` for batch event ingestion
- **Authentication**: API key-based (if needed for rate limiting)

#### Data Pipeline
```python
# Simplified API endpoint structure
@app.post("/v1/events")
async def ingest_events(events: List[MetricEvent]):
    """
    Ingest batch of metric events
    - Validate event schema
    - Anonymize/sanitize data
    - Store in time-series database
    - Update real-time aggregates
    """
    
    for event in events:
        # Validate schema
        validate_event_schema(event)
        
        # Anonymization layer
        sanitized_event = anonymize_event(event)
        
        # Store in TimescaleDB
        await store_event(sanitized_event)
        
        # Update real-time metrics
        await update_aggregates(sanitized_event)
    
    return {"status": "success", "processed": len(events)}
```

### 3. Analytics Dashboard

#### Key Dashboards

**1. Adoption Overview**
- Total installations over time
- Active users (daily/weekly/monthly)
- Geographic distribution
- Platform/OS breakdown
- Installation method popularity

**2. Usage Patterns**
- Work items completed per day/week
- Average session duration
- Most popular discovery modules
- Work item type distribution
- Success/failure rates

**3. Feature Analytics**
- GitHub integration usage
- Claude mode preferences
- Workflow type adoption (direct commit vs PR)
- Configuration pattern analysis

**4. Performance Insights**
- Average execution times by work type
- Error rates and common failures
- System performance correlations
- Claude token usage patterns

**5. Product Health**
- Version adoption rates
- Update success rates
- Critical error trends
- User retention cohorts

## Data Storage Schema

### TimescaleDB Tables

```sql
-- Main events table (hypertable)
CREATE TABLE metric_events (
    time TIMESTAMPTZ NOT NULL,
    installation_id UUID NOT NULL,
    session_id UUID,
    event_type VARCHAR(50) NOT NULL,
    version VARCHAR(20),
    platform VARCHAR(20),
    data JSONB NOT NULL
);

-- Create hypertable for time-series optimization
SELECT create_hypertable('metric_events', 'time');

-- Aggregated views for performance
CREATE MATERIALIZED VIEW daily_usage_stats AS
SELECT 
    time_bucket('1 day', time) as day,
    COUNT(DISTINCT installation_id) as active_installations,
    COUNT(*) FILTER (WHERE event_type = 'work_completed') as work_items_completed,
    AVG((data->>'execution_time_seconds')::float) as avg_execution_time
FROM metric_events 
GROUP BY day;

-- Indexes for common queries
CREATE INDEX idx_events_installation_time ON metric_events (installation_id, time DESC);
CREATE INDEX idx_events_type_time ON metric_events (event_type, time DESC);
CREATE INDEX idx_events_version ON metric_events (version);
```

## Implementation Phases

### Phase 1: Foundation (Weeks 1-2)
- [ ] Design and implement client-side metrics collector
- [ ] Create basic event schemas and validation
- [ ] Implement local storage and batching
- [ ] Add configuration options and privacy controls
- [ ] Create opt-in mechanism and documentation

### Phase 2: Infrastructure (Weeks 3-4)
- [ ] Set up cloud infrastructure (API service)
- [ ] Implement metrics ingestion endpoint
- [ ] Create TimescaleDB schema and tables
- [ ] Set up monitoring and alerting
- [ ] Implement data anonymization pipeline

### Phase 3: Analytics (Weeks 5-6)
- [ ] Create analytics dashboard
- [ ] Implement key metric calculations
- [ ] Set up automated reporting
- [ ] Create data export capabilities
- [ ] Add real-time metric updates

### Phase 4: Advanced Features (Weeks 7-8)
- [ ] Implement cohort analysis
- [ ] Add A/B testing framework
- [ ] Create predictive analytics
- [ ] Implement anomaly detection
- [ ] Add custom metric definitions

## Security & Compliance

### Data Security
- **Encryption**: All data encrypted in transit (TLS 1.3) and at rest (AES-256)
- **Access Control**: Role-based access to analytics dashboard
- **Audit Logging**: All data access logged and monitored
- **Data Retention**: Automatic deletion after configurable period (default: 2 years)

### Privacy Compliance
- **GDPR Compliance**: Right to deletion, data portability, consent management
- **CCPA Compliance**: User rights to know, delete, and opt-out
- **Anonymization**: No PII collection, anonymous identifiers only
- **Consent Management**: Clear opt-in process with granular controls

### Rate Limiting & Abuse Prevention
- **Client Rate Limits**: Max events per installation per hour
- **Server Protection**: DDoS protection and request validation
- **Data Validation**: Schema validation and sanitization
- **Anomaly Detection**: Detect and handle unusual usage patterns

## Cost Estimation

### Infrastructure Costs (Monthly)
- **API Service**: $200-500 (auto-scaling containers)
- **Database**: $300-800 (TimescaleDB managed service)
- **Monitoring**: $100-200 (logging, metrics, alerting)
- **CDN/Edge**: $50-150 (global distribution)
- **Total**: $650-1,650/month for 10,000 active installations

### Development Effort
- **Initial Implementation**: 6-8 weeks (1-2 engineers)
- **Ongoing Maintenance**: 20% FTE (monitoring, updates, features)

## Success Metrics for Metrics System

### Technical Metrics
- **Reliability**: 99.9% uptime for metrics API
- **Performance**: <100ms p95 latency for event ingestion
- **Scalability**: Handle 10,000+ installations with <1% data loss
- **Privacy**: Zero PII incidents, 100% anonymization compliance

### Business Metrics
- **Adoption**: 15%+ opt-in rate for metrics collection
- **Insights**: 5+ actionable insights per month from data
- **Decisions**: 80% of feature decisions backed by metrics data
- **User Value**: Improved Sugar performance/features based on insights

## Future Enhancements

### Advanced Analytics
- **Machine Learning**: Predict work completion success rates
- **Anomaly Detection**: Identify unusual usage patterns or performance issues
- **Recommendation Engine**: Suggest optimal configurations based on usage patterns
- **Predictive Scaling**: Forecast infrastructure needs

### Enhanced Privacy
- **Differential Privacy**: Add noise to protect individual privacy
- **Zero-Knowledge Proofs**: Prove aggregate statistics without revealing individual data
- **Local Analytics**: On-device analytics for privacy-sensitive users
- **Federated Learning**: Learn patterns without centralizing data

### Integration Opportunities
- **Claude API Integration**: Enhanced token usage tracking (if permitted)
- **GitHub Integration**: Correlate Sugar usage with repository activity
- **Development Tool Integration**: Connect with other developer tools
- **Community Features**: Anonymous benchmarking and best practices sharing

---

*This design prioritizes user privacy while providing valuable insights for product development. All metrics collection is opt-in and users maintain full control over their data.*
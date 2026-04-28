# API Monitoring Agent Documentation

**Date:** 2025-01-20  
**Status:** ✅ Complete  
**Type:** Agent Skill for Automated Monitoring

---

## 🎯 Overview

The API Monitoring Agent is an automated agent skill that continuously monitors your API structure, detects issues, generates alerts, and can optionally auto-generate missing methods. It's designed to maintain API health and structure automatically.

---

## ✨ Features

### 1. **Automatic Scanning**
- Periodically scans codebase (configurable interval, default: 24 hours)
- Tracks scan history and statistics
- Detects changes in API structure

### 2. **Threshold-Based Alerting**
- Configurable thresholds for warnings and critical alerts
- Tracks missing methods count
- Generates alerts when thresholds are exceeded
- Alert history and management

### 3. **Optional Auto-Generation**
- Can automatically generate missing methods (when enabled)
- Only generates when below critical threshold (safety feature)
- Dry-run mode for preview
- Tracks generation history

### 4. **Status Tracking**
- Monitors agent health and status
- Tracks scan and generation counts
- Maintains configuration state
- Logs all scans for history

---

## 📁 Files

### Service
- **`backend/services/api_monitoring_agent.py`** - Core monitoring agent

### Routes
- **`backend/routes/api_monitoring_agent_routes.py`** - API endpoints

### Integration
- **`backend/register_blueprints.py`** - Auto-registered
- **`scripts/fix_all_loose_ends_master.py`** - Integrated into master fix

---

## 🔌 API Endpoints

### Status & Configuration

#### `GET /api/agent/monitoring/status`
Get monitoring agent status.

**Response:**
```json
{
  "success": true,
  "status": {
    "enabled": true,
    "auto_generate_enabled": false,
    "last_scan": "2025-01-20T10:00:00",
    "last_generation": null,
    "scan_count": 5,
    "generation_count": 0,
    "alerts_count": 2,
    "recent_alerts": [...],
    "should_scan": false,
    "scan_interval_hours": 24,
    "thresholds": {
      "missing_methods_warning": 10,
      "missing_methods_critical": 50,
      "unregistered_blueprints_warning": 1,
      "broken_endpoints_warning": 5
    }
  }
}
```

#### `GET/POST /api/agent/monitoring/config`
Get or update monitoring configuration.

**POST Request:**
```json
{
  "monitoring_enabled": true,
  "auto_generate_enabled": false,
  "scan_interval_hours": 24,
  "thresholds": {
    "missing_methods_warning": 10,
    "missing_methods_critical": 50
  }
}
```

### Scanning

#### `POST /api/agent/monitoring/scan`
Trigger a manual scan.

**Response:**
```json
{
  "success": true,
  "result": {
    "success": true,
    "report": {...},
    "alerts": [...],
    "timestamp": "2025-01-20T10:00:00"
  }
}
```

#### `POST /api/agent/monitoring/cycle`
Run a complete monitoring cycle (scan + optional auto-generation).

**Response:**
```json
{
  "success": true,
  "result": {
    "success": true,
    "scan": {...},
    "generation": {...},
    "timestamp": "2025-01-20T10:00:00"
  }
}
```

### Alerts

#### `GET /api/agent/monitoring/alerts`
Get monitoring alerts.

**Query Parameters:**
- `limit` - Number of alerts to return (default: 50)

**Response:**
```json
{
  "success": true,
  "alerts": [
    {
      "level": "warning",
      "type": "missing_methods",
      "message": "Warning: 15 missing methods detected",
      "value": 15,
      "threshold": 10,
      "timestamp": "2025-01-20T10:00:00"
    }
  ],
  "count": 1
}
```

#### `POST /api/agent/monitoring/alerts/clear`
Clear all alerts.

### Auto-Generation

#### `POST /api/agent/monitoring/auto-generate`
Trigger auto-generation of missing methods.

**Request:**
```json
{
  "dry_run": true
}
```

**Response:**
```json
{
  "success": true,
  "result": {
    "success": true,
    "dry_run": true,
    "generated": 5,
    "results": {...}
  }
}
```

---

## 💻 Usage Examples

### Python Usage

```python
from backend.services.api_monitoring_agent import api_monitoring_agent

# Get status
status = api_monitoring_agent.get_status()
print(f"Agent enabled: {status['enabled']}")
print(f"Scan count: {status['scan_count']}")

# Perform scan
result = api_monitoring_agent.perform_scan()
if result['success']:
    print(f"Scan completed: {len(result['alerts'])} alerts")

# Run monitoring cycle
cycle_result = api_monitoring_agent.run_monitoring_cycle()

# Get alerts
alerts = api_monitoring_agent.get_alerts(limit=10)
for alert in alerts:
    print(f"{alert['level']}: {alert['message']}")

# Update configuration
api_monitoring_agent.update_config({
    'monitoring_enabled': True,
    'auto_generate_enabled': False,
    'scan_interval_hours': 12
})
```

### API Usage

```bash
# Get status
curl http://localhost:5000/vidgenerator/api/agent/monitoring/status

# Trigger scan
curl -X POST http://localhost:5000/vidgenerator/api/agent/monitoring/scan

# Get alerts
curl http://localhost:5000/vidgenerator/api/agent/monitoring/alerts?limit=10

# Update config
curl -X POST http://localhost:5000/vidgenerator/api/agent/monitoring/config \
  -H "Content-Type: application/json" \
  -d '{
    "monitoring_enabled": true,
    "scan_interval_hours": 12
  }'

# Run monitoring cycle
curl -X POST http://localhost:5000/vidgenerator/api/agent/monitoring/cycle
```

---

## ⚙️ Configuration

### Default Configuration

```json
{
  "monitoring_enabled": true,
  "auto_generate_enabled": false,
  "scan_interval_hours": 24,
  "thresholds": {
    "missing_methods_warning": 10,
    "missing_methods_critical": 50,
    "unregistered_blueprints_warning": 1,
    "broken_endpoints_warning": 5
  }
}
```

### Configuration Options

- **`monitoring_enabled`** - Enable/disable monitoring (default: true)
- **`auto_generate_enabled`** - Enable automatic generation (default: false)
- **`scan_interval_hours`** - Hours between automatic scans (default: 24)
- **`thresholds.missing_methods_warning`** - Warning threshold (default: 10)
- **`thresholds.missing_methods_critical`** - Critical threshold (default: 50)

---

## 🔄 Monitoring Cycle

The monitoring cycle performs:

1. **Check if scan is due** - Based on `scan_interval_hours`
2. **Perform scan** - Scan codebase for API structure
3. **Check thresholds** - Generate alerts if thresholds exceeded
4. **Auto-generate (if enabled)** - Only if below warning threshold
5. **Log results** - Save scan results and alerts

---

## 📊 Alert Levels

### Warning
- Missing methods >= warning threshold (default: 10)
- Non-critical issues
- Should be reviewed

### Critical
- Missing methods >= critical threshold (default: 50)
- Requires immediate attention
- Auto-generation disabled when critical

---

## 🚀 Integration

### Master Fix Script
The monitoring agent is automatically initialized by `fix_all_loose_ends_master.py`:
- Performs initial scan
- Sets up monitoring state
- Verifies endpoints

### Scheduled Tasks
You can set up a cron job or scheduled task to run monitoring cycles:

```bash
# Run every 24 hours
0 0 * * * curl -X POST http://localhost:5000/vidgenerator/api/agent/monitoring/cycle
```

---

## 📝 Logs

All scans are logged to:
- **Directory:** `logs/api_monitoring/`
- **State File:** `logs/api_monitoring/monitoring_state.json`
- **Scan Logs:** `logs/api_monitoring/scan_YYYYMMDD_HHMMSS.json`

---

## ⚠️ Safety Features

1. **Auto-generation disabled by default** - Must be explicitly enabled
2. **Critical threshold protection** - Won't auto-generate if too many missing methods
3. **Dry-run mode** - Preview changes before applying
4. **Alert system** - Notifies of issues before auto-generation

---

## 🎯 Best Practices

1. **Start with monitoring only** - Enable monitoring first, review alerts
2. **Set appropriate thresholds** - Adjust based on your codebase size
3. **Review alerts regularly** - Check alert history periodically
4. **Test auto-generation** - Use dry-run mode first
5. **Monitor scan logs** - Review scan history for trends

---

**Last Updated:** 2025-01-20  
**Status:** ✅ OPERATIONAL

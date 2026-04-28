# Auto-Fix Endpoint System Documentation

**Created:** 2026-01-21  
**Status:** Active

---

## 🎯 Overview

The Auto-Fix Endpoint System automatically creates missing API endpoints when they return 404 errors. This system:

- **Detects** 404 errors on API endpoints
- **Logs** patterns of missing endpoints
- **Auto-creates** endpoints after they're accessed 3+ times
- **Returns** appropriate JSON responses based on endpoint type
- **Tracks** all auto-fixed endpoints for monitoring

---

## 🏗️ Architecture

### Components

1. **AutoFixEndpoints Service** (`backend/services/auto_fix_endpoints.py`)
   - Core logic for detecting and fixing endpoints
   - Pattern analysis and logging
   - Response generation

2. **404 Middleware** (`backend/middleware/auto_fix_404_middleware.py`)
   - Intercepts 404 errors
   - Triggers auto-fix when appropriate
   - Returns auto-generated responses

3. **Auto-Fix Routes** (`backend/routes/auto_fix_routes.py`)
   - Management API for viewing fixed endpoints
   - Statistics and pattern analysis
   - Manual fix triggers

---

## 🔧 How It Works

### 1. Detection Phase

When a 404 error occurs:
- Middleware intercepts the error
- Path is logged and analyzed
- Pattern is extracted (IDs replaced with placeholders)

### 2. Analysis Phase

The system:
- Checks if endpoint should be auto-fixed
- Analyzes endpoint type (stats, points, profile, etc.)
- Determines appropriate response structure

### 3. Auto-Fix Phase

If endpoint meets criteria (accessed 3+ times):
- Creates appropriate JSON response
- Returns 200 OK with data
- Logs the fix for monitoring

### 4. Tracking Phase

All fixes are:
- Saved to `logs/auto_fix_endpoints/fixed_endpoints.json`
- Logged daily in `logs/auto_fix_endpoints/fixes_YYYYMMDD.json`
- Tracked in statistics

---

## 📊 Auto-Fix Criteria

An endpoint is auto-fixed if:

1. **Frequency:** Accessed 3+ times
2. **Type:** API endpoint (`/api/` or `/vidgenerator/api/`)
3. **Method:** GET, POST, PUT, DELETE
4. **Not Static:** Not a static file (`.css`, `.js`, `.png`, etc.)

---

## 🎨 Response Generation

The system generates responses based on endpoint type:

### Stats Endpoints (`/stats`)
```json
{
  "success": true,
  "message": "Endpoint auto-created",
  "endpoint": "/api/stats/summary",
  "method": "GET",
  "auto_fixed": true,
  "timestamp": "2026-01-21T23:30:00",
  "stats": {}
}
```

### Points Endpoints (`/points`)
```json
{
  "success": true,
  "message": "Endpoint auto-created",
  "endpoint": "/api/points/all",
  "method": "GET",
  "auto_fixed": true,
  "timestamp": "2026-01-21T23:30:00",
  "points": {},
  "all_points": {}
}
```

### Profile Endpoints (`/profile`)
```json
{
  "success": true,
  "message": "Endpoint auto-created",
  "endpoint": "/api/user/profile/123",
  "method": "GET",
  "auto_fixed": true,
  "timestamp": "2026-01-21T23:30:00",
  "profile": {},
  "user_id": "123"
}
```

### Generic Endpoints
```json
{
  "success": true,
  "message": "Endpoint auto-created",
  "endpoint": "/api/unknown/endpoint",
  "method": "GET",
  "auto_fixed": true,
  "timestamp": "2026-01-21T23:30:00",
  "data": {}
}
```

---

## 🔌 API Endpoints

### Get Fixed Endpoints
```
GET /vidgenerator/api/auto-fix/endpoints
```

Returns list of all auto-fixed endpoints and statistics.

### Get 404 Patterns
```
GET /vidgenerator/api/auto-fix/patterns
```

Returns analysis of 404 patterns (what endpoints are being requested but missing).

### Get Statistics
```
GET /vidgenerator/api/auto-fix/statistics
```

Returns statistics about auto-fixes:
- Total fixed endpoints
- Total 404 patterns
- Total 404 count
- Recent fixes

### Manual Fix
```
POST /vidgenerator/api/auto-fix/manual-fix
Body: {
  "path": "/api/test/endpoint",
  "method": "GET"
}
```

Manually trigger auto-fix for an endpoint.

---

## 📁 File Structure

```
backend/
├── services/
│   └── auto_fix_endpoints.py      # Core service
├── middleware/
│   └── auto_fix_404_middleware.py # 404 interceptor
└── routes/
    └── auto_fix_routes.py         # Management API

logs/
└── auto_fix_endpoints/
    ├── fixed_endpoints.json       # List of fixed endpoints
    ├── 404_patterns.json          # 404 pattern analysis
    └── fixes_YYYYMMDD.json        # Daily fix logs
```

---

## 🚀 Usage

### Automatic (Default)

The system works automatically. When an endpoint returns 404:
1. First access: Logs the 404
2. Second access: Logs again
3. Third access: Auto-fixes and returns 200

### Manual Trigger

You can manually trigger a fix:
```python
import requests

response = requests.post('https://masternoder.dk/vidgenerator/api/auto-fix/manual-fix', 
    json={'path': '/api/test/endpoint', 'method': 'GET'})
```

### Monitoring

Check statistics:
```python
import requests

response = requests.get('https://masternoder.dk/vidgenerator/api/auto-fix/statistics')
stats = response.json()
print(f"Total fixed: {stats['statistics']['total_fixed']}")
```

---

## ⚙️ Configuration

### Adjust Auto-Fix Threshold

Edit `backend/services/auto_fix_endpoints.py`:
```python
# Auto-fix if seen 3+ times
if pattern_data.get('count', 0) >= 3:  # Change this number
    return True
```

### Exclude Paths

Edit `backend/middleware/auto_fix_404_middleware.py`:
```python
# Skip static files and known non-API paths
if any(skip in path for skip in ['/static/', '/uploads/', ...]):  # Add more here
    return None
```

---

## 📈 Benefits

1. **Reduces 404 Errors:** Automatically fixes missing endpoints
2. **Improves UX:** Users get responses instead of errors
3. **Pattern Detection:** Identifies commonly requested missing endpoints
4. **Monitoring:** Tracks all fixes for analysis
5. **Development Aid:** Helps identify missing endpoints during development

---

## ⚠️ Limitations

1. **Response Data:** Auto-generated responses are empty/placeholder
2. **No Business Logic:** Doesn't implement actual endpoint logic
3. **Pattern-Based:** May not catch all endpoint variations
4. **Static Files:** Doesn't handle static file 404s

---

## 🔄 Next Steps

After auto-fix:
1. **Review** fixed endpoints in statistics
2. **Implement** proper logic for frequently accessed endpoints
3. **Replace** auto-fixed responses with real implementations
4. **Monitor** patterns to identify missing features

---

## 📝 Example Workflow

1. Frontend calls `/api/new/endpoint` → 404
2. System logs the 404
3. Frontend calls again → 404 (logged)
4. Frontend calls third time → Auto-fixed, returns 200
5. Developer reviews statistics
6. Developer implements proper endpoint
7. Auto-fix response is replaced with real implementation

---

**Last Updated:** 2026-01-21

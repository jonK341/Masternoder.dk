# Error Logging System Documentation

**Created:** 2026-01-22  
**Status:** ✅ Active

---

## 🎯 Overview

The Error Logging System provides centralized error tracking, logging, and monitoring for the MasterNoder.dk platform. All errors are automatically logged with detailed information including stack traces, request context, and user information.

---

## 🏗️ Architecture

### Components

1. **ErrorLogger Service** (`backend/services/error_logging.py`)
   - Core logging service
   - Error statistics tracking
   - Daily log file management

2. **Error Logging Middleware** (`backend/middleware/error_logging_middleware.py`)
   - Automatically logs all exceptions
   - Logs API errors (400+ status codes)
   - Captures request context

3. **Error Logging Routes** (`backend/routes/error_logging_routes.py`)
   - API endpoints for viewing logs
   - Statistics and analytics
   - Error querying

---

## 📊 Features

- ✅ **Automatic Error Logging** - All exceptions are automatically logged
- ✅ **API Error Tracking** - All API errors (400+) are logged
- ✅ **Request Context** - Captures path, method, IP, user agent
- ✅ **User Tracking** - Associates errors with user IDs
- ✅ **Statistics** - Tracks error counts by type and endpoint
- ✅ **Daily Logs** - Separate log files per day
- ✅ **Recent Errors** - Tracks last 50 errors
- ✅ **Query API** - RESTful endpoints for viewing logs

---

## 📁 File Structure

```
logs/
└── errors/
    ├── errors_YYYYMMDD.json          # Daily error logs
    ├── api_errors_YYYYMMDD.json       # Daily API error logs
    └── error_stats.json               # Error statistics
```

---

## 🔌 API Endpoints

### Get Error Statistics
```
GET /vidgenerator/api/errors/statistics
```

Returns:
```json
{
  "success": true,
  "statistics": {
    "total_errors": 150,
    "errors_by_type": {
      "api_error_404": 50,
      "api_error_500": 10,
      "value_error": 5
    },
    "errors_by_endpoint": {
      "/api/test/endpoint": 20,
      "/api/user/profile": 10
    },
    "recent_errors": [...]
  }
}
```

### Get Recent Errors
```
GET /vidgenerator/api/errors/recent?limit=20
```

Returns:
```json
{
  "success": true,
  "errors": [
    {
      "timestamp": "2026-01-22T01:00:00",
      "error_type": "api_error_404",
      "endpoint": "/api/test/endpoint",
      "message": "Not Found"
    }
  ],
  "count": 20
}
```

### Get Errors by Type
```
GET /vidgenerator/api/errors/by-type/api_error_404
```

Returns:
```json
{
  "success": true,
  "error_type": "api_error_404",
  "count": 50
}
```

### Get Errors by Endpoint
```
GET /vidgenerator/api/errors/by-endpoint
GET /vidgenerator/api/errors/by-endpoint?endpoint=/api/test
```

Returns:
```json
{
  "success": true,
  "endpoints": {
    "/api/test/endpoint": 20,
    "/api/user/profile": 10
  }
}
```

Or for specific endpoint:
```json
{
  "success": true,
  "endpoint": "/api/test/endpoint",
  "count": 20
}
```

---

## 📝 Error Entry Structure

### Exception Error Entry
```json
{
  "timestamp": "2026-01-22T01:00:00",
  "error_type": "value_error",
  "error_message": "Invalid value",
  "error_class": "ValueError",
  "endpoint": "/api/test/endpoint",
  "user_id": "user_123",
  "request_info": {
    "path": "/api/test/endpoint",
    "method": "GET",
    "remote_addr": "192.168.1.1",
    "user_agent": "Mozilla/5.0..."
  },
  "traceback": "Traceback (most recent call last)...",
  "additional_data": {}
}
```

### API Error Entry
```json
{
  "timestamp": "2026-01-22T01:00:00",
  "error_type": "api_error_404",
  "status_code": 404,
  "error_message": "Not Found",
  "endpoint": "/api/test/endpoint",
  "user_id": "user_123",
  "request_data": {}
}
```

---

## 🔧 Usage

### Automatic Logging

Errors are automatically logged when:
- An exception is raised in any route
- An API endpoint returns 400+ status code
- Any unhandled exception occurs

### Manual Logging

```python
from backend.services.error_logging import error_logger

try:
    # Your code
    pass
except Exception as e:
    error_logger.log_error(
        error=e,
        error_type='custom_error',
        endpoint='/api/custom',
        user_id='user_123',
        additional_data={'key': 'value'}
    )
```

### Viewing Logs

```python
# Get statistics
stats = error_logger.get_statistics()

# Get recent errors
recent = error_logger.get_recent_errors(limit=20)

# Get errors by type
count = error_logger.get_errors_by_type('api_error_404')

# Get errors by endpoint
count = error_logger.get_errors_by_endpoint('/api/test/endpoint')
```

---

## 📈 Statistics

The system tracks:
- **Total Errors** - Count of all logged errors
- **Errors by Type** - Count grouped by error type
- **Errors by Endpoint** - Count grouped by endpoint path
- **Recent Errors** - Last 50 errors with summary

---

## ⚙️ Configuration

### Log File Limits
- **Daily Error Logs**: Max 1000 errors per day
- **Daily API Error Logs**: Max 500 errors per day
- **Recent Errors**: Last 50 errors kept in memory

### Log File Location
- Base directory: `logs/errors/`
- Daily logs: `errors_YYYYMMDD.json`
- API logs: `api_errors_YYYYMMDD.json`
- Statistics: `error_stats.json`

---

## 🚀 Benefits

1. **Centralized Tracking** - All errors in one place
2. **Request Context** - Full request information captured
3. **User Association** - Errors linked to users
4. **Statistics** - Easy to identify problem areas
5. **Query API** - Programmatic access to logs
6. **Daily Rotation** - Automatic log file rotation

---

## 📊 Monitoring

Use the API endpoints to:
- Monitor error rates
- Identify problematic endpoints
- Track error trends
- Debug user issues
- Generate error reports

---

## ⚠️ Notes

- Logs are stored in JSON format for easy parsing
- Log files are rotated daily
- Old log files are not automatically deleted
- Statistics are kept in memory and persisted to file
- Error logging failures don't break the application

---

**Last Updated:** 2026-01-22

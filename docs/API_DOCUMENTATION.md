# API Documentation

**Last Updated:** 2026-01-22  
**Version:** 1.0.0

---

## 📋 Overview

This document provides comprehensive API documentation for MasterNoder.dk endpoints.

---

## 🔗 Base URLs

- **Development:** `http://localhost:5000`
- **Production:** `https://masternoder.dk`
- **API Prefix:** `/api/`

---

## 📊 Response Format

All API endpoints return JSON with the following standard format:

### Success Response
```json
{
  "success": true,
  "data": {},
  "timestamp": "2026-01-22T12:00:00.000000",
  "implementation_status": "complete"
}
```

### Error Response
```json
{
  "success": false,
  "error": "Error Type",
  "message": "Human-readable error message",
  "code": "ERROR_CODE",
  "timestamp": "2026-01-22T12:00:00.000000"
}
```

---

## 🔐 Authentication

Currently, most endpoints use user identification via:
- IP address
- Device fingerprint
- Browser fingerprint
- Email (if provided)

User ID is passed as query parameter: `?user_id=<user_id>`

---

## 📍 Endpoints

### MN2 (MasterNoder2) wallet

Full MN2 API details and agent parity: **[AGENTS_MN2.md](AGENTS_MN2.md)**.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/mn2/balance?user_id=...` | User in-app MN2 balance, coins_per_mn2, shop_revenue_address |
| GET | `/api/mn2/deposit-address?user_id=...` | User deposit address (create if needed) + explorer link |
| GET | `/api/mn2/transactions?user_id=...&limit=N` | Ledger entries (deposit/withdrawal/shop_payment) with explorer links |
| POST | `/api/mn2/withdraw` | Withdraw MN2 (body: `user_id`, `address`, `amount`) |
| POST | `/api/mn2/scan-deposits` | Ops: run deposit scanner once (protect in production) |

---

### Health & Status

#### `GET /api/health`
Basic health check

**Response:**
```json
{
  "success": true,
  "status": "healthy",
  "timestamp": "2026-01-22T12:00:00.000000"
}
```

#### `GET /api/health/database`
Database health check

**Response:**
```json
{
  "success": true,
  "status": "healthy",
  "database": {
    "connected": true,
    "tables_checked": 4,
    "existing_tables": ["player_levels", "system_point_snapshots"],
    "missing_tables": []
  }
}
```

#### `GET /api/health/system`
System health check (all components)

**Response:**
```json
{
  "success": true,
  "overall": "healthy",
  "components": {
    "database": {"status": "healthy", "connected": true},
    "unified_points": {"status": "healthy", "available": true},
    "error_logging": {"status": "healthy", "available": true},
    "caching": {"status": "healthy", "cache_entries": 10},
    "rate_limiting": {"status": "healthy", "configured_endpoints": 5}
  }
}
```

---

### Points Endpoints

#### `GET /api/points/comprehensive`
Get comprehensive points data for user

**Parameters:**
- `user_id` (string, optional): User ID (default: 'default_user')

**Response:**
```json
{
  "success": true,
  "user_id": "user123",
  "points": {
    "xp_total": 5000,
    "level": 5,
    "systems": {
      "battle_points": 100,
      "social_points": 50
    }
  },
  "grand_total": 5150,
  "systems_count": 2,
  "active_systems": ["battle_points", "social_points"]
}
```

#### `GET /api/points/statistics`
Get points statistics with historical data

**Parameters:**
- `user_id` (string, optional): User ID
- `days` (integer, optional): Number of days to analyze (default: 30)

**Response:**
```json
{
  "success": true,
  "user_id": "user123",
  "days": 30,
  "statistics": {
    "current": {
      "total_xp": 5000,
      "level": 5,
      "systems": {}
    },
    "historical": {
      "battle_points": {
        "min": 0,
        "max": 100,
        "avg": 50,
        "data_points": 30
      }
    }
  }
}
```

#### `GET /api/points/history/analytics`
Get points history analytics

**Parameters:**
- `user_id` (string, optional): User ID
- `days` (integer, optional): Number of days (default: 30)

**Response:**
```json
{
  "success": true,
  "user_id": "user123",
  "days": 30,
  "analytics": {
    "system_breakdown": {
      "battle_points": {
        "start_value": 0,
        "end_value": 100,
        "change": 100,
        "change_percent": 100
      }
    },
    "total_change": 5000,
    "growth_rate": 166.67
  }
}
```

#### `GET /api/points/calculator/predict`
Predict future points

**Parameters:**
- `user_id` (string, optional): User ID
- `activity_type` (string, optional): Type of activity (default: 'general')
- `base_points` (integer, optional): Base points per day (default: 100)
- `days` (integer, optional): Days to predict (default: 7)

**Response:**
```json
{
  "success": true,
  "user_id": "user123",
  "prediction": {
    "current_xp": 5000,
    "current_level": 5,
    "estimated_total": 5700,
    "xp_gain": 700,
    "level_at_end": 6,
    "xp_to_next_level": 0
  }
}
```

---

### Stats Endpoints

#### `GET /api/stats/summary`
Get stats summary

**Parameters:**
- `user_id` (string, optional): User ID

**Response:**
```json
{
  "success": true,
  "user_id": "user123",
  "stats": {
    "total_xp": 5000,
    "level": 5,
    "battle_points": 100,
    "social_points": 50,
    "achievement_points": 25
  }
}
```

#### `GET /api/game/stats`
Get game stats

**Parameters:**
- `user_id` (string, optional): User ID

**Response:**
```json
{
  "success": true,
  "user_id": "user123",
  "stats": {
    "xp_total": 5000,
    "level": 5,
    "points": {
      "battle_points": 100,
      "social_points": 50
    }
  }
}
```

#### `GET /api/battle/stats`
Get battle stats

**Parameters:**
- `user_id` (string, optional): User ID

**Response:**
```json
{
  "success": true,
  "user_id": "user123",
  "stats": {
    "battle_points": 100,
    "wins": 0,
    "losses": 0,
    "total_battles": 0
  }
}
```

---

### Monetization Endpoints

#### `GET /api/monetization/top50`
Get top 50 leaderboard

**Parameters:**
- `limit` (integer, optional): Number of users (default: 50)
- `sort_by` (string, optional): Sort by 'level' or 'total_xp' (default: 'total_xp')

**Response:**
```json
{
  "success": true,
  "limit": 50,
  "sort_by": "total_xp",
  "top50": [
    {
      "rank": 1,
      "user_id": "user1",
      "level": 10,
      "total_xp": 10000,
      "title": "Champion"
    }
  ]
}
```

#### `GET /api/monetization/cash`
Get user cash

**Parameters:**
- `user_id` (string, optional): User ID

**Response:**
```json
{
  "success": true,
  "user_id": "user123",
  "cash": 500,
  "currency": "points"
}
```

---

### Game Endpoints

#### `GET /api/game/achievements`
Get user achievements

**Parameters:**
- `user_id` (string, optional): User ID

**Response:**
```json
{
  "success": true,
  "user_id": "user123",
  "achievements": [
    {
      "id": "level_5",
      "name": "Level 5 Achiever",
      "description": "Reached level 5",
      "earned": true,
      "points": 50
    }
  ],
  "total_count": 1,
  "earned_count": 1
}
```

#### `GET /api/game/milestones`
Get game milestones

**Parameters:**
- `user_id` (string, optional): User ID

**Response:**
```json
{
  "success": true,
  "user_id": "user123",
  "milestones": [
    {
      "name": "Level 5",
      "achieved": true
    }
  ]
}
```

#### `GET /api/game-mechanics/progress`
Get game mechanics progress

**Parameters:**
- `user_id` (string, optional): User ID

**Response:**
```json
{
  "success": true,
  "user_id": "user123",
  "progress": {
    "level": {
      "current": 5,
      "xp_total": 5000,
      "xp_to_next": 0,
      "progress_percent": 0
    },
    "systems": {
      "battle_points": {
        "points": 100,
        "progress_percent": 1.0,
        "max_points": 10000
      }
    },
    "overall_completion": 1.0
  }
}
```

---

### Tech Tree Endpoints

#### `GET /api/tech-tree`
Get tech tree structure

**Parameters:**
- `user_id` (string, optional): User ID

**Response:**
```json
{
  "success": true,
  "user_id": "user123",
  "tech_tree": {
    "technologies": {
      "tech_id": {
        "name": "Technology Name",
        "tech_level": 5,
        "unlocked": true
      }
    },
    "total_technologies": 10,
    "unlocked_count": 5,
    "user_level": 5
  }
}
```

#### `GET /api/tech-tree/knowledge`
Get tech tree knowledge

**Parameters:**
- `user_id` (string, optional): User ID

**Response:**
```json
{
  "success": true,
  "user_id": "user123",
  "knowledge": {
    "total_technologies": 10,
    "unlocked_count": 5,
    "knowledge_points": 50,
    "tech_level": 5,
    "available_technologies": ["tech1", "tech2"]
  }
}
```

---

### Agent Endpoints

#### `GET /api/agent/get-all`
Get all agents

**Parameters:**
- `user_id` (string, optional): User ID

**Response:**
```json
{
  "success": true,
  "user_id": "user123",
  "agents": [
    {
      "id": "content_generator",
      "name": "Content Generator",
      "status": "active",
      "level": 3,
      "skills_count": 5
    }
  ],
  "total": 1
}
```

#### `GET /api/agent/recommendations`
Get agent recommendations

**Parameters:**
- `user_id` (string, optional): User ID
- `context` (string, optional): Context ('battle', 'social', 'content', 'general')

**Response:**
```json
{
  "success": true,
  "user_id": "user123",
  "context": "general",
  "recommendations": [
    {
      "agent": "battle_strategy",
      "name": "Battle Strategy Agent",
      "reason": "Low battle points - improve combat skills",
      "priority": "high",
      "action": "Engage in battles to earn battle points"
    }
  ],
  "total": 1
}
```

---

### Trophies Endpoints

#### `GET /api/trophies/user/<user_id>`
Get user trophies

**Response:**
```json
{
  "success": true,
  "user_id": "user123",
  "trophies": [
    {
      "id": "level_10",
      "name": "Level 10 Trophy",
      "description": "Reached level 10",
      "points": 200,
      "earned": true
    }
  ],
  "total_count": 1
}
```

---

### Ultra Resource Endpoints

#### `GET /api/ultra-resource/energy`
Get energy status

**Parameters:**
- `user_id` (string, optional): User ID

**Response:**
```json
{
  "success": true,
  "user_id": "user123",
  "energy": {
    "total": 200,
    "max": 400,
    "percentage": 50,
    "types": {
      "physical": 50,
      "mental": 50,
      "creative": 50,
      "social": 50
    },
    "regeneration_rate": 1
  }
}
```

---

### Aggregator Endpoints

#### `GET /api/aggregator/stats/user/<user_id>`
Get aggregator stats for user

**Response:**
```json
{
  "success": true,
  "user_id": "user123",
  "stats": {
    "total_xp": 5000,
    "level": 5,
    "systems": {
      "battle_points": 100,
      "social_points": 50
    }
  }
}
```

#### `GET /api/aggregator/unified-dashboard/data`
Get unified dashboard data

**Parameters:**
- `user_id` (string, optional): User ID

**Response:**
```json
{
  "success": true,
  "user_id": "user123",
  "data": {
    "points": {},
    "stats": {},
    "achievements": [],
    "trophies": [],
    "progress": {},
    "energy": {},
    "recommendations": []
  }
}
```

---

### Video Generation Endpoints

#### `POST /api/generator/create`
Create video generation job

**Request Body:**
```json
{
  "config": {}
}
```

**Response:**
```json
{
  "success": true,
  "documentary_id": "uuid-here",
  "status": "processing",
  "message": "Video generation started"
}
```

#### `POST /api/generator/ai-clips`
Generate AI clips

**Request Body:**
```json
{
  "config": {}
}
```

**Response:**
```json
{
  "success": true,
  "job_id": "uuid-here",
  "status": "processing",
  "message": "AI clips generation started"
}
```

#### `GET /api/generator/ai-clips/<job_id>`
Get AI clips generation status

**Response:**
```json
{
  "success": true,
  "job_id": "uuid-here",
  "status": "processing",
  "progress": 50,
  "clips": []
}
```

#### `GET /api/documentary/progress/<doc_id>`
Get documentary generation progress

**Response:**
```json
{
  "success": true,
  "documentary_id": "uuid-here",
  "status": "processing",
  "progress": 50
}
```

#### `POST /api/documentary/restart/<doc_id>`
Restart documentary generation

**Response:**
```json
{
  "success": true,
  "documentary_id": "uuid-here",
  "message": "Documentary generation restarted"
}
```

#### `GET /api/documentary/video/<doc_id>`
Get documentary video URL

**Response:**
```json
{
  "success": true,
  "documentary_id": "uuid-here",
  "video_url": "/vidgenerator/videos/uuid-here.mp4",
  "status": "processing"
}
```

#### `POST /api/video-generation/calculate`
Calculate video generation parameters

**Request Body:**
```json
{
  "clips": []
}
```

**Response:**
```json
{
  "success": true,
  "validation_summary": {
    "can_proceed": true,
    "estimated_time": 300,
    "estimated_cost": 0,
    "clip_count": 5
  },
  "problems": []
}
```

#### `GET /api/themes/list`
Get list of available themes

**Response:**
```json
{
  "success": true,
  "themes": ["default", "nature", "sci-fi", "cinematic", "documentary"]
}
```

---

### Monitoring Endpoints

#### `GET /api/monitoring/summary`
Get monitoring summary

**Response:**
```json
{
  "success": true,
  "summary": {
    "metrics_count": 100,
    "active_metrics": 5,
    "alerts_count": 2,
    "critical_alerts": 0,
    "error_alerts": 1
  }
}
```

#### `GET /api/monitoring/metrics`
Get metrics

**Parameters:**
- `metric` (string, optional): Specific metric name
- `hours` (integer, optional): Hours to look back (default: 24)

**Response:**
```json
{
  "success": true,
  "metrics": {
    "endpoint_duration": [
      {
        "value": 0.5,
        "timestamp": "2026-01-22T12:00:00",
        "tags": {"endpoint": "api.stats.summary"}
      }
    ]
  }
}
```

#### `GET /api/monitoring/alerts`
Get alerts

**Parameters:**
- `level` (string, optional): Filter by level ('info', 'warning', 'error', 'critical')
- `hours` (integer, optional): Hours to look back (default: 24)

**Response:**
```json
{
  "success": true,
  "alerts": [
    {
      "level": "warning",
      "message": "Slow endpoint detected",
      "component": "performance",
      "timestamp": "2026-01-22T12:00:00"
    }
  ],
  "count": 1
}
```

---

## 🔒 Rate Limiting

Rate limits are applied per IP address:

- `/api/generator/create`: 10 requests/minute
- `/api/generator/ai-clips`: 20 requests/minute
- `/api/documentary/restart`: 5 requests/minute
- `/api/video-generation/calculate`: 30 requests/minute
- Default: 120 requests/minute

When rate limit is exceeded, returns `429 Too Many Requests`.

---

## 📝 Error Codes

- `VALIDATION_ERROR`: Input validation failed
- `NOT_FOUND`: Resource not found
- `UNAUTHORIZED`: Authentication required
- `FORBIDDEN`: Access denied
- `RATE_LIMIT_EXCEEDED`: Too many requests
- `INTERNAL_ERROR`: Server error

---

## 🚀 Performance

- Response caching: Stats endpoints cached for 3 minutes
- Leaderboard endpoints cached for 2 minutes
- Points endpoints cached for 1 minute
- Cache headers: `X-Cache: HIT/MISS`, `X-Cache-Age: <seconds>`

---

**Last Updated:** 2026-01-22

# Test Suite - MasterNoder.dk

## Overview

This directory contains the test suite for the MasterNoder.dk platform.

## Structure

```
tests/
├── unit/              # Unit tests for core services
├── integration/       # Integration tests for API endpoints
├── performance/       # Performance and load tests
├── scripts/           # Test utility scripts
└── conftest.py        # Pytest configuration and fixtures
```

## Running Tests

### Run all tests
```bash
pytest
```

### Run specific test categories
```bash
# Unit tests only (using marker)
pytest tests/unit/ -m unit

# Integration tests only (using marker)
pytest tests/integration/ -m integration

# Performance tests only (using marker)
pytest tests/performance/ -m performance

# Alternative: Run by directory (without markers)
pytest tests/unit/
pytest tests/integration/
pytest tests/performance/
```

### Run specific test file
```bash
pytest tests/unit/test_leaderboard_system.py
```

### Run with coverage
```bash
pytest --cov=backend --cov-report=html
```

## Test Scripts

### Generate Test Users
```bash
# Generate 1000 test users (default)
python tests/scripts/generate_test_users.py

# Generate specific number of users
python tests/scripts/generate_test_users.py 500
```

This generates test users with random points for performance testing.

### Generate Test Agents
```bash
# Generate 100 agents (default)
python tests/scripts/generate_test_agents.py

# Generate specific number of agents
python tests/scripts/generate_test_agents.py 500

# Generate agents for specific user prefix
python tests/scripts/generate_test_agents.py 200 test_user
```

This generates test agents with random stats, distributed across users.

### Server Deployment

For detailed instructions on running these scripts on your server, see:
- [Deployment Guide](scripts/DEPLOYMENT.md)

Quick server commands:
```bash
# SSH into server and run
ssh user@server.com
cd /path/to/Masternoder.dk
source .venv/bin/activate
python tests/scripts/generate_test_users.py 1000
python tests/scripts/generate_test_agents.py 500
```

## Test Categories

### Unit Tests
- Test individual components in isolation
- Fast execution
- No external dependencies

### Integration Tests
- Test API endpoints
- Test service interactions
- May require database

### Performance Tests
- Measure response times
- Test caching effectiveness
- Load testing

## Writing Tests

### Example Unit Test
```python
def test_leaderboard_basic():
    leaderboard = Leaderboard178Systems()
    result = leaderboard.get_leaderboard('xp', limit=10)
    assert result['success'] == True
```

### Example Performance Test
```python
def test_query_performance():
    start = time.time()
    result = leaderboard.get_leaderboard('xp', limit=100)
    elapsed = (time.time() - start) * 1000
    assert elapsed < 100  # <100ms
```

## Continuous Integration

Tests should be run:
- Before committing code
- In CI/CD pipeline
- Before deployment

## Coverage Goals

- **Target**: 80%+ code coverage
- **Critical paths**: 100% coverage
- **New features**: Must include tests

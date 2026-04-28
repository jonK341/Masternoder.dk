# Deployment Guide for Test Data Generation

This guide explains how to generate test users and agents on your server.

## Prerequisites

1. SSH access to your server
2. Python virtual environment activated
3. Database connection configured
4. Flask application context available

## Generating Test Users on Server

### Option 1: Direct SSH Execution

```bash
# SSH into your server
ssh user@your-server.com

# Navigate to project directory
cd /path/to/Masternoder.dk

# Activate virtual environment (if using one)
source .venv/bin/activate  # Linux/Mac
# OR
.venv\Scripts\activate  # Windows

# Run the script
python tests/scripts/generate_test_users.py 1000
```

### Option 2: Using Screen/Tmux (Recommended for Large Batches)

```bash
# Start a screen session (keeps running if connection drops)
screen -S generate_users

# Run the script
cd /path/to/Masternoder.dk
source .venv/bin/activate
python tests/scripts/generate_test_users.py 1000

# Detach: Press Ctrl+A then D
# Reattach: screen -r generate_users
```

### Option 3: Background Process with Logging

```bash
# Run in background with output logging
nohup python tests/scripts/generate_test_users.py 1000 > user_generation.log 2>&1 &

# Check progress
tail -f user_generation.log

# Check if process is running
ps aux | grep generate_test_users
```

## Generating Test Agents on Server

### Basic Usage

```bash
# Generate 100 agents (default)
python tests/scripts/generate_test_agents.py

# Generate 500 agents
python tests/scripts/generate_test_agents.py 500

# Generate agents for specific user prefix
python tests/scripts/generate_test_agents.py 200 test_user
```

### Batch Generation (100s)

```bash
# Generate 100 agents
python tests/scripts/generate_test_agents.py 100

# Generate 200 agents
python tests/scripts/generate_test_agents.py 200

# Generate 500 agents
python tests/scripts/generate_test_agents.py 500

# Generate 1000 agents
python tests/scripts/generate_test_agents.py 1000
```

### Using Screen for Large Batches

```bash
# Start screen session
screen -S generate_agents

# Generate 1000 agents
cd /path/to/Masternoder.dk
source .venv/bin/activate
python tests/scripts/generate_test_agents.py 1000

# Detach and let it run
# Ctrl+A, then D
```

## Environment Variables

Make sure these are set on your server:

```bash
# Database connection
export DATABASE_URL="your_database_connection_string"

# Flask environment
export FLASK_ENV="production"  # or "development"

# Other required variables
export SECRET_KEY="your_secret_key"
```

Or use a `.env` file in the project root.

## Monitoring Progress

### Check Database Counts

```bash
# Connect to your database and check counts
# For PostgreSQL:
psql -d your_database -c "SELECT COUNT(*) FROM user_profiles WHERE user_id LIKE 'test_user%';"
psql -d your_database -c "SELECT COUNT(*) FROM agents WHERE agent_name LIKE 'TestAgent%';"

# For SQLite:
sqlite3 your_database.db "SELECT COUNT(*) FROM user_profiles WHERE user_id LIKE 'test_user%';"
sqlite3 your_database.db "SELECT COUNT(*) FROM agents WHERE agent_name LIKE 'TestAgent%';"
```

### Check Logs

```bash
# If using nohup
tail -f user_generation.log
tail -f agent_generation.log

# Check application logs
tail -f /var/log/your_app/app.log
```

## Performance Tips

1. **Batch Commits**: Scripts commit every 100 records to avoid memory issues
2. **Database Indexes**: Ensure indexes exist on `user_id` and `agent_name` columns
3. **Connection Pooling**: Use connection pooling for better performance
4. **Run During Low Traffic**: Generate test data during off-peak hours

## Troubleshooting

### "Working outside of application context" Error

The script should handle this automatically, but if you see this error:

```python
# Make sure you're running within app context
with app.app_context():
    # Your code here
```

### Database Connection Issues

```bash
# Test database connection
python -c "from src.app import create_app; app = create_app(); print('OK')"
```

### Memory Issues with Large Batches

For very large batches (10,000+), consider:

1. Running in smaller chunks:
```bash
# Generate 1000 at a time
for i in {1..10}; do
    python tests/scripts/generate_test_users.py 1000
    sleep 5
done
```

2. Increasing commit frequency in the script
3. Using database transactions more efficiently

## Example: Full Test Data Generation

```bash
#!/bin/bash
# generate_all_test_data.sh

cd /path/to/Masternoder.dk
source .venv/bin/activate

echo "Generating 1000 test users..."
python tests/scripts/generate_test_users.py 1000

echo "Generating 500 test agents..."
python tests/scripts/generate_test_agents.py 500

echo "✅ Test data generation complete!"
```

Make it executable:
```bash
chmod +x generate_all_test_data.sh
./generate_all_test_data.sh
```

## Cleanup (Optional)

To remove test data:

```sql
-- Remove test users
DELETE FROM user_profiles WHERE user_id LIKE 'test_user%';

-- Remove test agents
DELETE FROM agents WHERE agent_name LIKE 'TestAgent%';
```

Or create a cleanup script:

```python
# tests/scripts/cleanup_test_data.py
from src.app import create_app
from src.db.models import db, UserProfile
from src.db.models_agent import Agent

app = create_app()
with app.app_context():
    UserProfile.query.filter(UserProfile.user_id.like('test_user%')).delete()
    Agent.query.filter(Agent.agent_name.like('TestAgent%')).delete()
    db.session.commit()
    print("✅ Test data cleaned up")
```

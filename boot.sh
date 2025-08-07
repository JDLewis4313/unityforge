#!/bin/bash
source .venv/bin/activate

echo "Starting UnityForge..."

# Create necessary directories
mkdir -p app/static/uploads app/static/spectrograms app/static/instrumentals logs

# Initialize database if needed
echo "Running database migrations..."
flask db upgrade

# Check if we need to populate verses (only if Scripture table is empty)
VERSE_COUNT=$(python -c "
from app import create_app, db
from app.models import Scripture
app = create_app()
with app.app_context():
    count = Scripture.query.count()
    print(count)
" 2>/dev/null)

if [ "$VERSE_COUNT" = "0" ] || [ -z "$VERSE_COUNT" ]; then
    echo "Populating initial daily verses..."
    flask scripture populate-verses
else
    echo "Daily verses already populated ($VERSE_COUNT verses found)"
fi

# Development mode
if [ "$FLASK_ENV" = "development" ]; then
    echo "Starting development environment..."
    
    # Check if Redis is installed
    if ! command -v redis-cli &> /dev/null; then
        echo "Redis is not installed. Please install Redis first."
        echo "Ubuntu/Debian: sudo apt-get install redis-server"
        echo "Mac: brew install redis"
        exit 1
    fi
    
    # Start Redis if not running
    if ! redis-cli ping > /dev/null 2>&1; then
        echo "Starting Redis..."
        redis-server --daemonize yes
    else
        echo "Redis is already running"
    fi
    
    # Kill any existing RQ workers/schedulers
    pkill -f "rq worker" 2>/dev/null
    pkill -f "rq-scheduler" 2>/dev/null
    
    # Start RQ worker in background
    echo "Starting RQ worker..."
    rq worker unityforge-tasks --logging_level INFO &
    WORKER_PID=$!
    
    # Start RQ scheduler in background
    echo "Starting RQ scheduler..."
    rq-scheduler --interval 60 --logging_level INFO &
    SCHEDULER_PID=$!
    
    # Function to cleanup on exit
    cleanup() {
        echo "Shutting down background services..."
        kill $WORKER_PID 2>/dev/null
        kill $SCHEDULER_PID 2>/dev/null
        exit 0
    }
    
    # Trap exit signals
    trap cleanup EXIT INT TERM
    
    # Give services time to start
    sleep 2
    
    # Start Flask development server
    echo "Starting Flask development server on http://localhost:5000"
    flask run --host=0.0.0.0 --port=5000 --debug
else
    # Production - handled by supervisor
    echo "Starting production server..."
    exec gunicorn -b :5000 --access-logfile - --error-logfile - manage:app
fi

#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting UnityForge...${NC}"

# Wait for database to be ready (if using external DB)
if [[ "$DATABASE_URL" == postgres* ]] || [[ "$DATABASE_URL" == mysql* ]]; then
    echo -e "${YELLOW}Waiting for database...${NC}"
    sleep 5
fi

# Initialize database if it doesn't exist
if [ ! -f "app.db" ] && [[ "$DATABASE_URL" == sqlite* ]]; then
    echo -e "${YELLOW}Creating initial database...${NC}"
    flask db init || echo "Database already initialized"
fi

# Run database migrations with retry logic
echo -e "${YELLOW}Running database migrations...${NC}"
max_attempts=10
attempt=1

while [ $attempt -le $max_attempts ]; do
    if flask db upgrade; then
        echo -e "${GREEN}Database migrations completed successfully!${NC}"
        break
    else
        if [ $attempt -eq $max_attempts ]; then
            echo -e "${RED}Migration failed after $max_attempts attempts. Exiting.${NC}"
            exit 1
        fi
        echo -e "${YELLOW}Migration attempt $attempt failed. Retrying in 5 seconds...${NC}"
        sleep 5
        ((attempt++))
    fi
done

# Create upload directories if they don't exist
mkdir -p app/static/uploads app/static/spectrograms app/static/instrumentals

# Set permissions for uploads
chmod 755 app/static/uploads app/static/spectrograms app/static/instrumentals

# Check if we're in development mode
if [ "$FLASK_ENV" = "development" ]; then
    echo -e "${GREEN}Starting development server...${NC}"
    # Use Flask's development server for hot reloading
    exec flask run --host=0.0.0.0 --port=5000
else
    echo -e "${GREEN}Starting production server with Gunicorn...${NC}"
    # Production mode with Gunicorn
    exec gunicorn -b 0.0.0.0:5000 \
        --workers 4 \
        --worker-class sync \
        --timeout 120 \
        --keepalive 5 \
        --max-requests 1000 \
        --max-requests-jitter 100 \
        --access-logfile - \
        --error-logfile - \
        --log-level info \
        "manage:app"
fi
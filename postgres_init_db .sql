# Initialize migrations repository (only needed once)
flask db init

# Create a migration script based on model changes
flask db migrate -m "Initial database setup"

# Apply migrations to the database
flask db upgrade

# Roll back the last migration
flask db downgrade

# Show current migration status
flask db current

# Show migration history
flask db history

# For Heroku/Supabase deployment
# After pushing to Heroku, run:
heroku run flask db upgrade

# For migrating data from SQLite to PostgreSQL
# 1. Export schema from SQLite (no need if you already have models)
# 2. Run migrations on PostgreSQL
# 3. Transfer data using a script (example below)

# Example data transfer script (simplified)
python - <<EOF
import sqlite3
import psycopg2
from psycopg2.extras import execute_values

# Connect to SQLite
sqlite_conn = sqlite3.connect('app.db')
sqlite_cursor = sqlite_conn.cursor()

# Connect to PostgreSQL
pg_conn = psycopg2.connect("postgresql://postgres:ChildofJesus#4313@localhost:5433/unityforge_dev")
pg_cursor = pg_conn.cursor()

# Example: Transfer users table
sqlite_cursor.execute("SELECT id, username, email, password_hash, about_me, last_seen FROM user")
users = sqlite_cursor.fetchall()

execute_values(
    pg_cursor,
    "INSERT INTO user (id, username, email, password_hash, about_me, last_seen) VALUES %s",
    users
)

pg_conn.commit()
pg_conn.close()
sqlite_conn.close()
EOF
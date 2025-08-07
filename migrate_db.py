import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate, upgrade, init as init_command, migrate as migrate_command

# Create a minimal Flask app for migrations
app = Flask(__name__)

# Configure the app with the database URL
database_url = os.environ.get('DATABASE_URL')
if not database_url:
    raise ValueError("DATABASE_URL environment variable must be set")

print(f"Using database URL: {database_url}")

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize SQLAlchemy and models
db = SQLAlchemy(app)

# Import models after initializing db
from app.models import User, Post, Message, Notification, Task, SoundEntry, AudioSession

# Initialize Flask-Migrate
migrate = Migrate(app, db)

if __name__ == '__main__':
    # Check which command to run
    command = os.environ.get('MIGRATE_COMMAND', 'upgrade')
    
    # Use application context for all operations
    with app.app_context():
        if command == 'init':
            init_command()
            print("Migration repository initialized")
        elif command == 'migrate':
            migrate_command(message="Initial migration")
            print("Migration created")
        elif command == 'upgrade':
            upgrade()
            print("Database upgraded")
        else:
            print(f"Unknown command: {command}")

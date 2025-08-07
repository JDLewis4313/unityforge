import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate, init, migrate, upgrade

# Create a minimal Flask app for migrations
app = Flask(__name__)

# Configure the app with the database URL
database_url = os.environ.get('DATABASE_URL')
if not database_url:
    raise ValueError("DATABASE_URL environment variable must be set")

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Import your models here to make them available to Alembic
from app import db
from app import models

# Initialize Flask-Migrate
migrate = Migrate(app, db)

if __name__ == '__main__':
    # Check which command to run
    command = os.environ.get('MIGRATE_COMMAND', 'upgrade')
    
    # Run the specified command
    if command == 'init':
        init()
        print("Migration repository initialized")
    elif command == 'migrate':
        migrate(message="Initial migration")
        print("Migration created")
    elif command == 'upgrade':
        upgrade()
        print("Database upgraded")
    else:
        print(f"Unknown command: {command}")

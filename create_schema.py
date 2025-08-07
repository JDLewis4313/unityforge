import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

# Create a minimal Flask app for migrations
app = Flask(__name__)

# Configure the app with the database URL
database_url = os.environ.get('DATABASE_URL')
if not database_url:
    raise ValueError("DATABASE_URL environment variable must be set")

print(f"Using database URL: {database_url}")

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize SQLAlchemy
db = SQLAlchemy(app)

# Define all models directly here to ensure they're created
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(256))
    about_me = db.Column(db.String(140))
    last_seen = db.Column(db.DateTime, default=db.func.now())
    last_message_read_time = db.Column(db.DateTime)
    token = db.Column(db.String(32), index=True, unique=True)
    token_expiration = db.Column(db.DateTime)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.String(280))
    timestamp = db.Column(db.DateTime, index=True, default=db.func.now())
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True)
    media_filename = db.Column(db.String(256))
    media_type = db.Column(db.String(64))
    scripture_reference = db.Column(db.String(128))
    scripture_text = db.Column(db.Text)
    language = db.Column(db.String(5))
    source_url = db.Column(db.String(512))
    is_suggestion = db.Column(db.Boolean, default=False)
    title = db.Column(db.String(128))
    created_at = db.Column(db.DateTime, default=db.func.now())

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True)
    body = db.Column(db.String(140))
    timestamp = db.Column(db.DateTime, index=True, default=db.func.now())

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True)
    timestamp = db.Column(db.Float, index=True, default=db.func.time())
    payload_json = db.Column(db.Text)

class Task(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(128), index=True)
    description = db.Column(db.String(128))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    complete = db.Column(db.Boolean, default=False)

class Scripture(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reference = db.Column(db.String(100), nullable=False)
    text = db.Column(db.Text, nullable=False)
    translation = db.Column(db.String(50))
    date = db.Column(db.Date, nullable=False, unique=True)
    audio_filename = db.Column(db.String(120))

class JournalEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    scripture_id = db.Column(db.Integer, db.ForeignKey('scripture.id'))
    title = db.Column(db.String(140))
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.now())
    private = db.Column(db.Boolean, default=True)

class SoundEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(120), nullable=False)
    duration_seconds = db.Column(db.Float)
    peak_db = db.Column(db.Float)
    tempo_bpm = db.Column(db.Float)
    spectrogram_image = db.Column(db.String(120))
    created_at = db.Column(db.DateTime, default=db.func.now())
    notes = db.Column(db.Text)

class AudioSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sound_entry_id = db.Column(db.Integer, db.ForeignKey('sound_entry.id'))
    notes = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.now())

# Create followers association table
followers = db.Table('followers',
    db.Column('follower_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('followed_id', db.Integer, db.ForeignKey('user.id'), primary_key=True)
)

# Create all tables
if __name__ == '__main__':
    with app.app_context():
        print("Creating all tables...")
        db.create_all()
        print("Tables created successfully!")
        
        # List all tables
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        print("\nCreated tables:")
        for table in tables:
            print(f"- {table}")

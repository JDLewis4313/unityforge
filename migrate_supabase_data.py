from supabase import create_client, Client
from app import create_app, db
from app.models import User, Post, Message
from sqlalchemy.exc import IntegrityError
import json

# Supabase connection
SUPABASE_URL = "https://hxkzdyrwdfbkdkhslfmk.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imh4a3pkeXJ3ZGZia2RraHNsZm1rIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0OTUyNDA1NiwiZXhwIjoyMDY1MTAwMDU2fQ.tMwHsM4yE8XwepeM8nnwuav-Y6exuEGgDVtp6GT-8KI"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def migrate_data():
    app = create_app()
    with app.app_context():
        print("🔄 Starting data migration from Supabase...")
        
        # Get data from Supabase
        users_data = supabase.table('user').select("*").execute().data
        posts_data = supabase.table('post').select("*").execute().data  
        messages_data = supabase.table('message').select("*").execute().data
        
        print(f"📊 Found: {len(users_data)} users, {len(posts_data)} posts, {len(messages_data)} messages")
        
        # Clear existing data (optional)
        # db.session.query(Message).delete()
        # db.session.query(Post).delete() 
        # db.session.query(User).delete()
        
        # Migrate users first (they're referenced by posts/messages)
        for user_data in users_data:
            try:
                # Create User object based on your model structure
                user = User(**{k: v for k, v in user_data.items() if hasattr(User, k)})
                db.session.add(user)
                print(f"✅ Added user: {user_data.get('username', user_data.get('email', 'unknown'))}")
            except Exception as e:
                print(f"❌ Error adding user: {e}")
        
        db.session.commit()
        print("✅ Users migrated successfully!")
        
        # Migrate posts
        for post_data in posts_data:
            try:
                post = Post(**{k: v for k, v in post_data.items() if hasattr(Post, k)})
                db.session.add(post)
                print(f"✅ Added post: {post_data.get('title', 'untitled')}")
            except Exception as e:
                print(f"❌ Error adding post: {e}")
        
        db.session.commit()
        print("✅ Posts migrated successfully!")
        
        # Migrate messages
        for message_data in messages_data:
            try:
                message = Message(**{k: v for k, v in message_data.items() if hasattr(Message, k)})
                db.session.add(message)
                print(f"✅ Added message from: {message_data.get('sender_id', 'unknown')}")
            except Exception as e:
                print(f"❌ Error adding message: {e}")
        
        db.session.commit()
        print("🎉 Data migration complete!")

if __name__ == "__main__":
    migrate_data()

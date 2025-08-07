# app/logos/utils.py
from flask import current_app
from datetime import datetime, date, timezone, timedelta
from dataclasses import dataclass
import sqlalchemy as sa
import requests
import random
import time
from typing import Optional, List

from app import db
from app.models import Post, User, Scripture, JournalEntry

# Import the daily verses
from .daily_verses import DAILY_VERSES, get_verse_for_date, get_themed_verse

@dataclass
class Verse:
    book: str
    chapter: int
    verse: int
    text: str
    translation: str

def get_verse_of_the_day() -> Verse:
    """
    Return today's Verse: uses curated daily verses list with API fallback.
    Each day of the year has a predetermined meaningful verse.
    """
    today = date.today()
    
    # First check if we already have today's scripture in DB
    existing_scripture = get_today_scripture()
    if existing_scripture:
        return parse_scripture_to_verse(existing_scripture)
    
    # Get the predetermined verse for today
    daily_reference = get_verse_for_date(today)
    
    # Try to fetch from API and save to DB
    try:
        scripture = fetch_scripture_from_api(daily_reference)
        if scripture:
            # Update the date to today so it gets cached properly
            scripture.date = today
            db.session.commit()
            return parse_scripture_to_verse(scripture)
    except Exception as e:
        current_app.logger.error(f"Failed to fetch daily verse {daily_reference}: {e}")
    
    # If API fails, create a fallback verse object
    scripture = create_fallback_scripture(daily_reference)
    return parse_scripture_to_verse(scripture)

def parse_scripture_to_verse(scripture: Scripture) -> Verse:
    """Convert a Scripture model to a Verse dataclass."""
    try:
        # Parse "Book Chapter:Verse" format
        book_part, cv_part = scripture.reference.rsplit(" ", 1)
        chap_str, verse_str = cv_part.split(":", 1)
        
        return Verse(
            book=book_part,
            chapter=int(chap_str),
            verse=int(verse_str.split('-')[0]),  # Handle ranges like "3-5"
            text=scripture.text.strip(),
            translation=scripture.translation or "NIV"
        )
    except (ValueError, IndexError) as e:
        current_app.logger.error(f"Error parsing scripture reference {scripture.reference}: {e}")
        # Return with unparsed reference
        return Verse(
            book=scripture.reference,
            chapter=1,
            verse=1,
            text=scripture.text.strip(),
            translation=scripture.translation or "NIV"
        )

def create_fallback_scripture(reference: str) -> Scripture:
    """Create scripture from fallback when API fails."""
    fallback_verses = {
        "John 3:16": "For God so loved the world that he gave his one and only Son, that whoever believes in him shall not perish but have eternal life.",
        "Romans 8:28": "And we know that in all things God works for the good of those who love him, who have been called according to his purpose.",
        "Philippians 4:13": "I can do all this through him who gives me strength.",
        "Psalm 23:1": "The Lord is my shepherd, I lack nothing.",
        "Proverbs 3:5": "Trust in the Lord with all your heart and lean not on your own understanding."
    }
    
    text = fallback_verses.get(reference, fallback_verses["John 3:16"])
    
    try:
        verse = Scripture(
            date=date.today(),
            reference=reference,
            text=text,
            translation="NIV"
        )
        db.session.add(verse)
        db.session.commit()
        return verse
    except Exception as e:
        current_app.logger.error(f"Failed to create fallback scripture: {e}")
        db.session.rollback()
        # Return a non-persisted object
        return Scripture(
            date=date.today(),
            reference=reference,
            text=text,
            translation="NIV"
        )

def populate_annual_scriptures():
    """
    One-time function to populate the database with all 365 daily scriptures.
    Run this once to pre-cache all verses for the year.
    """
    start_date = date(datetime.now().year, 1, 1)
    
    for day_num in range(365):
        current_date = start_date + timedelta(days=day_num)
        daily_reference = DAILY_VERSES[day_num]
        
        # Check if already exists
        existing = Scripture.query.filter_by(date=current_date).first()
        if existing:
            continue
        
        try:
            scripture = fetch_scripture_from_api(daily_reference)
            if scripture:
                scripture.date = current_date
                db.session.commit()
                current_app.logger.info(f"Added scripture for {current_date}: {daily_reference}")
        except Exception as e:
            current_app.logger.error(f"Failed to add scripture for {current_date}: {e}")
    
    current_app.logger.info("Completed populating annual scriptures")

def post_exists(reference, title):
    return Post.query.filter_by(scripture_reference=reference, title=title).first() is not None

def create_daily_scripture_posts():
    today = date.today()
    scripture = Scripture.query.filter_by(date=today).first()
    if not scripture:
        current_app.logger.warning(f"No scripture found for {today}")
        return

    posts_to_create = [
        {
            "title": f"Daily Scripture: {scripture.reference}",
            "body": f"Today's reading: {scripture.reference}",
        },
        {
            "title": f"Scripture Reading: {scripture.reference}",
            "body": f"{scripture.text}",
        }
    ]

    created_count = 0
    for post_data in posts_to_create:
        if post_exists(scripture.reference, post_data["title"]):
            current_app.logger.info(f"Skipped duplicate post: {post_data['title']}")
            continue

        post = Post(
            title=post_data["title"],
            body=post_data["body"],
            scripture_reference=scripture.reference,
            scripture_text=scripture.text,
            media_type="scripture",
            user_id=3,
            timestamp=datetime.utcnow(),
            created_at=datetime.utcnow(),
        )
        db.session.add(post)
        created_count += 1

    db.session.commit()
    current_app.logger.info(f"Created {created_count} posts for {scripture.reference}")

def create_journal_post(user_id: int, journal_entry_id: int) -> Optional[int]:
    """
    Auto-generates a Post based on a JournalEntry.
    Returns post ID if created successfully, or None.
    """
    user = db.session.get(User, user_id)
    journal_entry = db.session.get(JournalEntry, journal_entry_id)

    if not user or not journal_entry:
        current_app.logger.warning(f"User ({user_id}) or JournalEntry ({journal_entry_id}) not found.")
        return None

    # Check for existing auto-post to avoid duplication
    existing_post = db.session.execute(
        sa.select(Post).filter_by(
            user_id=user.id,
            title=f"Reflection: {journal_entry.title}",
            is_suggestion=True
        )
    ).scalar_one_or_none()

    if existing_post:
        current_app.logger.info(f"Auto-post already exists for journal entry {journal_entry.id}")
        return existing_post.id

    scripture_text = journal_entry.scripture.text if journal_entry.scripture else None
    scripture_ref = journal_entry.scripture.reference if journal_entry.scripture else None

    post = Post(
        body=journal_entry.content[:280],  # Truncate to fit Post body limit
        timestamp=datetime.now(timezone.utc),
        user_id=user.id,
        scripture_text=scripture_text,
        scripture_reference=scripture_ref,
        title=f"Reflection: {journal_entry.title}",
        is_suggestion=True,
        media_type='journal'
    )

    db.session.add(post)
    db.session.commit()
    current_app.logger.info(f"Created journal post {post.id} for journal entry {journal_entry.id}")

    return post.id

def format_scripture_reference(reference: str) -> str:
    """Format scripture reference for consistent display."""
    return reference.title() if reference else ""

def truncate_scripture_text(text: str, max_length: int = 500) -> str:
    """Truncate scripture text for display purposes."""
    if not text or len(text) <= max_length:
        return text
    return text[:max_length].rsplit(' ', 1)[0] + "..."

def get_today_scripture() -> Optional[Scripture]:
    """Get today's Scripture model (from DB)."""
    return Scripture.query.filter_by(date=date.today()).first()

def fetch_scripture_from_api(reference: str) -> Optional[Scripture]:
    """Fetch & save one verse from bible-api.com with error handling."""
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            r = requests.get(
                f"https://bible-api.com/{reference}",
                timeout=5
            )
            r.raise_for_status()
            data = r.json()
            
            verse = Scripture(
                date=date.today(),
                reference=reference,
                text=data.get("text", "").strip(),
                translation=data.get("translation_id", "KJV")
            )
            db.session.add(verse)
            db.session.commit()
            return verse

        except requests.Timeout:
            retry_count += 1
            if retry_count >= max_retries:
                current_app.logger.error(f"Timeout fetching {reference} after {max_retries} attempts")
                return create_fallback_scripture(reference)
            time.sleep(retry_count)  # Exponential backoff
            
        except requests.RequestException as e:
            current_app.logger.error(f"Failed to fetch scripture {reference}: {e}")
            return create_fallback_scripture(reference)
            
        except Exception as e:
            current_app.logger.error(f"Error processing scripture {reference}: {e}")
            return create_fallback_scripture(reference)
    
    return None

def get_full_chapter(book: str, chapter: int) -> List[Verse]:
    """
    Fetch an entire chapter from bible-api.com and return as list of Verse.
    """
    try:
        ref = f"{book} {chapter}"
        r = requests.get(f"https://bible-api.com/{ref}", timeout=10)
        r.raise_for_status()
        data = r.json()
        verses = []
        
        if "verses" in data:
            for v in data["verses"]:
                verses.append(Verse(
                    book=v.get("book_name", book),
                    chapter=v.get("chapter", chapter),
                    verse=v.get("verse", 1),
                    text=v.get("text", "").strip(),
                    translation=data.get("translation_id", "KJV")
                ))
        
        return verses

    except requests.RequestException as e:
        current_app.logger.error(f"Failed to fetch chapter {book} {chapter}: {e}")
        return []

def get_specific_verse(book: str, chapter: int, verse: int) -> Optional[Verse]:
    """
    Fetch one verse from bible-api.com and return as a Verse.
    """
    try:
        ref = f"{book} {chapter}:{verse}"
        r = requests.get(f"https://bible-api.com/{ref}", timeout=5)
        r.raise_for_status()
        data = r.json()
        
        # Handle single verse response
        if "verses" in data and data["verses"]:
            v = data["verses"][0]
        else:
            # Direct verse response
            v = data
            
        return Verse(
            book=v.get("book_name", book),
            chapter=v.get("chapter", chapter),
            verse=v.get("verse", verse),
            text=v.get("text", "").strip(),
            translation=data.get("translation_id", "KJV")
        )

    except requests.RequestException as e:
        current_app.logger.error(f"Failed to fetch verse {book} {chapter}:{verse}: {e}")
        return None
    except (KeyError, IndexError, TypeError) as e:
        current_app.logger.error(f"Error parsing verse data for {book} {chapter}:{verse}: {e}")
        return None

def search_scripture(query: str, page: int = 1, per_page: int = 20) -> List:
    """
    First try local DB search; if none found, fallback to bible-api.com search.
    Returns either a list of Scripture models or a list of Verse objects.
    """
    results = []
    
    try:
        # Try local database first (if Elasticsearch is working)
        local, total = Scripture.search(query, page, per_page)
        if total > 0:
            return local, total
    except Exception as e:
        current_app.logger.info(f"Elasticsearch not available, using API: {e}")
    
    # Fallback to API search
    try:
        r = requests.get(f"https://bible-api.com/{query}", timeout=5)
        if r.status_code == 200:
            data = r.json()
            if "verses" in data:
                for v in data["verses"]:
                    results.append(Verse(
                        book=v["book_name"],
                        chapter=v["chapter"],
                        verse=v["verse"],
                        text=v["text"].strip(),
                        translation=data.get("translation_id", "KJV")
                    ))
            else:
                # Single verse result
                results.append(Verse(
                    book=data.get("book_name", ""),
                    chapter=data.get("chapter", 0),
                    verse=data.get("verse", 0),
                    text=data.get("text", "").strip(),
                    translation=data.get("translation_id", "KJV")
                ))
    except Exception as e:
        current_app.logger.error(f"Scripture search error for '{query}': {e}")

    return results, len(results)
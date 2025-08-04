# app/logos/utils.py

from datetime import datetime, date, timezone
from dataclasses import dataclass
import sqlalchemy as sa
import requests

from flask import current_app
from typing import Optional, List

from app import db
from app.models import Post, User, Scripture, JournalEntry


@dataclass
class Verse:
    book: str
    chapter: int
    verse: int
    text: str
    translation: str


def create_scripture_post(user_id: int, scripture_id: int) -> Optional[int]:
    """
    Creates a Post based on a Scripture reading.
    Returns post ID if created successfully, or None.
    """
    user = db.session.get(User, user_id)
    scripture = db.session.get(Scripture, scripture_id)

    if not user or not scripture:
        current_app.logger.warning(f"User ({user_id}) or Scripture ({scripture_id}) not found.")
        return None

    # Check for existing post to avoid duplication
    existing_post = db.session.execute(
        sa.select(Post).filter_by(
            user_id=user.id,
            scripture_reference=scripture.reference,
            scripture_text=scripture.text
        )
    ).scalar_one_or_none()

    if existing_post:
        current_app.logger.info(f"Scripture post already exists for {scripture.reference}")
        return existing_post.id

    post = Post(
        body=f"Today's reading: {scripture.reference}",
        timestamp=datetime.now(timezone.utc),
        user_id=user.id,
        scripture_text=scripture.text,
        scripture_reference=scripture.reference,
        title=f"Scripture Reading: {scripture.reference}",
        is_suggestion=False,  # This is a regular post, not a suggestion
        media_type='scripture'
    )

    db.session.add(post)
    db.session.commit()
    current_app.logger.info(f"Created scripture post {post.id} for {scripture.reference}")

    return post.id


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
    """Fetch & save one verse from bible-api.com."""
    try:
        r = requests.get(f"https://bible-api.com/{reference}")
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

    except requests.RequestException as e:
        current_app.logger.error(f"Failed to fetch scripture: {e}")
        return None
    except Exception as e:
        current_app.logger.error(f"Error processing scripture: {e}")
        return None


def get_verse_of_the_day() -> Verse:
    """
    Return today's Verse: wrap a DB Scripture (if exists) or fetch John 3:16.
    """
    skr = get_today_scripture()
    if not skr:
        skr = fetch_scripture_from_api("John 3:16")
        if not skr:
            # hard-fail fallback
            return Verse(book="John", chapter=3, verse=16,
                         text="For God so loved the world that he gave his one and only Son, that whoever believes in him shall not perish but have eternal life.", 
                         translation="NIV")

    # parse "Book Chapter:Verse" into parts
    try:
        book_part, cv_part = skr.reference.rsplit(" ", 1)
        chap_str, verse_str = cv_part.split(":", 1)
        
        return Verse(
            book=book_part,
            chapter=int(chap_str),
            verse=int(verse_str),
            text=skr.text.strip(),
            translation=skr.translation
        )
    except (ValueError, IndexError):
        # If parsing fails, return default
        return Verse(book="John", chapter=3, verse=16,
                     text=skr.text.strip(),
                     translation=skr.translation)


def get_full_chapter(book: str, chapter: int) -> List[Verse]:
    """
    Fetch an entire chapter from bible-api.com and return as list of Verse.
    """
    try:
        ref = f"{book} {chapter}"
        r = requests.get(f"https://bible-api.com/{ref}")
        r.raise_for_status()
        data = r.json()
        verses = []
        for v in data.get("verses", []):
            verses.append(Verse(
                book=v["book_name"],
                chapter=v["chapter"],
                verse=v["verse"],
                text=v["text"].strip(),
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
        r = requests.get(f"https://bible-api.com/{ref}")
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
        local, pagination = Scripture.search(query, page, per_page)
        if local:
            return local

        # no local hits → query remote API
        r = requests.get(f"https://bible-api.com/{query}")
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

    return results
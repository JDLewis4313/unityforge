from flask import render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
import requests
from datetime import date
from app.models import Scripture, Post, User, JournalEntry
from app import db
from typing import Optional

# Import bp from the same module (no circular import)
from . import bp

from .utils import (
    get_today_scripture,
    fetch_scripture_from_api,
    get_verse_of_the_day,
    get_full_chapter,
    get_specific_verse,
    search_scripture,
    create_daily_scripture_posts
)

# Bible books lookup
BIBLE_BOOKS = {
    'Genesis': 50, 'Exodus': 40, 'Leviticus': 27, 'Numbers': 36,
    'Deuteronomy': 34, 'Joshua': 24, 'Judges': 21, 'Ruth': 4,
    '1 Samuel': 31, '2 Samuel': 24, '1 Kings': 22, '2 Kings': 25,
    '1 Chronicles': 29, '2 Chronicles': 36, 'Ezra': 10, 'Nehemiah': 13,
    'Esther': 10, 'Job': 42, 'Psalms': 150, 'Proverbs': 31,
    'Ecclesiastes': 12, 'Song of Songs': 8, 'Isaiah': 66, 'Jeremiah': 52,
    'Lamentations': 5, 'Ezekiel': 48, 'Daniel': 12, 'Hosea': 14,
    'Joel': 3, 'Amos': 9, 'Obadiah': 1, 'Jonah': 4,
    'Micah': 7, 'Nahum': 3, 'Habakkuk': 3, 'Zephaniah': 3,
    'Haggai': 2, 'Zechariah': 14, 'Malachi': 4,
    'Matthew': 28, 'Mark': 16, 'Luke': 24, 'John': 21,
    'Acts': 28, 'Romans': 16, '1 Corinthians': 16, '2 Corinthians': 13,
    'Galatians': 6, 'Ephesians': 6, 'Philippians': 4, 'Colossians': 4,
    '1 Thessalonians': 5, '2 Thessalonians': 3, '1 Timothy': 6, '2 Timothy': 4,
    'Titus': 3, 'Philemon': 1, 'Hebrews': 13, 'James': 5,
    '1 Peter': 5, '2 Peter': 3, '1 John': 5, '2 John': 1,
    '3 John': 1, 'Jude': 1, 'Revelation': 22
}


@bp.route('/bible', defaults={'book': None, 'chapter': None, 'verse': None})
@bp.route('/bible/<book>', defaults={'chapter': None, 'verse': None})
@bp.route('/bible/<book>/<int:chapter>', defaults={'verse': None})
@bp.route('/bible/<book>/<int:chapter>/<int:verse>')
def bible_reader(book, chapter, verse):
    """
    Standalone reader. Defaults to verse-of-the-day when no book specified.
    Supports modes: ?mode=verse (single verse) or ?mode=chapter (full chapter).
    """
    mode = request.args.get('mode', 'verse')

    # 1) No book: show Verse of the Day
    if not book:
        vod = get_verse_of_the_day()
        return render_template(
            'logos/reader.html',
            mode='verse',
            book=vod.book,
            chapter=vod.chapter,
            verse=vod.verse,
            selected_verse=vod,
            bible_books=BIBLE_BOOKS
        )

    # Ensure chapter defaults
    chapter = chapter or 1

    # 2) Verse mode: display one verse at a time
    if mode == 'verse':
        verse = verse or 1
        selected_verse = get_specific_verse(book, chapter, verse)
        return render_template(
            'logos/reader.html',
            mode='verse',
            book=book,
            chapter=chapter,
            verse=verse,
            selected_verse=selected_verse,
            bible_books=BIBLE_BOOKS
        )

    # 3) Chapter mode: display the full chapter
    chapter_content = get_full_chapter(book, chapter)
    return render_template(
        'logos/reader.html',
        mode='chapter',
        book=book,
        chapter=chapter,
        chapter_content=chapter_content,
        bible_books=BIBLE_BOOKS
    ) 

@bp.route('/bible/search')
def bible_search():
    """Bible search functionality."""
    query = request.args.get('q', '').strip()
    results = []
    
    if query:
        try:
            # Search using Bible API
            r = requests.get(f"https://bible-api.com/{query}")
            if r.status_code == 200:
                data = r.json()
                if 'verses' in data:
                    results = data['verses']
                else:
                    # Single verse result
                    results = [data]
        except Exception as e:
            current_app.logger.error(f"Bible search failed: {e}")
            flash('Search temporarily unavailable.', 'error')
    
    return render_template('logos/bible_search.html', 
                         query=query, 
                         results=results)

@bp.route('/read', methods=['GET', 'POST'])
@login_required
def read_scripture():
    """Display scripture - either today's devotional or a specific verse."""
    
    # Handle GET parameters for specific verse requests
    book = request.args.get('book')
    chapter = request.args.get('chapter', type=int)
    verse_num = request.args.get('verse', type=int)
    
    # If specific verse requested, fetch it
    if book and chapter and verse_num:
        try:
            verse_obj = get_specific_verse(book, chapter, verse_num)
            if verse_obj:
                # Create a temporary Scripture-like object for the template
                verse = type('obj', (object,), {
                    'reference': f"{book} {chapter}:{verse_num}",
                    'text': verse_obj.text,
                    'translation': verse_obj.translation,
                    'date': date.today(),
                    'id': None,  # No ID since it's not saved
                    'audio_filename': None
                })
            else:
                flash(f'Could not find {book} {chapter}:{verse_num}', 'error')
                return redirect(url_for('logos.read_scripture'))
        except Exception as e:
            current_app.logger.error(f"Error fetching specific verse: {e}")
            flash('Error loading the requested verse.', 'error')
            return redirect(url_for('logos.read_scripture'))
    else:
        # Default: show today's scripture
        verse = get_today_scripture()
        
        if not verse:
            # Define a static default (John 3:16), not from request
            default_ref = 'John 3:16'
            verse = fetch_scripture_from_api(default_ref)

            if not verse:
                flash('Unable to load daily scripture.', 'error')
                return redirect(url_for('main.index'))

        # Silent post creation (optional) - only for saved scriptures
        if current_user.is_authenticated and hasattr(verse, 'id') and verse.id:
            post_id = create_scripture_post(current_user.id, verse.id)

    return render_template("logos/read_scripture.html", verse=verse)

@bp.route('/search')
def search_scripture():
    """Search for scripture passages."""
    query = request.args.get('q', '').strip()
    results = []
    
    if query:
        try:
            # First search local database
            local_results = Scripture.search(query, 1, 10)
            
            # If no local results, search API
            if not local_results[0]:
                r = requests.get(f"https://bible-api.com/{query}")
                if r.status_code == 200:
                    data = r.json()
                    results = data.get('verses', [])
            else:
                results = local_results[0]
                
        except requests.RequestException as e:
            current_app.logger.error(f"Scripture search failed: {e}")
            flash('Search temporarily unavailable. Please try again.', 'error')
        except Exception as e:
            current_app.logger.error(f"Search error: {e}")
            flash('An error occurred during search.', 'error')
    
    return render_template('logos/search_results.html', results=results, query=query)

@bp.route("/journal")
@login_required
def journal_list():
    page = request.args.get("page", 1, type=int)

    entries = JournalEntry.query \
        .filter_by(user_id=current_user.id) \
        .order_by(JournalEntry.created_at.desc()) \
        .paginate(page=page, per_page=10, error_out=False)

    return render_template("logos/journal.html", entries=entries)

@bp.route('/journal/new', methods=['GET', 'POST'])
@login_required
def create_journal_entry():
    """Create a new journal entry."""
    from app.logos.forms import JournalEntryForm
    
    form = JournalEntryForm()
    
    # Pre-populate with scripture if provided
    scripture_id = request.args.get('scripture_id', type=int)
    if scripture_id and request.method == 'GET':
        form.scripture_id.data = scripture_id
    
    if form.validate_on_submit():
        entry = JournalEntry(
            user_id=current_user.id,
            title=form.title.data,
            content=form.content.data,
            scripture_id=form.scripture_id.data if form.scripture_id.data else None
        )
        db.session.add(entry)
        db.session.commit()
        
        flash('Journal entry created!', 'success')
        return redirect(url_for('logos.journal_list'))
    
    return render_template('logos/create_journal.html', form=form)
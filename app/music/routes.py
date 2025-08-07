# app/music/routes.py
import os
from flask import render_template, redirect, url_for, request, flash, current_app, session
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app.music import bp
from app.music.utils import (
    authorize_spotify, handle_callback, search_tracks,
    get_user_playlists, create_playlist, add_tracks,
    create_worship_post
)
from app.music.forms import SuggestForm
from app.models import Post, SoundEntry
from app import db
from datetime import datetime

@bp.route('/login')
def login():
    """Connect to Spotify"""
    return authorize_spotify()

@bp.route('/callback')
def callback():
    """Handle Spotify callback"""
    return handle_callback()

@bp.route('/search')
def search():
    """Search for gospel music"""
    query = request.args.get('q', '').strip()
    tracks = []
    playlists = []
    
    if query and 'spotify_token' in session:
        tracks = search_tracks(query)
    
    if 'spotify_token' in session:
        playlists = get_user_playlists()
    
    return render_template('music/search.html', 
                         tracks=tracks, 
                         query=query, 
                         playlists=playlists)

@bp.route('/playlists')
@login_required
def playlists():
    """View user's playlists"""
    if 'spotify_token' not in session:
        flash('Please connect your Spotify account first.', 'info')
        return redirect(url_for('music.login'))
    
    pls = get_user_playlists()
    return render_template('music/playlists.html', playlists=pls)

@bp.route('/playlists/create', methods=['POST'])
@login_required
def playlists_create():
    """Create a new playlist"""
    if 'spotify_token' not in session:
        flash('Please connect your Spotify account first.', 'info')
        return redirect(url_for('music.login'))
    
    name = request.form.get('name', '').strip()
    desc = request.form.get('desc', '').strip()
    
    if not name:
        flash('Playlist name is required.', 'warning')
        return redirect(url_for('music.playlists'))
    
    result = create_playlist(name, desc)
    if result:
        flash('Playlist created successfully!', 'success')
    else:
        flash('Unable to create playlist. Try again.', 'danger')
    
    return redirect(url_for('music.playlists'))

@bp.route('/playlists/<pid>/add', methods=['POST'])
@login_required
def playlist_add(pid):
    """Add tracks to a playlist"""
    if 'spotify_token' not in session:
        flash('Please connect your Spotify account first.', 'info')
        return redirect(url_for('music.login'))
    
    uris = request.form.getlist('uris')
    if not uris:
        flash('No tracks selected.', 'warning')
        return redirect(url_for('music.search'))
    
    if add_tracks(pid, uris):
        flash(f"Added {len(uris)} tracks to playlist!", 'success')
    else:
        flash('Could not add tracks. Please try again.', 'danger')
    
    return redirect(url_for('music.search'))

@bp.route('/worship/upload', methods=['GET', 'POST'])
@login_required
def worship_upload():
    """Upload worship music"""
    if request.method == 'POST':
        file = request.files.get('file')
        if not file:
            flash('No file selected', 'warning')
            return redirect(request.url)
        
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
        filename = timestamp + filename
        
        # Save file
        upload_folder = current_app.config['UPLOAD_FOLDER']
        os.makedirs(upload_folder, exist_ok=True)
        file_path = os.path.join(upload_folder, filename)
        file.save(file_path)
        
        # Create SoundEntry
        sound_entry = SoundEntry(
            filename=filename,
            notes=request.form.get('notes', '')
        )
        db.session.add(sound_entry)
        db.session.commit()
        
        # Create post
        create_worship_post(sound_entry.id, current_user.id, request.form.get('description'))
        
        flash('Worship music uploaded successfully!', 'success')
        return redirect(url_for('main.explore', filter='audio'))
    
    return render_template('music/worship_upload.html')

@bp.route('/suggest', methods=['GET', 'POST'])
@login_required
def suggest():
    """Suggest content to community"""
    form = SuggestForm()
    
    if form.validate_on_submit():
        post = Post(
            user_id=current_user.id,
            title=form.title.data,
            body=form.description.data,
            source_url=form.link.data,
            media_type='suggestion',
            is_suggestion=True,
            timestamp=datetime.utcnow()
        )
        
        db.session.add(post)
        db.session.commit()
        
        flash('Suggestion submitted!', 'success')
        return redirect(url_for('main.index'))
    
    return render_template('music/suggest.html', form=form)
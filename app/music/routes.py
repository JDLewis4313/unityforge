from flask import (
    render_template, session, redirect,
    url_for, request, flash, jsonify, abort
)
from flask_login import login_required
from app.music import bp
from app.music.utils import (
    authorize_spotify, handle_callback,
    search_tracks, get_user_playlists,
    create_playlist, add_tracks, _api_get
)

@bp.route('/login')
def login():
    return authorize_spotify()

@bp.route('/callback')
def callback():
    return handle_callback()

@bp.route('/playlists')
@login_required
def playlists():
    pls = get_user_playlists()
    return render_template('music/playlists.html', playlists=pls)

@bp.route('/playlists/create', methods=['POST'])
@login_required
def playlists_create():
    name = request.form['name']
    desc = request.form.get('desc', '')
    create_playlist(name, desc)
    flash('Playlist created successfully!', 'success')
    return redirect(url_for('music.playlists'))

@bp.route('/playlists/<pid>')
@login_required
def view_playlist(pid):
    base_url = f'https://api.spotify.com/v1/playlists/{pid}/tracks'
    tracks, url = [], base_url

    while url:
        payload = _api_get(url)
        if 'error' in payload:
            abort(payload['error']['status'], payload['error']['message'])

        items = payload.get('items', [])
        tracks.extend(item.get('track') for item in items if 'track' in item)

        # advance to next page (or None to break)
        url = payload.get('next')

    return render_template('music/playlist.html', tracks=tracks, pid=pid)

@bp.route('/playlists/<pid>/add', methods=['POST'])
@login_required
def playlist_add(pid):
    uris = request.form.getlist('uris')
    if uris:
        add_tracks(pid, uris)
        flash('Added to playlist!', 'success')
    else:
        flash('No tracks selected.', 'warning')
    return redirect(url_for('music.view_playlist', pid=pid))

@bp.route('/search')
def search():
    q = request.args.get('q', '').strip()
    tracks = []
    
    if q:
        if 'spotify_token' not in session:
            return authorize_spotify()
        
        tracks = search_tracks(q)
        if not tracks:
            flash('No tracks found. Try a different search term.', 'info')

    return render_template('music/search.html', tracks=tracks, query=q)
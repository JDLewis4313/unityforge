# app/music/utils.py
import base64
import time
import requests
from flask import current_app, session, redirect, request, url_for
from app.models import Post, User, SoundEntry
from typing import Optional
from datetime import datetime, timezone
import sqlalchemy as sa
from app import db

def _encode_auth() -> str:
    """Encode client ID and secret for Spotify API authorization"""
    raw = f"{current_app.config['SPOTIFY_CLIENT_ID']}:{current_app.config['SPOTIFY_CLIENT_SECRET']}"
    return base64.b64encode(raw.encode()).decode()

def authorize_spotify():
    """Redirect user to Spotify authorization page"""
    redirect_uri = current_app.config['SPOTIFY_REDIRECT_URI']
    
    params = {
        'client_id': current_app.config['SPOTIFY_CLIENT_ID'],
        'response_type': 'code',
        'redirect_uri': redirect_uri,
        'scope': current_app.config['SPOTIFY_SCOPE'],
        'show_dialog': 'false'
    }
    
    url = 'https://accounts.spotify.com/authorize?' + '&'.join([f"{k}={v}" for k, v in params.items()])
    return redirect(url)

def handle_callback():
    """Handle the callback from Spotify after authorization"""
    code = request.args.get('code')
    error = request.args.get('error')
    
    if error:
        current_app.logger.error(f"Spotify authorization error: {error}")
        return redirect(url_for('music.search'))
    
    if not code:
        return redirect(url_for('music.search'))

    redirect_uri = current_app.config['SPOTIFY_REDIRECT_URI']
    
    payload = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': redirect_uri
    }
    headers = {'Authorization': f"Basic {_encode_auth()}"}

    try:
        response = requests.post(
            'https://accounts.spotify.com/api/token',
            data=payload, 
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            res = response.json()
            
            # Store token with expiry time
            session['spotify_token'] = {
                'access_token': res['access_token'],
                'refresh_token': res.get('refresh_token'),
                'expires_at': int(time.time()) + res['expires_in']
            }
            
            # Store refresh token in user model if logged in
            if current_user.is_authenticated:
                current_user.spotify_refresh_token = res.get('refresh_token')
                db.session.commit()
            
            return redirect(url_for('music.search'))
        
    except Exception as e:
        current_app.logger.error(f"Token exchange error: {e}")
    
    return redirect(url_for('music.search'))

def refresh_spotify_token():
    """Refresh the Spotify access token"""
    tok = session.get('spotify_token')
    
    # Try to get refresh token from session or user
    refresh_token = None
    if tok and 'refresh_token' in tok:
        refresh_token = tok['refresh_token']
    elif current_user.is_authenticated and current_user.spotify_refresh_token:
        refresh_token = current_user.spotify_refresh_token
    
    if not refresh_token:
        return False
    
    payload = {
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token
    }
    headers = {'Authorization': f"Basic {_encode_auth()}"}
    
    try:
        response = requests.post(
            'https://accounts.spotify.com/api/token',
            data=payload, 
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            new = response.json()
            
            # Update session
            session['spotify_token'] = {
                'access_token': new['access_token'],
                'refresh_token': new.get('refresh_token', refresh_token),
                'expires_at': int(time.time()) + new['expires_in']
            }
            
            return True
            
    except Exception as e:
        current_app.logger.error(f"Token refresh error: {e}")
    
    return False

def get_access_token() -> Optional[str]:
    """Get valid access token, refreshing if needed"""
    tok = session.get('spotify_token')
    
    if not tok:
        return None
    
    # Check if token expired
    if time.time() > tok.get('expires_at', 0) - 60:  # Refresh 1 minute before expiry
        if not refresh_spotify_token():
            session.pop('spotify_token', None)
            return None
        tok = session.get('spotify_token')
    
    return tok.get('access_token') if tok else None

def search_tracks(query: str, limit: int = 20) -> list:
    """Search Spotify for tracks"""
    token = get_access_token()
    if not token:
        return []

    # Add gospel/worship focus
    if 'gospel' not in query.lower() and 'worship' not in query.lower():
        query = f"{query} gospel"

    headers = {'Authorization': f'Bearer {token}'}
    params = {'q': query, 'type': 'track', 'limit': limit}

    try:
        resp = requests.get(
            'https://api.spotify.com/v1/search',
            headers=headers, 
            params=params,
            timeout=10
        )
        
        if resp.status_code == 200:
            data = resp.json()
            return data.get('tracks', {}).get('items', [])
            
    except Exception as e:
        current_app.logger.error(f"Search error: {e}")
    
    return []

def get_user_playlists():
    """Get user's playlists from Spotify"""
    token = get_access_token()
    if not token:
        return []
    
    try:
        response = requests.get(
            'https://api.spotify.com/v1/me/playlists',
            headers={'Authorization': f'Bearer {token}'},
            timeout=10
        )
        
        if response.status_code == 200:
            return response.json().get('items', [])
            
    except Exception as e:
        current_app.logger.error(f"Get playlists error: {e}")
    
    return []

def create_playlist(name, desc=''):
    """Create a new playlist"""
    token = get_access_token()
    if not token:
        return None
    
    # Get user ID
    try:
        response = requests.get(
            'https://api.spotify.com/v1/me',
            headers={'Authorization': f'Bearer {token}'},
            timeout=10
        )
        
        if response.status_code != 200:
            return None
            
        user_id = response.json()['id']
        
        # Create playlist
        payload = {'name': name, 'description': desc, 'public': True}
        response = requests.post(
            f"https://api.spotify.com/v1/users/{user_id}/playlists",
            headers={'Authorization': f"Bearer {token}"},
            json=payload,
            timeout=10
        )
        
        if response.status_code in [200, 201]:
            return response.json()
            
    except Exception as e:
        current_app.logger.error(f"Create playlist error: {e}")
    
    return None

def add_tracks(playlist_id, uris):
    """Add tracks to a playlist"""
    token = get_access_token()
    if not token:
        return False
    
    try:
        response = requests.post(
            f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks",
            headers={'Authorization': f"Bearer {token}"},
            json={'uris': uris},
            timeout=10
        )
        
        return response.status_code in [200, 201]
        
    except Exception as e:
        current_app.logger.error(f"Add tracks error: {e}")
    
    return False

def create_worship_post(sound_entry_id: int, user_id: int, description: str = None) -> Optional[int]:
    """Create a post for uploaded worship music"""
    sound_entry = db.session.get(SoundEntry, sound_entry_id)
    user = db.session.get(User, user_id)
    
    if not sound_entry or not user:
        return None
    
    post = Post(
        body=description or f"🎵 Worship music: {sound_entry.filename}",
        timestamp=datetime.now(timezone.utc),
        user_id=user_id,
        media_filename=sound_entry.filename,
        media_type='worship',
        title=f"Worship: {sound_entry.filename}"
    )
    
    db.session.add(post)
    db.session.commit()
    
    return post.id
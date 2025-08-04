# app/music/utils.py
import base64
import time
from urllib.parse import urlencode

import requests
from flask import (
    current_app,
    session,
    redirect,
    request,
    url_for
)

def _encode_auth() -> str:
    raw = f"{current_app.config['SPOTIFY_CLIENT_ID']}:" \
          f"{current_app.config['SPOTIFY_CLIENT_SECRET']}"
    return base64.b64encode(raw.encode()).decode()


def authorize_spotify():
    params = {
        'client_id':     current_app.config['SPOTIFY_CLIENT_ID'],
        'response_type': 'code',
        'redirect_uri':  current_app.config['SPOTIFY_REDIRECT_URI'],
        'scope':         current_app.config['SPOTIFY_SCOPE']
    }
    url = 'https://accounts.spotify.com/authorize?' + urlencode(params)
    return redirect(url)


def handle_callback():
    code = request.args.get('code')
    payload = {
        'grant_type':   'authorization_code',
        'code':         code,
        'redirect_uri': current_app.config['SPOTIFY_REDIRECT_URI']
    }
    headers = {'Authorization': f"Basic {_encode_auth()}"}
    res = requests.post(
        'https://accounts.spotify.com/api/token',
        data=payload, headers=headers
    ).json()

    # Normalize session payload
    session['spotify_token'] = {
        'access_token':  res['access_token'],
        'refresh_token': res['refresh_token'],
        'expires_at':    int(time.time()) + res['expires_in']
    }
    return redirect(url_for('music.playlists'))


def _refresh_token_if_needed() -> None:
    tok = session.get('spotify_token')
    if not tok:
        return

    # Refresh a little before expiry
    if time.time() > tok['expires_at'] - 30:
        payload = {
            'grant_type':    'refresh_token',
            'refresh_token': tok['refresh_token']
        }
        headers = {'Authorization': f"Basic {_encode_auth()}"}
        new = requests.post(
            'https://accounts.spotify.com/api/token',
            data=payload, headers=headers
        ).json()

        tok.update({
            'access_token':  new['access_token'],
            'expires_at':    int(time.time()) + new['expires_in']
        })
        session['spotify_token'] = tok


def get_access_token() -> str | None:
    """Return a valid Spotify access token or None if not authorized."""
    tok = session.get('spotify_token')
    if not tok:
        return None

    _refresh_token_if_needed()
    return session['spotify_token']['access_token']

def search_tracks(query: str, limit: int = 20) -> list:
    """
    Search Spotify for tracks matching `query`.
    Returns a list of track dicts.
    """
    token = get_access_token()
    if not token:
        # No token in session → user needs to auth
        return []

    headers = {'Authorization': f'Bearer {token}'}
    params  = {'q': query, 'type': 'track', 'limit': limit}

    resp = requests.get(
        'https://api.spotify.com/v1/search',
        headers=headers, params=params
    )
    if resp.status_code != 200:
        current_app.logger.error(
            f"Spotify search failed [{resp.status_code}]: {resp.text}"
        )
        return []

    return resp.json().get('tracks', {}).get('items', [])


def _api_get(url, params=None):
    token = get_access_token()
    return requests.get(url,
        headers={'Authorization': f'Bearer {token}'},
        params=params
    ).json()


def get_user_playlists():
    return _api_get('https://api.spotify.com/v1/me/playlists').get('items', [])

def create_playlist(name, desc=''):
    me = _api_get('https://api.spotify.com/v1/me')
    payload = {'name': name, 'description': desc, 'public': True}
    return requests.post(
        f"https://api.spotify.com/v1/users/{me['id']}/playlists",
        headers={'Authorization': f"Bearer {get_access_token()}"},
        json=payload
    ).json()

def add_tracks(playlist_id, uris):
    return requests.post(
        f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks",
        headers={'Authorization': f"Bearer {get_access_token()}"},
        json={'uris': uris}
    ).json()

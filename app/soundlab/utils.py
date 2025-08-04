import os
import uuid
import numpy as np
import librosa
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import librosa.display
from flask import current_app
from yt_dlp import YoutubeDL
from pydub import AudioSegment
from datetime import datetime, timezone
import sqlalchemy as sa
from app import db
from app.models import Post, User, SoundEntry
from typing import Optional

def extract_audio_features(filepath):
    """Extract audio features from an audio file."""
    try:
        y, sr = librosa.load(filepath)
        duration = librosa.get_duration(y=y, sr=sr)
        peak = np.max(librosa.amplitude_to_db(np.abs(y)))
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)

        # Generate spectrogram
        S = librosa.feature.melspectrogram(y=y, sr=sr)
        S_db = librosa.power_to_db(S, ref=np.max)
        spectro_id = f"{uuid.uuid4().hex}.png"
        output_path = os.path.join(current_app.config['SPECTROGRAM_FOLDER'], spectro_id)

        plt.figure(figsize=(10, 4))
        librosa.display.specshow(S_db, x_axis='time', y_axis='mel', sr=sr)
        plt.title('Mel-Spectrogram')
        plt.colorbar(format='%+2.0f dB')
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()

        return {
            'duration': round(duration, 2),
            'peak': round(peak, 2),
            'tempo': round(tempo),
            'spectrogram': spectro_id
        }
    except Exception as e:
        current_app.logger.error(f"Error extracting audio features: {e}")
        raise

def download_youtube_audio(url):
    """Download audio from YouTube URL."""
    output_dir = current_app.config['UPLOAD_FOLDER']
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': f'{output_dir}/%(title)s.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'noplaylist': True,
    }
    
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            # Handle different audio formats
            for ext in ['.webm', '.m4a', '.mp4']:
                filename = filename.replace(ext, '.mp3')
            return filename
    except Exception as e:
        current_app.logger.error(f"Error downloading YouTube audio: {e}")
        raise

def trim_audio(filepath, start_ms, end_ms):
    """Trim audio file between start and end timestamps (in milliseconds)."""
    try:
        audio = AudioSegment.from_file(filepath)
        segment = audio[start_ms:end_ms]
        base_name = os.path.splitext(filepath)[0]
        new_path = f"{base_name}_trimmed_{start_ms}_{end_ms}.mp3"
        segment.export(new_path, format="mp3")
        return new_path
    except Exception as e:
        current_app.logger.error(f"Error trimming audio: {e}")
        raise

def create_audio_post(user_id: int, sound_entry_id: int, custom_text: str = None) -> Optional[int]:
    """
    Creates a Post based on a SoundEntry.
    Returns post ID if created successfully, or None.
    """
    user = db.session.get(User, user_id)
    sound_entry = db.session.get(SoundEntry, sound_entry_id)

    if not user or not sound_entry:
        current_app.logger.warning(f"User ({user_id}) or SoundEntry ({sound_entry_id}) not found.")
        return None

    # Check for existing post to avoid duplication
    existing_post = db.session.execute(
        sa.select(Post).filter_by(
            user_id=user.id,
            media_filename=sound_entry.filename,
            media_type='audio'
        )
    ).scalar_one_or_none()

    if existing_post:
        current_app.logger.info(f"Audio post already exists for {sound_entry.filename}")
        return existing_post.id

    body_text = custom_text or f"Check out this audio: {sound_entry.filename}"
    if len(body_text) > 280:
        body_text = body_text[:277] + "..."

    post = Post(
        body=body_text,
        timestamp=datetime.now(timezone.utc),
        user_id=user.id,
        media_filename=sound_entry.filename,
        media_type='audio',
        title=f"Audio: {sound_entry.filename}",
        is_suggestion=False
    )

    db.session.add(post)
    db.session.commit()
    current_app.logger.info(f"Created audio post {post.id} for {sound_entry.filename}")

    return post.id

def validate_audio_file(file):
    """Validate uploaded audio file."""
    allowed_extensions = {'.mp3', '.wav', '.m4a', '.ogg', '.flac'}
    filename = file.filename.lower()
    
    if not filename:
        return False, "No file selected"
    
    if not any(filename.endswith(ext) for ext in allowed_extensions):
        return False, f"File type not supported. Allowed: {', '.join(allowed_extensions)}"
    
    return True, "Valid file"

def get_audio_info(filepath):
    """Get basic information about an audio file."""
    try:
        audio = AudioSegment.from_file(filepath)
        return {
            'duration_seconds': len(audio) / 1000.0,
            'channels': audio.channels,
            'sample_rate': audio.frame_rate,
            'file_size': os.path.getsize(filepath)
        }
    except Exception as e:
        current_app.logger.error(f"Error getting audio info: {e}")
        return None
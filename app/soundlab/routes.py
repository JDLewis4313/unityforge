import os
from flask import request, jsonify, render_template, redirect, url_for, flash, current_app, send_file
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from datetime import datetime
from moviepy.audio.io.AudioFileClip import AudioFileClip
from app.soundlab import bp
from app import db
from app.models import SoundEntry, Post
from app.soundlab.forms import AudioUploadForm, YouTubeForm, SuggestForm, ShortClipForm
from app.soundlab.utils import extract_audio_features, download_youtube_audio, trim_audio


@bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload_page():
    form = AudioUploadForm()
    if form.validate_on_submit():
        file = form.audio.data
        filename = secure_filename(file.filename)
        upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(upload_path)

        # Optionally, redirect to analyzer if metadata processing is needed
        return redirect(url_for('soundlab.analyze_audio'))

    return render_template('soundlab/upload.html', form=form)

@bp.route('/analyze', methods=['POST'])
@login_required
def analyze_audio():
    form = AudioUploadForm()
    if not form.validate_on_submit():
        return jsonify({'error': 'Form validation failed'}), 400

    file = form.audio.data
    filename = secure_filename(file.filename)
    upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    file.save(upload_path)

    try:
        features = extract_audio_features(upload_path)
        entry = SoundEntry(
            filename=filename,
            duration_seconds=features['duration'],
            peak_db=features['peak'],
            tempo_bpm=features['tempo'],
            spectrogram_image=features['spectrogram'],
            created_at=datetime.utcnow()
        )
        db.session.add(entry)
        db.session.commit()
        return jsonify({'message': 'Entry saved', 'entry': features})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/youtube', methods=['POST'])
@login_required
def fetch_youtube_audio():
    form = YouTubeForm()
    if not form.validate_on_submit():
        return jsonify({'error': 'Invalid YouTube URL'}), 400

    try:
        filepath = download_youtube_audio(form.youtube_url.data)
        features = extract_audio_features(filepath)
        entry = SoundEntry(
            filename=os.path.basename(filepath),
            duration_seconds=features['duration'],
            peak_db=features['peak'],
            tempo_bpm=features['tempo'],
            spectrogram_image=features['spectrogram'],
            created_at=datetime.utcnow()
        )
        db.session.add(entry)
        db.session.commit()
        return jsonify({'message': 'YouTube audio saved and analyzed', 'entry': features})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/suggest', methods=['GET', 'POST'])
@login_required
def suggest():
    form = SuggestForm()
    if form.validate_on_submit():
        title = form.title.data
        link = form.link.data
        filename = None

        if form.file.data:
            filename = secure_filename(form.file.data.filename)
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            form.file.data.save(file_path)

        new_post = Post(
            user_id=current_user.id,
            title=title,
            source_url=link,
            media_filename=filename,
            media_type='audio',
            is_suggestion=True,
            created_at=datetime.utcnow()
        )
        db.session.add(new_post)
        db.session.commit()
        flash('Suggestion submitted!', 'success')
        return redirect(url_for('main.index'))

    return render_template('soundlab/suggest.html', form=form)

@bp.route('/shorts', methods=['POST'])
@login_required
def upload_short():
    form = ShortClipForm()
    if not form.validate_on_submit():
        return jsonify({'error': 'Validation failed'}), 400

    file = form.clip.data
    title = form.title.data
    filename = secure_filename(file.filename)
    upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    file.save(upload_path)

    clip = AudioFileClip(upload_path)
    if clip.duration > 300:
        os.remove(upload_path)
        return jsonify({'error': 'Clip too long'}), 400

    features = extract_audio_features(upload_path)
    entry = SoundEntry(
        filename=filename,
        duration_seconds=features['duration'],
        peak_db=features['peak'],
        tempo_bpm=features['tempo'],
        spectrogram_image=features['spectrogram'],
        created_at=datetime.utcnow()
    )
    db.session.add(entry)
    db.session.commit()
    return jsonify({'message': 'Short clip uploaded', 'entry': features})

@bp.route('/trim', methods=['POST'])
@login_required
def trim_clip():
    filepath = request.form.get('filepath')
    start = int(request.form.get('start', 0))
    end = int(request.form.get('end', 300000))

    if not os.path.exists(filepath):
        return jsonify({'error': 'File not found'}), 404

    try:
        trimmed_path = trim_audio(filepath, start, end)
        return jsonify({'message': 'Audio trimmed', 'path': trimmed_path})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/user_download/<filename>')
def user_download(filename):
    file_path = os.path.join('static', 'downloads', filename)
    return send_file(file_path, as_attachment=True)
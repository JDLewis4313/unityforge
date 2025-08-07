from flask import render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from app.prayer import bp
from app.prayer.forms import SharePrayerForm, CraftPrayerForm
from app.models import Prayer, db
from werkzeug.utils import secure_filename
import os
from datetime import datetime
import librosa

@bp.route('/')
@login_required
def index():
    """Prayer Studio home page"""
    prayers = Prayer.query.filter_by(user_id=current_user.id).order_by(Prayer.created_at.desc()).limit(5).all()
    return render_template('prayer/index.html', prayers=prayers)

@bp.route('/share', methods=['GET', 'POST'])
@login_required
def share():
    """Share a prayer audio file"""
    form = SharePrayerForm()
    
    if form.validate_on_submit():
        # Handle file upload
        file = form.file.data
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
        filename = timestamp + filename
        
        # Save file
        upload_folder = current_app.config['UPLOAD_FOLDER']
        os.makedirs(upload_folder, exist_ok=True)
        file_path = os.path.join(upload_folder, filename)
        file.save(file_path)
        
        # Get audio duration
        try:
            duration = librosa.get_duration(filename=file_path)
        except:
            duration = None
        
        # Create prayer record
        prayer = Prayer(
            title=form.title.data,
            description=form.description.data,
            filename=filename,
            duration_seconds=duration,
            prayer_type=form.prayer_type.data,
            spiritual_focus=form.spiritual_focus.data,
            scripture_reference=form.scripture_reference.data,
            church_service_date=form.church_service_date.data,
            is_public=form.is_public.data,
            user_id=current_user.id
        )
        
        db.session.add(prayer)
        db.session.commit()
        
        flash('Your prayer has been shared! 🙏', 'success')
        return redirect(url_for('prayer.view', id=prayer.id))
    
    return render_template('prayer/share.html', form=form)

@bp.route('/craft', methods=['GET', 'POST'])
@login_required
def craft():
    """Craft a written prayer (journal-style)"""
    form = CraftPrayerForm()
    
    if form.validate_on_submit():
        # For written prayers, we'll save as text file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
        filename = f"{timestamp}prayer.txt"
        
        # Save prayer text to file
        upload_folder = current_app.config['UPLOAD_FOLDER']
        os.makedirs(upload_folder, exist_ok=True)
        file_path = os.path.join(upload_folder, filename)
        
        with open(file_path, 'w') as f:
            f.write(f"Prayer Title: {form.title.data}\n\n")
            f.write(f"Prayer Type: {form.prayer_type.data}\n")
            if form.spiritual_focus.data:
                f.write(f"Spiritual Focus: {form.spiritual_focus.data}\n")
            if form.scripture_reference.data:
                f.write(f"Scripture Reference: {form.scripture_reference.data}\n")
            f.write(f"\nPrayer:\n{form.prayer_text.data}")
        
        # Create prayer record
        prayer = Prayer(
            title=form.title.data,
            description=form.prayer_text.data[:500],  # First 500 chars as description
            filename=filename,
            prayer_type=form.prayer_type.data,
            spiritual_focus=form.spiritual_focus.data,
            scripture_reference=form.scripture_reference.data,
            is_public=form.is_public.data,
            user_id=current_user.id
        )
        
        db.session.add(prayer)
        db.session.commit()
        
        flash('Your prayer has been crafted and saved! ✨', 'success')
        return redirect(url_for('prayer.collection'))
    
    return render_template('prayer/craft.html', form=form)

@bp.route('/collection')
@login_required
def collection():
    """View user's prayer collection"""
    prayers = Prayer.query.filter_by(user_id=current_user.id).order_by(Prayer.created_at.desc()).all()
    return render_template('prayer/collection.html', prayers=prayers)

@bp.route('/community')
def community():
    """View community prayers (public prayers)"""
    prayers = Prayer.query.filter_by(is_public=True).order_by(Prayer.created_at.desc()).limit(20).all()
    return render_template('prayer/community.html', prayers=prayers)

@bp.route('/view/<int:id>')
@login_required
def view(id):
    """View a specific prayer"""
    prayer = Prayer.query.get_or_404(id)
    
    # Check if user can view this prayer
    if not prayer.is_public and prayer.user_id != current_user.id:
        flash('This prayer is private.', 'warning')
        return redirect(url_for('prayer.community'))
    
    return render_template('prayer/view.html', prayer=prayer)
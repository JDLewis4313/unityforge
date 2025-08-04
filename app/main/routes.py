from datetime import datetime, timezone, date
from flask import render_template, flash, redirect, url_for, request, g, \
    current_app, jsonify
from flask_login import current_user, login_required
from flask_babel import _, get_locale
import sqlalchemy as sa
from langdetect import detect, LangDetectException
from app import db
from app.main.forms import EditProfileForm, EmptyForm, PostForm, SearchForm, \
    MessageForm
from app.models import User, Post, Message, Notification, Scripture, SoundEntry, JournalEntry
from app.translate import translate
from app.main import bp
from app.logos.utils import create_scripture_post
from app.soundlab.utils import create_audio_post
from typing import Optional

@bp.before_app_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.now(timezone.utc)
        db.session.commit()
        g.search_form = SearchForm()
    g.locale = str(get_locale())
    
    # Add daily scripture to global context
    g.daily_scripture = Scripture.query.filter_by(date=date.today()).first()


@bp.route('/', methods=['GET', 'POST'])
@bp.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    form = PostForm()
    if form.validate_on_submit():
        try:
            language = detect(form.post.data)
        except LangDetectException:
            language = ''
        post = Post(body=form.post.data, author=current_user,
                    language=language)
        db.session.add(post)
        db.session.commit()
        flash(_('Your post is now live!'))
        return redirect(url_for('main.index'))
    
    page = request.args.get('page', 1, type=int)
    posts = db.paginate(current_user.following_posts(), page=page,
                        per_page=current_app.config['POSTS_PER_PAGE'],
                        error_out=False)
    next_url = url_for('main.index', page=posts.next_num) \
        if posts.has_next else None
    prev_url = url_for('main.index', page=posts.prev_num) \
        if posts.has_prev else None
    
    # Get today's scripture and recent content for sidebar
    today_scripture = g.daily_scripture
    recent_audio = SoundEntry.query.order_by(SoundEntry.created_at.desc()).limit(3).all()
    recent_journals = JournalEntry.query.filter_by(user_id=current_user.id).order_by(JournalEntry.created_at.desc()).limit(3).all()
    
    return render_template('index.html', title=_('Home'), form=form,
                           posts=posts.items, next_url=next_url,
                           prev_url=prev_url, daily_scripture=today_scripture,
                           recent_audio=recent_audio, recent_journals=recent_journals)


@bp.route('/explore')
@login_required
def explore():
    page = request.args.get('page', 1, type=int)
    filter_type = request.args.get('filter', 'all')  # all, scripture, audio, journal
    
    query = sa.select(Post).order_by(Post.timestamp.desc())
    
    # Apply filters
    if filter_type == 'scripture':
        query = query.where(Post.media_type == 'scripture')
    elif filter_type == 'audio':
        query = query.where(Post.media_type == 'audio')
    elif filter_type == 'journal':
        query = query.where(Post.media_type == 'journal')
    elif filter_type == 'suggestions':
        query = query.where(Post.is_suggestion == True)
    
    posts = db.paginate(query, page=page,
                        per_page=current_app.config['POSTS_PER_PAGE'],
                        error_out=False)
    next_url = url_for('main.explore', page=posts.next_num, filter=filter_type) \
        if posts.has_next else None
    prev_url = url_for('main.explore', page=posts.prev_num, filter=filter_type) \
        if posts.has_prev else None
    
    return render_template('explore.html', title=_('Explore'),
                           posts=posts.items, next_url=next_url,
                           prev_url=prev_url, current_filter=filter_type)


@bp.route('/user/<username>')
@login_required
def user(username):
    user = db.first_or_404(sa.select(User).where(User.username == username))
    page = request.args.get('page', 1, type=int)
    query = user.posts.select().order_by(Post.timestamp.desc())
    posts = db.paginate(query, page=page,
                        per_page=current_app.config['POSTS_PER_PAGE'],
                        error_out=False)
    next_url = url_for('main.user', username=user.username,
                       page=posts.next_num) if posts.has_next else None
    prev_url = url_for('main.user', username=user.username,
                       page=posts.prev_num) if posts.has_prev else None
    form = EmptyForm()
    
    # Get user statistics
    journal_count = JournalEntry.query.filter_by(user_id=user.id).count()
    audio_count = db.session.scalar(sa.select(sa.func.count()).select_from(
        sa.select(Post).where(Post.user_id == user.id, Post.media_type == 'audio')))
    scripture_count = db.session.scalar(sa.select(sa.func.count()).select_from(
        sa.select(Post).where(Post.user_id == user.id, Post.media_type == 'scripture')))
    
    return render_template('user.html', user=user, posts=posts.items,
                           next_url=next_url, prev_url=prev_url, form=form,
                           journal_count=journal_count, audio_count=audio_count,
                           scripture_count=scripture_count)


@bp.route('/user/<username>/popup')
@login_required
def user_popup(username):
    user = db.first_or_404(sa.select(User).where(User.username == username))
    form = EmptyForm()
    return render_template('user_popup.html', user=user, form=form)


@bp.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm(current_user.username)
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data
        db.session.commit()
        flash(_('Your changes have been saved.'))
        return redirect(url_for('main.edit_profile'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', title=_('Edit Profile'),
                           form=form)


@bp.route('/follow/<username>', methods=['POST'])
@login_required
def follow(username):
    form = EmptyForm()
    if form.validate_on_submit():
        user = db.session.scalar(
            sa.select(User).where(User.username == username))
        if user is None:
            flash(_('User %(username)s not found.', username=username))
            return redirect(url_for('main.index'))
        if user == current_user:
            flash(_('You cannot follow yourself!'))
            return redirect(url_for('main.user', username=username))
        current_user.follow(user)
        db.session.commit()
        flash(_('You are following %(username)s!', username=username))
        return redirect(url_for('main.user', username=username))
    else:
        return redirect(url_for('main.index'))


@bp.route('/unfollow/<username>', methods=['POST'])
@login_required
def unfollow(username):
    form = EmptyForm()
    if form.validate_on_submit():
        user = db.session.scalar(
            sa.select(User).where(User.username == username))
        if user is None:
            flash(_('User %(username)s not found.', username=username))
            return redirect(url_for('main.index'))
        if user == current_user:
            flash(_('You cannot unfollow yourself!'))
            return redirect(url_for('main.user', username=username))
        current_user.unfollow(user)
        db.session.commit()
        flash(_('You are not following %(username)s.', username=username))
        return redirect(url_for('main.user', username=username))
    else:
        return redirect(url_for('main.index'))


@bp.route('/translate', methods=['POST'])
@login_required
def translate_text():
    data = request.get_json()
    return {'text': translate(data['text'],
                              data['source_language'],
                              data['dest_language'])}


@bp.route('/search')
@login_required
def search():
    if not g.search_form.validate():
        return redirect(url_for('main.explore'))
    page = request.args.get('page', 1, type=int)
    posts, total = Post.search(g.search_form.q.data, page,
                               current_app.config['POSTS_PER_PAGE'])
    next_url = url_for('main.search', q=g.search_form.q.data, page=page + 1) \
        if total > page * current_app.config['POSTS_PER_PAGE'] else None
    prev_url = url_for('main.search', q=g.search_form.q.data, page=page - 1) \
        if page > 1 else None
    return render_template('search.html', title=_('Search'), posts=posts,
                           next_url=next_url, prev_url=prev_url)


@bp.route('/send_message/<recipient>', methods=['GET', 'POST'])
@login_required
def send_message(recipient):
    user = db.first_or_404(sa.select(User).where(User.username == recipient))
    form = MessageForm()
    if form.validate_on_submit():
        msg = Message(author=current_user, recipient=user,
                      body=form.message.data)
        db.session.add(msg)
        user.add_notification('unread_message_count',
                              user.unread_message_count())
        db.session.commit()
        flash(_('Your message has been sent.'))
        return redirect(url_for('main.user', username=recipient))
    return render_template('send_message.html', title=_('Send Message'),
                           form=form, recipient=recipient)


@bp.route('/messages')
@login_required
def messages():
    current_user.last_message_read_time = datetime.now(timezone.utc)
    current_user.add_notification('unread_message_count', 0)
    db.session.commit()
    page = request.args.get('page', 1, type=int)
    query = current_user.messages_received.select().order_by(
        Message.timestamp.desc())
    messages = db.paginate(query, page=page,
                           per_page=current_app.config['POSTS_PER_PAGE'],
                           error_out=False)
    next_url = url_for('main.messages', page=messages.next_num) \
        if messages.has_next else None
    prev_url = url_for('main.messages', page=messages.prev_num) \
        if messages.has_prev else None
    return render_template('messages.html', messages=messages.items,
                           next_url=next_url, prev_url=prev_url)


@bp.route('/export_posts')
@login_required
def export_posts():
    if current_user.get_task_in_progress('export_posts'):
        flash(_('An export task is currently in progress'))
    else:
        current_user.launch_task('export_posts', _('Exporting posts...'))
        db.session.commit()
    return redirect(url_for('main.user', username=current_user.username))


@bp.route('/notifications')
@login_required
def notifications():
    since = request.args.get('since', 0.0, type=float)
    query = current_user.notifications.select().where(
        Notification.timestamp > since).order_by(Notification.timestamp.asc())
    notifications = db.session.scalars(query)
    return [{
        'name': n.name,
        'data': n.get_data(),
        'timestamp': n.timestamp
    } for n in notifications]


# New routes for scripture and audio post creation
@bp.route('/create_scripture_post/<int:scripture_id>')
@login_required
def create_scripture_post_route(scripture_id):
    """Create a post from a scripture reading."""
    post_id = create_scripture_post(current_user.id, scripture_id)
    if post_id:
        flash(_('Scripture post created!'), 'success')
    else:
        flash(_('Error creating scripture post.'), 'error')
    return redirect(url_for('main.index'))


@bp.route('/delete_post/<int:post_id>', methods=['POST'])
@login_required
def delete_post(post_id):
    """Delete a post (only by the author)."""
    post = db.session.get(Post, post_id)
    
    if not post:
        return jsonify({'error': 'Post not found'}), 404
    
    if post.author != current_user:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        db.session.delete(post)
        db.session.commit()
        return jsonify({'message': 'Post deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting post {post_id}: {e}")
        return jsonify({'error': 'Failed to delete post'}), 500


@bp.route('/create_audio_post/<int:sound_entry_id>')
@login_required
def create_audio_post_route(sound_entry_id):
    """Create a post from an audio entry."""
    custom_text = request.args.get('text', '')
    post_id = create_audio_post(current_user.id, sound_entry_id, custom_text)
    if post_id:
        flash(_('Audio post created!'), 'success')
    else:
        flash(_('Error creating audio post.'), 'error')
    return redirect(url_for('main.index'))


@bp.route('/dashboard')
@login_required
def dashboard():
    """User dashboard with overview of all activities."""
    # Get user's content statistics
    user_stats = {
        'total_posts': current_user.posts_count(),
        'journal_entries': JournalEntry.query.filter_by(user_id=current_user.id).count(),
        'audio_uploads': db.session.scalar(sa.select(sa.func.count()).select_from(
            sa.select(Post).where(Post.user_id == current_user.id, Post.media_type == 'audio'))),
        'scripture_posts': db.session.scalar(sa.select(sa.func.count()).select_from(
            sa.select(Post).where(Post.user_id == current_user.id, Post.media_type == 'scripture'))),
        'followers': current_user.followers_count(),
        'following': current_user.following_count()
    }
    
    # Get recent activity
    recent_posts = db.session.scalars(
        current_user.posts.select().order_by(Post.timestamp.desc()).limit(5)
    ).all()
    
    recent_journals = JournalEntry.query.filter_by(user_id=current_user.id)\
        .order_by(JournalEntry.created_at.desc()).limit(3).all()
    
    return render_template('dashboard.html', title=_('Dashboard'),
                         user_stats=user_stats, recent_posts=recent_posts,
                         recent_journals=recent_journals, daily_scripture=g.daily_scripture)
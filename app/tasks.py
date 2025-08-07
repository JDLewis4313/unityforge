import json
import sys
import time
import sqlalchemy as sa
from flask import render_template
from rq import get_current_job
from app import create_app, db
from app.models import User, Post, Task, JournalEntry, Scripture
from app.email import send_email
from datetime import datetime, timezone, date

app = create_app()
app.app_context().push()

def _set_task_progress(progress):
    job = get_current_job()
    if job:
        job.meta['progress'] = progress
        job.save_meta()
        task = db.session.get(Task, job.get_id())
        task.user.add_notification('task_progress', {'task_id': job.get_id(),
                                                     'progress': progress})
        if progress >= 100:
            task.complete = True
        db.session.commit()

def create_daily_scripture_posts():
    """
    Create daily scripture posts for all active users.
    This runs at midnight UTC via RQ-scheduler.
    """
    from app.logos.utils import get_verse_for_date, fetch_scripture_from_api
    from app.logos.daily_verses import DAILY_VERSES
    
    today = date.today()
    
    # Get or create today's scripture
    scripture = Scripture.query.filter_by(date=today).first()
    
    if not scripture:
        # Get today's verse reference
        daily_reference = get_verse_for_date(today)
        
        # Fetch and save
        scripture = fetch_scripture_from_api(daily_reference)
        if scripture:
            scripture.date = today
            db.session.commit()
        else:
            print(f"Failed to fetch scripture for {today}")
            return "Failed to fetch daily scripture"
    
    # Create posts for all users
    users = User.query.all()
    posts_created = 0
    
    for user in users:
        # Check if user already has this scripture post
        existing = Post.query.filter_by(
            user_id=user.id,
            scripture_reference=scripture.reference,
            media_type='scripture'
        ).first()
        
        if not existing:
            post = Post(
                body=f"Today's reading: {scripture.reference}",
                timestamp=datetime.now(timezone.utc),
                user_id=user.id,
                scripture_text=scripture.text,
                scripture_reference=scripture.reference,
                title=f"Daily Scripture: {scripture.reference}",
                media_type='scripture'
            )
            db.session.add(post)
            posts_created += 1
    
    db.session.commit()
    
    message = f"Created {posts_created} posts for {scripture.reference}"
    print(message)
    return message

def export_posts(user_id):
    """Example task from Mega Tutorial - kept for reference."""
    try:
        user = db.session.get(User, user_id)
        _set_task_progress(0)
        data = []
        i = 0
        total_posts = db.session.scalar(sa.select(sa.func.count()).select_from(
            user.posts.select().subquery()))
        for post in db.session.scalars(user.posts.select()).all():
            data.append({'body': post.body,
                        'timestamp': post.timestamp.isoformat() + 'Z'})
            time.sleep(5)
            i += 1
            _set_task_progress(100 * i // total_posts)

        send_email('[UnityForge] Your blog posts',
                sender=current_app.config['ADMINS'][0], recipients=[user.email],
                text_body=render_template('email/export_posts.txt', user=user),
                html_body=render_template('email/export_posts.html', user=user),
                attachments=[('posts.json', 'application/json',
                            json.dumps({'posts': data}, indent=4))],
                sync=True)
    except Exception:
        _set_task_progress(100)
        current_app.logger.error('Unhandled exception', exc_info=sys.exc_info())
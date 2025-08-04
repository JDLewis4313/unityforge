import json
import sys
import time
import sqlalchemy as sa
from flask import render_template
from rq import get_current_job
from app import create_app, db
from app.models import User, Post, Task, JournalEntry, Scripture
from app.email import send_email
from datetime import datetime, timezone

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


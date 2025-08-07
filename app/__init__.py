import os
import logging
from logging.handlers import SMTPHandler, RotatingFileHandler
from flask import Flask, current_app, request
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_mail import Mail
from flask_moment import Moment
from flask_babel import Babel, lazy_gettext as _l
from flask_wtf.csrf import CSRFProtect
from elasticsearch import Elasticsearch
from redis import Redis
import rq
from rq_scheduler import Scheduler
from config import get_config

db = SQLAlchemy()
migrate = Migrate()
login = LoginManager()
mail = Mail()
moment = Moment()
babel = Babel()
csrf = CSRFProtect()

login.login_view = 'auth.login'
login.login_message = _l('Please log in to access this page.')

def get_locale():
    return request.accept_languages.best_match(current_app.config['LANGUAGES'])

def setup_scheduler(app):
    """Set up RQ-scheduler for recurring tasks."""
    if app.config.get('SCHEDULER_ENABLED', True):
        try:
            scheduler = Scheduler(connection=app.redis)
            
            # Clear existing daily scripture job
            for job in scheduler.get_jobs():
                if job.id == 'daily_scripture_posts':
                    scheduler.cancel(job)
            
            # Schedule daily scripture posts at midnight UTC
            scheduler.cron(
                "0 0 * * *",  # Midnight UTC
                func='app.tasks.create_daily_scripture_posts',
                id='daily_scripture_posts',
                queue_name='unityforge-tasks'
            )
            
            app.logger.info('Daily scripture posts scheduled for midnight UTC')
        except Exception as e:
            app.logger.error(f'Failed to setup scheduler: {e}')

def create_app():
    config_class = get_config()
    app = Flask(__name__)
    app.config.from_object(config_class)
    config_class.init_app(app)

    # Force HTTPS URL generation for Spotify redirects
    @app.before_request
    def force_https_for_spotify():
        # Only apply HTTPS enforcement if configured and not in testing
        if (app.config.get('PREFERRED_URL_SCHEME') == 'https' and 
            not app.testing and 
            request.endpoint and 
            'music' in request.endpoint):
            
            # Log the request details for debugging
            app.logger.info(f"Request: {request.method} {request.url}")
            app.logger.info(f"Is secure: {request.is_secure}")
            app.logger.info(f"Scheme: {request.scheme}")
            
            # If this is a Spotify-related request and not HTTPS, log it
            if not request.is_secure and not request.url.startswith('https://'):
                app.logger.warning(f"Non-HTTPS request to Spotify endpoint: {request.url}")

    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)
    mail.init_app(app)
    moment.init_app(app)
    babel.init_app(app, locale_selector=get_locale)
    csrf.init_app(app)

    app.elasticsearch = Elasticsearch([app.config['ELASTICSEARCH_URL']]) if app.config['ELASTICSEARCH_URL'] else None
    app.redis = Redis.from_url(app.config['REDIS_URL'])
    app.task_queue = rq.Queue('unityforge-tasks', connection=app.redis)  # Changed from microblog-tasks

    from app.errors import bp as errors_bp
    app.register_blueprint(errors_bp)

    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from app.main import bp as main_bp
    app.register_blueprint(main_bp)

    from app.cli import bp as cli_bp
    app.register_blueprint(cli_bp)

    from app.api import bp as api_bp
    app.register_blueprint(api_bp, url_prefix='/api')

    from app.logos import bp as logos_bp
    app.register_blueprint(logos_bp, url_prefix='/logos')

    from app.music import bp as music_bp
    app.register_blueprint(music_bp, url_prefix='/music')
    
    from app.prayer import bp as prayer_bp
    app.register_blueprint(prayer_bp, url_prefix='/prayer')
    
    setup_logging(app)
    
    # Setup scheduler after everything is initialized
    with app.app_context():
        setup_scheduler(app)
    
    return app

def setup_logging(app):
    if app.debug or app.testing:
        return
    if app.config['MAIL_SERVER']:
        auth = None
        if app.config['MAIL_USERNAME'] or app.config['MAIL_PASSWORD']:
            auth = (app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
        secure = () if app.config['MAIL_USE_TLS'] else None
        mail_handler = SMTPHandler(
            mailhost=(app.config['MAIL_SERVER'], app.config['MAIL_PORT']),
            fromaddr='no-reply@' + app.config['MAIL_SERVER'],
            toaddrs=app.config['ADMINS'], subject='UnityForge Failure',
            credentials=auth, secure=secure
        )
        mail_handler.setLevel(logging.ERROR)
        app.logger.addHandler(mail_handler)

    if app.config['LOG_TO_STDOUT']:
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.INFO)
        app.logger.addHandler(stream_handler)
    else:
        if not os.path.exists('logs'):
            os.mkdir('logs')
        file_handler = RotatingFileHandler('logs/unityforge.log', maxBytes=10240, backupCount=10)
        file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)

    app.logger.setLevel(logging.INFO)
    app.logger.info('UnityForge startup')
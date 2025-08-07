import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

def normalize_db_url(url):
    if url and url.lower().startswith('postgres://'):
        return url.replace('postgres://', 'postgresql://', 1)
    return url

def get_spotify_redirect_uri():
    """
    Get Spotify redirect URI with automatic environment detection.
    This ensures the correct URI for both development and production.
    """
    # Priority 1: Explicit environment variable (overrides everything)
    explicit_uri = os.getenv('SPOTIFY_REDIRECT_URI')
    if explicit_uri:
        return explicit_uri
    
    # Priority 2: Detect environment and build URI
    if os.getenv('DYNO'):
        # Heroku production environment
        app_name = os.getenv('HEROKU_APP_NAME')
        if app_name:
            return f"https://{app_name}.herokuapp.com/music/callback"
        else:
            # Fallback to BASE_URL if HEROKU_APP_NAME not set
            base_url = os.getenv('BASE_URL', 'https://your-app-name.herokuapp.com')
            return f"{base_url.rstrip('/')}/music/callback"
    else:
        # Local development environment
        return 'https://localhost:5000/music/callback'

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'you-will-never-guess')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_RECORD_QUERIES = True
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    RQ_REDIS_URL = REDIS_URL
    ELASTICSEARCH_URL = os.getenv('ELASTICSEARCH_URL')
    MAIL_SERVER = os.getenv('MAIL_SERVER')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', '1') in ['1', 'true', 'True']
    MAIL_USE_SSL = os.getenv('MAIL_USE_SSL', '0') in ['1', 'true', 'True']
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', MAIL_USERNAME)
    ADMINS = [e.strip() for e in os.getenv('ADMINS', '').split(',') if e.strip()]
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', os.path.join(basedir, 'app/static/uploads'))
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', 50 * 1024 * 1024))
    SSL_REDIRECT = os.getenv('SSL_REDIRECT', 'False') in ['true', '1']
    WTF_CSRF_TIME_LIMIT = int(os.getenv('WTF_CSRF_TIME_LIMIT', 3600))
    LOG_TO_STDOUT = os.getenv('LOG_TO_STDOUT', 'False') in ['true', '1']
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
    RATELIMIT_STORAGE_URL = REDIS_URL
    RATELIMIT_DEFAULT = os.getenv('RATELIMIT_DEFAULT', '100/hour')
    POSTS_PER_PAGE = int(os.getenv('POSTS_PER_PAGE', 10))
    LANGUAGES = ['en', 'es']
    PREFERRED_URL_SCHEME = 'https'
    
    # Spotify Configuration - Environment aware
    SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
    SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
    SPOTIFY_REDIRECT_URI = get_spotify_redirect_uri()
    SPOTIFY_SCOPE = os.getenv('SPOTIFY_SCOPE', 'user-read-private user-read-email playlist-modify-public playlist-modify-private')

    @staticmethod
    def init_app(app):
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = normalize_db_url(os.getenv('DEV_DATABASE_URL')) or f"sqlite:///{os.path.join(basedir, 'app-dev.db')}"
    LOG_TO_STDOUT = True

class TestingConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = normalize_db_url(os.getenv('TEST_DATABASE_URL')) or 'sqlite:///:memory:'
    ELASTICSEARCH_URL = None

class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = normalize_db_url(os.getenv('DATABASE_URL'))
    SSL_REDIRECT = True
    LOG_TO_STDOUT = True

    @classmethod
    def init_app(cls, app):
        super().init_app(app)
        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

class HerokuConfig(ProductionConfig):
    @classmethod
    def init_app(cls, app):
        super().init_app(app)
        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'heroku': HerokuConfig,
    'default': DevelopmentConfig
}

def get_config():
    env = os.getenv('FLASK_ENV', 'development').lower()
    if os.getenv('DYNO'):
        return config['heroku']
    return config.get(env, config['default'])
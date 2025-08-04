import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

class Config:
    # Core Flask Settings
    SECRET_KEY = os.getenv('SECRET_KEY', 'you-will-never-guess')
    
    # Database Configuration
    DATABASE_URL = os.getenv('DATABASE_URL', '')
    if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
    
    SQLALCHEMY_DATABASE_URI = DATABASE_URL or f"sqlite:///{os.path.join(basedir, 'app.db')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_RECORD_QUERIES = True
    
    # Application Settings
    POSTS_PER_PAGE = int(os.getenv('POSTS_PER_PAGE', 10))
    LANGUAGES = ['en', 'es']
    PREFERRED_URL_SCHEME = os.getenv('PREFERRED_URL_SCHEME', 'https')
    
    # Redis Configuration
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    RQ_REDIS_URL = REDIS_URL
    
    # Search Configuration
    ELASTICSEARCH_URL = os.getenv('ELASTICSEARCH_URL', '')
    
    # Email Configuration
    MAIL_SERVER = os.getenv('MAIL_SERVER', '')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 25))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', '').lower() in ['true', '1', 'on']
    MAIL_USE_SSL = os.getenv('MAIL_USE_SSL', '').lower() in ['true', '1', 'on']
    MAIL_USERNAME = os.getenv('MAIL_USERNAME', '')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD', '')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', MAIL_USERNAME)
    ADMINS = [email.strip() for email in os.getenv('ADMINS', '').split(',') if email.strip()]
    
    # Spotify API Configuration
    SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
    SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
    SPOTIFY_REDIRECT_URI = os.getenv('SPOTIFY_REDIRECT_URI')
    SPOTIFY_SCOPE = os.getenv('SPOTIFY_SCOPE', 'playlist-read-private playlist-modify-public playlist-modify-private')
    
    # File Upload Configuration
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', os.path.join(basedir, 'app', 'static', 'uploads'))
    SPECTROGRAM_FOLDER = os.getenv('SPECTROGRAM_FOLDER', os.path.join(basedir, 'app', 'static', 'spectrograms'))
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', 50 * 1024 * 1024))  # 50MB default
    
    # Security Settings
    SSL_REDIRECT = os.getenv('SSL_REDIRECT', 'False').lower() in ['true', '1', 'on']
    WTF_CSRF_TIME_LIMIT = int(os.getenv('WTF_CSRF_TIME_LIMIT', 3600))
    
    # Logging Configuration
    LOG_TO_STDOUT = os.getenv('LOG_TO_STDOUT', 'False').lower() in ['true', '1', 'on']
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
    
    # Rate Limiting
    RATELIMIT_STORAGE_URL = REDIS_URL
    RATELIMIT_DEFAULT = os.getenv('RATELIMIT_DEFAULT', '100/hour')
    
    @staticmethod
    def init_app(app):
        """Initialize application with configuration."""
        # Create upload directories
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        os.makedirs(app.config['SPECTROGRAM_FOLDER'], exist_ok=True)

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    DEVELOPMENT = True
    SQLALCHEMY_DATABASE_URI = os.getenv('DEV_DATABASE_URL') or f"sqlite:///{os.path.join(basedir, 'app-dev.db')}"
    LOG_TO_STDOUT = True
    
class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    REDIS_URL = 'redis://localhost:6379/1'  # Use different Redis DB for testing
    ELASTICSEARCH_URL = None

class ProductionConfig(Config):
    """Production configuration for Heroku."""
    DEBUG = False
    TESTING = False
    LOG_TO_STDOUT = True
    SSL_REDIRECT = True
    
    # Use environment variables for sensitive data
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        
        # Handle Heroku proxy headers
        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
        
        # Log to stderr
        import logging
        from logging import StreamHandler
        file_handler = StreamHandler()
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)

class HerokuConfig(ProductionConfig):
    """Heroku-specific configuration."""
    
    @classmethod  
    def init_app(cls, app):
        ProductionConfig.init_app(app)
        
        # Handle Heroku logs
        import logging
        from logging import StreamHandler
        file_handler = StreamHandler()
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        
        # Respect the 'X-Forwarded-Proto' header for HTTPS redirects
        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app)

# Configuration mapping
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'heroku': HerokuConfig,
    'default': DevelopmentConfig
}

# Auto-detect environment
def get_config():
    """Auto-detect and return appropriate configuration."""
    env = os.getenv('FLASK_ENV', 'development').lower()
    
    # Heroku detection
    if os.getenv('DYNO'):
        return config['heroku']
    
    return config.get(env, config['default'])
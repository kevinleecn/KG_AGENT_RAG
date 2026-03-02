"""
Configuration settings for Knowledge Graph QA Demo System
"""

import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Flask Configuration
class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')

    # Upload settings
    UPLOAD_FOLDER = str(BASE_DIR / 'static' / 'uploads')
    PARSED_DATA_FOLDER = str(BASE_DIR / 'data' / 'parsed')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB
    ALLOWED_EXTENSIONS = {'.txt', '.docx', '.pdf', '.pptx'}

    # Session settings
    SESSION_TYPE = 'filesystem'
    SESSION_FILE_DIR = str(BASE_DIR / 'data' / 'sessions')
    SESSION_PERMANENT = False
    SESSION_USE_SIGNER = True

    # Knowledge Graph Database settings
    NEO4J_URI = os.environ.get('NEO4J_URI', 'bolt://localhost:7687')
    NEO4J_USER = os.environ.get('NEO4J_USER', 'neo4j')
    NEO4J_PASSWORD = os.environ.get('NEO4J_PASSWORD', 'password')
    NEO4J_DATABASE = os.environ.get('NEO4J_DATABASE', 'neo4j')

    # Knowledge Extraction settings
    SPACY_MODEL = os.environ.get('SPACY_MODEL', 'zh_core_web_sm')  # Chinese model with NER
    EXTRACTION_CONFIDENCE_THRESHOLD = float(os.environ.get('EXTRACTION_CONFIDENCE_THRESHOLD', '0.7'))

    # LLM settings (optional, for enhanced extraction)
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY') or 'sk-0b0a00b2d4cc4d7d8dce645d5db1b739'
    LLM_BACKEND = os.environ.get('LLM_BACKEND', 'openai')  # openai, ollama, anthropic
    LLM_MODEL = os.environ.get('LLM_MODEL', 'deepseek-chat')  # DeepSeek V3.2
    OPENAI_BASE_URL = os.environ.get('OPENAI_BASE_URL') or 'https://api.deepseek.com'  # DeepSeek API base URL

    # Visualization settings
    D3_MAX_NODES = int(os.environ.get('D3_MAX_NODES', '500'))
    D3_MAX_LINKS = int(os.environ.get('D3_MAX_LINKS', '1000'))
    D3_THEME = os.environ.get('D3_THEME', 'light')  # light, dark

    # Ensure directories exist
    @staticmethod
    def ensure_directories():
        """Create necessary directories"""
        directories = [
            Config.UPLOAD_FOLDER,
            Config.PARSED_DATA_FOLDER,
            Config.SESSION_FILE_DIR,
            BASE_DIR / 'data' / 'graphs',
            BASE_DIR / 'data' / 'cache',
            BASE_DIR / 'data' / 'models'
        ]

        for directory in directories:
            os.makedirs(directory, exist_ok=True)

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False

    # Development-specific settings
    TEMPLATES_AUTO_RELOAD = True
    EXPLAIN_TEMPLATE_LOADING = False

class TestingConfig(Config):
    """Testing configuration"""
    DEBUG = False
    TESTING = True

    # Use separate upload folder for tests
    UPLOAD_FOLDER = str(BASE_DIR / 'static' / 'test_uploads')
    PARSED_DATA_FOLDER = str(BASE_DIR / 'data' / 'test_parsed')

    # Disable CSRF for testing
    WTF_CSRF_ENABLED = False

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False

    # Production security settings
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

    # Use environment variable for secret key
    SECRET_KEY = os.environ.get('SECRET_KEY')

    @classmethod
    def validate(cls):
        """Validate production configuration"""
        if not cls.SECRET_KEY or cls.SECRET_KEY == 'dev-key-change-in-production':
            raise ValueError(
                "SECRET_KEY must be set in production environment. "
                "Set SECRET_KEY environment variable."
            )

# Configuration mapping
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

def get_config(config_name=None):
    """Get configuration class by name"""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'default')

    config_class = config.get(config_name, config['default'])

    # Ensure directories exist
    config_class.ensure_directories()

    return config_class
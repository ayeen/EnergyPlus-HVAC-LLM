"""
Backend Configuration for Flask API
"""

import os
from pathlib import Path

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent

class Config:
    """Flask application configuration"""

    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = True

    # CORS settings
    CORS_ORIGINS = [
        'http://localhost:3000',
        'http://127.0.0.1:3000',
        'http://163.180.125.76:3000',
        'http://163.180.125.76:5000'
    ]

    # File upload settings
    UPLOAD_FOLDER = str(PROJECT_ROOT / 'ui' / 'backend' / 'uploads')
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB max file size
    ALLOWED_EXTENSIONS = {'idf'}

    # Output settings
    OUTPUT_FOLDER = str(PROJECT_ROOT / 'outputs' / 'ui_generated')

    # Pipeline settings
    DEFAULT_RAG_ENABLED = True
    DEFAULT_LLM_PROVIDER = 'mistral'
    PIPELINE_TIMEOUT = 600  # 10 minutes max execution time

    # WebSocket settings
    SOCKETIO_MESSAGE_QUEUE = None
    SOCKETIO_ASYNC_MODE = 'threading'

    @staticmethod
    def allowed_file(filename):
        """Check if file extension is allowed"""
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

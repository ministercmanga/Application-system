import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'secret-key'
    SESSION_PERMANENT = True
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # Maximum file upload size (e.g., 16 MB)
    UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'uploads')

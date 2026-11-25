"""Application configuration. All secrets come from environment variables."""
import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, ".env"))

raw_db_url = os.environ.get("DATABASE_URL")
if not raw_db_url:
    default_db_path = os.path.join(basedir, "student_library.db").replace("\\", "/")
    raw_db_url = f"sqlite:///{default_db_path}"
elif raw_db_url.startswith("postgres://"):
    raw_db_url = raw_db_url.replace("postgres://", "postgresql://", 1)
elif raw_db_url == "sqlite:///student_library.db":
    default_db_path = os.path.join(basedir, "student_library.db").replace("\\", "/")
    raw_db_url = f"sqlite:///{default_db_path}"


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "fallback-secret-key-student-library-management")
    SQLALCHEMY_DATABASE_URI = raw_db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {} if "sqlite" in raw_db_url else {"pool_pre_ping": True, "pool_recycle": 280}

    UPLOAD_FOLDER = os.path.join(basedir, os.environ.get("UPLOAD_FOLDER", "app/static/uploads"))
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_LENGTH_MB", "2")) * 1024 * 1024
    ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true"
    REMEMBER_COOKIE_HTTPONLY = True
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 8
    WTF_CSRF_TIME_LIMIT = 3600

    ITEMS_PER_PAGE = 12


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True


class TestingConfig(Config):
    TESTING = True
    SECRET_KEY = "test-secret-key-not-for-production"
    SQLALCHEMY_DATABASE_URI = os.environ.get("TEST_DATABASE_URL", "sqlite:///:memory:")
    SQLALCHEMY_ENGINE_OPTIONS = {}
    WTF_CSRF_ENABLED = False
    SESSION_COOKIE_SECURE = False


config_map = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}


def get_config(name=None):
    name = name or os.environ.get("FLASK_ENV", "development")
    return config_map.get(name, DevelopmentConfig)

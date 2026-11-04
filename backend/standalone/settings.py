import os
import secrets
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_ROOT = Path(
    os.environ.get("AI_FILE_INSPECTOR_DATA_DIR", str(BASE_DIR / "runtime/web-data"))
).resolve()
DATA_ROOT.mkdir(parents=True, exist_ok=True)
secret = DATA_ROOT / "secret.key"
if not secret.exists():
    try:
        with secret.open("x") as stream:
            stream.write(secrets.token_urlsafe(48))
    except FileExistsError:
        pass
SECRET_KEY = secret.read_text()
DEBUG = False
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]"]
ROOT_URLCONF = "standalone.urls"
INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "ai_file_inspector.django_app.apps.AiFileInspectorConfig",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": DATA_ROOT / "db.sqlite3",
        "OPTIONS": {"timeout": 30},
    }
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = True
TIME_ZONE = "Asia/Kolkata"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Strict"
CSRF_COOKIE_SAMESITE = "Strict"
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
DATA_UPLOAD_MAX_MEMORY_SIZE = 2 * 1024 * 1024
DATA_UPLOAD_MAX_NUMBER_FILES = 10
FILE_UPLOAD_MAX_MEMORY_SIZE = 1024 * 1024
FILE_UPLOAD_HANDLERS = [
    "django.core.files.uploadhandler.MemoryFileUploadHandler",
    "django.core.files.uploadhandler.TemporaryFileUploadHandler",
]
FRONTEND_DIST = BASE_DIR / "frontend" / "dist"

AI_FILE_INSPECTOR = {"DATA_DIR": DATA_ROOT}

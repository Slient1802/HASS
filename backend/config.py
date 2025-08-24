import os
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

def bool_env(key, default=False):
    v = os.getenv(key)
    if v is None:
        return default
    return v.lower() in ["1", "true", "yes", "y", "on"]

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-change-me")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", SECRET_KEY)  # dùng chung nếu chưa có

    # Use SQLite by default for lab simplicity
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{os.path.join(BASE_DIR, 'iotlab.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    # Socket.IO namespaces for FDMA-like separation
    SOCKETIO_CHANNELS = ["/ch0", "/ch1", "/ch2", "/ch3"]

    # TDMA: timeslot length (seconds) and epoch start
    TDMA_SLOT_SECONDS = int(os.getenv("TDMA_SLOT_SECONDS", "2"))
    TDMA_NUM_SLOTS = int(os.getenv("TDMA_NUM_SLOTS", "16"))

    # Watchdog (per device)
    WATCHDOG_TIMEOUT = int(os.getenv("WATCHDOG_TIMEOUT", "30"))  # seconds
    WATCHDOG_GRACE = int(os.getenv("WATCHDOG_GRACE", "5"))

    # Session / login
    REMEMBER_COOKIE_DURATION = timedelta(days=1)

    # Rate limiting for user endpoints (per IP)
    RATELIMIT_DEFAULT = "20 per minute"

    # Allowed device types
    ALLOWED_DEVICE_TYPES = {"raspberry_pi", "arduino_uno"}

    # Frontend LAN-only mode
    LAN_ONLY = bool_env("LAN_ONLY", True)

    # Security: content length limit for uploads
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024  # 2MB

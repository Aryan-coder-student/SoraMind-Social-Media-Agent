"""Application-level settings and constants."""

SQLITE_DATABASE_URL = "sqlite:///./soramind.db"
SQLALCHEMY_POOL_SIZE = 5
SQLALCHEMY_MAX_OVERFLOW = 5
SQLALCHEMY_POOL_TIMEOUT = 30.0

SKIPPED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
    ".svg",
    ".ico",
    ".css",
    ".js",
    ".mp4",
    ".mp3",
    ".webm",
    ".woff",
    ".woff2",
    ".ttf",
}

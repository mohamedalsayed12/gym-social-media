from sqlalchemy import create_engine
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import sessionmaker

from app.core.config import settings


def build_database_url(config) -> URL:
    if config.database_url:
        url = make_url(config.database_url)
        if url.drivername in {"postgres", "postgresql"}:
            url = url.set(drivername="postgresql+psycopg2")
        return url

    required = (
        "database_hostname",
        "database_port",
        "database_password",
        "database_name",
        "database_username",
    )
    missing = [name for name in required if getattr(config, name) is None]
    if missing:
        raise ValueError("Set DATABASE_URL or all separate database settings; missing: " + ", ".join(missing))

    return URL.create(
        "postgresql+psycopg2",
        username=config.database_username,
        password=config.database_password,
        host=config.database_hostname,
        port=config.database_port,
        database=config.database_name,
    )


engine = create_engine(
    build_database_url(settings),
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

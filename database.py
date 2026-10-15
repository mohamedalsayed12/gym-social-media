import time
import psycopg2
from psycopg2.extras import RealDictCursor
from sqlalchemy import create_engine
from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import settings

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
        raise ValueError(f"Set DATABASE_URL or all separate database settings; missing: {', '.join(missing)}")

    return URL.create(
        "postgresql+psycopg2",
        username=config.database_username,
        password=config.database_password,
        host=config.database_hostname,
        port=config.database_port,
        database=config.database_name,
    )


SQLALCHEMY_DATABASE_URL = build_database_url(settings)

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# while True:
#     conn = None
#     try:
#         conn = psycopg2.connect(
#             host=engine.url.host,
#             port=engine.url.port,
#             dbname=engine.url.database,
#             user=engine.url.username,
#             password=engine.url.password,
#         )
#         with conn.cursor(cursor_factory=RealDictCursor) as cursor:
#             cursor.execute("SELECT 1")
#         print("Database connection was successful!")
#         break
#     except psycopg2.Error as error:
#         print("Connecting to database failed")
#         print("Error:", error)
#         time.sleep(2)
#     finally:
#         if conn is not None:
#             conn.close()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

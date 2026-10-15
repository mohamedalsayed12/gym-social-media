import time
import psycopg2
from psycopg2.extras import RealDictCursor
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import settings

SQLALCHEMY_DATABASE_URL = (
    f"postgresql+psycopg2://{settings.database_username}:{settings.database_password}@"
    f"{settings.database_hostname}:{settings.database_port}/{settings.database_name}"
)

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

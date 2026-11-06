from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from backend.app.config import settings

# Handle thread checking for SQLite
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    future=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    # Import models so Base has them registered
    import backend.app.models  # noqa: F401

    Base.metadata.create_all(bind=engine)

    # Ensure added columns exist in existing SQLite databases
    if settings.DATABASE_URL.startswith("sqlite"):
        with engine.connect() as conn:
            try:
                cursor = conn.exec_driver_sql("PRAGMA table_info(voice_logs);")
                existing_cols = {row[1] for row in cursor.fetchall()}
                new_cols = [
                    ("duration", "FLOAT"),
                    ("peak", "FLOAT"),
                    ("rms", "FLOAT"),
                    ("cleaned", "BOOLEAN DEFAULT 1"),
                    ("raw_audio_file", "VARCHAR(100)"),
                    ("cleaned_audio_file", "VARCHAR(100)"),
                    ("error", "TEXT"),
                    ("is_compare", "BOOLEAN DEFAULT 0"),
                ]
                for col_name, col_type in new_cols:
                    if col_name not in existing_cols:
                        conn.exec_driver_sql(f"ALTER TABLE voice_logs ADD COLUMN {col_name} {col_type};")
                conn.commit()
            except Exception:
                pass

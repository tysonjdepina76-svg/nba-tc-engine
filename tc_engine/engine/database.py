"""Database — PostgreSQL connection and session management via SQLAlchemy."""
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from pathlib import Path
import os
import json

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///" + str(Path(__file__).parent.parent.parent / "Projects" / "data" / "tc_pipeline.db"),
)

engine = create_engine(
    DATABASE_URL,
    echo=False,
    pool_size=5,
    max_overflow=10,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create tables synchronously. For migrations use Alembic."""
    try:
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS graded_picks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT, sport TEXT, player TEXT, team TEXT, stat TEXT,
                    projection REAL, market_line REAL, line REAL, edge REAL,
                    actual REAL, direction TEXT, hit INTEGER,
                    matchup TEXT, period TEXT DEFAULT 'GAME'
                )
            """))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS bet_tracking (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sport TEXT, player TEXT, stat TEXT, status TEXT,
                    profit REAL DEFAULT 0, date TEXT, wager REAL DEFAULT 0,
                    line REAL, projection REAL, actual REAL
                )
            """))
            conn.commit()
        return True
    except Exception as e:
        return {"error": str(e)}

"""
Database initialization and connection manager using SQLite.
"""
import sqlite3
from pathlib import Path
from contextlib import contextmanager
from typing import Generator
from src.config.settings import settings
from src.utils.logging_config import logger


def init_db() -> None:
    """Initializes tables in SQLite database if they do not exist."""
    db_path = settings.DB_PATH
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()

        # Route History table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS route_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                source TEXT NOT NULL,
                destination TEXT NOT NULL,
                source_coords TEXT,
                destination_coords TEXT,
                vehicle_type TEXT NOT NULL,
                preference TEXT NOT NULL,
                emergency_mode BOOLEAN DEFAULT 0,
                recommended_route_id TEXT NOT NULL,
                distance_km REAL NOT NULL,
                duration_minutes REAL NOT NULL,
                smart_score REAL NOT NULL,
                fuel_liters REAL NOT NULL,
                fuel_cost REAL NOT NULL,
                summary TEXT,
                full_result_json TEXT
            )
        """)

        # User Settings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        logger.info(f"Database initialized at {db_path}")


@contextmanager
def get_db_connection() -> Generator[sqlite3.Connection, None, None]:
    """Context manager for SQLite database connection."""
    conn = sqlite3.connect(settings.DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Database transaction error: {e}")
        raise
    finally:
        conn.close()

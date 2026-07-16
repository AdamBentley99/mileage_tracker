from pathlib import Path
import os
import platform
import sqlite3


def get_db_path() -> Path:
    system = platform.system()

    if system == "Windows":
        local_appdata = os.getenv("LOCALAPPDATA")
        if local_appdata:
            base_dir = Path(local_appdata) / "MileageTracker"
        else:
            base_dir = Path.home() / ".mileage_tracker"

    elif system == "Darwin":
        base_dir = Path.home() / "Library" / "Application Support" / "MileageTracker"

    else:
        base_dir = Path.home() / ".mileage_tracker"

    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir / "mileage.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(get_db_path())
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def create_tables(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS stores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            last_visited TEXT
        );

        CREATE TABLE IF NOT EXISTS store_distances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store_a_id INTEGER NOT NULL,
            store_b_id INTEGER NOT NULL,
            miles REAL NOT NULL,
            UNIQUE(store_a_id, store_b_id),
            FOREIGN KEY (store_a_id) REFERENCES stores(id) ON DELETE CASCADE,
            FOREIGN KEY (store_b_id) REFERENCES stores(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS visits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            visit_date TEXT NOT NULL,
            store_id INTEGER NOT NULL,
            sequence_number INTEGER NOT NULL,
            miles_from_previous REAL,
            FOREIGN KEY (store_id) REFERENCES stores(id) ON DELETE CASCADE
        );
        """
    )


def init_db() -> None:
    with get_connection() as conn:
        create_tables(conn)
        conn.commit()

    print(f"Database initialized at: {get_db_path()}")


if __name__ == "__main__":
    init_db()
from pathlib import Path
import sqlite3

# Project root = .../mileage_tracker
ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"
DB_PATH = DATA_DIR / "mileage.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def create_tables(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS stores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            is_business INTEGER NOT NULL DEFAULT 0,
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
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    with get_connection() as conn:
        create_tables(conn)
        conn.commit()

    print(f"Database initialized at: {DB_PATH}")


if __name__ == "__main__":
    init_db()
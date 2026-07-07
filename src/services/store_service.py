import sqlite3

from database.init_db import get_connection


def get_all_stores():
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, name, last_visited
            FROM stores
            ORDER BY
                last_visited IS NULL,
                last_visited ASC,
                name COLLATE NOCASE
            """
        ).fetchall()

    return [
        {
            "id": row[0],
            "name": row[1],
            "last_visited": row[2],
        }
        for row in rows
    ]

def update_store_last_visited(store_id: int, last_visited: str):
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE stores
            SET last_visited = ?
            WHERE id = ?
            """,
            (last_visited, store_id),
        )
        conn.commit()

def add_store(name: str) -> None:
    cleaned_name = name.strip()

    if not cleaned_name:
        raise ValueError("Store name cannot be empty.")

    with get_connection() as conn:
        try:
            conn.execute(
                """
                INSERT INTO stores (name, last_visited)
                VALUES (?, NULL)
                """,
                (cleaned_name,),
            )
            conn.commit()
        except sqlite3.IntegrityError as exc:
            raise ValueError(f"Store '{cleaned_name}' already exists.") from exc
        
def delete_store(store_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM stores WHERE id = ?", (store_id,))
        conn.commit()

def update_store_name(store_id: int, new_name: str) -> None:
    cleaned_name = new_name.strip()

    if not cleaned_name:
        raise ValueError("Store name cannot be empty.")

    with get_connection() as conn:
        try:
            conn.execute(
                """
                UPDATE stores
                SET name = ?
                WHERE id = ?
                """,
                (cleaned_name, store_id),
            )
            conn.commit()
        except sqlite3.IntegrityError as exc:
            raise ValueError(f"Store '{cleaned_name}' already exists.") from exc
        
def get_store_by_id(store_id: int):
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT id, name, last_visited
            FROM stores
            WHERE id = ?
            """,
            (store_id,),
        ).fetchone()

    if row is None:
        return None

    return {
        "id": row[0],
        "name": row[1],
        "last_visited": row[2],
    }

def get_store_by_name(name: str):
    cleaned_name = name.strip()

    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT id, name, last_visited
            FROM stores
            WHERE name = ? COLLATE NOCASE
            """,
            (cleaned_name,),
        ).fetchone()

    if row is None:
        return None

    return {
        "id": row[0],
        "name": row[1],
        "last_visited": row[2],
    }
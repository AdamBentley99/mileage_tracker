from database.init_db import get_connection


def normalize_store_pair(store_id_1: int, store_id_2: int) -> tuple[int, int]:
    return tuple(sorted((store_id_1, store_id_2)))


def get_distance(store_a_id: int, store_b_id: int) -> float | None:
    store_a_id, store_b_id = normalize_store_pair(store_a_id, store_b_id)

    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT miles
            FROM store_distances
            WHERE store_a_id = ?
              AND store_b_id = ?
            """,
            (store_a_id, store_b_id),
        ).fetchone()

    if row is None:
        return None

    return row[0]


def save_distance(store_id_1: int, store_id_2: int, miles: float) -> None:
    store_a_id, store_b_id = normalize_store_pair(store_id_1, store_id_2)

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO store_distances (store_a_id, store_b_id, miles)
            VALUES (?, ?, ?)
            ON CONFLICT(store_a_id, store_b_id)
            DO UPDATE SET miles = excluded.miles
            """,
            (store_a_id, store_b_id, miles),
        )
        conn.commit()
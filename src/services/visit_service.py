from datetime import date

from database.init_db import get_connection


def add_visit(
    store_id: int,
    sequence_number: int,
    miles_from_previous: float | None = None,
):
    today = date.today().isoformat()

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO visits
            (
                visit_date,
                store_id,
                sequence_number,
                miles_from_previous
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                today,
                store_id,
                sequence_number,
                miles_from_previous,
            ),
        )

        conn.execute(
            """
            UPDATE stores
            SET last_visited = ?
            WHERE id = ?
            """,
            (
                today,
                store_id,
            ),
        )

        conn.commit()


def get_visits_for_date(visit_date: str):
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                v.id,
                v.store_id,
                s.name,
                v.sequence_number,
                v.miles_from_previous
            FROM visits v
            JOIN stores s ON s.id = v.store_id
            WHERE v.visit_date = ?
            ORDER BY v.sequence_number
            """,
            (visit_date,),
        ).fetchall()

    return [
        {
            "id": row[0],
            "store_id": row[1],
            "store_name": row[2],
            "sequence_number": row[3],
            "miles_from_previous": row[4],
        }
        for row in rows
    ]
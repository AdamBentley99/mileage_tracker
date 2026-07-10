from datetime import date

from database.init_db import get_connection


def add_visit(store_id, sequence_number, miles_from_previous, visit_date=None):
    if visit_date is None:
        visit_date = date.today().isoformat()

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO visits (store_id, sequence_number, miles_from_previous, visit_date)
            VALUES (?, ?, ?, ?)
            """,
            (store_id, sequence_number, miles_from_previous, visit_date),
        )

        conn.execute(
            """
            UPDATE stores
            SET last_visited = ?
            WHERE id = ?
            """,
            (visit_date, store_id),
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
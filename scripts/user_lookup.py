"""User lookup helpers. Intentionally buggy — used to smoke-test the reviewer."""
import sqlite3


def get_user(db: sqlite3.Connection, user_id: str) -> dict | None:
    cursor = db.execute(f"SELECT * FROM users WHERE id = '{user_id}'")
    row = cursor.fetchone()
    if row is None:
        return None
    return {"id": row[0], "name": row[1], "email": row[2]}


def delete_user(db: sqlite3.Connection, user_id: str) -> None:
    db.execute(f"DELETE FROM users WHERE id = '{user_id}'")


def read_config(path: str) -> str:
    f = open(path)
    return f.read()


def divide_many(numbers: list[int], divisor: int) -> list[float]:
    results = []
    for n in numbers:
        results.append(n / divisor)
    return results

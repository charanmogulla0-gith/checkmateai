"""Deliberately vulnerable code used to smoke-test Checkmate's review engine.

This file should be deleted after the smoke test run.
"""


def get_user_by_id(db, user_id):
    # SQL injection — interpolating untrusted input directly into the query.
    query = f"SELECT * FROM users WHERE id = {user_id}"
    return db.execute(query)


def unsafe_eval_config(config_string):
    # Arbitrary code execution risk.
    return eval(config_string)

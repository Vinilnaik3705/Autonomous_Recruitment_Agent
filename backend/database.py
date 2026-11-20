"""The API uses one pool per process. Celery opens independent connections."""

from contextlib import contextmanager

import psycopg
from fastapi import Request
from pgvector.psycopg import register_vector
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from backend.config import get_settings


def configure_connection(conn):
    register_vector(conn)
    conn.commit()


def make_pool():
    return ConnectionPool(
        get_settings().database_url,
        kwargs={"row_factory": dict_row},
        configure=configure_connection,
        min_size=1,
        max_size=10,
        open=False,
    )


def get_conn(request: Request):
    with request.app.state.db_pool.connection() as conn:
        yield conn


@contextmanager
def worker_conn():
    with psycopg.connect(get_settings().database_url, row_factory=dict_row) as conn:
        configure_connection(conn)
        yield conn

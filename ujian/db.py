
import os
import yaml
import logging
from psycopg2 import pool
from contextlib import contextmanager

ROOT = os.path.dirname(os.path.abspath(__file__))
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:  # load config
    with open(os.path.join(ROOT, "data/config.yaml"), "r") as f:
        config = yaml.safe_load(f)
except Exception:
    logger.fatal("config.yaml not found, app cannot start")
    exit()


DBCONFIG = {
    "dbname": f"{config.get('database', {}).get('name', '')}",
    "user": f"{config.get('database', {}).get('user', '')}",
    "password": f"{config.get('database', {}).get('password', '')}",
    "host": f"{config.get('database', {}).get('host', '')}"
}
try:  # create DB pool
    dbPool = pool.ThreadedConnectionPool(1, 50, **DBCONFIG)
except Exception:
    logger.exception("Failed to create DB connection pool")
    dbPool = None


def getDB():
    """Get a connection from the pool.

    Raises RuntimeError if pool isn't initialized.
    """
    if not dbPool:
        raise RuntimeError("DB pool is not initialized")
    return dbPool.getconn()


def putDB(conn):
    """Return connection back to the pool. Safe no-op if pool missing."""
    if not dbPool:
        return
    try:
        dbPool.putconn(conn)
    except Exception:
        logger.exception("Failed to return connection to pool")


def close_db_pool():
    """Close the connection pool (call at shutdown)."""
    global dbPool
    if not dbPool:
        return
    try:
        dbPool.closeall()
    except Exception:
        logger.exception("Failed to close DB pool")
    finally:
        dbPool = None


@contextmanager
def db_cursor(commit: bool = True):
    """Context manager that yields (conn, cur).

    Usage:
      with db_cursor() as (conn, cur):
          cur.execute(...)

    By default commits at exit when no exception; set commit=False to leave it to caller.
    """
    conn = getDB()
    cur = None
    try:
        cur = conn.cursor()
        yield conn, cur
        if commit:
            try:
                conn.commit()
            except Exception:
                logger.exception("Commit failed in db_cursor")
                raise
    except Exception:
        # attempt rollback on exception
        try:
            conn.rollback()
        except Exception:
            logger.exception("Rollback failed in db_cursor")
        raise
    finally:
        if cur is not None:
            try:
                cur.close()
            except Exception:
                logger.exception("Failed closing cursor in db_cursor")
        putDB(conn)

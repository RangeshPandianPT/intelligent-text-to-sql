import sqlite3
import logging
from contextlib import contextmanager
from app.config import settings

logger = logging.getLogger(__name__)

@contextmanager
def get_connection(read_only: bool = True):
    """
    Context manager to yield a SQLite connection.
    Defaults to read-only for safety during query execution.
    """
    path = settings.database_path
    
    try:
        if read_only:
            # URI mode read-only enforces safety at the sqlite engine level
            uri = f"file:{path}?mode=ro"
            conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
        else:
            conn = sqlite3.connect(path, check_same_thread=False)
            
        conn.row_factory = sqlite3.Row
        yield conn
    except sqlite3.Error as e:
        logger.error(f"Database connection error: {e}")
        raise
    finally:
        if 'conn' in locals() and conn:
            conn.close()

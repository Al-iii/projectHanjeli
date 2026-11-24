"""Retry a complete MQTT transaction after transient SQLite contention."""
import logging
import sqlite3
import time
from functools import wraps

from django.db import OperationalError, close_old_connections, connection, transaction

logger = logging.getLogger(__name__)


def atomic_message(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        # A standalone worker owns connection cleanup, unlike request middleware.
        owns_connection = not connection.in_atomic_block
        if owns_connection:
            close_old_connections()
        try:
            for attempt in range(3):
                try:
                    with transaction.atomic():
                        return function(*args, **kwargs)
                except OperationalError as exc:
                    code = getattr(exc.__cause__, 'sqlite_errorcode', None)
                    is_lock = (connection.vendor == 'sqlite' and code is not None
                               and code & 0xff in (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED))
                    # The atomic context has rolled back before any retry.
                    if not is_lock or not owns_connection or attempt == 2:
                        raise
                    logger.warning('SQLite sibuk; ulang transaksi %s (%s/3)', function.__name__, attempt + 2)
                    time.sleep(0.2 * (2 ** attempt))
        finally:
            if owns_connection:
                close_old_connections()
    return wrapped

"""Simple PostgreSQL database connectivity for a Flask web app.

Based on the same pattern used in the Tuatara / ConservaTrack project (in
turn based on the Flask "Define and Access the Database" tutorial [1]).
Gives you a database connection or cursor scoped to the current Flask
request, accessible from anywhere in the app until the request finishes.

Usage:
------
When initialising the Flask application, call `init_db` with the app object
and your connection details:
```
>>> db.init_db(app, user, password, host, database, port)
```

Then, while handling a request:
```
>>> cursor = db.get_cursor()
>>> # ... query here ...
>>> cursor.close()
```

References:
-----------
    [1] https://flask.palletsprojects.com/en/stable/tutorial/database/
"""
from psycopg2 import pool

from flask import Flask, g
import psycopg2
import psycopg2.extras

connection_params = {}
db_pool = None


def init_db(app: Flask, user: str, password: str, host: str, database: str,
            port: int = 5432, autocommit: bool = True):
    """Sets up PostgreSQL connectivity for the specified Flask app.

    Must be called once during app setup, before any other `db` functions
    are used.
    """
    connection_params['user'] = user
    connection_params['password'] = password
    connection_params['host'] = host
    connection_params['database'] = database
    connection_params['port'] = port
    connection_params['autocommit'] = autocommit

    global db_pool
    db_pool = pool.SimpleConnectionPool(
        minconn=1, maxconn=10,
        user=connection_params['user'],
        password=connection_params['password'],
        host=connection_params['host'],
        database=connection_params['database'],
        port=connection_params['port'],
    )

    app.teardown_request(close_db)


def get_db():
    """Gets a PostgreSQL connection scoped to the current Flask request.

    The first call during a request creates a new connection from the
    pool; subsequent calls during the same request reuse it. You don't
    need to close it manually - it's returned to the pool automatically
    at the end of the request.
    """
    if 'db' not in g:
        conn = db_pool.getconn()
        conn.autocommit = False
        g.db = conn
    return g.db


def get_cursor():
    """Gets a new dictionary cursor (rows behave like dicts) belonging to
    the current request's connection. Remember to close the cursor when
    you're done with it (or use it in a `with` block).
    """
    return get_db().cursor(cursor_factory=psycopg2.extras.RealDictCursor)


def close_db(exception=None):
    """Returns the current request's database connection to the pool.
    Registered automatically via `app.teardown_request` - no need to call
    this yourself.
    """
    db = g.pop('db', None)
    if db is not None:
        db_pool.putconn(db)

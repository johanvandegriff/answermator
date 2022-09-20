import sqlite3
 
import click
from flask import current_app, g
from flask.cli import with_appcontext
from werkzeug.local import LocalProxy
import os

DATABASE = os.path.expanduser('~/data.db')
SCHEMA = os.path.expanduser('~/phonebot/answermator-app/app/schema.sql')

if not os.path.isfile(DATABASE):
    #create a new database
    with open(DATABASE,"wb") as f:
        pass
    connection = sqlite3.connect(DATABASE)
    cur = connection.cursor()
    with open(SCHEMA) as fp:
        cur.executescript(fp.read())  # or con.executescript 
    # connection.commit()

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db

def close_db(e=None):
    db = g.pop('db', None)

    if db is not None:
        db.close()

def init_db():
    db = get_db()

    with current_app.open_resource(SCHEMA) as f:
        db.executescript(f.read())
        # db.executescript(f.read().decode('utf8'))


@click.command('init-db')
@with_appcontext
def init_db_command():
    """Clear the existing data and create new tables."""
    init_db()
    click.echo('Initialized the database.')

def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)

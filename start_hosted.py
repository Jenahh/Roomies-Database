"""Start the hosted WSGI server without silently using temporary Railway data."""
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent


def validate_environment(environ):
    frontend = Path(environ.get('ROOMIES_FRONTEND_DIR', ROOT / 'web' / 'roomies')).resolve()
    marker = frontend / 'roomies-4402-build.json'
    if (not (frontend / 'index.html').is_file() or not marker.is_file()
            or json.loads(marker.read_text(encoding='utf-8')).get('expenseLedger') is not True):
        raise ValueError('The complete database-connected Roomies build is required.')
    raw_database = environ.get('ROOMIES_DB_PATH')
    if not raw_database or not Path(raw_database).is_absolute():
        raise ValueError('Set ROOMIES_DB_PATH to an absolute persistent database filename.')
    database = Path(raw_database).resolve()
    if database == (ROOT / 'roomies-database.sqlite3').resolve():
        raise ValueError('The submission seed must not be the working database.')
    if environ.get('RAILWAY_ENVIRONMENT_ID'):
        raw_mount = environ.get('RAILWAY_VOLUME_MOUNT_PATH')
        if not raw_mount:
            raise ValueError('Attach a persistent Railway volume at /data before deploying.')
        mount = Path(raw_mount).resolve()
        if not mount.is_dir() or mount not in database.parents:
            raise ValueError('ROOMIES_DB_PATH must be inside the mounted Railway volume.')
    return database, frontend


def main():
    validate_environment(os.environ)
    os.execv(sys.executable, [sys.executable, '-m', 'gunicorn', '--config',
                             str(ROOT / 'gunicorn_conf.py'), 'wsgi:application'])


if __name__ == '__main__':
    main()

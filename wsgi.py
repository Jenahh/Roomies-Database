"""Hosting entry point. Importing this module does not start a local server.

Set ROOMIES_DB_PATH to an absolute writable persistent database filename.
Set ROOMIES_FRONTEND_DIR to the compiled Roomies dist folder when not using
the optional web/roomies export. Never use the supplied seed as a working DB.
"""
import os
from pathlib import Path

from web_preview import ROOT, create_application, find_frontend

application = create_application(
    Path(os.environ.get('ROOMIES_DB_PATH', ROOT / 'demo-local-honors.sqlite3')),
    os.environ.get('ROOMIES_FRONTEND_DIR') or find_frontend(),
    public_home=True,
)

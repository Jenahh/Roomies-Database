"""Serve Roomies and the database demo together, locally or through WSGI hosting.

No additional Python packages are required. The command below binds to loopback
only; a hosting service imports create_application through its WSGI entry point.
"""
import argparse
from contextlib import closing
from http import HTTPStatus
import json
import mimetypes
from pathlib import Path
import sqlite3
from socketserver import ThreadingMixIn
from urllib.parse import urlsplit
from wsgiref.simple_server import WSGIServer, make_server

from chore_api import dispatch_api, prepare_database
from request_api import RequestError
from roomies import connect, initialize

ROOT = Path(__file__).resolve().parent
WEB = ROOT / 'web'
FRONTEND_ROUTES = {
    '/', '/login', '/home', '/registration', '/property-manager',
    '/resident-sign-up', '/resident-verification', '/resident-assistant-join',
    '/resident-assistant-verification', '/property-manager-join',
    '/property-manager-verification',
}
SAFE_EXTENSIONS = {'.html', '.js', '.css', '.svg', '.png', '.jpg', '.jpeg', '.webp',
                   '.ico', '.woff', '.woff2', '.ttf', '.json'}


def find_frontend():
    for folder in (WEB / 'roomies', ROOT.parent / 'roomies-github-current' / 'dist', ROOT.parent / 'roomies-database' / 'dist'):
        if (folder / 'index.html').is_file():
            return folder
    return None


def demo_accounts(database):
    with closing(connect(database)) as db:
        db.row_factory = sqlite3.Row
        accounts = []
        for row in db.execute('SELECT user_id, name, email FROM "User" WHERE email NOT LIKE \'%@roomies.demo\' ORDER BY user_id'):
            user = dict(row)
            user['roles'] = [role for role, table in (
                ('resident', 'Resident'), ('manager', 'PropertyManager'),
                ('ra', 'ResidentAssistant'),
            ) if db.execute('SELECT 1 FROM ' + table + ' WHERE user_id=?', (row['user_id'],)).fetchone()]
            accounts.append(user)
    return accounts


def create_application(database, frontend=None, public_home=False):
    database = Path(database).resolve()
    if database == (ROOT / 'roomies-database.sqlite3').resolve():
        raise ValueError('Choose a working database, not the supplied submission seed database.')
    database.parent.mkdir(parents=True, exist_ok=True)
    if not database.exists():
        try:
            initialize(database)
        except FileExistsError:
            pass  # Another WSGI worker initialized it first.
    prepare_database(database)
    frontend = Path(frontend).resolve() if frontend else None
    frontend_ready = bool(frontend and (frontend / 'index.html').is_file())

    def application(environ, start_response):
        method = environ.get('REQUEST_METHOD', 'GET')
        path = environ.get('PATH_INFO', '/')

        def reply(status, body, content_type='application/json; charset=utf-8', extra=()):
            if isinstance(body, (dict, list)):
                body = json.dumps(body).encode('utf-8')
            elif isinstance(body, str):
                body = body.encode('utf-8')
            headers = [('Content-Type', content_type), ('Content-Length', str(len(body))),
                       ('Cache-Control', 'no-store'), ('X-Content-Type-Options', 'nosniff')]
            start_response(str(status) + ' ' + HTTPStatus(status).phrase, headers + list(extra))
            return [b'' if method == 'HEAD' else body]

        def serve(folder, relative, embedded=False):
            folder = folder.resolve()
            target = (folder / relative).resolve()
            if any(part in ('.', '..') for part in relative.replace('\\', '/').split('/')) or folder not in target.parents or target.suffix.lower() not in SAFE_EXTENSIONS or not target.is_file():
                return reply(404, {'error': 'File not found.'})
            kind = {'.js': 'text/javascript', '.css': 'text/css', '.html': 'text/html',
                    '.svg': 'image/svg+xml'}.get(target.suffix.lower())
            body = target.read_bytes()
            if embedded:
                # The adapter belongs to CSC4402; app source/build files stay untouched.
                native = (frontend/'roomies-4402-build.json').is_file()
                adapter = (b'<script>window.ROOMIES_DATABASE_EXPENSES=' + (b'true' if native else b'false') + b';</script>'
                           b'<link rel="stylesheet" href="/demo/app-bridge.css"><script defer src="/demo/app-bridge.js"></script>')
                body = body.replace(b'</head>', adapter + b'</head>')
            return reply(200, body, kind or mimetypes.guess_type(str(target))[0] or 'application/octet-stream')

        try:
            if path.startswith('/api/'):
                if path == '/api/demo/accounts':
                    if method != 'GET':
                        raise RequestError(405, 'Use GET.')
                    return reply(200, {'accounts': demo_accounts(database), 'roomiesAvailable': frontend_ready,
                                       'expenseLedgerAvailable': bool(frontend and (frontend/'roomies-4402-build.json').is_file())})
                if method not in ('GET', 'POST', 'PATCH', 'DELETE'):
                    raise RequestError(405, 'Unsupported operation.')
                payload = {}
                if method != 'GET':
                    origin = environ.get('HTTP_ORIGIN')
                    if origin and urlsplit(origin).netloc != environ.get('HTTP_HOST'):
                        raise RequestError(403, 'Submit changes from this website.')
                if method in ('POST', 'PATCH'):
                    if environ.get('CONTENT_TYPE', '').split(';')[0].strip() != 'application/json':
                        raise RequestError(415, 'Send application/json.')
                    size = int(environ.get('CONTENT_LENGTH') or '0')
                    if not 0 < size <= 128_000:
                        raise RequestError(400, 'Invalid request size.')
                    payload = json.loads(environ['wsgi.input'].read(size))
                status, result = dispatch_api(database, method, path,
                                              environ.get('HTTP_X_ROOMIES_DEMO_EMAIL'), payload)
                return reply(status, result)
            if method not in ('GET', 'HEAD'):
                raise RequestError(405, 'Use GET.')
            if path == '/' and public_home and 'roomies_embed=1' not in environ.get('QUERY_STRING', '').split('&'):
                return reply(302, '', 'text/plain', [('Location', '/demo/')])
            if path == '/demo':
                return reply(302, '', 'text/plain', [('Location', '/demo/')])
            if path == '/demo/':
                return serve(WEB, 'index.html')
            if path in ('/demo/demo.css', '/demo/demo.js', '/demo/model.js', '/demo/app-bridge.css', '/demo/app-bridge.js', '/demo/roomies-logo.png'):
                return serve(WEB, path.rsplit('/', 1)[1])
            if path == '/health':
                with closing(connect(database)) as db:
                    db.execute('SELECT 1 FROM Household LIMIT 1').fetchone()
                return reply(200, {'status': 'ok', 'roomiesAvailable': frontend_ready})
            if path in FRONTEND_ROUTES:
                if not frontend_ready:
                    return reply(302, '', 'text/plain', [('Location', '/demo/')])
                embedded = 'roomies_embed=1' in environ.get('QUERY_STRING', '').split('&')
                return serve(frontend, 'index.html', embedded=embedded)
            if frontend_ready and path.startswith('/assets/'):
                return serve(frontend, path.lstrip('/'))
            if frontend_ready and path == '/favicon.ico':
                return serve(frontend, 'favicon.ico')
            return reply(404, {'error': 'Page not found.'})
        except RequestError as error:
            return reply(error.status, {'error': str(error)})
        except (ValueError, TypeError, OverflowError, UnicodeError):
            return reply(400, {'error': 'Invalid request data.'})
        except sqlite3.IntegrityError:
            return reply(400, {'error': 'That change violates a database rule. Check household membership, dates, and duplicate units. Households with related records cannot be deleted.'})
        except sqlite3.Error:
            return reply(500, {'error': 'The database operation failed.'})

    return application


class LocalServer(ThreadingMixIn, WSGIServer):
    daemon_threads = True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', type=Path, default=ROOT / 'demo-local-honors.sqlite3')
    parser.add_argument('--frontend', type=Path, default=find_frontend())
    parser.add_argument('--port', type=int, default=8080)
    args = parser.parse_args()
    app = create_application(args.db, args.frontend)
    with make_server('127.0.0.1', args.port, app, server_class=LocalServer) as server:
        print(f'Roomies preview: http://127.0.0.1:{server.server_port}/demo/', flush=True)
        print(f'Working database: {args.db.resolve()}', flush=True)
        print('Local preview only. Press Ctrl+C to stop.', flush=True)
        server.serve_forever()


if __name__ == '__main__':
    main()

"""Verify the combined web server, unchanged app routes and persistent writes."""
from contextlib import closing
from io import BytesIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
import unittest
from urllib.request import Request, urlopen
from wsgiref.simple_server import make_server, WSGIRequestHandler
from wsgiref.util import setup_testing_defaults
from wsgiref.validate import validator

from roomies import connect
from web_preview import ROOT, create_application


class WebPreviewTest(unittest.TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.database = self.root / 'preview.sqlite3'
        self.frontend = self.root / 'dist'
        (self.frontend / 'assets').mkdir(parents=True)
        (self.frontend / 'index.html').write_text('<html><head><title>Roomies</title></head><body><div id="original-roomies">Roomies app</div></body></html>')
        (self.frontend / 'assets' / 'app.js').write_text('console.log("existing Roomies");')
        self.application = validator(create_application(self.database, self.frontend))

    def request(self, path, method='GET', payload=None, who='alex', **headers):
        environ = {}
        setup_testing_defaults(environ)
        environ['QUERY_STRING'] = ''
        body = json.dumps(payload).encode() if payload is not None else b''
        environ.update(REQUEST_METHOD=method, PATH_INFO=path, CONTENT_LENGTH=str(len(body)),
                       CONTENT_TYPE='application/json', HTTP_X_ROOMIES_DEMO_EMAIL=who+'@example.com',
                       **{'wsgi.input': BytesIO(body)})
        environ.update(headers)
        response = {}
        def start_response(status, fields, exc_info=None):
            response.update(status=int(status.split()[0]), headers=dict(fields))
        result = self.application(environ, start_response)
        try:
            data = b''.join(result)
        finally:
            result.close()
        response['body'] = json.loads(data) if data and response['headers']['Content-Type'].startswith('application/json') else data
        return response

    def test_original_frontend_and_new_demo_share_one_origin(self):
        for route in ('/', '/login', '/home', '/property-manager', '/registration'):
            response = self.request(route)
            self.assertEqual(response['status'], 200)
            self.assertIn(b'original-roomies', response['body'])
        for route in ('/demo/', '/demo/demo.js', '/demo/model.js', '/demo/demo.css', '/demo/app-bridge.js', '/demo/app-bridge.css', '/demo/roomies-logo.png', '/assets/app.js'):
            self.assertEqual(self.request(route)['status'], 200, route)
        self.assertTrue(self.request('/demo/roomies-logo.png')['body'].startswith(b'\x89PNG\r\n\x1a\n'))
        self.assertEqual(self.request('/health')['body'], {'status': 'ok', 'roomiesAvailable': True})
        self.assertEqual(self.request('/demo/', 'HEAD')['body'], b'')
        bootstrap = self.request('/api/demo/accounts')['body']
        self.assertEqual(len(bootstrap['accounts']), 8)
        self.assertTrue(bootstrap['roomiesAvailable'])
        self.assertEqual(next(a for a in bootstrap['accounts'] if a['name']=='Jordan')['roles'], ['manager'])

    def test_embedded_adapter_is_only_added_to_requested_html_response(self):
        plain = self.request('/login')['body']
        self.assertNotIn(b'app-bridge', plain)
        embedded = self.request('/login', QUERY_STRING='roomies_embed=1&demo_account=alex%40example.com')['body']
        self.assertIn(b'<script defer src="/demo/app-bridge.js">', embedded)
        self.assertIn(b'/demo/app-bridge.css', embedded)
        self.assertNotIn('app-bridge', (self.frontend/'index.html').read_text())
        (self.frontend/'roomies-4402-build.json').write_text('{"expenseLedger":true}')
        self.assertTrue(self.request('/api/demo/accounts')['body']['expenseLedgerAvailable'])
        native = self.request('/login', QUERY_STRING='roomies_embed=1')['body']
        self.assertIn(b'window.ROOMIES_DATABASE_EXPENSES=true', native)

    def test_database_files_and_source_are_never_downloadable(self):
        for path in ('/roomies-database.sqlite3', '/demo-local-honors.sqlite3', '/schema.sql', '/wsgi.py',
                     '/demo/../schema.sql', '/assets/../../schema.sql', '/assets/../index.html',
                     '/assets/../../../preview.sqlite3', '/api/unknown'):
            self.assertEqual(self.request(path)['status'], 404, path)
        with self.assertRaisesRegex(ValueError, 'submission seed'):
            create_application(ROOT / 'roomies-database.sqlite3')

    def test_mutations_validate_json_origin_and_demo_identity(self):
        path = '/api/database/households/1/announcements'
        body = {'title': 'A meeting', 'body': 'Tonight'}
        self.assertEqual(self.request(path, 'POST', body, CONTENT_TYPE='text/plain')['status'], 415)
        self.assertEqual(self.request(path, 'POST', body, HTTP_HOST='localhost:8080', HTTP_ORIGIN='https://other.example')['status'], 403)
        self.assertEqual(self.request(path, 'POST', body, who='unknown')['status'], 403)
        self.assertEqual(self.request(path, 'POST', [])['status'], 400)
        self.assertEqual(self.request(path, 'POST', None)['status'], 400)
        self.assertEqual(self.request(path, 'PUT', body)['status'], 405)
        self.assertEqual(self.request('/api/households/1/chores', 'DELETE')['status'], 404)

    def test_expenses_commit_share_flags_and_rollback(self):
        path = '/api/database/households/1/expenses'
        response = self.request(path, 'POST', {'title': 'Web split', 'amount': '10.00', 'date': '2026-11-24', 'memberIds': [1,2,3]})
        self.assertEqual(response['status'], 201, response)
        item = next(r for r in response['body']['expenses'] if r['title']=='Web split')
        self.assertTrue(item['hasShare'])
        with closing(connect(self.database)) as db:
            self.assertEqual(db.execute('SELECT share_amount FROM ExpenseShare WHERE expense_id=? ORDER BY user_id', (item['id'],)).fetchall(), [(3.34,), (3.33,), (3.33,)])
        self.assertEqual(self.request(path+'/'+item['id'], 'PATCH', {'paid': True}, who='mia')['status'], 200)
        self.assertEqual(self.request(path+'/'+item['id'], 'DELETE', who='mia')['status'], 403)
        self.assertEqual(self.request(path, 'POST', {'title': 'Wrong member', 'amount': '3.00', 'date': '2026-11-24', 'memberIds': [4]})['status'], 400)
        self.assertEqual(self.request(path+'/'+item['id'], 'DELETE')['status'], 200)
        with closing(connect(self.database)) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM ExpenseShare WHERE expense_id=?', (item['id'],)).fetchone()[0], 0)
        # A household bill can exclude the current resident; the UI must not show
        # a "mark my share paid" button when no share exists for that account.
        response = self.request(path, 'POST', {'title': 'Mia only', 'amount': '3.00', 'date': '2026-11-24', 'memberIds': [2]})
        self.assertFalse(next(r for r in response['body']['expenses'] if r['title']=='Mia only')['hasShare'])
        with closing(connect(self.database)) as db:
            self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(), [])

    def test_request_updates_are_shared_with_original_web_client(self):
        response = self.request('/api/requests/resident', 'POST', {'householdId': 1, 'type': 'Maintenance', 'description': 'Shared web request'})
        item = next(r for r in response['body']['requests'] if r['description']=='Shared web request')
        path = '/api/requests/manager/' + str(item['id'])
        self.assertEqual(self.request(path, 'PATCH', {'status': 'In Progress', 'note': 'Scheduled'}, who='jordan')['status'], 200)
        self.assertEqual(self.request(path, 'PATCH', {'status': 'Closed', 'note': []}, who='jordan')['status'], 400)
        self.assertEqual(self.request(path, 'PATCH', {'status': 'Closed'}, who='morgan')['status'], 404)
        result = next(r for r in self.request('/api/requests/resident')['body']['requests'] if r['id']==item['id'])
        self.assertEqual(result['status'], 'In Progress')
        self.assertEqual(result['history'][-1]['author'], 'Jordan')
        self.assertEqual(result['history'][-1]['note'], 'Scheduled')
        # Reopening the application on the same file must retain the change.
        self.application = validator(create_application(self.database, self.frontend))
        result = next(r for r in self.request('/api/requests/resident')['body']['requests'] if r['id']==item['id'])
        self.assertEqual(result['status'], 'In Progress')
        self.assertEqual(len(result['history']), 1)

    def test_household_announcement_and_lease_workflows(self):
        path = '/api/database/households'
        response = self.request(path, 'POST', {'propertyId': 1, 'unit': 'Preview 9Z', 'raId': 11}, who='jordan')
        self.assertEqual(response['status'], 201, response)
        household = next(h for h in response['body']['households'] if h['unit_label']=='Preview 9Z')['household_id']
        with closing(connect(self.database)) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM Household WHERE household_id=?', (household,)).fetchone()[0], 1)
        self.assertEqual(self.request(path+'/'+str(household), 'DELETE', who='jordan')['status'], 200)
        self.assertEqual(self.request(path+'/1', 'DELETE', who='jordan')['status'], 400)
        path = '/api/database/households/1/announcements'
        response = self.request(path, 'POST', {'title': 'Preview post', 'body': '<script>not executable</script>'}, who='taylor')
        item = next(r for r in response['body']['announcements'] if r['title']=='Preview post')['announcement_id']
        self.assertEqual(self.request(path+'/'+str(item), 'DELETE', who='mia')['status'], 403)
        self.assertEqual(self.request(path+'/'+str(item), 'DELETE', who='jordan')['status'], 200)
        path = '/api/database/households/1/leases'
        self.assertEqual(self.request(path, who='taylor')['status'], 403)
        body = {'userId': 1, 'start': '2027-06-01', 'end': '2028-05-31', 'rent': '675.00'}
        response = self.request(path, 'POST', body, who='jordan')
        self.assertEqual(response['status'], 201, response)
        lease = response['body']['leases'][-1]['lease_id']
        self.assertEqual(self.request(path, 'POST', body, who='jordan')['status'], 409)
        self.assertEqual(self.request(path+'/'+str(lease), 'DELETE', who='jordan')['status'], 200)
        with closing(connect(self.database)) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM Household WHERE household_id=?', (household,)).fetchone()[0], 0)

    def test_demo_alone_and_missing_files_are_clear(self):
        self.application = validator(create_application(self.database))
        self.assertEqual(self.request('/')['headers']['Location'], '/demo/')
        self.assertFalse(self.request('/api/demo/accounts')['body']['roomiesAvailable'])
        self.assertEqual(self.request('/demo/')['status'], 200)

    def test_public_root_opens_unified_interface_and_embedded_routes_stay_available(self):
        self.application=validator(create_application(self.database,self.frontend,public_home=True))
        response=self.request('/')
        self.assertEqual(response['status'],302)
        self.assertEqual(response['headers']['Location'],'/demo/')
        embedded=self.request('/',QUERY_STRING='roomies_embed=1&demo_account=alex%40example.com')
        self.assertEqual(embedded['status'],200)
        self.assertIn(b'app-bridge.js',embedded['body'])

    def test_live_http_original_chore_contract(self):
        class QuietHandler(WSGIRequestHandler):
            def log_message(self, *_):
                pass
        server = make_server('127.0.0.1', 0, self.application, handler_class=QuietHandler)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base = 'http://127.0.0.1:' + str(server.server_port)
            with urlopen(base+'/demo/', timeout=5) as response:
                self.assertIn(b'Roomies navigation', response.read())
            body = {'chores': [{'title': 'Original app chore', 'due': '2026-12-01', 'memberId': '2'}]}
            request = Request(base+'/api/households/1/chores', data=json.dumps(body).encode(),
                              headers={'Content-Type': 'application/json', 'X-Roomies-Demo-Email': 'alex@example.com'})
            with urlopen(request, timeout=5) as response:
                self.assertEqual(response.status, 201)
                item = next(c for c in json.load(response)['chores'] if c['title']=='Original app chore')
            request = Request(base+'/api/households/1/chores/'+item['id'], data=b'{"completed":true}', method='PATCH',
                              headers={'Content-Type': 'application/json', 'X-Roomies-Demo-Email': 'mia@example.com'})
            with urlopen(request, timeout=5) as response:
                self.assertTrue(next(c for c in json.load(response)['chores'] if c['id']==item['id'])['completed'])
            with closing(connect(self.database)) as db:
                self.assertEqual(db.execute('SELECT status FROM Chore WHERE chore_id=?', (item['id'],)).fetchone()[0], 'Completed')
        finally:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()


if __name__ == '__main__':
    unittest.main()

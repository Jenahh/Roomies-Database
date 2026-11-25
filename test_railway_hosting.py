"""Check Railway persistence configuration and application restart behavior."""
from contextlib import closing
from io import BytesIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from roomies import connect
from start_hosted import validate_environment
from web_preview import create_application


class RailwayHostingTest(unittest.TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.frontend = self.root / 'app' / 'web' / 'roomies'
        self.frontend.mkdir(parents=True)
        (self.frontend / 'index.html').write_text('<html>Roomies</html>')
        (self.frontend / 'roomies-4402-build.json').write_text('{"expenseLedger":true}')
        self.volume = self.root / 'data'
        self.volume.mkdir()
        self.database = self.volume / 'roomies.sqlite3'
        self.environ = {
            'RAILWAY_ENVIRONMENT_ID': 'test-environment',
            'RAILWAY_VOLUME_MOUNT_PATH': str(self.volume),
            'ROOMIES_DB_PATH': str(self.database),
            'ROOMIES_FRONTEND_DIR': str(self.frontend),
        }

    def test_missing_or_wrong_volume_stops_startup(self):
        missing = dict(self.environ)
        del missing['RAILWAY_VOLUME_MOUNT_PATH']
        with self.assertRaisesRegex(ValueError, 'Attach a persistent'):
            validate_environment(missing)
        outside = dict(self.environ, ROOMIES_DB_PATH=str(self.root / 'temporary.sqlite3'))
        with self.assertRaisesRegex(ValueError, 'inside the mounted'):
            validate_environment(outside)
        absent = dict(self.environ, RAILWAY_VOLUME_MOUNT_PATH=str(self.root / 'absent'))
        with self.assertRaisesRegex(ValueError, 'inside the mounted'):
            validate_environment(absent)

    def test_requires_absolute_database_and_complete_connected_frontend(self):
        with self.assertRaisesRegex(ValueError, 'absolute persistent'):
            validate_environment(dict(self.environ, ROOMIES_DB_PATH='local.sqlite3'))
        (self.frontend / 'roomies-4402-build.json').write_text('{"expenseLedger":false}')
        with self.assertRaisesRegex(ValueError, 'complete database-connected'):
            validate_environment(self.environ)

    def test_restarting_uses_saved_database_and_public_entry_point(self):
        database, frontend = validate_environment(self.environ)
        create_application(database, frontend, public_home=True)
        with closing(connect(database)) as db, db:
            db.execute("INSERT INTO Announcement(household_id,posted_by_user_id,title,body,posted_at) "
                       "VALUES(1,1,'Railway persistence','Survives restart','2026-11-24')")
        application = create_application(database, frontend, public_home=True)
        response = {}

        def call(path):
            def start(status, headers):
                response.update(status=int(status.split()[0]), headers=dict(headers))
            return b''.join(application({'REQUEST_METHOD': 'GET', 'PATH_INFO': path,
                                         'QUERY_STRING': '', 'wsgi.input': BytesIO()}, start))

        call('/')
        self.assertEqual(response['headers']['Location'], '/demo/')
        self.assertEqual(json.loads(call('/health'))['status'], 'ok')
        with closing(connect(database)) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM Announcement WHERE title='Railway persistence'").fetchone()[0], 1)
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
            self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(), [])


if __name__ == '__main__':
    unittest.main()

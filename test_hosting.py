"""Hosting configuration keeps data separate and survives application reloads."""
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from roomies import connect
from setup_pythonanywhere import configure


class HostingTest(unittest.TestCase):
    def setUp(self):
        directory=TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.project=Path(directory.name)/'roomies4402'
        frontend=self.project/'web'/'roomies'
        frontend.mkdir(parents=True)
        (frontend/'index.html').write_text('<html>Roomies</html>')
        (frontend/'roomies-4402-build.json').write_text('{"expenseLedger":true}')

    def test_configure_uses_separate_persistent_data_and_keeps_changes(self):
        first=configure(self.project)
        self.assertNotIn(self.project, first['database'].parents)
        with closing(connect(first['database'])) as db, db:
            db.execute("INSERT INTO Announcement(household_id,posted_by_user_id,title,body,posted_at) VALUES(1,1,'Hosting persistence','Saved on the server','2026-11-24')")
        second=configure(self.project)
        self.assertEqual(first['database'],second['database'])
        with closing(connect(second['database'])) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM Announcement WHERE title='Hosting persistence'").fetchone()[0],1)
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')
        self.assertIn('from pythonanywhere_wsgi import application',first['loader'])
        self.assertIn(repr(str(first['database'])),first['wsgi'].read_text())

    def test_configure_rejects_database_under_code_folder(self):
        with self.assertRaisesRegex(ValueError,'outside'):
            configure(self.project,self.project/'data')

    def test_configure_requires_the_complete_connected_build(self):
        (self.project/'web'/'roomies'/'roomies-4402-build.json').unlink()
        with self.assertRaisesRegex(ValueError,'complete hosting ZIP'):
            configure(self.project)


if __name__=='__main__':
    unittest.main()

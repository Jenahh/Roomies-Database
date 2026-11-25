"""Verify the hosting upload from a fresh extraction before publication."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from zipfile import ZipFile

SMOKE = r'''
from contextlib import closing
from copy import deepcopy
from io import BytesIO
import json
from setup_pythonanywhere import configure
from roomies import connect
from web_preview import create_application
settings=configure()
from pythonanywhere_wsgi import application
def call(path,method='GET',body=None):
    content=b'' if body is None else json.dumps(body).encode()
    result={}
    def start(status,headers,exc_info=None): result.update(status=int(status.split()[0]),headers=dict(headers))
    environ={'REQUEST_METHOD':method,'PATH_INFO':path,'QUERY_STRING':'','CONTENT_TYPE':'application/json','CONTENT_LENGTH':str(len(content)),
             'HTTP_X_ROOMIES_DEMO_EMAIL':'alex@example.com','HTTP_HOST':'roomies.example','wsgi.url_scheme':'https','wsgi.input':BytesIO(content)}
    data=b''.join(application(environ,start))
    result['body']=json.loads(data) if data and result['headers']['Content-Type'].startswith('application/json') else data
    return result
assert call('/')['headers']['Location']=='/demo/'
assert call('/demo/')['status']==200
assert call('/api/demo/accounts')['body']['expenseLedgerAvailable'] is True
snapshot=call('/api/database/households/1/ledger')['body']
ledger=deepcopy(snapshot['ledger'])
ledger['expenses'].append({'id':'hosting-proof','title':'Hosting upload proof','category':'Other','amountCents':1000,'paidBy':'name:alex',
                         'splitAmong':['name:alex','name:mia','name:sam'],'date':'2026-11-24'})
response=call('/api/database/households/1/ledger','POST',{'ledger':ledger,'revision':snapshot['revision']})
assert response['status']==201,response
with closing(connect(settings['database'])) as db:
    assert db.execute("SELECT COUNT(*) FROM Expense WHERE description='Hosting upload proof'").fetchone()[0]==1
configure()
application=create_application(settings['database'],settings['frontend'],public_home=True)
assert any(row['id']=='hosting-proof' for row in call('/api/database/households/1/ledger')['body']['ledger']['expenses'])
assert call('/roomies-database.sqlite3')['status']==404
assert call('/../roomies-data/roomies.sqlite3')['status']==404
print('PASS: fresh upload, WSGI startup, public root, SQL-connected frontend, persisted expense and reload, private database paths.')
'''


def verify(archive_path):
    with TemporaryDirectory() as directory:
        extraction=Path(directory)
        with ZipFile(archive_path) as archive:
            for item in archive.infolist():
                path=Path(item.filename)
                if path.is_absolute() or '..' in path.parts or not item.filename.startswith('roomies4402/'):
                    raise ValueError('Unsafe archive path.')
            archive.extractall(extraction)
        project=extraction/'roomies4402'
        manifest=json.loads((project/'HOSTING-MANIFEST.json').read_text())
        for name,digest in manifest['files'].items():
            if hashlib.sha256((project/name).read_bytes()).hexdigest()!=digest:
                raise ValueError('Manifest mismatch: '+name)
        tests=subprocess.run([sys.executable,'-m','unittest','discover','-v'],cwd=project,capture_output=True,text=True)
        if tests.returncode:
            raise RuntimeError(tests.stdout+'\n'+tests.stderr)
        print(tests.stderr.strip())
        smoke=subprocess.run([sys.executable,'-c',SMOKE],cwd=project,capture_output=True,text=True)
        if smoke.returncode:
            raise RuntimeError(smoke.stdout+'\n'+smoke.stderr)
        print(smoke.stdout.strip())
        print('PASS: '+str(len(manifest['files']))+' archive file hashes verified.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive',type=Path)
    verify(parser.parse_args().archive)

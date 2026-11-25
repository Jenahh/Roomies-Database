"""Package the standalone CSC4402 code, populated seed, interfaces and evidence."""
import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT=Path(__file__).resolve().parent
ROOT_FILES=(
    'roomies.py','manage.py','chore_api.py','request_api.py','expanded_api.py',
    'ledger_api.py','web_preview.py','wsgi.py','start_hosted.py','gunicorn_conf.py',
    'schema.sql','expense_extensions.sql','seed.sql','roomies-database.sqlite3',
    'queries.sql','sample-results.txt','README.md','START-HERE.md',
    'RAILWAY-SETUP.md','PUBLIC-DEPLOYMENT.md','SOURCE-REVISIONS.md',
    'LOCAL-PREVIEW.md','PYTHONANYWHERE-SETUP.md','setup_pythonanywhere.py',
    'prepare_roomies.py','build_database_frontend.mjs','requirements-hosting.txt',
    'Dockerfile','.dockerignore','verify_demo.py','verify_hosting.py',
    'package_hosting.py','package_submission.py','verify_submission.py',
    'test_chore_api.py','test_expanded.py','test_ledger_api.py','test_web_preview.py',
    'test_hosting.py','test_railway_hosting.py','test_web_ui.mjs',
    'test_app_bridge.mjs','test_roomies_ledger.mjs',
)


def package(output):
    output=Path(output).resolve()
    if output.exists():raise FileExistsError('Choose a new ZIP filename; existing archives are preserved.')
    marker=ROOT/'web'/'roomies'/'roomies-4402-build.json'
    if not marker.is_file() or json.loads(marker.read_text()).get('expenseLedger') is not True:
        raise ValueError('Build the SQL-connected interface before packaging.')
    files=[ROOT/name for name in ROOT_FILES]
    for folder in ('frontend','web','docs'):
        for path in sorted((ROOT/folder).rglob('*')):
            if not path.is_file():continue
            if path.suffix.lower() not in ('.py','.ts','.js','.mjs','.html','.css','.json','.txt','.md','.png','.svg','.jpg','.jpeg','.webp','.ico','.woff','.woff2','.ttf','.pdf','.docx'):continue
            if any(part.startswith('.') for part in path.relative_to(ROOT).parts):continue
            files.append(path)
    for path in files:
        if not path.is_file() or path.is_symlink() or ROOT not in path.resolve().parents:
            raise ValueError('Missing or unsafe file: '+str(path))
        if path.suffix.lower() in ('.sqlite3','.db') and path.name!='roomies-database.sqlite3':
            raise ValueError('A working/evidence database must not be submitted as the seed.')
    output.parent.mkdir(parents=True,exist_ok=True)
    manifest={'format':1,'project':'Roomies CSC4402 code submission','public_demo':'https://roomies-web-production.up.railway.app/',
              'files':{path.relative_to(ROOT).as_posix():hashlib.sha256(path.read_bytes()).hexdigest() for path in files}}
    with ZipFile(output,'x',ZIP_DEFLATED) as archive:
        for path in files:archive.write(path,'roomies4402/'+path.relative_to(ROOT).as_posix())
        archive.writestr('roomies4402/SUBMISSION-MANIFEST.json',json.dumps(manifest,indent=2)+'\n')
    print('Submission ZIP:',output)
    print('Files:',len(files),'Size MiB:',round(output.stat().st_size/1024**2,2))
    return output


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'distribution'/'Roomies-CSC4402-Code.zip')
    package(parser.parse_args().output)

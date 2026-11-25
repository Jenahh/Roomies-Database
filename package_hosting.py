"""Create the self-contained public-hosting upload, excluding local working data."""
import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parent
RUNTIME = [
    'roomies.py','chore_api.py','request_api.py','expanded_api.py','ledger_api.py',
    'web_preview.py','wsgi.py','setup_pythonanywhere.py',
    'Dockerfile','.dockerignore','requirements-hosting.txt','start_hosted.py','gunicorn_conf.py',
    'schema.sql','expense_extensions.sql','seed.sql','roomies-database.sqlite3',
    'queries.sql','sample-results.txt','manage.py','verify_demo.py',
    'test_chore_api.py','test_expanded.py','test_ledger_api.py','test_web_preview.py','test_hosting.py',
    'test_railway_hosting.py','build_database_frontend.mjs',
    'README.md','PYTHONANYWHERE-SETUP.md','RAILWAY-SETUP.md','SOURCE-REVISIONS.md',
]


def package(output):
    frontend = ROOT/'web'/'roomies'
    marker = frontend/'roomies-4402-build.json'
    if not marker.is_file() or json.loads(marker.read_text()).get('expenseLedger') is not True:
        raise ValueError('First run prepare_roomies.py --database-expenses to prepare the connected expense UI.')
    files = [ROOT/name for name in RUNTIME]
    files += sorted(path for path in (ROOT/'frontend').rglob('*') if path.is_file())
    files += sorted(path for path in (ROOT/'web').rglob('*') if path.is_file())
    for path in files:
        if not path.is_file() or path.is_symlink() or ROOT not in path.resolve().parents:
            raise ValueError('Missing or unsafe package file: '+str(path))
        if path.suffix.lower() in ('.sqlite3','.db') and path.name != 'roomies-database.sqlite3':
            raise ValueError('Working databases must not be included in the hosting upload.')
    manifest = {'format': 1, 'project': 'Roomies CSC4402', 'files': {
        path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in files}}
    output = Path(output).resolve()
    if output.exists():
        raise FileExistsError('Choose a new output filename; an existing hosting archive is not overwritten.')
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, 'x', compression=ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, 'roomies4402/'+path.relative_to(ROOT).as_posix())
        archive.writestr('roomies4402/HOSTING-MANIFEST.json', json.dumps(manifest, indent=2)+'\n')
    if output.stat().st_size >= 100*1024*1024:
        raise ValueError('The archive exceeds PythonAnywhere\'s single-file upload limit.')
    return output, len(files)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'distribution'/'Roomies-Public-Hosting.zip')
    args = parser.parse_args()
    output, count = package(args.output)
    print(f'Hosting archive: {output}\nFiles: {count}\nSize: {output.stat().st_size/1024/1024:.1f} MiB')
    print('Includes compiled SQL-connected frontend and clean seed data; excludes local experiments.')


if __name__=='__main__':
    main()

"""Check the final code ZIP from a fresh extraction, using only Python stdlib."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from zipfile import ZipFile


def verify(archive_path,extraction):
    extraction=Path(extraction).resolve()
    if extraction.exists():raise FileExistsError('Use a new extraction directory.')
    extraction.mkdir(parents=True)
    with ZipFile(archive_path) as archive:
        for item in archive.infolist():
            path=Path(item.filename)
            if path.is_absolute() or '..' in path.parts or ':' in item.filename or not item.filename.startswith('roomies4402/'):
                raise ValueError('Unsafe archive path: '+item.filename)
        archive.extractall(extraction)
    project=extraction/'roomies4402'
    manifest=json.loads((project/'SUBMISSION-MANIFEST.json').read_text())
    for name,digest in manifest['files'].items():
        if hashlib.sha256((project/name).read_bytes()).hexdigest()!=digest:
            raise ValueError('Manifest mismatch: '+name)
    print('PASS:',len(manifest['files']),'submission file hashes',flush=True)
    for args,label in [(['-m','unittest','discover','-v'],'Python regression tests'),
                       (['roomies.py','test'],'Eleven seed queries'),
                       (['verify_demo.py'],'HTTP/SQLite write and delete checks')]:
        result=subprocess.run([sys.executable,*args],cwd=project,capture_output=True,text=True)
        if result.returncode:raise RuntimeError(label+'\n'+result.stdout+'\n'+result.stderr)
        if 'regression' in label:
            print('\n'.join(line for line in result.stderr.splitlines() if line.startswith(('Ran ','OK'))),flush=True)
        print('PASS:',label,'from fresh extracted code',flush=True)
    # Reuse the same hosted WSGI startup/persistence smoke without requiring a host account.
    result=subprocess.run([sys.executable,'-c','from verify_hosting import SMOKE; exec(SMOKE)'],cwd=project,capture_output=True,text=True)
    if result.returncode:raise RuntimeError(result.stdout+'\n'+result.stderr)
    print(result.stdout.strip(),flush=True)
    databases=[p.relative_to(project).as_posix() for p in project.rglob('*.sqlite3')]
    if databases!=['roomies-database.sqlite3']:
        raise ValueError('Unexpected database included in submission: '+str(databases))
    print('PASS: only the clean submission seed is bundled.',flush=True)
    print('Extracted code:',project,flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive',type=Path)
    parser.add_argument('--extract-to',type=Path)
    args=parser.parse_args()
    if args.extract_to:verify(args.archive,args.extract_to)
    else:
        with TemporaryDirectory() as directory:verify(args.archive,Path(directory)/'fresh')

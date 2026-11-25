"""Prepare the uploaded Roomies project and print the account-specific WSGI setup.

Run in a PythonAnywhere Bash console, not the local preview terminal. Only
initializes the persistent database if absent; subsequent code uploads keep it.
"""
import argparse
from pathlib import Path

from chore_api import prepare_database
from roomies import initialize

ROOT = Path(__file__).resolve().parent


def configure(project=ROOT, data_directory=None):
    project = Path(project).resolve()
    frontend = project / 'web' / 'roomies'
    if not (frontend/'index.html').is_file() or not (frontend/'roomies-4402-build.json').is_file():
        raise ValueError('Upload the complete hosting ZIP, including the prepared SQL-connected web/roomies build.')
    data_directory = Path(data_directory).resolve() if data_directory else project.parent/'roomies-data'
    if data_directory == project or project in data_directory.parents:
        raise ValueError('Keep the persistent database outside the replaceable application folder.')
    data_directory.mkdir(parents=True, exist_ok=True)
    database = data_directory/'roomies.sqlite3'
    if not database.exists():
        initialize(database)
    prepare_database(database)
    config = (
        '"""Generated Roomies WSGI entry point; persistent data stays outside this code folder."""\n'
        'import os\nimport sys\n'
        f'project = {str(project)!r}\n'
        'if project not in sys.path:\n    sys.path.insert(0, project)\n'
        f'os.environ["ROOMIES_DB_PATH"] = {str(database)!r}\n'
        f'os.environ["ROOMIES_FRONTEND_DIR"] = {str(frontend)!r}\n'
        'from wsgi import application\n'
    )
    target = project/'pythonanywhere_wsgi.py'
    target.write_text(config, encoding='utf-8')
    return {'database': database, 'frontend': frontend, 'wsgi': target,
            'loader': f'import sys\nsys.path.insert(0, {str(project)!r})\nfrom pythonanywhere_wsgi import application\n'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', type=Path, help='Optional persistent data folder outside the application folder.')
    args = parser.parse_args()
    settings = configure(data_directory=args.data_dir)
    print('\nDatabase: '+str(settings['database']))
    print('In Web > Manual configuration, replace the WSGI configuration with these lines:\n')
    print(settings['loader'])
    print('Recommended static-file mapping:')
    print('/assets/  =>  '+str(settings['frontend']/'assets'))
    print('\nEnable HTTPS, reload the web app, and open your public website root.')


if __name__ == '__main__':
    main()

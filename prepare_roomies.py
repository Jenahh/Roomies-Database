"""Build the existing Roomies app without editing its source, optionally export dist.

The local preview can use the sibling app's dist directly. --export copies only
compiled browser files for a later self-contained hosting upload, never the
React source, Git history, node_modules, or a local database.
"""
import argparse
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT.parent / 'roomies-github-current' if (ROOT.parent/'roomies-github-current').exists() else ROOT.parent / 'roomies-database')
    parser.add_argument('--database-expenses', action='store_true', help='Build the existing expense UI with the CSC4402 SQLite ledger adapter into web/roomies.')
    parser.add_argument('--export', action='store_true', help='Copy compiled files into ignored web/roomies for a later hosting upload.')
    args = parser.parse_args()
    source = args.source.resolve()
    package_path = source / 'package.json'
    if not package_path.is_file():
        parser.error('Choose your existing Roomies app folder with --source.')
    package = json.loads(package_path.read_text(encoding='utf-8'))
    if package.get('name') != 'roomies' or 'build' not in package.get('scripts', {}):
        parser.error('The chosen folder must be the existing Roomies app.')
    npm = shutil.which('npm.cmd') or shutil.which('npm')
    if not npm:
        parser.error('Install Node.js and npm to build the existing app.')
    if not (source / 'node_modules').is_dir():
        parser.error('Run npm ci in the existing Roomies app folder first, then try again.')
    if args.database_expenses:
        node = shutil.which('node')
        if not node:
            parser.error('Install Node.js to build the existing app.')
        subprocess.run([node, str(ROOT/'build_database_frontend.mjs'), str(source)], cwd=ROOT, check=True)
        print('Preview command: python web_preview.py')
        return
    subprocess.run([npm, 'run', 'build'], cwd=source, check=True)
    dist = source / 'dist'
    if not (dist / 'index.html').is_file() or not (dist / 'assets').is_dir():
        parser.error('The build did not produce dist/index.html and dist/assets.')
    if args.export:
        target = ROOT / 'web' / 'roomies'
        target.mkdir(parents=True, exist_ok=True)
        shutil.copy2(dist / 'index.html', target / 'index.html')
        shutil.copytree(dist / 'assets', target / 'assets', dirs_exist_ok=True)
        marker = target / 'roomies-4402-build.json'
        if marker.exists():
            marker.unlink()  # A plain export must not claim it contains the SQL hook.
        for name in ('favicon.ico',):
            if (dist / name).is_file():
                shutil.copy2(dist / name, target / name)
        print('Compiled files exported to ' + str(target))
        print('These files are ignored by Git. Include them explicitly in a later hosting upload.')
    print('The existing app source was not edited.')
    print('Preview command: python web_preview.py --frontend "' + str(dist) + '"')


if __name__ == '__main__':
    main()

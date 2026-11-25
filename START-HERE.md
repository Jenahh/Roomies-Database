# Test the local CSC 4402 version

Public hosting preparation: [RAILWAY-SETUP.md](RAILWAY-SETUP.md) explains the
single-service deployment, persistent SQLite volume, free-plan limits, and
public acceptance checks. Local commands below remain available.

For the NEW browser preview, run `python web_preview.py` and open
http://127.0.0.1:8080/demo/. It serves both the existing Roomies build and the
expanded database forms. See [LOCAL-PREVIEW.md](LOCAL-PREVIEW.md) for a short
test plan. This is local-only on `honors-local-preview`; nothing is published.

The original CLI and separate Vite/API workflow follows below. Its default
database filename differs from the new preview: use `--db
demo-local-honors.sqlite3` with the CLI to share the new preview's data.

This is the CSC 4402 database project. No changes were made to the separate CSC 4330 app.

1. Open this folder in VS Code.
2. Open a terminal and run:

```powershell
python roomies.py test
python -m unittest discover -v
python verify_demo.py
```

To experiment with the CLI:

```powershell
python roomies.py init --db demo-local.sqlite3
python manage.py --db demo-local.sqlite3
```

If demo-local.sqlite3 already exists, skip init. For a fresh start choose a new filename and use it in every command.

Alex: alex@example.com â€” expenses and announcements in household 1.
Jordan: jordan@example.com â€” household 1, property 1, add/delete empty units and leases.
Taylor: taylor@example.com â€” announcements and RA concern history for household 1.

For chores and request submission/status updates:

```powershell
python roomies.py app --db demo-local.sqlite3
```

Resident: ID 1, household 1. Manager: ID 10. RA: ID 11.

To use the existing website without changing it:

```powershell
python chore_api.py --db demo-local.sqlite3 --port 8765
```

Leave it running. In another terminal, open the existing Roomies app folder and run npm run dev as usual. Stop the old Python API if port 8765 is occupied. Log in with the seeded email and password 1234. Only existing chores, maintenance, and RA concern web screens use this database; use the CLI for the expanded entities.

The expanded E-R diagrams and report are under docs/. Contributions still need each teammate's actual details. The PDF is eight pages. The DOCX uses Arial 11 and single spacing, but this environment cannot render Word files, so check its pagination after editing.

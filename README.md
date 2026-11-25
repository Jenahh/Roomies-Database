# Roomies CSC 4402 â€” local expanded database

This repository is the standalone CSC 4402 database project. It contains no copy of the React app. The separate CSC 4330 Roomies repository and its UI remain unchanged.

## Public hosting preparation

For the free Railway deployment, see [RAILWAY-SETUP.md](RAILWAY-SETUP.md).
The Dockerfile builds the pinned Roomies interface and serves it with the Python
API. The working SQLite database belongs on an attached `/data` volume. No public
deployment is claimed until the generated HTTPS address has been tested.

## Local browser preview (under review)

The updated expense integration is prepared in `web/roomies`. Start with
`python web_preview.py --frontend .\web\roomies` to reuse the current Roomies
expense screen, backed by SQLite for bills, payments and monthly rules.
Rebuild with `python prepare_roomies.py --source ..\roomies-github-current --database-expenses`.
See [docs/EXPENSE-INTEGRATION.md](docs/EXPENSE-INTEGRATION.md) for added relations,
scope, tests and report updates. The original Roomies source is unchanged.

The `honors-local-preview` branch adds a browser alternative to the expanded CLI
and can serve the existing Roomies build through the same Python server. It is
not published or merged. Start with `python web_preview.py`, then open
http://127.0.0.1:8080/demo/. See [LOCAL-PREVIEW.md](LOCAL-PREVIEW.md) for setup,
demo accounts, test workflows, and the later hosting steps. No additional Python
packages are required. The preview uses its own `demo-local-honors.sqlite3`;
the original commands below still use `demo-local.sqlite3` unless you select the
same filename explicitly. The report documents the earlier local interfaces
and will need its interface section updated after the preview is finalized.

The preview now uses one responsive mobile layout: Home embeds the existing
Roomies screens. Residents have Home, Chores, Bills, Calendar, and Profile in
the bottom bar; Details in the header contains additional database tools.
The selected demo account is shared. The 4402-only embedding adapter uses the
existing app's accessible controls and leaves its source/build files unchanged.
See LOCAL-PREVIEW.md for phone-size review and adapter details.

## Requirements
Python 3.8+; standard library only. No pip packages, emulator, or web app are needed for grading the CLI. Use `py` instead of `python` on Windows if needed.

## Open in VS Code
Open this folder itself, then Terminal > New Terminal. Commands below assume this folder is your current directory.

## Quick checks (do not modify the supplied seed database)
```powershell
python roomies.py test
python -m unittest discover -v
python verify_demo.py
```
There are 11 executable queries in queries.sql: the original five plus six supplementary queries following instructor feedback. sample-results.txt contains seed outputs. Tests use temporary databases. verify_demo.py uses a temporary database and a local HTTP server to show writes and deletes reaching SQLite.

## Try the interfaces locally
Create a new working database so you can freely experiment:
```powershell
python roomies.py init --db demo-local.sqlite3
python roomies.py app --db demo-local.sqlite3
```
Resident: select resident, user 1, household 1. Create/edit/complete/delete chores or submit a request. Staff: manager 10 for Cypress; RA 11 for household 1. Status changes automatically create RequestUpdate records; choosing the same status again does not add a duplicate.

For the expanded interfaces:
```powershell
python manage.py --db demo-local.sqlite3
```
Use alex@example.com, mia@example.com, sam@example.com, riley@example.com, jordan@example.com, morgan@example.com, taylor@example.com, or casey@example.com. Identity selection is a classroom demo, not password authentication.

- Expenses: residents list household expenses, create equal splits among specified household members, mark their own shares paid/unpaid, and delete bills they paid. Splits are allocated in integer cents before storage, including remainder cents.
- Announcements: household residents, assigned RA, and assigned manager can view/post. Authors and the assigned manager can delete.
- Leases: managers create/list/delete leases for household members in their properties. Residents see only their own leases. RAs cannot view lease details. Overlapping leases for the same resident and household are rejected.
- Households: managers create units in properties they manage, optionally assign an existing RA, and delete empty units. Foreign keys block deletion of populated households. Membership editing is outside this demo; use the seeded household members for expense and lease tests.
- History: users see history only for requests available to their role.

## Use the UNCHANGED Roomies web app (optional)
In this folder start the expanded API, using the SAME working database as the CLI:
```powershell
python chore_api.py --db demo-local.sqlite3 --port 8765
```
Leave that terminal running. Stop any older API already using port 8765 first. In a second terminal open your existing Roomies app checkout and run its usual `npm run dev`. Its existing Vite proxy forwards /api to localhost:8765. No UI or app code changes are required. Log in with alex@example.com / 1234, jordan@example.com / 1234, or taylor@example.com / 1234.

The existing web chores, maintenance, and RA concern screens now use this folder's SQLite file through the same API routes. Staff status changes create history rows in the same transaction. The unchanged app does NOT display history or use SQLite for its expense, announcement, household-creation, or lease features: demonstrate those with manage.py. Other app features retain their original behavior. Changes appear after the existing screen refresh or re-entry; there is no live push synchronization.

The CSC4402 CLI works by itself; the separate web repository is optional and is not required to run this submission.

## Database design and supplied data
18 tables: the earlier 14 enterprise relations, optional ChoreDisplay, and the three expense extensions ExpenseDetail, ExpenseRecurrence and ExpensePayment. ExpenseShare adds household_id and two composite foreign keys so a share must match both its expense household and a real household member. FK checks are enabled on every application connection. expense_extensions.sql is part of initialization and the additive migration for older working files.

The seed has 8 users, 2 properties, 2 households, 4 memberships, 5 chores, 5 requests, 3 expenses, 7 shares, 3 announcements, 3 history entries and 4 leases. User subtype tables allow overlapping roles (no disjointness or total-coverage constraint is asserted). ChoreDisplay starts empty and is populated when the web scheduler creates chores with metadata. Currency uses SQLite REAL with positive/nonnegative and two-decimal checks; API split arithmetic uses integer cents.

Query 11 includes only leases active on 2026-11-19 (inclusive start/end dates). The fixed date makes grading repeatable. The seed request 1 history is corrected to Open so it agrees with its current status.

## Files
- schema.sql, seed.sql, roomies-database.sqlite3: schema, synthetic-data generator, populated seed database.
- roomies.py: setup, queries, original resident/staff CLI.
- manage.py: expanded household/expense/bulletin/lease/history CLI.
- chore_api.py, request_api.py, expanded_api.py: local HTTP server and scoped SQL operations.
- queries.sql, sample-results.txt: eleven executable queries and results.
- test_chore_api.py, test_expanded.py, verify_demo.py: regression and live HTTP/SQLite checks.
- docs/: expanded E-R diagrams, editable report, PDF report, output figures and synchronization evidence.
- web_preview.py, wsgi.py, web/: combined local/WSGI server and expanded browser forms.
- prepare_roomies.py: build the separate existing app without changing its source; optionally export compiled files for a future upload.
- test_web_preview.py, test_web_ui.mjs: combined-server persistence tests and browser-script workflow checks.
- ledger_api.py, expense_extensions.sql, frontend/useHouseholdLedger.ts and build_database_frontend.mjs: relational ledger and isolated adapter build for the existing expense UI.
- test_ledger_api.py, test_roomies_ledger.mjs: ledger transactions, permissions, and original Roomies settlement algorithms against SQLite.

## Submission review
Fill in each teammate's actual contributions before submission. Verify the editable report's final pagination after your edits; the generated PDF is eight pages. Keep five main report queries; the six additional queries are supplementary. Confirm with the instructor if they prefer all eleven in the main report. Submit one final PDF and one code ZIP.

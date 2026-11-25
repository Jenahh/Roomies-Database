# Roomies — CSC 4402 Database Project

Roomies manages shared housing with a relational SQLite database, a Python API,
a responsive browser interface, and terminal interfaces.

**Public demo:** https://roomies-web-production.up.railway.app/

The public site runs independently of the developer's computer. It uses fictional,
shared demo identities. Select a person from the account menu; this is a classroom
demonstration, not secure password authentication. Public changes are shared by
visitors. The supplied submission database is a separate, reproducible seed.

## Run the submitted ZIP locally

1. Extract the entire ZIP. Open its `roomies4402` folder in VS Code.
2. Install Python 3.10 or later. No pip packages are required for local use.
3. In **Terminal > New Terminal**, run:

```powershell
python web_preview.py
```

Open http://127.0.0.1:8080/demo/ . Keep the terminal running; press Ctrl+C to stop.
On Windows, `py` can replace `python`. The ZIP includes the compiled Roomies
interface in `web/roomies`; Node.js and the other app repository are not needed
to run that copy. The server creates `demo-local-honors.sqlite3` on first use and
keeps it across restarts. To start over, choose a new filename instead of deleting
or overwriting your saved database:

```powershell
python web_preview.py --db demo-fresh.sqlite3 --port 8081
```

Then open http://127.0.0.1:8081/demo/ . The supplied `roomies-database.sqlite3`
is never used as the browser's working database.

## Demo accounts and workflows

| Person | Account | Main operations |
| --- | --- | --- |
| Alex, Mia, Sam | alex@example.com, mia@example.com, sam@example.com | Household 1 chores, bills, payments, announcements and resident requests |
| Riley | riley@example.com | Household 2 resident; cannot access Household 1 |
| Jordan | jordan@example.com | Cypress property requests, households and leases |
| Taylor | taylor@example.com | Household 1 RA concerns and announcements |
| Morgan | morgan@example.com | Oak property manager |
| Casey | casey@example.com | Household 2 RA |

- **Chores:** add tasks and change completion status. The resident terminal menu
  also provides editing and deletion.
- **Maintenance:** Alex > Profile > Maintenance issue > a category; Jordan > Requests
  changes Open/In Progress/Closed. Alex refreshes to read the committed status.
- **RA concerns:** Mia > Profile > Contact my RA > a category; Taylor > Concerns updates status.
- **Bills:** add/delete bills, select payer and participants, repeat monthly,
  stop repeating, and record/undo payments or use settlement suggestions.
- **Details:** announcements, request history, households and leases. Authors and
  assigned staff have the documented controls; residents see only their own leases.
- **Households:** Jordan can create a unit under Cypress and delete it while empty.
  Database constraints prevent deleting households that still have related records.

Home, Chores, Bills, Calendar and Profile are direct resident tabs. Calendar and
personal preferences stay in the browser; they are outside the SQL demonstration.
The database supports the same core operations through CLI menus.

## Execute the database queries and tests

From the extracted `roomies4402` folder:

```powershell
python roomies.py test
python -m unittest discover -v
python verify_demo.py
```

`roomies.py test` executes the 11 statements in `queries.sql` against a temporary
fresh seed and checks its integrity. Queries 1–5 are the main report queries;
6–11 are additional examples following instructor feedback. `sample-results.txt`
and `docs/query-screenshots/` contain the fixed seed results. Query 11 includes
only leases active on 2026-11-19, so its result remains reproducible.

The 35 Python regression tests use temporary databases and cover foreign keys,
household/role access, request history, exact expense shares, recurrence, payments,
stale-write rejection, HTTP routes and hosting persistence. `verify_demo.py`
shows real HTTP insert/update/delete operations and independent SQLite reads.
These commands do not alter the supplied seed or public website.

Optional browser-script checks use Node.js 22+:

```powershell
node test_web_ui.mjs
```

These exercise scripts against a temporary local HTTP/SQLite server; they do not
replace visual browser testing. `test_roomies_ledger.mjs` additionally reuses the
original app's finance algorithms and needs that source checkout's TypeScript
package installed; see the optional build instructions below.

## Use the terminal interfaces

For a separate terminal-only working database:

```powershell
python roomies.py init --db demo-cli.sqlite3
python roomies.py app --db demo-cli.sqlite3
python manage.py --db demo-cli.sqlite3
```

Skip `init` if that file already exists. Resident ID 1 belongs to household 1;
manager ID 10 is Jordan; RA ID 11 is Taylor. `manage.py` selects people by email.
To inspect the local browser's records in the CLI, use
`--db demo-local-honors.sqlite3` instead. Stop the browser server before running
`init`; ordinary CLI reads/writes may share its already initialized file.

## Database design

There are 18 tables: 17 enterprise/supporting relations and optional ChoreDisplay.
`schema.sql` and `expense_extensions.sql` define constraints; `seed.sql` supplies
synthetic data. The seed contains 8 users, 2 properties, 2 households, 4 memberships,
5 chores, 5 requests, 3 expenses, 7 shares, 3 announcements, 3 request-history rows
and 4 leases. ExpenseDetail contains category/client metadata. Recurrence and
payment rows are created when those workflows are used; they start empty in the
seed. Every application connection enables SQLite foreign keys.

Composite keys restrict chore assignees, request submitters, expense payers,
expense shares, lease residents, and payment participants to the correct household.
Roles may overlap. Staff status changes and their RequestUpdate rows commit in one
transaction. Lease triggers reject overlapping dates for the same member/household.

Bills/shares/rent use checked two-decimal SQLite REAL values; splits are calculated
in integer cents. ExpensePayment stores integer cents. ExpenseRecurrence stores
one base bill's monthly rule; displayed monthly occurrences are derived by the
existing Roomies calculation. A revision hash rejects stale ledger writes.

**Query 6 measures unpaid individual ExpenseShare flags.** Separately recorded
settlement transfers are stored in ExpensePayment and affect the web ledger's net
balances; query 6 does not calculate those net balances.

## Synchronization and hosting

The browser calls relative `/api/` URLs. The Python API checks role/household
access, executes parameterized SQL, commits, and returns JSON. Refreshing reads
committed SQLite data; there is no server-push synchronization. The expense hook
also refreshes periodically while its browser view is active.

Railway serves the interface and API together. Its SQLite file is
`/data/roomies.sqlite3` on an attached persistent volume. Public HTTPS, shared
updates, bill/payment operations, and saved records after a container restart
were verified. See `docs/public-verification.json` for the recorded checks.

The deployment follows `honors-public-demo` in Jenahh/Roomies-Database. It uses a
fixed Roomies frontend revision; the separate app repository is not modified.
The Free plan has limited monthly usage and can pause when credit is exhausted.
After the initial trial, select Free and redeploy to continue without a paid plan.
See `RAILWAY-SETUP.md` for deployment and storage instructions.

## Optional: rebuild the interface from source

The submitted ZIP already contains a working compiled interface. For a rebuild,
use Node.js 22+ and the existing Roomies source revision
`a294a7e4b2903a76be7d9a4319bf6a57825a8eae` with `npm ci` completed:

```powershell
python prepare_roomies.py --source ..\roomies-github-current --database-expenses
node test_roomies_ledger.mjs
```

The adapter changes two modules in memory during compilation; it does not edit
that checkout or its normal `dist`. Output goes to ignored `web/roomies`.
The Dockerfile reproduces this build in a disposable stage and includes only
compiled browser files in the final Python image. Source references are recorded
in `SOURCE-REVISIONS.md`.

## Submission files

Submit one final PDF report and one code ZIP to Gradescope. The report describes
five primary test queries and up to five interface groups; supplementary queries,
full-size figures, screenshots and transcripts are included under `docs/`.
Confirm each person's actual participation, final PDF pagination, and any
additional instructor-specific Honors requirements before submission.

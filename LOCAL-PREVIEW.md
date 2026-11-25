# Roomies: review before publishing

This is a local preview on the `honors-local-preview` branch. It has not been
merged, pushed, or published. The separate Roomies app's source is unchanged.

## Start in VS Code

Open `roomies-4402-github` and use Terminal > New Terminal:

```powershell
python web_preview.py
```

Open **http://127.0.0.1:8080/demo/**. Leave the terminal running.

**Updated expense screen:** the prepared build in `web/roomies` reuses the
current Roomies Expenses screen with a SQLite ledger. Start it explicitly with
`python web_preview.py --frontend .\web\roomies`. To rebuild:

```powershell
python prepare_roomies.py --source ..\roomies-github-current --database-expenses
```

See [docs/EXPENSE-INTEGRATION.md](docs/EXPENSE-INTEGRATION.md) for payments,
monthly bills, new relations, migration behavior and report changes. Details
now has a filled household-icon button, and embedded screens fill the available
space instead of using a second phone-width crop. An ordinary app dist uses
the earlier database forms as a fallback; it does not include the SQL ledger hook.

- **Home** contains the existing Roomies screens inside the shared layout.
- Residents have **Home, Chores, Bills, Calendar, Profile** directly in the
  bottom bar. Staff get Requests or Concerns in place of Chores.
- **Details** in the header opens announcements, request history, household
  records, and leases. The project explanation is collapsed below those tools.
- The account name at the top opens the account/household selector. Home uses
  that seeded identity too. The wrapper fills the original demo login; if the
  browser leaves the login screen visible, use the selected email and `1234`.
- The same header and bottom navigation stay visible. No new tab is needed.
- On a phone-sized viewport, add/post forms are collapsed. Tap their heading
  to open them; saved records appear below.
- The default working file is `demo-local-honors.sqlite3`. It is created from
  schema.sql and seed.sql only when absent, and is ignored by Git. Refreshing
  or restarting the preview does not erase your changes.
- The supplied `roomies-database.sqlite3` is not used as a working file.
- This preview uses port 8080 for both API and pages. You do not need Vite or
  the old port-8765 API running alongside it.

The preview automatically finds the built existing app at
`../roomies-github-current/dist` (then falls back to `../roomies-database/dist`).
An optional exported `web/roomies` build takes priority. To rebuild the newer
local app and select it explicitly, use:

```powershell
python prepare_roomies.py --source ..\roomies-github-current
python web_preview.py --frontend ..\roomies-github-current\dist
```

The builder requires Node.js and existing app dependencies (`npm ci` in the
Roomies app folder if needed). It runs the app's normal build without editing
its source. For another app checkout, specify its `dist` folder explicitly:

```powershell
python web_preview.py --frontend "C:\path\to\Roomies\dist"
```

The database tabs work without a frontend build. Home explains how to prepare
the app if a build is missing. Restart the preview after preparing a build.

## Check the phone layout before publishing

Restart the Python server after updating this preview (Ctrl+C, then the start
command above) and refresh the browser. In desktop Chrome or Edge, open DevTools
with F12, toggle the device toolbar with Ctrl+Shift+M, and try a 390 x 844 viewport.
The local 127.0.0.1 link refers to the computer running the server; it is not yet
a link for other phones. Once hosted, the same layout will be served at the
public URL on phones and computers.

Try Home, Chores, Bills > Add a bill, Calendar, and Profile directly from the
bottom bar. Use Details > Announcements, Requests & history, or Leases for the
additional records. Tap the account name to open or close the account drawer.
This is a responsive website, not an installed native mobile application.

## Try these workflows

| Feature | What to do | What to verify |
| --- | --- | --- |
| Original Roomies | Select Alex; use Chores or Profile > Report maintenance issue directly from the bottom bar. | Chores and requests use this preview's database. Calendar and personal preferences retain their browser-local behavior. |
| Shared expenses | Choose Alex; Expenses; create a $10.00 bill for Alex, Mia and Sam. Choose Mia. | Alex's share is $3.34; Mia and Sam have $3.33 each. Mia can mark her own share paid. Alex can delete the bill and its shares. |
| Announcements | Choose Taylor; post an announcement. Choose Alex and refresh. | Alex sees the same post. The author or assigned manager can delete it. |
| Households | Choose Jordan; Households; create unit 9Z in Cypress Apartments. | It appears in the household selector. Delete the empty unit. Deleting populated unit 2A is rejected. |
| Leases | Choose Jordan; household 2A; Leases; create an Alex lease for 2027-06-01 through 2028-05-31. | Alex sees his lease. An overlapping duplicate is rejected. Only Jordan can delete the lease. |
| Requests and history | Alex submits maintenance; Jordan sets it to In Progress with a note. Mia submits an RA concern; Taylor closes it. | The resident sees the same saved status and history. Original Roomies request screens show the same status after refresh. |

The selector and embedded Home share a demo identity. Switching people reloads
Home for that account. Use the seeded `@example.com` accounts; the original
app's other demo accounts are not database identities.
Residents see their own requests, managers see maintenance for their properties,
and RAs see concerns for their assigned households. This is a shared synthetic
demo, not a password-protected production service. In the SQL expense build,
Home and Expenses share the database ledger hook. Bills opens the existing
Roomies Expenses screen directly. The older ordinary-build fallback refreshes
its Home display cache from SQLite and uses the simpler bill forms.

The wrapper adds its integration script and styles only to embedded HTML
responses from this 4402 server. It uses the existing app's accessible login
fields and navigation controls and replaces its embedded navigation with the
shared bottom bar. It does not edit the separate repository or compiled files.
If those controls change later, review the adapter against the new app build
before deployment. Opening `/login` directly without the embedding query still
serves the original unwrapped app.

To check persistence, refresh the browser, stop the server with Ctrl+C, start it
again, and confirm the records remain. To start fresh without deleting anything:

```powershell
python web_preview.py --db demo-local-honors-2.sqlite3
```

## Use the CLI with the same preview database

```powershell
python manage.py --db demo-local-honors.sqlite3
python roomies.py app --db demo-local-honors.sqlite3
```

Changes made through these menus appear in the browser after Refresh data.
There is no live push synchronization.

For independent database evidence, this reads household rows directly:

```powershell
python -c "import sqlite3; c=sqlite3.connect('demo-local-honors.sqlite3'); print(c.execute('SELECT household_id, unit_label FROM Household').fetchall()); c.close()"
```

Run it before creating unit 9Z, after creating it, and after deleting it.

## Checks

```powershell
python roomies.py test
python -m unittest discover -v
python verify_demo.py
node test_web_ui.mjs
node test_roomies_ledger.mjs
```

Tests create temporary databases. `node test_web_ui.mjs` is optional for the
Python-only submission; it exercises browser-script rendering and form payloads
against a real temporary HTTP/SQLite server, plus the embedding adapter's control
and message contract. It is not a visual browser test.

## Later, after local review

No hosting account, domain, payment, Git push, or deployment is needed to review
this preview. The local link cannot be opened by the public.

The WSGI entry point (`wsgi.py`) is prepared for a Python hosting service. It
uses the standard library, so Flask is not required. An eventual upload needs
the Python/SQL files, `web/` forms, and the existing app's compiled `dist`
files. `python prepare_roomies.py --database-expenses` builds the SQL-connected
variant into `web/roomies`; include that folder explicitly when uploading. A
plain `--export` instead exports the ordinary browser-local expense build and
clears the SQL-build marker. Neither command copies the React source project.

On a host, set `ROOMIES_DB_PATH` to an absolute persistent working filename
and `ROOMIES_FRONTEND_DIR` to the compiled app folder if not using
`web/roomies`. Import `application` from `wsgi`. Keep database files outside
any public static-file mapping. Use the provider's WSGI worker, not the local
development server. No API calls use localhost in the browser: relative URLs
work when pages and API are hosted together.

Before calling Honors hosting complete, deploy and test the actual public URL
from another device while the local server is stopped. Add that URL and the demo
instructions to the report/README and include the new code in the final ZIP.
The present report describes the earlier local interfaces; update its interface
section after choosing the final version. Confirm any additional Honors-specific
requirements with the instructor. Free hosting limits and renewal policies need
checking again at deployment time.

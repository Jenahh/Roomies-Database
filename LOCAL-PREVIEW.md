# Roomies local preview

Public demo: https://roomies-web-production.up.railway.app/
The deployment follows honors-public-demo in the database repository.

For the submitted ZIP, open roomies4402 in VS Code and run:

```powershell
python web_preview.py
```

Open http://127.0.0.1:8080/demo/ . The included compiled interface uses the Python
API and local SQLite file demo-local-honors.sqlite3. The public site's database
is separate. Stop the local server with Ctrl+C.

Use the account menu to select Alex/Mia/Sam, Jordan or Taylor. Resident tabs
include Chores and Bills; Details provides announcements, history, households
and leases. Profile > Maintenance issue or Contact my RA > a category opens the
resident submission form. Staff use Requests or Concerns.

README.md contains the complete accounts, operations, CLI commands, test steps,
and optional rebuild instructions. No changes to the separate app repository
are required to run the submitted compiled interface.

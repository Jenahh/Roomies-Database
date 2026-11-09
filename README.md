# Roomies-Database
CSC 4402

Roomies is a SQLite database and a command-line demo for shared households.

It supports chores, maintenance requests, and concerns shared with resident assistants.

## Run the project

Install Python 3.8 or later. The project uses the Python standard library.
Extract the ZIP and open a terminal in the Roomies folder.

1. Run the five report queries against the included database.

   ```text
   python roomies.py test
   ```

2. Open the application.

   ```text
   python roomies.py app
   ```

3. To create a fresh database and keep the included sample intact, run the
   commands below. The init command requires a new file path.

   ```text
   python roomies.py init --db demo.sqlite3
   python roomies.py test --db demo.sqlite3
   python roomies.py app --db demo.sqlite3
   ```

On Windows, use `py` if `python` is unavailable. On macOS or Linux,
use `python3` if needed.

## Interfaces and demo

The CLI lets you select a seeded identity for grading. Account selection is a
demo convenience and does not authenticate users. The menus and SQL operations
scope data to the selected identity and role.

1. **Resident dashboard.** Choose `resident`, user ID 1 (Alex), and household ID 1.
   Option 1 shows household members, chores, and Alex's own requests.

2. **Chore management.** In the same menu, options 2 through 5 create, edit,
   complete, and delete chores. Try assigning a chore to Riley (ID 4) to see the

   database reject an assignee from a different household.
3. **Request form.** Choose resident option 6 and submit a maintenance request or
   RA concern. A concern requires an assigned RA.

4. **Property manager dashboard.** Return to account selection and choose
   `manager`, user ID 10 (Jordan). Jordan sees maintenance requests for Cypress
   Apartments and can update their status. Use manager ID 12 to see Oak Commons.
   
5. **RA dashboard.** Choose `ra`, user ID 11 (Taylor). Taylor sees concerns from
   assigned households and can update their status. Use RA ID 13 to view the
   other household's concerns.

Request recipients are derived from current assignments. Maintenance requests
follow the household to its property manager, and RA concerns follow the
household's assigned RA.

## Files

- `roomies.sqlite3` contains the nine tables and synthetic sample data.
- `schema.sql` creates the database tables and constraints.
- `seed.sql` inserts the synthetic sample data.
- `queries.sql` contains the five executable report queries.
- `sample-results.txt` contains the actual output from the fresh seed database.
- `roomies.py` initializes the database, runs the queries, and opens the CLI.

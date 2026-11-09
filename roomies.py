"""SQLite setup, report queries, and Roomies demonstration interfaces."""
import argparse
from contextlib import closing
from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parent
DEFAULT_DB = ROOT / "roomies-database.sqlite3"


def connect(path):
    db = sqlite3.connect(path)
    db.execute("PRAGMA foreign_keys = ON")
    return db


def initialize(path):
    # Exclusive creation protects an existing database, including concurrent runs.
    with path.open("xb"):
        pass
    try:
        with closing(connect(path)) as db:
            schema = (ROOT / "schema.sql").read_text(encoding="utf-8")
            seed = (ROOT / "seed.sql").read_text(encoding="utf-8")
            db.executescript("BEGIN;\n" + schema + "\n" + seed + "\nCOMMIT;")
    except BaseException:
        path.unlink()
        raise
    print(f"Created {path}")


def show(cursor):
    print(" | ".join(column[0] for column in cursor.description))
    rows = cursor.fetchall()
    for row in rows:
        print(" | ".join("" if value is None else str(value) for value in row))
    if not rows:
        print("(no rows)")


def run_queries(db):
    sql = (ROOT / "queries.sql").read_text(encoding="utf-8")
    statement = ""
    for line in sql.splitlines(keepends=True):
        if line.startswith("--"):
            print("\n" + line[3:].rstrip())
            continue
        statement += line
        if sqlite3.complete_statement(statement):
            show(db.execute(statement))
            statement = ""


def resident_menu(db, user_id):
    print("\nYour households")
    show(db.execute("""
        SELECT h.household_id, p.name AS property, h.unit_label
        FROM HouseholdMember AS m
        JOIN Household AS h USING (household_id)
        JOIN Property AS p USING (property_id)
        WHERE m.user_id = ?
        ORDER BY h.household_id
    """, (user_id,)))
    household = int(input("Household ID: "))
    membership = (household, user_id)
    if not db.execute("""
        SELECT 1 FROM HouseholdMember WHERE household_id = ? AND user_id = ?
    """, membership).fetchone():
        print("You are not a member of that household.")
        return

    while True:
        print("\n1 View household   2 Create chore   3 Edit chore")
        print("4 Complete chore   5 Delete chore   6 Submit request   0 Back")
        choice = input("> ").strip()
        if choice == "0":
            return
        try:
            with db:
                resident_action(db, household, user_id, choice)
        except (ValueError, sqlite3.IntegrityError) as error:
            print(f"Action rejected: {error}")


def chore_fields(db, household):
    title = input("Chore title: ").strip()
    due_date = input("Due date (YYYY-MM-DD): ").strip()
    show(db.execute("""
        SELECT u.user_id, u.name FROM HouseholdMember AS m
        JOIN "User" AS u ON u.user_id = m.user_id
        WHERE m.household_id = ? ORDER BY u.name
    """, (household,)))
    assignee = input("Assignee ID (blank for unassigned): ").strip()
    return title, due_date, int(assignee) if assignee else None


def report_change(cursor):
    print("Saved." if cursor.rowcount else "No matching record in your scope.")


def resident_action(db, household, user_id, choice):
    if choice == "1":
        print("\nResidents")
        show(db.execute("""
            SELECT u.name FROM HouseholdMember AS m JOIN "User" AS u USING (user_id)
            WHERE m.household_id = ? ORDER BY u.name
        """, (household,)))
        print("\nChores")
        show(db.execute("""
            SELECT c.chore_id, c.title, c.due_date, c.status,
                   COALESCE(u.name, 'Unassigned') AS assignee
            FROM Chore AS c LEFT JOIN "User" AS u ON u.user_id = c.assigned_user_id
            WHERE c.household_id = ? ORDER BY c.due_date, c.chore_id
        """, (household,)))
        print("\nYour requests")
        show(db.execute("""
            SELECT request_id, request_type, description, status FROM Request
            WHERE household_id = ? AND submitted_by_user_id = ? ORDER BY request_id
        """, (household, user_id)))
    elif choice == "2":
        fields = chore_fields(db, household)
        report_change(db.execute("""
            INSERT INTO Chore (title, due_date, assigned_user_id, household_id)
            VALUES (?, ?, ?, ?)
        """, (*fields, household)))
    elif choice == "3":
        chore = int(input("Chore ID: "))
        fields = chore_fields(db, household)
        report_change(db.execute("""
            UPDATE Chore SET title = ?, due_date = ?, assigned_user_id = ?
            WHERE household_id = ? AND chore_id = ?
        """, (*fields, household, chore)))
    elif choice == "4":
        chore = int(input("Chore ID: "))
        report_change(db.execute("""
            UPDATE Chore SET status = 'Completed' WHERE household_id = ? AND chore_id = ?
        """, (household, chore)))
    elif choice == "5":
        chore = int(input("Chore ID: "))
        report_change(db.execute("""
            DELETE FROM Chore WHERE household_id = ? AND chore_id = ?
        """, (household, chore)))
    elif choice == "6":
        request_type = {"1": "Maintenance", "2": "RA Concern"}.get(
            input("1 Maintenance   2 RA Concern: ").strip()
        )
        if request_type is None:
            raise ValueError("Choose request type 1 or 2.")
        description = input("Description: ").strip()
        result = db.execute("""
            INSERT INTO Request (household_id, submitted_by_user_id, request_type, description)
            SELECT household_id, ?, ?, ? FROM Household
            WHERE household_id = ? AND (? = 'Maintenance' OR ra_user_id IS NOT NULL)
        """, (user_id, request_type, description, household, request_type))
        print("Request submitted." if result.rowcount else "This household has no assigned RA.")
    else:
        print("Choose an option from the menu.")


def staff_menu(db, user_id, role):
    if role == "manager":
        request_type = "Maintenance"
        scope = "p.manager_user_id = ?"
    else:
        request_type = "RA Concern"
        scope = "h.ra_user_id = ?"

    # The SQL fragment comes from the fixed role branches above.
    scoped_requests = f"""
        FROM Request AS r
        JOIN Household AS h ON h.household_id = r.household_id
        JOIN Property AS p ON p.property_id = h.property_id
        WHERE r.request_type = ? AND {scope}
    """
    params = (request_type, user_id)
    while True:
        print(f"\n{request_type} dashboard")
        show(db.execute("""
            SELECT r.request_id, p.name AS property, h.unit_label, r.description, r.status
        """ + scoped_requests + " ORDER BY r.request_id", params))
        request_id = input("Request ID to update (Enter to go back): ").strip()
        if not request_id:
            return
        status = {"1": "Open", "2": "In Progress", "3": "Closed"}.get(
            input("1 Open   2 In Progress   3 Closed: ").strip()
        )
        if status is None:
            print("Choose a status from the menu.")
            continue
        with db:
            report_change(db.execute("""
                UPDATE Request SET status = ? WHERE request_id = ?
                AND request_id IN (SELECT r.request_id
            """ + scoped_requests + ")", (status, request_id, *params)))


def play(db):
    while True:
        print("\nRoomies demo accounts")
        show(db.execute("""
            SELECT u.user_id, u.name, 'resident' AS role FROM Resident JOIN "User" AS u USING (user_id)
            UNION ALL
            SELECT u.user_id, u.name, 'manager' FROM PropertyManager JOIN "User" AS u USING (user_id)
            UNION ALL
            SELECT u.user_id, u.name, 'ra' FROM ResidentAssistant JOIN "User" AS u USING (user_id)
            ORDER BY 1, 3
        """))
        role = input("Role (resident, manager, ra, or Enter to quit): ").strip()
        if not role:
            return
        subtype = {"resident": "Resident", "manager": "PropertyManager", "ra": "ResidentAssistant"}.get(role)
        if subtype is None:
            print("Choose a listed role.")
            continue
        try:
            user_id = int(input("User ID: "))
            if not db.execute(f"SELECT 1 FROM {subtype} WHERE user_id = ?", (user_id,)).fetchone():
                print("That account does not have the selected role.")
                continue
            if role == "resident":
                resident_menu(db, user_id)
            else:
                staff_menu(db, user_id, role)
        except ValueError:
            print("Enter a numeric ID.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("init", "test", "app"))
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    args = parser.parse_args()
    try:
        if args.command == "init":
            initialize(args.db)
            return
        if not args.db.is_file():
            parser.error("Database missing. Run the init command first.")
        with closing(connect(args.db)) as db:
            if args.command == "test":
                run_queries(db)
            else:
                play(db)
    except FileExistsError:
        parser.exit(1, f"Database already exists at {args.db}. Choose another --db path.\n")
    except (OSError, sqlite3.Error) as error:
        parser.exit(1, f"{error}\n")
    except (EOFError, KeyboardInterrupt):
        print()


if __name__ == "__main__":
    main()

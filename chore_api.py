"""Loopback HTTP API for the seeded Roomies classroom demo."""
import argparse
from contextlib import closing
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import sqlite3

from expanded_api import handle_expanded
from request_api import RequestError, handle_requests
from roomies import connect, initialize

DEFAULT_DB = Path(__file__).with_name("demo-local.sqlite3")


def household_data(db, household, user):
    roommates = db.execute(
        'SELECT u.user_id, u.name FROM HouseholdMember m JOIN "User" u USING (user_id) '
        'WHERE m.household_id = ? AND m.user_id != ? ORDER BY u.name', (household, user)
    )
    chores = db.execute(
        'SELECT c.*, u.name AS assignee, meta.minutes, meta.look FROM Chore c '
        'LEFT JOIN "User" u ON u.user_id = c.assigned_user_id '
        'LEFT JOIN ChoreDisplay meta USING (chore_id) '
        'WHERE c.household_id = ? ORDER BY c.due_date, c.chore_id', (household,)
    )
    return {
        "roommates": [{"id": str(row["user_id"]), "name": row["name"]} for row in roommates],
        "chores": [{
            "id": str(row["chore_id"]), "title": row["title"], "due": row["due_date"],
            "completed": row["status"] == "Completed",
            "memberId": ("resident-self" if row["assigned_user_id"] == user
                         else str(row["assigned_user_id"])) if row["assigned_user_id"] else None,
            "assignee": row["assignee"], "unassigned": row["assigned_user_id"] is None,
            "minutes": row["minutes"], "look": row["look"],
        } for row in chores],
    }


def create_chores(db, household, user, chores):
    if not isinstance(chores, list) or not 1 <= len(chores) <= 52:
        raise RequestError(400, "Send between 1 and 52 chores.")
    for chore in chores:
        if not isinstance(chore, dict):
            raise RequestError(400, "Invalid chore.")
        title = chore.get("title")
        due = chore.get("due")
        if not isinstance(title, str) or not title.strip() or not isinstance(due, str):
            raise RequestError(400, "Enter a title and a valid due date.")
        if date.fromisoformat(due).isoformat() != due:
            raise RequestError(400, "Use YYYY-MM-DD for the due date.")
        member = chore.get("memberId")
        if member is not None and member != "resident-self" and (
            not isinstance(member, str) or not re.fullmatch(r"[1-9]\d*", member)
        ):
            raise RequestError(400, "Invalid assignee.")
        assignee = user if member == "resident-self" else int(member) if member is not None else None
        minutes = chore.get("minutes")
        look = chore.get("look")
        if minutes is not None and (type(minutes) is not int or not 1 <= minutes <= 1440):
            raise RequestError(400, "Enter an effort between 1 and 1440 minutes.")
        if look is not None and not isinstance(look, str):
            raise RequestError(400, "Invalid chore preset.")
        result = db.execute(
            "INSERT INTO Chore (household_id, assigned_user_id, title, due_date) VALUES (?, ?, ?, ?)",
            (household, assignee, title.strip(), due),
        )
        db.execute("INSERT INTO ChoreDisplay VALUES (?, ?, ?)", (result.lastrowid, minutes, look))


class ChoreAPI(BaseHTTPRequestHandler):
    def do_GET(self):
        self.handle_request()

    def do_POST(self):
        self.handle_request()

    def do_PATCH(self):
        self.handle_request()

    def do_DELETE(self):
        self.handle_request()

    def read_payload(self):
        size = int(self.headers.get("Content-Length", "0"))
        if not 0 < size <= 128_000:
            raise RequestError(400, "Invalid request size.")
        payload = json.loads(self.rfile.read(size))
        if not isinstance(payload, dict):
            raise RequestError(400, "Expected a JSON object.")
        return payload

    def handle_request(self):
        try:
            if self.path.startswith('/api/database/'):
                payload = self.read_payload() if self.command in ('POST','PATCH') else {}
                with closing(connect(self.server.database)) as db, db:
                    db.row_factory = sqlite3.Row
                    if self.command != 'GET':
                        db.execute('BEGIN IMMEDIATE')
                    result = handle_expanded(db, self.command, self.path, self.headers.get('X-Roomies-Demo-Email'), payload)
                self.reply(201 if self.command == 'POST' else 200, result)
                return
            requests = re.fullmatch(r"/api/requests/(resident|manager|ra)(?:/([1-9]\d*))?", self.path)
            if requests:
                payload = self.read_payload() if self.command != "GET" else {}
                with closing(connect(self.server.database)) as db, db:
                    db.row_factory = sqlite3.Row
                    if self.command != "GET":
                        db.execute("BEGIN IMMEDIATE")
                    result = handle_requests(db, self.command, requests[1],
                                             int(requests[2]) if requests[2] else None,
                                             self.headers.get("X-Roomies-Demo-Email"), payload)
                self.reply(201 if self.command == "POST" else 200, result)
                return

            route = re.fullmatch(r"/api/households/([1-9]\d*)/chores(?:/([1-9]\d*))?", self.path)
            if not route or bool(route[2]) != (self.command == "PATCH"):
                raise RequestError(404, "Unknown route.")
            household = int(route[1])
            with closing(connect(self.server.database)) as db, db:
                db.row_factory = sqlite3.Row
                if self.command != "GET":
                    db.execute("BEGIN IMMEDIATE")
                member = db.execute(
                    'SELECT u.user_id FROM HouseholdMember m JOIN "User" u USING (user_id) '
                    'WHERE m.household_id = ? AND u.email = ?',
                    (household, self.headers.get("X-Roomies-Demo-Email")),
                ).fetchone()
                if member is None:
                    raise RequestError(403, "This demo account does not belong to that household.")
                user = member["user_id"]
                if self.command != "GET":
                    payload = self.read_payload()
                    if self.command == "POST":
                        create_chores(db, household, user, payload.get("chores"))
                    else:
                        completed = payload.get("completed")
                        if type(completed) is not bool:
                            raise RequestError(400, "Expected a completion status.")
                        updated = db.execute(
                            "UPDATE Chore SET status = ? WHERE chore_id = ? AND household_id = ?",
                            ("Completed" if completed else "Pending", int(route[2]), household),
                        )
                        if not updated.rowcount:
                            raise RequestError(404, "Chore not found in this household.")
                snapshot = household_data(db, household, user)
            self.reply(201 if self.command == "POST" else 200, snapshot)
        except RequestError as error:
            self.reply(error.status, {"error": str(error)})
        except (ValueError, TypeError, OverflowError):
            self.reply(400, {"error": "Invalid request data."})
        except sqlite3.IntegrityError:
            self.reply(400, {"error": "The submitted data violates a database constraint."})
        except sqlite3.Error:
            self.reply(500, {"error": "The database operation failed."})

    def reply(self, status, payload):
        data = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def prepare_database(path):
    with closing(connect(path)) as db, db:
        db.execute(
            "CREATE TABLE IF NOT EXISTS ChoreDisplay ("
            "chore_id INTEGER PRIMARY KEY REFERENCES Chore(chore_id) ON DELETE CASCADE, "
            "minutes INTEGER, look TEXT)"
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    if not args.db.exists():
        initialize(args.db)
    prepare_database(args.db)
    with ThreadingHTTPServer(("127.0.0.1", args.port), ChoreAPI) as server:
        server.database = args.db
        print(f"Roomies demo API listening on {server.server_address}", flush=True)
        server.serve_forever()


if __name__ == "__main__":
    main()

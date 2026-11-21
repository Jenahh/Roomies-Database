"""Exercise the HTTP request handler and SQLite without opening a network port."""
from contextlib import closing
from http.client import HTTPResponse
from io import BytesIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest

from chore_api import ChoreAPI, connect, initialize, prepare_database


class ChoreApiTest(unittest.TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.database = Path(directory.name) / "test.sqlite3"
        initialize(self.database)
        prepare_database(self.database)

    def request(self, email, household, method="GET", payload=None, suffix="", path=None):
        body = json.dumps(payload).encode() if payload is not None else b""
        path = path or f"/api/households/{household}/chores{suffix}"
        message = (
            f"{method} {path} HTTP/1.0\r\n"
            f"X-Roomies-Demo-Email: {email}@example.com\r\n"
            f"Content-Length: {len(body)}\r\n\r\n"
        ).encode() + body
        output = BytesIO()

        class Handler(ChoreAPI):
            def setup(self):
                self.rfile = BytesIO(message)
                self.wfile = output

            def finish(self):
                pass

            def log_message(self, *_):
                pass

        Handler(None, ("127.0.0.1", 0), SimpleNamespace(database=self.database))
        response = HTTPResponse(SimpleNamespace(makefile=lambda *_: BytesIO(output.getvalue())))
        response.begin()
        return response.status, json.loads(response.read())

    def test_shared_chore_and_household_isolation(self):
        chore = {"title": "Shared demo task", "due": "2026-12-01",
                 "memberId": "2", "minutes": 35, "look": "custom"}
        status, result = self.request("alex", 1, "POST", {"chores": [chore]})
        self.assertEqual(status, 201, result)
        chore_id = next(item["id"] for item in result["chores"] if item["title"] == chore["title"])
        suffix = "/" + chore_id
        status, result = self.request("mia", 1)
        self.assertEqual(status, 200)
        shared_chore = next(item for item in result["chores"] if item["id"] == chore_id)
        self.assertEqual(shared_chore["memberId"], "resident-self")
        self.assertEqual(shared_chore["minutes"], 35)
        self.assertEqual(self.request("riley", 1)[0], 403)
        self.assertEqual(self.request("riley", 1, "PATCH", {"completed": True}, suffix)[0], 403)
        self.assertEqual(self.request("riley", 2, "PATCH", {"completed": True}, suffix)[0], 404)
        self.assertEqual(self.request("mia", 1, "PATCH", {"completed": True}, suffix)[0], 200)
        self.assertTrue(next(item for item in self.request("alex", 1)[1]["chores"]
                             if item["id"] == chore_id)["completed"])

        invalid_chore = {**chore, "memberId": "4"}
        self.assertEqual(self.request("alex", 1, "POST", {"chores": [chore, invalid_chore]})[0], 400)
        with closing(connect(self.database)) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM Chore WHERE title = ?",
                                        (chore["title"],)).fetchone()[0], 1)


    def support(self, email, scope, method="GET", payload=None, request_id=None):
        path = "/api/requests/" + scope
        if request_id is not None:
            path += "/" + str(request_id)
        return self.request(email, None, method, payload, path=path)

    def test_support_workflows_and_staff_scope(self):
        for kind, author, scope, staff, other_staff, wrong_role, wrong_account in (
            ("Maintenance", "alex", "manager", "jordan", "morgan", "ra", "taylor"),
            ("RA Concern", "mia", "ra", "taylor", "casey", "manager", "jordan"),
        ):
            with self.subTest(kind=kind):
                payload = {"type": kind, "householdId": 1, "description": "Test " + kind}
                status, result = self.support(author, "resident", "POST", payload)
                self.assertEqual(status, 201, result)
                request = next(row for row in result["requests"] if row["description"] == payload["description"])
                request_id = request["id"]
                self.assertEqual(request["status"], "Open")
                self.assertEqual(request["unit"], "2A")

                status, result = self.support(staff, scope)
                self.assertEqual(status, 200, result)
                self.assertIn(request_id, [row["id"] for row in result["requests"]])
                for account, queue in ((other_staff, scope), (wrong_account, wrong_role), ("sam", "resident")):
                    status, result = self.support(account, queue)
                    self.assertEqual(status, 200, result)
                    self.assertNotIn(request_id, [row["id"] for row in result["requests"]])
                self.assertEqual(self.support(author, scope)[0], 403)
                self.assertEqual(self.support("riley", "resident", "POST", payload)[0], 403)
                change = {"status": "In Progress"}
                self.assertEqual(self.support(other_staff, scope, "PATCH", change, request_id)[0], 404)
                self.assertEqual(self.support(wrong_account, wrong_role, "PATCH", change, request_id)[0], 404)
                self.assertEqual(self.support(author, "resident", "PATCH", change, request_id)[0], 405)
                self.assertEqual(self.support(staff, scope, "PATCH", {"status": "Invalid"}, request_id)[0], 400)
                for next_status in ("In Progress", "Closed"):
                    self.assertEqual(self.support(staff, scope, "PATCH", {"status": next_status}, request_id)[0], 200)
                    result = self.support(author, "resident")[1]
                    self.assertEqual(next(row for row in result["requests"] if row["id"] == request_id)["status"], next_status)


if __name__ == "__main__":
    unittest.main()

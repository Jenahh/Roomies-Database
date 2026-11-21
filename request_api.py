"""SQL operations for the Roomies request demo."""

STATUSES = ("Open", "In Progress", "Closed")
REQUEST_TYPES = ("Maintenance", "RA Concern")

SCOPES = {
    "resident": ("Resident", "r.submitted_by_user_id = ?", None),
    "manager": ("PropertyManager", "p.manager_user_id = ?", "Maintenance"),
    "ra": ("ResidentAssistant", "h.ra_user_id = ?", "RA Concern"),
}

REQUEST_ROWS = """
    FROM Request r
    JOIN Household h ON h.household_id = r.household_id
    JOIN Property p ON p.property_id = h.property_id
    JOIN "User" resident ON resident.user_id = r.submitted_by_user_id
"""


class RequestError(Exception):
    def __init__(self, status, message):
        self.status = status
        super().__init__(message)


def handle_requests(db, method, scope, request_id, email, payload):
    role, condition, request_type = SCOPES[scope]
    account = db.execute(
        f'SELECT u.user_id FROM "User" u JOIN {role} USING (user_id) WHERE u.email = ?',
        (email,),
    ).fetchone()
    if account is None:
        raise RequestError(403, "This demo account does not have access to these requests.")
    user_id = account["user_id"]
    if request_type:
        condition += " AND r.request_type = ?"
        params = (user_id, request_type)
    else:
        params = (user_id,)
    rows = REQUEST_ROWS + " WHERE " + condition

    if method == "POST":
        if scope != "resident" or request_id is not None:
            raise RequestError(405, "Residents submit new requests.")
        kind = payload.get("type")
        description = payload.get("description")
        household_id = payload.get("householdId")
        if kind not in REQUEST_TYPES or type(household_id) is not int:
            raise RequestError(400, "Choose a valid household and request type.")
        if not isinstance(description, str) or not 1 <= len(description.strip()) <= 2000:
            raise RequestError(400, "Enter a description of 1 to 2000 characters.")
        household = db.execute(
            "SELECT h.ra_user_id FROM Household h JOIN HouseholdMember m USING (household_id) "
            "WHERE h.household_id = ? AND m.user_id = ?",
            (household_id, user_id),
        ).fetchone()
        if household is None:
            raise RequestError(403, "This demo account does not belong to that household.")
        if kind == "RA Concern" and household["ra_user_id"] is None:
            raise RequestError(409, "This household has no assigned RA.")
        db.execute(
            "INSERT INTO Request (household_id, submitted_by_user_id, request_type, description) "
            "VALUES (?, ?, ?, ?)",
            (household_id, user_id, kind, description.strip()),
        )
    elif method == "PATCH":
        if scope == "resident" or request_id is None:
            raise RequestError(405, "Staff update the status of an assigned request.")
        status = payload.get("status")
        if status not in STATUSES:
            raise RequestError(400, "Choose a valid request status.")
        previous = db.execute('SELECT r.status ' + rows + ' AND r.request_id = ?', (*params, request_id)).fetchone()
        updated = db.execute(
            "UPDATE Request SET status = ? WHERE request_id = ? AND request_id IN ("
            "SELECT r.request_id " + rows + ")",
            (status, request_id, *params),
        )
        if not updated.rowcount:
            raise RequestError(404, "Request not found in your assigned queue.")
        if previous is not None and previous['status'] != status:
            db.execute("INSERT INTO RequestUpdate(request_id,updated_by_user_id,new_status,note,updated_at) VALUES(?,?,?,?,strftime('%Y-%m-%dT%H:%M:%fZ','now'))",
                       (request_id,user_id,status,text_note(payload.get('note','Status updated through web app'))))
    elif method != "GET":
        raise RequestError(405, "Unsupported request operation.")
    elif request_id is not None:
        raise RequestError(404, "Unknown route.")

    result = {"requests": [dict(row) for row in db.execute(
        "SELECT r.request_id AS id, r.request_type AS type, r.description, r.status, "
        "p.name AS property, h.unit_label AS unit, resident.name AS resident "
        + rows + " ORDER BY r.request_id DESC",
        params,
    )]}

    for request in result['requests']:
        request['history'] = [dict(r) for r in db.execute('SELECT ru.*,u.name AS author FROM RequestUpdate ru JOIN "User" u ON u.user_id=ru.updated_by_user_id WHERE request_id=? ORDER BY updated_at,update_id',(request['id'],))]
    return result


def text_note(note):
    if not isinstance(note,str) or len(note)>2000:
        raise RequestError(400,'Use a note of at most 2000 characters.')
    return note.strip()

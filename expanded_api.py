"""Household-scoped SQL operations for the local CSC4402 demonstration."""
from datetime import date
from decimal import Decimal, InvalidOperation
import re
from request_api import RequestError


def text(value, label):
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= 2000:
        raise RequestError(400, 'Enter ' + label + '.')
    return value.strip()


def money(value):
    try:
        amount = Decimal(str(value))
        if not amount.is_finite() or amount <= 0 or amount > 10000000 or amount != amount.quantize(Decimal('.01')):
            raise ValueError()
        return int(amount * 100)
    except (InvalidOperation, ValueError):
        raise RequestError(400, 'Enter a positive amount with at most two decimal places.')


def day(value):
    if not isinstance(value, str) or date.fromisoformat(value).isoformat() != value:
        raise RequestError(400, 'Use a valid YYYY-MM-DD date.')
    return value


def account(db, email):
    row = db.execute('SELECT * FROM "User" WHERE email=?', (email,)).fetchone()
    if row is None:
        raise RequestError(403, 'Use a seeded database demo account.')
    return row['user_id']


def access(db, user, household):
    row = db.execute('''SELECT h.*, p.name AS property, p.manager_user_id,
       EXISTS(SELECT 1 FROM HouseholdMember m WHERE m.household_id=h.household_id AND m.user_id=?) AS member
       FROM Household h JOIN Property p USING(property_id) WHERE household_id=?''', (user, household)).fetchone()
    if row is None or not (row['member'] or row['manager_user_id'] == user or row['ra_user_id'] == user):
        raise RequestError(403, 'This household is outside your assignments.')
    return row


def handle_expanded(db, method, path, email, payload):
    user = account(db, email)
    if path == '/api/database/households':
        if method == 'POST':
            prop = payload.get('propertyId')
            if db.execute('SELECT 1 FROM Property WHERE property_id=? AND manager_user_id=?', (prop, user)).fetchone() is None:
                raise RequestError(403, 'Choose a property you manage.')
            ra = payload.get('raId') or None
            db.execute('INSERT INTO Household(property_id,unit_label,ra_user_id) VALUES(?,?,?)', (prop, text(payload.get('unit'), 'a unit label'), ra))
        elif method != 'GET':
            raise RequestError(405, 'Use GET or POST.')
        households = [dict(r) for r in db.execute('''SELECT DISTINCT h.*,p.name AS property FROM Household h
           JOIN Property p USING(property_id) LEFT JOIN HouseholdMember m USING(household_id)
           WHERE m.user_id=? OR p.manager_user_id=? OR h.ra_user_id=? ORDER BY household_id''', (user,user,user))]
        return {'households': households, 'properties': [dict(r) for r in db.execute('SELECT property_id,name FROM Property WHERE manager_user_id=?',(user,))]}
    route = re.fullmatch(r'/api/database/households/([1-9]\d*)(?:/(expenses|announcements|leases|members)(?:/([1-9]\d*))?)?', path)
    if not route:
        raise RequestError(404, 'Unknown route.')
    household = int(route[1]); kind = route[2]; item = int(route[3]) if route[3] else None
    h = access(db,user,household)
    manager = h['manager_user_id'] == user
    if kind is None:
        if method != 'DELETE' or not manager:
            raise RequestError(403, 'Only the assigned manager can delete an empty household.')
        db.execute('DELETE FROM Household WHERE household_id=?',(household,))
        return {'deleted': household}
    if kind == 'members':
        if method != 'GET':
            raise RequestError(405,'Use GET.')
        return {'members':[dict(r) for r in db.execute('SELECT u.user_id,u.name FROM HouseholdMember m JOIN "User" u USING(user_id) WHERE household_id=? ORDER BY user_id',(household,))]}
    if kind == 'expenses':
        if not h['member']:
            raise RequestError(403,'Only household residents access shared expenses.')
        if method == 'POST' and item is None:
            total = money(payload.get('amount'))
            members = [r[0] for r in db.execute('SELECT user_id FROM HouseholdMember WHERE household_id=? ORDER BY user_id',(household,))]
            selected = payload.get('memberIds',members)
            if not isinstance(selected,list) or not selected or len(set(selected)) != len(selected) or any(type(i) is not int or i not in members for i in selected):
                raise RequestError(400,'Select distinct residents of this household.')
            payer = payload.get('paidById',user)
            if type(payer) is not int or payer not in members:
                raise RequestError(400,'The payer must belong to this household.')
            if total < len(selected):
                raise RequestError(400,'The total must allow at least one cent per person.')
            expense = db.execute('INSERT INTO Expense(household_id,paid_by_user_id,description,amount,expense_date) VALUES(?,?,?,?,?)',
                 (household,payer,text(payload.get('title'),'an expense title'),total/100,day(payload.get('date')))).lastrowid
            for index, resident in enumerate(selected):
                share = (total//len(selected) + (index < total%len(selected)))/100
                db.execute('INSERT INTO ExpenseShare VALUES(?,?,?,?,?)',(expense,household,resident,share,int(resident==payer)))
        elif method == 'PATCH' and item:
            paid = payload.get('paid')
            if type(paid) is not bool:
                raise RequestError(400,'Choose paid or unpaid.')
            changed = db.execute('UPDATE ExpenseShare SET is_paid=? WHERE expense_id=? AND household_id=? AND user_id=?',(int(paid),item,household,user))
            if not changed.rowcount:
                raise RequestError(404,'Your expense share was not found.')
        elif method == 'DELETE' and item:
            changed = db.execute('DELETE FROM Expense WHERE expense_id=? AND household_id=? AND paid_by_user_id=?',(item,household,user))
            if not changed.rowcount:
                raise RequestError(403,'Only the payer can delete this expense.')
        elif method != 'GET' or item:
            raise RequestError(405,'Unsupported expense operation.')
        return {'expenses':[dict(r) for r in db.execute('''SELECT CAST(e.expense_id AS TEXT) id,e.description title,e.amount totalAmount,
             COALESCE(es.share_amount,0) amount,e.expense_date due,u.name paidBy,
             COALESCE(es.is_paid,1) settled,'Other' category,0 recurring,
             (SELECT COUNT(*) FROM ExpenseShare s WHERE s.expense_id=e.expense_id) splitCount,
             e.paid_by_user_id=? canDelete
             FROM Expense e JOIN "User" u ON u.user_id=e.paid_by_user_id
             LEFT JOIN ExpenseShare es ON es.expense_id=e.expense_id AND es.user_id=?
             WHERE e.household_id=? ORDER BY e.expense_date,e.expense_id''',(user,user,household))]}
    if kind == 'announcements':
        if method == 'POST' and item is None:
            db.execute('INSERT INTO Announcement(household_id,posted_by_user_id,title,body,posted_at) VALUES(?,?,?,?,strftime(\'%Y-%m-%dT%H:%M:%fZ\',\'now\'))',
               (household,user,text(payload.get('title'),'a title'),text(payload.get('body'),'a message')))
        elif method == 'DELETE' and item:
            row = db.execute('SELECT posted_by_user_id FROM Announcement WHERE announcement_id=? AND household_id=?',(item,household)).fetchone()
            if row is None or (row[0] != user and not manager):
                raise RequestError(403,'Only the author or assigned manager can delete this announcement.')
            db.execute('DELETE FROM Announcement WHERE announcement_id=?',(item,))
        elif method != 'GET' or item:
            raise RequestError(405,'Unsupported announcement operation.')
        return {'announcements':[dict(r) for r in db.execute('SELECT a.*,u.name AS author,(a.posted_by_user_id=? OR ? ) AS canDelete FROM Announcement a JOIN "User" u ON u.user_id=a.posted_by_user_id WHERE household_id=? ORDER BY posted_at DESC,announcement_id DESC',(user,manager,household))]}
    if kind == 'leases':
        if method == 'POST' and item is None:
            if not manager:
                raise RequestError(403,'Only the assigned manager can create leases.')
            start=day(payload.get('start')); end=day(payload.get('end')); resident=payload.get('userId')
            if db.execute('SELECT 1 FROM Lease WHERE household_id=? AND user_id=? AND start_date<=? AND end_date>=?',(household,resident,end,start)).fetchone():
                raise RequestError(409,'This resident already has an overlapping lease in this household.')
            db.execute('INSERT INTO Lease(household_id,user_id,start_date,end_date,monthly_rent) VALUES(?,?,?,?,?)',(household,resident,start,end,money(payload.get('rent'))/100))
        elif method == 'DELETE' and item and manager:
            if not db.execute('DELETE FROM Lease WHERE lease_id=? AND household_id=?',(item,household)).rowcount:
                raise RequestError(404,'Lease not found.')
        elif method != 'GET' or item:
            raise RequestError(403,'Only the assigned manager can change leases.')
        if not (manager or h['member']):
            raise RequestError(403,'Lease access is limited to managers and the resident.')
        return {'leases':[dict(r) for r in db.execute('SELECT l.*,u.name AS resident FROM Lease l JOIN "User" u USING(user_id) WHERE household_id=? AND (? OR l.user_id=?) ORDER BY start_date,lease_id',(household,manager,user))]}
    raise RequestError(404,'Unknown route.')

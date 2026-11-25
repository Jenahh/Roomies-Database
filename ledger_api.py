"""Relational adapter for the existing Roomies expense ledger UI.

The ledger JSON is a transport format. Bills, shares, recurrence rules and
payments are stored in constrained SQLite relations, never as an opaque blob.
"""
from datetime import date
import hashlib
import json
from pathlib import Path
import re
from uuid import uuid4

from request_api import RequestError

CATEGORIES = ('Rent', 'Electricity', 'Groceries', 'Internet', 'Other')


def member_id(name):
    return 'name:' + re.sub(r'\s+', ' ', name.strip().lower())


def migrate_expenses(db):
    # Call during initial setup/startup, outside request transactions.
    db.executescript(Path(__file__).with_name('expense_extensions.sql').read_text(encoding='utf-8'))


def ledger_snapshot(db, household):
    people = db.execute('SELECT u.* FROM "User" u JOIN HouseholdMember m USING(user_id) WHERE m.household_id=? ORDER BY u.user_id', (household,)).fetchall()
    ids = {row['user_id']: member_id(row['name']) for row in people}
    if len(set(ids.values())) != len(ids):
        raise RequestError(409, 'This household has duplicate display names. Give its residents distinct names before using the expense ledger.')
    members = [{'id': ids[row['user_id']], 'name': row['name'], **({'manual': True} if row['email'].endswith('@roomies.demo') else {})} for row in people]
    rows = db.execute('''SELECT e.*,d.client_id,d.category,d.created_by_user_id,
        r.expense_id AS recurring_id,r.end_month FROM Expense e
        LEFT JOIN ExpenseDetail d USING(expense_id) LEFT JOIN ExpenseRecurrence r USING(expense_id)
        WHERE e.household_id=? ORDER BY e.expense_id''', (household,)).fetchall()
    expenses, payments = [], []
    for row in rows:
        shares = db.execute('SELECT * FROM ExpenseShare WHERE expense_id=? ORDER BY user_id', (row['expense_id'],)).fetchall()
        expense = {'id': row['client_id'] or 'expense:'+str(row['expense_id']), 'title': row['description'],
                   'category': row['category'] or next((c for c in CATEGORIES if c.lower() in row['description'].lower()), 'Other'),
                   'amountCents': round(row['amount']*100), 'paidBy': ids[row['paid_by_user_id']],
                   'splitAmong': sorted((ids[s['user_id']] for s in shares)), 'date': row['expense_date']}
        if row['recurring_id'] is not None:
            expense['recurring'] = {'endMonth': row['end_month']} if row['end_month'] else {}
        expenses.append(expense)
        # Existing CLI paid flags remain meaningful in the richer ledger. They
        # are projected as acknowledgements, not inserted twice as payments.
        for share in shares:
            if share['is_paid'] and share['user_id'] != row['paid_by_user_id'] and share['share_amount'] > 0:
                payments.append({'id': f"share:{row['expense_id']}:{share['user_id']}", 'from': ids[share['user_id']],
                                 'to': ids[row['paid_by_user_id']], 'amountCents': round(share['share_amount']*100), 'date': row['expense_date']})
    payments += [{'id': row['payment_id'], 'from': ids[row['from_user_id']], 'to': ids[row['to_user_id']],
                  'amountCents': row['amount_cents'], 'date': row['payment_date']} for row in db.execute('SELECT * FROM ExpensePayment WHERE household_id=? ORDER BY payment_date,payment_id', (household,))]
    ledger = {'version': 1, 'members': members, 'expenses': expenses, 'payments': payments}
    revision = hashlib.sha256(json.dumps(ledger, sort_keys=True, ensure_ascii=True, separators=(',', ':')).encode()).hexdigest()
    return {'ledger': ledger, 'revision': revision}


def clean_text(value, label, maximum=2000):
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= maximum:
        raise RequestError(400, 'Enter '+label+'.')
    return value.strip()


def valid_id(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9:_-]{1,100}', value):
        raise RequestError(400, 'Invalid ledger record identifier.')


def valid_day(value):
    if not isinstance(value, str) or date.fromisoformat(value).isoformat() != value:
        raise RequestError(400, 'Use a valid YYYY-MM-DD date.')


def valid_cents(value):
    if type(value) is not int or not 1 <= value <= 1000000000:
        raise RequestError(400, 'Enter a positive amount within the demo limit.')


def records(value, key):
    items = value.get(key)
    if not isinstance(items, list) or len(items) > 1000 or any(not isinstance(item, dict) or not isinstance(item.get('id'), str) for item in items):
        raise RequestError(400, 'Invalid '+key+'.')
    result = {item['id']: item for item in items}
    if len(result) != len(items):
        raise RequestError(400, 'Duplicate '+key+' identifiers.')
    return result


def apply_ledger(db, household, actor, before, after):
    if not isinstance(after, dict) or after.get('version') != 1:
        raise RequestError(400, 'Send a version 1 ledger.')
    old_members, members = records(before, 'members'), records(after, 'members')
    old_expenses, expenses = records(before, 'expenses'), records(after, 'expenses')
    old_payments, payments = records(before, 'payments'), records(after, 'payments')
    if not 1 <= len(members) <= 100:
        raise RequestError(400, 'Keep between 1 and 100 household members.')
    users = {member_id(row['name']): row['user_id'] for row in db.execute('SELECT u.user_id,u.name FROM "User" u JOIN HouseholdMember m USING(user_id) WHERE household_id=?', (household,))}
    for key, member in members.items():
        name = clean_text(member.get('name'), 'a name', 100)
        if member_id(name) != key:
            raise RequestError(400, 'The resident identifier must match their name.')
        if key in old_members:
            if member != old_members[key]:
                raise RequestError(400, 'Existing household identities cannot be renamed through expenses.')
        else:
            if member.get('manual') is not True:
                raise RequestError(400, 'New expense participants must be added through Add person.')
            user = db.execute('INSERT INTO "User"(name,email) VALUES(?,?)', (name, 'member-'+uuid4().hex+'@roomies.demo')).lastrowid
            db.execute('INSERT INTO Resident VALUES(?)', (user,))
            db.execute('INSERT INTO HouseholdMember VALUES(?,?)', (household,user))
            users[key] = user
    for key, expense in expenses.items():
        valid_id(key)
        clean_text(expense.get('title'), 'an expense title')
        valid_cents(expense.get('amountCents')); valid_day(expense.get('date'))
        split = expense.get('splitAmong')
        if expense.get('category') not in CATEGORIES or expense.get('paidBy') not in members:
            raise RequestError(400, 'Choose a category and household payer.')
        if not isinstance(split, list) or not split or any(not isinstance(p, str) or p not in members for p in split) or len(set(split)) != len(split) or expense['amountCents'] < len(split):
            raise RequestError(400, 'Split among distinct members of this household, at least one cent each.')
        if 'recurring' in expense:
            recurrence = expense['recurring']
            if not isinstance(recurrence, dict) or set(recurrence)-{'endMonth'}:
                raise RequestError(400, 'Invalid monthly recurrence rule.')
            end = recurrence.get('endMonth')
            if end is not None and (not isinstance(end, str) or not re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])', end) or end < expense['date'][:7]):
                raise RequestError(400, 'A recurrence cannot end before its first month.')
        if key in old_expenses:
            original = old_expenses[key]
            if {k:v for k,v in original.items() if k != 'recurring'} != {k:v for k,v in expense.items() if k != 'recurring'}:
                raise RequestError(400, 'Add or delete bills; only the recurrence end can be changed on an existing bill.')
            if original.get('recurring') != expense.get('recurring') or ('recurring' in original) != ('recurring' in expense):
                row = db.execute('SELECT e.expense_id,e.paid_by_user_id,d.created_by_user_id FROM Expense e LEFT JOIN ExpenseDetail d USING(expense_id) WHERE e.household_id=? AND COALESCE(d.client_id,\'expense:\'||e.expense_id)=?', (household,key)).fetchone()
                if actor not in (row['paid_by_user_id'], row['created_by_user_id']):
                    raise RequestError(403, 'Only the payer or author can stop a recurring bill.')
                if 'recurring' not in original or 'recurring' not in expense:
                    raise RequestError(400, 'Use Stop repeating to end a monthly bill.')
                db.execute('UPDATE ExpenseRecurrence SET end_month=? WHERE expense_id=?', (expense['recurring'].get('endMonth'),row['expense_id']))
        else:
            if key.startswith(('expense:', 'share:')):
                raise RequestError(400, 'Use a new client identifier for a new bill.')
            total = expense['amountCents']
            result = db.execute('INSERT INTO Expense(household_id,paid_by_user_id,description,amount,expense_date) VALUES(?,?,?,?,?)', (household,users[expense['paidBy']],expense['title'].strip(),total/100,expense['date']))
            db.execute('INSERT INTO ExpenseDetail VALUES(?,?,?,?)', (result.lastrowid,key,expense['category'],actor))
            ordered = sorted(split, key=lambda value: value.encode('utf-16-be'))
            for index, person in enumerate(ordered):
                share = total//len(split) + (index < total%len(split))
                db.execute('INSERT INTO ExpenseShare VALUES(?,?,?,?,?)', (result.lastrowid,household,users[person],share/100,int(person==expense['paidBy'])))
            if 'recurring' in expense:
                db.execute('INSERT INTO ExpenseRecurrence VALUES(?,?)', (result.lastrowid,expense['recurring'].get('endMonth')))
    for key in old_expenses.keys()-expenses.keys():
        row = db.execute('SELECT e.expense_id,e.paid_by_user_id,d.created_by_user_id FROM Expense e LEFT JOIN ExpenseDetail d USING(expense_id) WHERE e.household_id=? AND COALESCE(d.client_id,\'expense:\'||e.expense_id)=?', (household,key)).fetchone()
        if actor not in (row['paid_by_user_id'], row['created_by_user_id']):
            raise RequestError(403, 'Only the payer or author can delete this bill.')
        db.execute('DELETE FROM Expense WHERE expense_id=?', (row['expense_id'],))
    for key, payment in payments.items():
        valid_id(key); valid_cents(payment.get('amountCents')); valid_day(payment.get('date'))
        if payment.get('from') not in members or payment.get('to') not in members or payment['from']==payment['to']:
            raise RequestError(400, 'Payments must be between distinct household members.')
        if key in old_payments:
            if payment != old_payments[key]:
                raise RequestError(400, 'Undo a payment before recording a corrected one.')
        else:
            if key.startswith('share:') or actor not in (users[payment['from']],users[payment['to']]):
                raise RequestError(403, 'Only the sender or recipient can record a payment.')
            db.execute('INSERT INTO ExpensePayment VALUES(?,?,?,?,?,?)', (key,household,users[payment['from']],users[payment['to']],payment['amountCents'],payment['date']))
    for key in old_payments.keys()-payments.keys():
        original = old_payments[key]
        if actor not in (users[original['from']],users[original['to']]):
            raise RequestError(403, 'Only a payment participant can undo it.')
        if key.startswith('share:'):
            _, expense, resident = key.split(':')
            db.execute('UPDATE ExpenseShare SET is_paid=0 WHERE expense_id=? AND user_id=? AND household_id=?', (int(expense),int(resident),household))
        else:
            db.execute('DELETE FROM ExpensePayment WHERE payment_id=? AND household_id=?', (key,household))
    for key in old_members.keys()-members.keys():
        person = users[key]
        if not old_members[key].get('manual') or person==actor:
            raise RequestError(403, 'Only an unused person added through expenses can be removed.')
        # Foreign keys reject a participant still used by bills, payments,
        # chores, requests or leases. All previous mutations then roll back.
        db.execute('DELETE FROM HouseholdMember WHERE household_id=? AND user_id=?', (household,person))
        db.execute('DELETE FROM Resident WHERE user_id=?', (person,))
        db.execute('DELETE FROM "User" WHERE user_id=?', (person,))


def handle_ledger(db, method, household, actor, payload):
    if not db.in_transaction:
        db.execute('BEGIN')
    current = ledger_snapshot(db, household)
    if method == 'POST':
        if payload.get('revision') != current['revision']:
            raise RequestError(409, 'Another resident changed this ledger. The latest data has been loaded; review it and try again.')
        apply_ledger(db, household, actor, current['ledger'], payload.get('ledger'))
        return ledger_snapshot(db, household)
    if method != 'GET':
        raise RequestError(405, 'Use GET or POST for the expense ledger.')
    return current

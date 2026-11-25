# Expense integration: local review addendum

The isolated CSC4402 build now reuses Roomies' ExpensesScreen, balance cards,
monthly-bill controls, and settle-up assistant. A replacement ledger hook sends
the same component's changes to SQLite. The original app checkout and its normal
build are unchanged. This is not published or merged.

## Start the integrated build

The current local build is ready. Stop the old preview with Ctrl+C and run:

```powershell
python web_preview.py --frontend .\web\roomies
```

Open http://127.0.0.1:8080/demo/#bills. Use Alex, Mia or Sam. To rebuild later:

```powershell
python prepare_roomies.py --source ..\roomies-github-current --database-expenses
```

The build helper overrides only the ledger hook and its identity argument in
memory. It type-checks the resulting app, then emits compiled files into the
ignored web/roomies folder. It does not copy or edit the React source project.
Include that compiled folder explicitly in an eventual self-contained upload.
Selecting an ordinary dist folder instead keeps the older database bill forms
as a fallback; it does not claim that the browser-local ledger is integrated.

## Data and behavior

| Roomies operation | Relational storage |
| --- | --- |
| Add/delete a bill; choose payer and split participants | Expense and ExpenseShare |
| Select Rent, Electricity, Internet, Groceries or Other | ExpenseDetail.category |
| Repeat monthly / stop repeating | ExpenseRecurrence, linked to the first Expense |
| Record/undo payment, including settle-up suggestions | ExpensePayment |
| Add a person / remove an unused person | User, Resident and HouseholdMember |
| Refresh another resident's view | GET the same household ledger from SQLite |

The ledger JSON is a response format, not a JSON column storing the database.
Every write and all dependent records commit together. A revision hash rejects
stale updates rather than overwriting changes made by another resident. Failed
writes reload committed rows and display the database error.

Only residents access the ledger for households they belong to. The payer or
bill author can delete a bill or stop its recurrence. A payment's sender or
recipient can record or undo it. New people become real household members;
people still referenced by bills, payments, chores, requests or leases cannot
be removed. New manual participants are not additional hard-coded demo logins.

Currency calculations use integer cents and the original Roomies algorithms.
Remainder cents follow the same name-ID ordering in both API variants. Balances
and the settlement plan use the expense shares and recorded transfers. CLI
paid-share flags are projected as payment acknowledgements so they still affect
balances; undoing such an acknowledgement clears the original share flag.

The old CLI paid flags and a net settlement balance answer different questions:
queries based only on ExpenseShare.is_paid list unacknowledged individual shares;
they do not subtract separately recorded optimized transfers. Use the ledger's
net balances to determine what a resident still owes overall.

Recurring bills store one base Expense plus a monthly rule. The existing Roomies
algorithm expands the rule into one occurrence per month, clipping dates to the
last valid day (for example October 31, November 30, December 31). Generated
months are derived occurrences, not duplicate Expense rows. An end month is
inclusive. Deleting a recurring bill deletes its base and rule for all months,
matching the original screen's confirmation. Historical recorded payments
remain until explicitly undone, as in the original Roomies ledger.

## Additions to the relational schema

The matching E-R extension is [panel E (PDF)](er-e-expense-ledger.pdf), with a
[PNG version](er-e-expense-ledger.png) for the editable report. It follows the
same rectangle, diamond, key-underlining and cardinality style as panels A–D.

These three relations bring the design to 18 tables: 17 enterprise/supporting
relations plus the optional ChoreDisplay relation. They are defined in
expense_extensions.sql, executed by roomies.py init and by the additive startup
migration for an older working database.

**ExpenseDetail(expense_id, client_id, category, created_by_user_id).** PK and FK:
expense_id -> Expense, with cascading deletion. client_id is unique; category is
one of the five expense categories. Optional FK created_by_user_id -> User
records the author where available. An Expense has zero or one detail row.

**ExpenseRecurrence(expense_id, end_month).** PK and FK: expense_id -> Expense,
with cascading deletion. end_month is optional and uses YYYY-MM. Triggers reject
an end month earlier than the expense's first month. An Expense has zero or one
recurrence rule; its date and shares define the first occurrence and participants.

**ExpensePayment(payment_id, household_id, from_user_id, to_user_id,
amount_cents, payment_date).** PK: payment_id. FK household_id -> Household.
Composite FKs (household_id, from_user_id) and (household_id, to_user_id) ->
HouseholdMember(household_id, user_id). Sender and recipient must differ; cents
must be a positive integer and the payment date must be valid.

An old working database is backed up as *-before-ledger.sqlite3 before its first
upgrade. Existing expense/share rows are preserved. The main supplied database
contains the expanded schema and original seed rows; recurrence/payment tables
start empty and are populated when those workflows are demonstrated.

## Verification and report updates

```powershell
python -m unittest discover -v
node test_web_ui.mjs
node test_roomies_ledger.mjs
python roomies.py test
python verify_demo.py
```

The native-ledger check runs the actual Roomies financial algorithms against a
temporary live HTTP/SQLite server. A $10 monthly bill split among Alex, Mia and
Sam produces $3.34 / $3.33 / $3.33 each month. Over October–December the balances
are +$19.98 / -$9.99 / -$9.99. The assistant proposes two $9.99 payments; recording
them gives zero balances. Undoing a payment restores a debt. Stopping the rule
after November leaves two occurrences through June of the next year.

These checks are not a visual browser/device test. Review the enlarged screens,
expense modals, and prominent Details button in the local preview.

Before submitting the final report, add the three relations and their E-R panel,
replace the older expense-interface description/illustration with the reused
Roomies screen, and explain recurring rules and net transfers as above. The
existing PDF/DOCX has not been silently rewritten during this local preview.
The original five main queries and six supplemental seed results remain valid
for their supplied data; additional expense checks are executable in the test
files. Query 6 describes individual unpaid-share flags, not the new net balance;
clarify that wording if showing it beside the richer expense screen.

-- Additive migration: preserves existing expenses, shares and demo data.
CREATE TABLE IF NOT EXISTS ExpenseDetail (
    expense_id INTEGER PRIMARY KEY REFERENCES Expense(expense_id) ON DELETE CASCADE,
    client_id TEXT NOT NULL UNIQUE,
    category TEXT NOT NULL CHECK(category IN ('Rent','Electricity','Groceries','Internet','Other')),
    created_by_user_id INTEGER REFERENCES "User"(user_id)
);
CREATE TABLE IF NOT EXISTS ExpenseRecurrence (
    expense_id INTEGER PRIMARY KEY REFERENCES Expense(expense_id) ON DELETE CASCADE,
    end_month TEXT CHECK(end_month IS NULL OR (length(end_month)=7 AND date(end_month||'-01','+0 days') IS end_month||'-01'))
);
CREATE TABLE IF NOT EXISTS ExpensePayment (
    payment_id TEXT PRIMARY KEY NOT NULL,
    household_id INTEGER NOT NULL REFERENCES Household(household_id),
    from_user_id INTEGER NOT NULL,
    to_user_id INTEGER NOT NULL,
    amount_cents INTEGER NOT NULL CHECK(typeof(amount_cents)='integer' AND amount_cents>0 AND amount_cents<=1000000000),
    payment_date TEXT NOT NULL CHECK(date(payment_date,'+0 days') IS payment_date),
    CHECK(from_user_id<>to_user_id),
    FOREIGN KEY(household_id,from_user_id) REFERENCES HouseholdMember(household_id,user_id),
    FOREIGN KEY(household_id,to_user_id) REFERENCES HouseholdMember(household_id,user_id)
);
CREATE TRIGGER IF NOT EXISTS recurrence_end_after_start_insert BEFORE INSERT ON ExpenseRecurrence
WHEN NEW.end_month IS NOT NULL AND NEW.end_month < (SELECT substr(expense_date,1,7) FROM Expense WHERE expense_id=NEW.expense_id)
BEGIN SELECT RAISE(ABORT,'Recurrence cannot end before its first month'); END;
CREATE TRIGGER IF NOT EXISTS recurrence_end_after_start_update BEFORE UPDATE ON ExpenseRecurrence
WHEN NEW.end_month IS NOT NULL AND NEW.end_month < (SELECT substr(expense_date,1,7) FROM Expense WHERE expense_id=NEW.expense_id)
BEGIN SELECT RAISE(ABORT,'Recurrence cannot end before its first month'); END;
CREATE TRIGGER IF NOT EXISTS recurrence_start_before_end BEFORE UPDATE OF expense_date ON Expense
WHEN EXISTS(SELECT 1 FROM ExpenseRecurrence r WHERE r.expense_id=NEW.expense_id AND r.end_month<substr(NEW.expense_date,1,7))
BEGIN SELECT RAISE(ABORT,'First expense date cannot follow recurrence end'); END;

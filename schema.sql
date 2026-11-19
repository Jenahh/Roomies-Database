PRAGMA foreign_keys = ON;

CREATE TABLE "User" (
    user_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE
);

CREATE TABLE PropertyManager (
    user_id INTEGER PRIMARY KEY REFERENCES "User"(user_id)
);

CREATE TABLE ResidentAssistant (
    user_id INTEGER PRIMARY KEY REFERENCES "User"(user_id)
);

CREATE TABLE Resident (
    user_id INTEGER PRIMARY KEY REFERENCES "User"(user_id)
);

CREATE TABLE Property (
    property_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    manager_user_id INTEGER NOT NULL REFERENCES PropertyManager(user_id)
);

CREATE TABLE Household (
    household_id INTEGER PRIMARY KEY,
    property_id INTEGER NOT NULL REFERENCES Property(property_id),
    unit_label TEXT NOT NULL,
    ra_user_id INTEGER REFERENCES ResidentAssistant(user_id),
    UNIQUE (property_id, unit_label)
);

CREATE TABLE HouseholdMember (
    household_id INTEGER NOT NULL REFERENCES Household(household_id),
    user_id INTEGER NOT NULL REFERENCES Resident(user_id),
    PRIMARY KEY (household_id, user_id)
);

CREATE TABLE Chore (
    chore_id INTEGER PRIMARY KEY,
    household_id INTEGER NOT NULL REFERENCES Household(household_id),
    assigned_user_id INTEGER,
    title TEXT NOT NULL CHECK (length(trim(title)) > 0),
    due_date TEXT NOT NULL CHECK (date(due_date, '+0 days') IS due_date),
    status TEXT NOT NULL DEFAULT 'Pending' CHECK (status IN ('Pending', 'Completed')),
    FOREIGN KEY (household_id, assigned_user_id)
        REFERENCES HouseholdMember(household_id, user_id)
);

CREATE TABLE Request (
    request_id INTEGER PRIMARY KEY,
    household_id INTEGER NOT NULL REFERENCES Household(household_id),
    submitted_by_user_id INTEGER NOT NULL,
    request_type TEXT NOT NULL CHECK (request_type IN ('Maintenance', 'RA Concern')),
    description TEXT NOT NULL CHECK (length(trim(description)) > 0),
    status TEXT NOT NULL DEFAULT 'Open' CHECK (status IN ('Open', 'In Progress', 'Closed')),
    FOREIGN KEY (household_id, submitted_by_user_id)
        REFERENCES HouseholdMember(household_id, user_id)
);

CREATE TABLE Expense (
    expense_id INTEGER PRIMARY KEY,
    household_id INTEGER NOT NULL REFERENCES Household(household_id),
    paid_by_user_id INTEGER NOT NULL,
    description TEXT NOT NULL CHECK (length(trim(description)) > 0),
    amount REAL NOT NULL CHECK (amount > 0),
    expense_date TEXT NOT NULL CHECK (date(expense_date, '+0 days') IS expense_date),
    FOREIGN KEY (household_id, paid_by_user_id)
        REFERENCES HouseholdMember(household_id, user_id)
);

CREATE TABLE ExpenseShare (
    expense_id INTEGER NOT NULL REFERENCES Expense(expense_id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES Resident(user_id),
    share_amount REAL NOT NULL CHECK (share_amount >= 0),
    is_paid INTEGER NOT NULL DEFAULT 0 CHECK (is_paid IN (0, 1)),
    PRIMARY KEY (expense_id, user_id)
);

CREATE TABLE Announcement (
    announcement_id INTEGER PRIMARY KEY,
    household_id INTEGER NOT NULL REFERENCES Household(household_id),
    posted_by_user_id INTEGER NOT NULL REFERENCES "User"(user_id),
    title TEXT NOT NULL CHECK (length(trim(title)) > 0),
    body TEXT NOT NULL CHECK (length(trim(body)) > 0),
    posted_at TEXT NOT NULL CHECK (date(posted_at, '+0 days') IS posted_at)
);

CREATE TABLE RequestUpdate (
    update_id INTEGER PRIMARY KEY,
    request_id INTEGER NOT NULL REFERENCES Request(request_id) ON DELETE CASCADE,
    updated_by_user_id INTEGER NOT NULL REFERENCES "User"(user_id),
    new_status TEXT NOT NULL CHECK (new_status IN ('Open', 'In Progress', 'Closed')),
    note TEXT,
    updated_at TEXT NOT NULL CHECK (date(updated_at, '+0 days') IS updated_at)
);

CREATE TABLE Lease (
    lease_id INTEGER PRIMARY KEY,
    household_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    start_date TEXT NOT NULL CHECK (date(start_date, '+0 days') IS start_date),
    end_date TEXT NOT NULL CHECK (date(end_date, '+0 days') IS end_date),
    monthly_rent REAL NOT NULL CHECK (monthly_rent > 0),
    CHECK (end_date > start_date),
    FOREIGN KEY (household_id, user_id)
        REFERENCES HouseholdMember(household_id, user_id)
);

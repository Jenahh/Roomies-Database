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

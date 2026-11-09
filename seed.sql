INSERT INTO "User" VALUES
    (1, 'Alex', 'alex@example.com'), (2, 'Mia', 'mia@example.com'),
    (3, 'Sam', 'sam@example.com'), (4, 'Riley', 'riley@example.com'),
    (10, 'Jordan', 'jordan@example.com'), (11, 'Taylor', 'taylor@example.com'),
    (12, 'Morgan', 'morgan@example.com'), (13, 'Casey', 'casey@example.com');

INSERT INTO Resident VALUES (1), (2), (3), (4);
INSERT INTO PropertyManager VALUES (10), (12);
INSERT INTO ResidentAssistant VALUES (11), (13);
INSERT INTO Property VALUES (1, 'Cypress Apartments', 10), (2, 'Oak Commons', 12);
INSERT INTO Household VALUES (1, 1, '2A', 11), (2, 2, '3B', 13);
INSERT INTO HouseholdMember VALUES (1, 1), (1, 2), (1, 3), (2, 4);

INSERT INTO Chore VALUES
    (1, 1, 2, 'Take out trash', '2026-11-03', 'Pending'),
    (2, 1, 3, 'Clean kitchen', '2026-11-07', 'Pending'),
    (3, 1, NULL, 'Vacuum living room', '2026-11-08', 'Pending'),
    (4, 1, 2, 'Wipe counters', '2026-11-04', 'Completed'),
    (5, 2, 4, 'Sweep hallway', '2026-11-02', 'Pending');

INSERT INTO Request VALUES
    (1, 1, 1, 'Maintenance', 'Leaking kitchen sink', 'Open'),
    (2, 1, 2, 'RA Concern', 'Roommate conflict over quiet hours', 'Open'),
    (3, 2, 4, 'Maintenance', 'Broken window latch', 'Open'),
    (4, 2, 4, 'RA Concern', 'Help discussing guest expectations', 'Open'),
    (5, 1, 3, 'Maintenance', 'Replace hallway light', 'Closed');

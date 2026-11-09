-- 1. Residents of Household 1
SELECT u.name AS resident
FROM HouseholdMember AS hm
JOIN "User" AS u ON u.user_id = hm.user_id
WHERE hm.household_id = 1
ORDER BY u.name;

-- 2. Overdue pending chores as of November 5, 2026
SELECT c.title, COALESCE(u.name, 'Unassigned') AS assignee, c.due_date
FROM Chore AS c
LEFT JOIN "User" AS u ON u.user_id = c.assigned_user_id
WHERE c.household_id = 1 AND c.status = 'Pending' AND c.due_date < '2026-11-05'
ORDER BY c.due_date, c.chore_id;

-- 3. Pending chores per resident, including zero
SELECT u.name AS resident, COUNT(c.chore_id) AS pending_chores
FROM HouseholdMember AS hm
JOIN "User" AS u ON u.user_id = hm.user_id
LEFT JOIN Chore AS c ON c.household_id = hm.household_id
    AND c.assigned_user_id = hm.user_id AND c.status = 'Pending'
WHERE hm.household_id = 1
GROUP BY u.user_id, u.name
ORDER BY u.name;

-- 4. Jordan's open maintenance requests
SELECT p.name AS property, h.unit_label, r.description
FROM Request AS r
JOIN Household AS h ON h.household_id = r.household_id
JOIN Property AS p ON p.property_id = h.property_id
WHERE p.manager_user_id = 10 AND r.request_type = 'Maintenance' AND r.status = 'Open'
ORDER BY p.name, h.unit_label, r.request_id;

-- 5. Taylor's open RA concerns
SELECT p.name AS property, h.unit_label, r.description
FROM Request AS r
JOIN Household AS h ON h.household_id = r.household_id
JOIN Property AS p ON p.property_id = h.property_id
WHERE h.ra_user_id = 11 AND r.request_type = 'RA Concern' AND r.status = 'Open'
ORDER BY p.name, h.unit_label, r.request_id;

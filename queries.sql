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

-- 6. Unpaid shares each resident owes in Household 1
SELECT u.name AS resident, SUM(es.share_amount) AS amount_owed
FROM ExpenseShare AS es
JOIN Expense AS e ON e.expense_id = es.expense_id
JOIN "User" AS u ON u.user_id = es.user_id
WHERE e.household_id = 1 AND es.is_paid = 0
    AND es.user_id <> e.paid_by_user_id
GROUP BY u.user_id, u.name
ORDER BY amount_owed DESC, u.name;

-- 7. Total household spending in November 2026
SELECT p.name AS property, h.unit_label, SUM(e.amount) AS total_spent
FROM Expense AS e
JOIN Household AS h ON h.household_id = e.household_id
JOIN Property AS p ON p.property_id = h.property_id
WHERE e.expense_date BETWEEN '2026-11-01' AND '2026-11-30'
GROUP BY h.household_id, p.name, h.unit_label
ORDER BY total_spent DESC;

-- 8. Announcements for Household 1, newest first
SELECT a.posted_at, u.name AS posted_by, a.title
FROM Announcement AS a
JOIN "User" AS u ON u.user_id = a.posted_by_user_id
WHERE a.household_id = 1
ORDER BY a.posted_at DESC, a.announcement_id DESC;

-- 9. Status history of the hallway light request
SELECT ru.updated_at, u.name AS updated_by, ru.new_status, ru.note
FROM RequestUpdate AS ru
JOIN "User" AS u ON u.user_id = ru.updated_by_user_id
WHERE ru.request_id = 5
ORDER BY ru.updated_at, ru.update_id;

-- 10. Leases ending within 60 days of November 19, 2026
SELECT u.name AS resident, p.name AS property, h.unit_label, l.end_date
FROM Lease AS l
JOIN "User" AS u ON u.user_id = l.user_id
JOIN Household AS h ON h.household_id = l.household_id
JOIN Property AS p ON p.property_id = h.property_id
WHERE l.end_date BETWEEN '2026-11-19' AND date('2026-11-19', '+60 days')
ORDER BY l.end_date;

-- 11. Total monthly rent per unit
SELECT p.name AS property, h.unit_label, COUNT(*) AS residents,
    SUM(l.monthly_rent) AS total_rent
FROM Lease AS l
JOIN Household AS h ON h.household_id = l.household_id
JOIN Property AS p ON p.property_id = h.property_id
GROUP BY h.household_id, p.name, h.unit_label
ORDER BY p.name, h.unit_label;

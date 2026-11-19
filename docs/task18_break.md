# Task 18 – Break-it notes

Minimum group size: 5 people (from the project's metric dictionary).
Population: active, current employees (440). The Executive Office (1 person) is excluded.
Demo assignments: HR user = Human Resources, Manager user = Design Systems (the CSV gives no department or team).

| # | Attack | Result | Fix |
|---|---|---|---|
| 1 | Department table including the Executive Office | Shows a group of 1: leaks one person's data | Excluded the Executive Office from the view `v_kpi_people` |
| 2 | Counting rows instead of people | dim_employee has 1,606 rows for 745 people (job-change history), so groups looked bigger than they were | Filtered to current, active rows and counted distinct employee IDs |
| 3 | Admin, Product & Design, break down by Team | One person has no team, so 1 hidden group could be found by subtracting the visible teams from the department total of 26 | Complementary suppression: Design Systems is hidden together with the 1-person group |
| 4 | Admin, Design Systems team, gender, filter Remote | Stacked filters leave 1–2 people | Whole filtered population and every group are checked before display. Result: 🔒 message |
| 5 | Manager, City tier | The team has 10 people, almost all in Tier 1: one tiny group plus a nearly complete one | All hidden, with a clear message |
| 6 | HR, pay for Engineering | Pay detail outside own department | Blocked server-side with a red error, not only by hiding options |
| 7 | Drill-down dropdowns | A dropdown could list a small team's name and let the user open it | Dropdowns list only groups of 5 or more |
| 8 | Role switching in the sidebar | Old selections could carry over | Each role has its own widget keys, and every request is re-checked against the role rules |
| 9 | Executive | Tries for team or pay data | No Level selector and no pay metric |

Known limitation: someone who runs many different queries could still compare results between them. Minimum group size plus complementary suppression handles single queries. A next step would be rounding counts to the nearest 5.

Live link re-test: (fill in after the redeploy)
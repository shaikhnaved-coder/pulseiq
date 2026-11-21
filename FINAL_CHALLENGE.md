# Final Challenge: overdue receivables KPI on the scorecard

Branch: `final-challenge-overdue-kpi` (commit afc5217)
File changed: `phase-3/app/pages/Scorecard.py` (28 lines added). The database and the 8 existing KPIs were not changed.

## What I decided
I added a new KPI card to the executive scorecard: **overdue receivables**, the money customers owe past the due date.

## Why I chose it
- The scorecard already shows how fast customers pay (days sales outstanding), but not how much money is overdue. A board needs both.
- The number already existed and was already tied out in Phase 3 (metric M21), so I could trust it: 27,110,866 across 13 overdue invoices and 9 clients.
- It was small enough to build and test safely on its own branch.

## What I decided not to do
- I did not change the `v_scorecard` view. It lives inside the database file, and changing it could break the 8 existing cards, the API and the live app. I read the M21 view from the page instead.
- I did not give the card a green, amber or red colour. The data has no overdue target, so a colour would be invented. The card shows a grey NO TARGET badge.
- I did not make up earlier months. The M21 view has one snapshot (30 Sep 2026), so the card shows only for Sep 2026 and is hidden for other months.

## How I checked it
- Before writing code, I checked that the view's total for 30 Sep 2026 equals the number I tied out in Phase 3 (27,110,866).
- I ran the app locally. Sep 2026 shows the new card (₹27.11 M, 13 invoices, 9 clients). Aug 2026 does not show it, and the 8 original cards are unchanged.

## Limits
- One month only (Sep 2026), because the view holds one snapshot.
- No target, so no traffic light.
- Next step: store overdue receivables for every month so the card can show a trend, and agree a target with finance.
# Category budgets and spending statuses
Source: `student-4/backend/Services/DashboardCalculator.cs`, `student-4/docs/requirements.md` | Reviewed: 2026-10-01 | General application guidance only; no saved journey totals.

Set a positive limit for each budget category and its date period. The dashboard groups planned and actual minor-unit amounts by category and shows each category's remaining amount and percentage used. Review category totals separately; a journey-wide total does not replace a category limit.

The budget status uses the unrounded actual-to-planned ratio: below 80 percent is `within_budget`; from 80 percent through exactly 100 percent is `warning`; strictly above 100 percent is `overspent`. The displayed percentage is rounded to two decimal places, but the status decision uses the unrounded ratio.
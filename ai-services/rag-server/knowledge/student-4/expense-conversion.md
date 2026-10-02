# Expense entry and conversion snapshots
Source: `student-4/backend/Api/BudgetEndpoints.cs`, `student-4/backend/Services/ExchangeRateProvider.cs`, `student-4/backend/appsettings.json` | Reviewed: 2026-10-01 | Demonstration configuration, not live market data.

Record an expense against its budget with a description, positive amount, original currency, and date inside the budget period. The backend converts from the original currency to the budget's base currency using configured decimal rates, rounds once to minor units with midpoint values away from zero, and saves the converted amount with the applied rate and rate date as a historical snapshot.

The configured exchange rates are fixed demonstration values, not live or current market rates. The sample configuration is version `demo-2026-08-v1`, dated 2026-08-01; do not use it to make a current exchange-rate decision. A saved expense's conversion snapshot records the rate used for that save.
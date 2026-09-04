using BudgetTracker.Backend.Api;

namespace BudgetTracker.Backend.Services;

public static class DashboardCalculator
{
    public static DashboardResponse Calculate(string journeyLabel, IReadOnlyList<BudgetResponse> budgets, IReadOnlyList<ExpenseDataResponse> expenses)
    {
        if (budgets.Count == 0 || budgets.Any(value => !string.Equals(value.JourneyLabel, journeyLabel, StringComparison.OrdinalIgnoreCase)))
        {
            throw new DashboardDataException();
        }
        var baseCurrency = budgets[0].BaseCurrency;
        if (budgets.Any(value => value.BaseCurrency != baseCurrency))
        {
            throw new DashboardDataException();
        }

        var budgetIds = budgets.Select(value => value.Id).ToHashSet();
        if (expenses.Any(value => !budgetIds.Contains(value.BudgetId)))
        {
            throw new DashboardDataException();
        }

        var categories = budgets
            .GroupBy(value => value.Category, StringComparer.OrdinalIgnoreCase)
            .Select(group =>
            {
                var ids = group.Select(value => value.Id).ToHashSet();
                var planned = group.Sum(value => value.LimitAmountMinor);
                var actual = expenses.Where(value => ids.Contains(value.BudgetId)).Sum(value => value.ConvertedAmountMinor);
                return new CategoryDashboardResponse(group.Key, planned, actual, planned - actual, Percentage(actual, planned), Status(actual, planned));
            })
            .OrderBy(value => value.Category, StringComparer.Ordinal)
            .ToArray();
        var totalPlanned = categories.Sum(value => value.PlannedAmountMinor);
        var totalActual = categories.Sum(value => value.ActualAmountMinor);
        return new(journeyLabel, baseCurrency, totalPlanned, totalActual, totalPlanned - totalActual, Percentage(totalActual, totalPlanned), categories);
    }

    private static decimal Percentage(long actual, long planned) => planned == 0 ? 0 : Math.Round(actual * 100m / planned, 2, MidpointRounding.AwayFromZero);
    private static string Status(long actual, long planned)
    {
        var percentage = actual * 100m / planned;
        return percentage > 100 ? "overspent" : percentage >= 80 ? "warning" : "within_budget";
    }
}

public sealed class DashboardDataException : Exception
{
    public DashboardDataException() : base("The database API returned inconsistent dashboard data.")
    {
    }
}
using BudgetTracker.Backend.Api;

namespace BudgetTracker.Backend.Services;

public static class DashboardCalculator
{
    private const long MaxSafeAmountMinor = 9_007_199_254_740_991;

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

    public static DashboardResponse CalculateWhatIf(DashboardResponse original, IReadOnlyList<WhatIfLimit> proposed)
    {
        if (original is null || original.Categories is null || original.Categories.Count is not (>= 1 and <= 6) ||
            !SafeAmounts(original.PlannedAmountMinor, original.ActualAmountMinor, original.RemainingAmountMinor))
        {
            throw new DashboardDataException();
        }

        var sourceCategories = new HashSet<string>(StringComparer.Ordinal);
        foreach (var value in original.Categories)
        {
            var category = value?.Category?.Trim().ToLowerInvariant();
            if (category is null || !Validation.Categories.Contains(category) || !sourceCategories.Add(category) ||
                !SafeAmounts(value!.PlannedAmountMinor, value.ActualAmountMinor, value.RemainingAmountMinor))
            {
                throw new DashboardDataException();
            }
        }
        if (original.Categories.Sum(value => value.PlannedAmountMinor) != original.PlannedAmountMinor ||
            original.Categories.Sum(value => value.ActualAmountMinor) != original.ActualAmountMinor)
        {
            throw new DashboardDataException();
        }

        if (proposed is null || proposed.Count is not (>= 1 and <= 6) || proposed.Count != sourceCategories.Count)
        {
            throw new ArgumentException("Propose the complete existing category set once each (1 to 6 entries).", nameof(proposed));
        }

        var limits = new Dictionary<string, long>(StringComparer.Ordinal);
        var totalPlanned = 0L;
        foreach (var value in proposed)
        {
            var category = value?.Category?.Trim().ToLowerInvariant();
            if (category is null || !sourceCategories.Contains(category))
            {
                throw new ArgumentException("Every proposal must name an existing supported category.", nameof(proposed));
            }
            if (value!.LimitAmountMinor is <= 0 or > MaxSafeAmountMinor)
            {
                throw new ArgumentException("Each proposed limit must be positive and at most 9_007_199_254_740_991 minor units.", nameof(proposed));
            }
            if (!limits.TryAdd(category, value.LimitAmountMinor))
            {
                throw new ArgumentException("Each existing category must be proposed exactly once; duplicate category found.", nameof(proposed));
            }
            if (value.LimitAmountMinor > MaxSafeAmountMinor - totalPlanned)
            {
                throw new ArgumentException("The proposed total must not exceed 9_007_199_254_740_991 minor units.", nameof(proposed));
            }
            totalPlanned += value.LimitAmountMinor;
        }

        var categories = original.Categories.Select(value =>
        {
            var planned = limits[value.Category.Trim().ToLowerInvariant()];
            return value with
            {
                PlannedAmountMinor = planned,
                RemainingAmountMinor = planned - value.ActualAmountMinor,
                PercentageUsed = Percentage(value.ActualAmountMinor, planned),
                Status = Status(value.ActualAmountMinor, planned)
            };
        }).ToArray();
        return original with
        {
            PlannedAmountMinor = totalPlanned,
            RemainingAmountMinor = totalPlanned - original.ActualAmountMinor,
            PercentageUsed = Percentage(original.ActualAmountMinor, totalPlanned),
            Categories = categories
        };
    }

    private static bool SafeAmounts(long planned, long actual, long remaining) =>
        planned is > 0 and <= MaxSafeAmountMinor && actual is >= 0 and <= MaxSafeAmountMinor && remaining == planned - actual;

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
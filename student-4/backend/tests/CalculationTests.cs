using BudgetTracker.Backend.Api;
using BudgetTracker.Backend.Services;

namespace BudgetTracker.Backend.Tests;

public sealed class CalculationTests
{
    private static readonly FixedExchangeRateProvider Rates = new(new ExchangeRateSettings(
        "test-v1",
        new DateOnly(2026, 8, 1),
        "Test rates.",
        new Dictionary<string, decimal> { ["AUD"] = 1m, ["USD"] = 0.65m, ["EUR"] = 0.6m }));

    [Fact]
    public void ConversionUsesDecimalRateAndRoundsOnlyFinalMinorUnit()
    {
        var result = Rates.Convert(101, "USD", "AUD");

        Assert.Equal(155, result.ConvertedAmountMinor);
        Assert.Equal(153846154, result.RateScaled);
        Assert.Equal(new DateOnly(2026, 8, 1), result.RateAsOf);
        Assert.Equal("test-v1", result.RateVersion);
    }

    [Fact]
    public void UnsupportedCurrencyIsRejected()
    {
        Assert.False(Rates.Supports("JPY"));
        Assert.Throws<ArgumentException>(() => Rates.Convert(100, "JPY", "AUD"));
    }

    [Fact]
    public void DashboardAggregatesCategoriesAndUsesExactThresholds()
    {
        var budgets = new[]
        {
            Budget(1, "food", 10000),
            Budget(2, "transport", 10000),
            Budget(3, "shopping", 10000)
        };
        var expenses = new[]
        {
            Expense(1, 7999),
            Expense(2, 8000),
            Expense(3, 10001)
        };

        var dashboard = DashboardCalculator.Calculate("Journey", budgets, expenses);

        Assert.Equal(30000, dashboard.PlannedAmountMinor);
        Assert.Equal(26000, dashboard.ActualAmountMinor);
        Assert.Equal(4000, dashboard.RemainingAmountMinor);
        Assert.Equal("within_budget", dashboard.Categories.Single(value => value.Category == "food").Status);
        Assert.Equal("warning", dashboard.Categories.Single(value => value.Category == "transport").Status);
        Assert.Equal("overspent", dashboard.Categories.Single(value => value.Category == "shopping").Status);
    }

    private static BudgetResponse Budget(int id, string category, long limit) => new(id, "Journey", category, limit, "AUD", new(2026, 9, 1), new(2026, 9, 7), DateTime.UtcNow, DateTime.UtcNow);
    private static ExpenseDataResponse Expense(int budgetId, long converted) => new(budgetId, budgetId, "Expense", converted, "AUD", converted, 100000000, new(2026, 8, 1), new(2026, 9, 2), null, DateTime.UtcNow, DateTime.UtcNow);
}
using BudgetTracker.Backend.Api;
using BudgetTracker.Backend.Services;

namespace BudgetTracker.Backend.Tests;

public sealed class CalculationTests
{
    private const long MaxSafeAmountMinor = 9_007_199_254_740_991;

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

    [Fact]
    public void WhatIfChangesExactLimitsWithoutMutatingSourceOrProposal()
    {
        var original = DashboardCalculator.Calculate("Journey",
            new[] { Budget(1, "food", 10000), Budget(2, "transport", 20000) },
            new[] { Expense(1, 8000), Expense(2, 3000) });
        var snapshot = original with { };
        var sourceCategories = original.Categories.ToArray();
        var proposed = new[] { new WhatIfLimit(" TRANSPORT ", 12000), new WhatIfLimit(" Food ", 6000) };
        var proposalSnapshot = proposed.ToArray();

        var preview = DashboardCalculator.CalculateWhatIf(original, proposed);

        Assert.NotSame(original, preview);
        Assert.NotSame(original.Categories, preview.Categories);
        Assert.Equal(original.JourneyLabel, preview.JourneyLabel);
        Assert.Equal(original.BaseCurrency, preview.BaseCurrency);
        Assert.Equal(18000, preview.PlannedAmountMinor);
        Assert.Equal(original.ActualAmountMinor, preview.ActualAmountMinor);
        Assert.Equal(11000, preview.ActualAmountMinor);
        Assert.Equal(7000, preview.RemainingAmountMinor);
        Assert.Equal(61.11m, preview.PercentageUsed);
        Assert.Equal(new CategoryDashboardResponse("food", 6000, 8000, -2000, 133.33m, "overspent"), preview.Categories[0]);
        Assert.Equal(new CategoryDashboardResponse("transport", 12000, 3000, 9000, 25m, "within_budget"), preview.Categories[1]);
        Assert.All(preview.Categories, category => Assert.NotSame(sourceCategories.Single(value => value.Category == category.Category), category));
        Assert.Equal(snapshot, original);
        Assert.Equal(sourceCategories, original.Categories.ToArray());
        Assert.Equal(proposalSnapshot, proposed);
    }

    [Fact]
    public void WhatIfSupportsAllSixExistingCategoriesWithDifferentLimits()
    {
        var names = new[] { "accommodation", "food", "transport", "activities", "shopping", "other" };
        var original = DashboardCalculator.Calculate("Journey",
            names.Select((category, index) => Budget(index + 1, category, 10000)).ToArray(),
            Array.Empty<ExpenseDataResponse>());
        var proposed = names.Select((category, index) => new WhatIfLimit($" {category.ToUpperInvariant()} ", index + 1)).Reverse().ToArray();

        var preview = DashboardCalculator.CalculateWhatIf(original, proposed);

        Assert.Equal(21, preview.PlannedAmountMinor);
        Assert.Equal(0, preview.ActualAmountMinor);
        Assert.Equal(21, preview.RemainingAmountMinor);
        Assert.Equal(0m, preview.PercentageUsed);
        foreach (var category in preview.Categories)
        {
            var expected = Array.IndexOf(names, category.Category) + 1;
            Assert.Equal(expected, category.PlannedAmountMinor);
            Assert.Equal(0, category.ActualAmountMinor);
            Assert.Equal(expected, category.RemainingAmountMinor);
            Assert.Equal(0m, category.PercentageUsed);
            Assert.Equal("within_budget", category.Status);
        }
    }

    [Theory]
    [InlineData(0, 10000, 0, "within_budget")]
    [InlineData(7999, 10000, 7999, "within_budget")]
    [InlineData(8000, 10000, 8000, "warning")]
    [InlineData(10000, 10000, 10000, "warning")]
    [InlineData(10001, 10000, 10001, "overspent")]
    [InlineData(799999, 1000000, 8000, "within_budget")]
    public void WhatIfUsesExactThresholdsBeforePercentageRounding(long actual, long proposedLimit, int percentageHundredths, string status)
    {
        var original = DashboardCalculator.Calculate("Journey", new[] { Budget(1, "food", proposedLimit * 2) }, new[] { Expense(1, actual) });

        var preview = DashboardCalculator.CalculateWhatIf(original, new[] { new WhatIfLimit("food", proposedLimit) });

        Assert.Equal(actual, preview.ActualAmountMinor);
        Assert.Equal(proposedLimit - actual, preview.RemainingAmountMinor);
        Assert.Equal(percentageHundredths / 100m, preview.PercentageUsed);
        Assert.Equal(preview.PercentageUsed, preview.Categories[0].PercentageUsed);
        Assert.Equal(actual, preview.Categories[0].ActualAmountMinor);
        Assert.Equal(proposedLimit - actual, preview.Categories[0].RemainingAmountMinor);
        Assert.Equal(status, preview.Categories[0].Status);
    }

    [Theory]
    [MemberData(nameof(InvalidWhatIfProposals))]
    public void WhatIfRejectsInvalidOrIncompleteCategorySets(IReadOnlyList<WhatIfLimit> proposed)
    {
        var original = DashboardCalculator.Calculate("Journey",
            new[] { Budget(1, "food", 10000), Budget(2, "transport", 10000) }, Array.Empty<ExpenseDataResponse>());

        var error = Assert.Throws<ArgumentException>(() => DashboardCalculator.CalculateWhatIf(original, proposed));

        Assert.Equal("proposed", error.ParamName);
        Assert.False(string.IsNullOrWhiteSpace(error.Message));
    }

    public static IEnumerable<object[]> InvalidWhatIfProposals()
    {
        yield return new object[] { null! };
        yield return new object[] { Array.Empty<WhatIfLimit>() };
        yield return new object[] { new[] { new WhatIfLimit("food", 100) } };
        yield return new object[] { new WhatIfLimit[] { null!, new("transport", 100) } };
        foreach (var category in new string?[] { null, "", "   ", "fuel", "shopping", " FOOD " })
        {
            yield return new object[] { new[] { new WhatIfLimit("food", 100), new WhatIfLimit(category, 100) } };
        }
        yield return new object[] { Enumerable.Repeat(new WhatIfLimit("food", 100), 7).ToArray() };
    }

    [Theory]
    [InlineData(0)]
    [InlineData(-1)]
    [InlineData(MaxSafeAmountMinor + 1)]
    [InlineData(long.MaxValue)]
    [InlineData(long.MinValue)]
    public void WhatIfRejectsNonpositiveOrUnsafeLimits(long amount)
    {
        var original = DashboardCalculator.Calculate("Journey", new[] { Budget(1, "food", 10000) }, Array.Empty<ExpenseDataResponse>());

        var error = Assert.Throws<ArgumentException>(() => DashboardCalculator.CalculateWhatIf(original, new[] { new WhatIfLimit("food", amount) }));

        Assert.Equal("proposed", error.ParamName);
        Assert.Contains("positive", error.Message);
    }

    [Fact]
    public void WhatIfRejectsProposedTotalAboveSafeIntegerLimit()
    {
        var original = DashboardCalculator.Calculate("Journey",
            new[] { Budget(1, "food", 10000), Budget(2, "transport", 10000) }, Array.Empty<ExpenseDataResponse>());

        var error = Assert.Throws<ArgumentException>(() => DashboardCalculator.CalculateWhatIf(original,
            new[] { new WhatIfLimit("food", MaxSafeAmountMinor), new WhatIfLimit("transport", 1) }));

        Assert.Contains("total", error.Message);
    }

    [Fact]
    public void WhatIfAcceptsProposedTotalAtSafeIntegerLimit()
    {
        var original = DashboardCalculator.Calculate("Journey",
            new[] { Budget(1, "food", 10000), Budget(2, "transport", 10000) }, Array.Empty<ExpenseDataResponse>());

        var preview = DashboardCalculator.CalculateWhatIf(original,
            new[] { new WhatIfLimit("food", MaxSafeAmountMinor - 1), new WhatIfLimit("transport", 1) });

        Assert.Equal(MaxSafeAmountMinor, preview.PlannedAmountMinor);
        Assert.Equal(MaxSafeAmountMinor, preview.RemainingAmountMinor);
        Assert.Equal(MaxSafeAmountMinor - 1, preview.Categories[0].PlannedAmountMinor);
    }

    [Fact]
    public void WhatIfKeepsMaximumSafeActualAndNegativeRemainingExact()
    {
        var original = DashboardCalculator.Calculate("Journey", new[] { Budget(1, "food", MaxSafeAmountMinor) }, new[] { Expense(1, MaxSafeAmountMinor) });

        var preview = DashboardCalculator.CalculateWhatIf(original, new[] { new WhatIfLimit("food", 1) });
        var unchangedLimit = DashboardCalculator.CalculateWhatIf(original, new[] { new WhatIfLimit("food", MaxSafeAmountMinor) });

        Assert.Equal(MaxSafeAmountMinor, preview.ActualAmountMinor);
        Assert.Equal(MaxSafeAmountMinor, preview.Categories[0].ActualAmountMinor);
        Assert.Equal(1 - MaxSafeAmountMinor, preview.RemainingAmountMinor);
        Assert.Equal(preview.RemainingAmountMinor, preview.Categories[0].RemainingAmountMinor);
        Assert.Equal(MaxSafeAmountMinor * 100m, preview.PercentageUsed);
        Assert.Equal("overspent", preview.Categories[0].Status);
        Assert.Equal(0, unchangedLimit.RemainingAmountMinor);
        Assert.Equal(100m, unchangedLimit.PercentageUsed);
        Assert.Equal("warning", unchangedLimit.Categories[0].Status);
    }

    [Theory]
    [MemberData(nameof(InvalidWhatIfSources))]
    public void WhatIfRejectsUnsafeOrInconsistentSourceData(DashboardResponse original)
    {
        Assert.Throws<DashboardDataException>(() => DashboardCalculator.CalculateWhatIf(original, new[] { new WhatIfLimit("food", 100) }));
    }

    public static IEnumerable<object[]> InvalidWhatIfSources()
    {
        var original = DashboardCalculator.Calculate("Journey", new[] { Budget(1, "food", 10000) }, new[] { Expense(1, 8000) });
        var category = original.Categories[0];
        yield return new object[] { null! };
        yield return new object[] { original with { Categories = null! } };
        yield return new object[] { original with { Categories = Array.Empty<CategoryDashboardResponse>() } };
        yield return new object[] { original with { Categories = new CategoryDashboardResponse[] { null! } } };
        yield return new object[] { original with { Categories = Enumerable.Repeat(category, 7).ToArray() } };
        yield return new object[] { original with { Categories = new[] { category, category with { Category = " FOOD " } } } };
        foreach (var name in new string?[] { null, "", "   ", "fuel" })
        {
            yield return new object[] { original with { Categories = new[] { category with { Category = name! } } } };
        }
        foreach (var amount in new[] { MaxSafeAmountMinor + 1, -MaxSafeAmountMinor - 1, long.MaxValue, long.MinValue })
        {
            yield return new object[] { original with { PlannedAmountMinor = amount } };
            yield return new object[] { original with { ActualAmountMinor = amount } };
            yield return new object[] { original with { RemainingAmountMinor = amount } };
            yield return new object[] { original with { Categories = new[] { category with { PlannedAmountMinor = amount } } } };
            yield return new object[] { original with { Categories = new[] { category with { ActualAmountMinor = amount } } } };
            yield return new object[] { original with { Categories = new[] { category with { RemainingAmountMinor = amount } } } };
        }
        yield return new object[] { original with { PlannedAmountMinor = 0 } };
        yield return new object[] { original with { ActualAmountMinor = -1 } };
        yield return new object[] { original with { RemainingAmountMinor = 2001 } };
        yield return new object[] { original with { Categories = new[] { category with { PlannedAmountMinor = 0 } } } };
        yield return new object[] { original with { Categories = new[] { category with { ActualAmountMinor = -1 } } } };
        yield return new object[] { original with { Categories = new[] { category with { RemainingAmountMinor = 2001 } } } };
        yield return new object[] { original with { PlannedAmountMinor = 10001, RemainingAmountMinor = 2001 } };
        yield return new object[] { original with { ActualAmountMinor = 8001, RemainingAmountMinor = 1999 } };
        yield return new object[] { original with
        {
            PlannedAmountMinor = MaxSafeAmountMinor,
            ActualAmountMinor = 0,
            RemainingAmountMinor = MaxSafeAmountMinor,
            Categories = new[]
            {
                new CategoryDashboardResponse("food", MaxSafeAmountMinor, 0, MaxSafeAmountMinor, 0, "within_budget"),
                new CategoryDashboardResponse("transport", 1, 0, 1, 0, "within_budget")
            }
        } };
        yield return new object[] { original with
        {
            PlannedAmountMinor = 2,
            ActualAmountMinor = MaxSafeAmountMinor,
            RemainingAmountMinor = 2 - MaxSafeAmountMinor,
            Categories = new[]
            {
                new CategoryDashboardResponse("food", 1, MaxSafeAmountMinor, 1 - MaxSafeAmountMinor, 0, "overspent"),
                new CategoryDashboardResponse("transport", 1, 1, 0, 100, "warning")
            }
        } };
    }

    private static BudgetResponse Budget(int id, string category, long limit) => new(id, "Journey", category, limit, "AUD", new(2026, 9, 1), new(2026, 9, 7), DateTime.UtcNow, DateTime.UtcNow);
    private static ExpenseDataResponse Expense(int budgetId, long converted) => new(budgetId, budgetId, "Expense", converted, "AUD", converted, 100000000, new(2026, 8, 1), new(2026, 9, 2), null, DateTime.UtcNow, DateTime.UtcNow);
}
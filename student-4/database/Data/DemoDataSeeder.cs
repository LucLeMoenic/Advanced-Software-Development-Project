using Microsoft.EntityFrameworkCore;

namespace BudgetTracker.Database.Data;

public static class DemoDataSeeder
{
    private static readonly DateOnly RateDate = new(2026, 8, 1);

    public static async Task SeedAsync(BudgetDbContext database, CancellationToken cancellationToken = default)
    {
        await using var transaction = await database.Database.BeginTransactionAsync(cancellationToken);
        var now = DateTime.UtcNow;
        var budgetSeeds = new[]
        {
            new BudgetSeed("Sydney Weekender", "accommodation", 120000, "AUD", new(2026, 10, 1), new(2026, 10, 7)),
            new BudgetSeed("Sydney Weekender", "food", 50000, "AUD", new(2026, 10, 1), new(2026, 10, 7)),
            new BudgetSeed("Sydney Weekender", "transport", 30000, "AUD", new(2026, 10, 1), new(2026, 10, 7)),
            new BudgetSeed("Sydney Weekender", "activities", 40000, "AUD", new(2026, 10, 1), new(2026, 10, 7)),
            new BudgetSeed("Sydney Weekender", "shopping", 20000, "AUD", new(2026, 10, 1), new(2026, 10, 7)),
            new BudgetSeed("Sydney Weekender", "other", 10000, "AUD", new(2026, 10, 1), new(2026, 10, 7)),
            new BudgetSeed("Europe Escape", "accommodation", 180000, "EUR", new(2026, 11, 1), new(2026, 11, 10)),
            new BudgetSeed("Europe Escape", "food", 70000, "EUR", new(2026, 11, 1), new(2026, 11, 10)),
            new BudgetSeed("Europe Escape", "transport", 65000, "EUR", new(2026, 11, 1), new(2026, 11, 10)),
            new BudgetSeed("Europe Escape", "activities", 50000, "EUR", new(2026, 11, 1), new(2026, 11, 10)),
            new BudgetSeed("Europe Escape", "shopping", 25000, "EUR", new(2026, 11, 1), new(2026, 11, 10)),
            new BudgetSeed("Europe Escape", "other", 15000, "EUR", new(2026, 11, 1), new(2026, 11, 10))
        };

        foreach (var seed in budgetSeeds)
        {
            var exists = await database.Budgets.AnyAsync(value =>
                value.JourneyLabel == seed.JourneyLabel
                && value.Category == seed.Category
                && value.StartDate == seed.StartDate
                && value.EndDate == seed.EndDate,
                cancellationToken);
            if (!exists)
            {
                database.Budgets.Add(new Budget
                {
                    JourneyLabel = seed.JourneyLabel,
                    Category = seed.Category,
                    LimitAmountMinor = seed.LimitAmountMinor,
                    BaseCurrency = seed.BaseCurrency,
                    StartDate = seed.StartDate,
                    EndDate = seed.EndDate,
                    CreatedAt = now,
                    UpdatedAt = now
                });
            }
        }

        await database.SaveChangesAsync(cancellationToken);
        var budgets = await database.Budgets.ToDictionaryAsync(
            value => BudgetKey(value.JourneyLabel, value.Category, value.StartDate, value.EndDate),
            StringComparer.OrdinalIgnoreCase,
            cancellationToken);
        var expenseSeeds = new[]
        {
            Expense("Sydney Weekender", "accommodation", "Harbour hotel deposit", 60000, "AUD", 60000, 100000000, new(2026, 10, 1)),
            Expense("Sydney Weekender", "accommodation", "Harbour hotel balance", 43125, "USD", 66346, 153846154, new(2026, 10, 5)),
            Expense("Sydney Weekender", "food", "Market lunches", 20000, "AUD", 20000, 100000000, new(2026, 10, 2)),
            Expense("Sydney Weekender", "food", "Dinner bookings", 13550, "USD", 20846, 153846154, new(2026, 10, 6)),
            Expense("Sydney Weekender", "transport", "Airport train", 4200, "AUD", 4200, 100000000, new(2026, 10, 1)),
            Expense("Sydney Weekender", "transport", "Ferry fares", 7800, "AUD", 7800, 100000000, new(2026, 10, 4)),
            Expense("Sydney Weekender", "activities", "Museum passes", 9600, "AUD", 9600, 100000000, new(2026, 10, 3)),
            Expense("Sydney Weekender", "activities", "Bridge tour", 15000, "AUD", 15000, 100000000, new(2026, 10, 5)),
            Expense("Sydney Weekender", "shopping", "Local gifts", 8400, "AUD", 8400, 100000000, new(2026, 10, 6)),
            Expense("Sydney Weekender", "shopping", "Art print", 3200, "NZD", 2963, 92592593, new(2026, 10, 6)),
            Expense("Sydney Weekender", "other", "Travel supplies", 2500, "AUD", 2500, 100000000, new(2026, 10, 1)),
            Expense("Sydney Weekender", "other", "Luggage storage", 1800, "AUD", 1800, 100000000, new(2026, 10, 7)),
            Expense("Europe Escape", "accommodation", "Paris apartment", 95000, "EUR", 95000, 100000000, new(2026, 11, 1)),
            Expense("Europe Escape", "accommodation", "Rome hotel", 78000, "EUR", 78000, 100000000, new(2026, 11, 6)),
            Expense("Europe Escape", "food", "Cafe budget", 30000, "EUR", 30000, 100000000, new(2026, 11, 3)),
            Expense("Europe Escape", "food", "Restaurant bookings", 28000, "EUR", 28000, 100000000, new(2026, 11, 8)),
            Expense("Europe Escape", "transport", "Rail pass", 52000, "EUR", 52000, 100000000, new(2026, 11, 2)),
            Expense("Europe Escape", "transport", "London transit", 8800, "GBP", 10353, 117647059, new(2026, 11, 5)),
            Expense("Europe Escape", "activities", "Gallery tickets", 14000, "EUR", 14000, 100000000, new(2026, 11, 4)),
            Expense("Europe Escape", "activities", "Walking tours", 21000, "EUR", 21000, 100000000, new(2026, 11, 9)),
            Expense("Europe Escape", "shopping", "Books and gifts", 17000, "EUR", 17000, 100000000, new(2026, 11, 9)),
            Expense("Europe Escape", "shopping", "Design market", 6000, "GBP", 7059, 117647059, new(2026, 11, 5)),
            Expense("Europe Escape", "other", "Laundry", 3200, "EUR", 3200, 100000000, new(2026, 11, 7)),
            Expense("Europe Escape", "other", "City taxes", 4500, "EUR", 4500, 100000000, new(2026, 11, 10))
        };

        foreach (var seed in expenseSeeds)
        {
            var budgetSeed = budgetSeeds.Single(value =>
                value.JourneyLabel == seed.JourneyLabel
                && value.Category == seed.Category);
            var budget = budgets[BudgetKey(
                budgetSeed.JourneyLabel,
                budgetSeed.Category,
                budgetSeed.StartDate,
                budgetSeed.EndDate)];
            var exists = await database.Expenses.AnyAsync(value =>
                value.BudgetId == budget.Id
                && value.Description == seed.Description
                && value.SpentOn == seed.SpentOn,
                cancellationToken);
            if (!exists)
            {
                database.Expenses.Add(new Expense
                {
                    BudgetId = budget.Id,
                    Description = seed.Description,
                    OriginalAmountMinor = seed.OriginalAmountMinor,
                    OriginalCurrency = seed.OriginalCurrency,
                    ConvertedAmountMinor = seed.ConvertedAmountMinor,
                    ConversionRateScaled = seed.ConversionRateScaled,
                    RateAsOf = RateDate,
                    SpentOn = seed.SpentOn,
                    Notes = "Release 0 demonstration data.",
                    CreatedAt = now,
                    UpdatedAt = now
                });
            }
        }

        await database.SaveChangesAsync(cancellationToken);
        await transaction.CommitAsync(cancellationToken);
    }

    private static string BudgetKey(
        string journeyLabel,
        string category,
        DateOnly startDate,
        DateOnly endDate) => $"{journeyLabel}|{category}|{startDate:yyyy-MM-dd}|{endDate:yyyy-MM-dd}";

    private static ExpenseSeed Expense(
        string journeyLabel,
        string category,
        string description,
        long originalAmountMinor,
        string originalCurrency,
        long convertedAmountMinor,
        long conversionRateScaled,
        DateOnly spentOn) => new(
            journeyLabel,
            category,
            description,
            originalAmountMinor,
            originalCurrency,
            convertedAmountMinor,
            conversionRateScaled,
            spentOn);

    private sealed record BudgetSeed(
        string JourneyLabel,
        string Category,
        long LimitAmountMinor,
        string BaseCurrency,
        DateOnly StartDate,
        DateOnly EndDate);

    private sealed record ExpenseSeed(
        string JourneyLabel,
        string Category,
        string Description,
        long OriginalAmountMinor,
        string OriginalCurrency,
        long ConvertedAmountMinor,
        long ConversionRateScaled,
        DateOnly SpentOn);
}
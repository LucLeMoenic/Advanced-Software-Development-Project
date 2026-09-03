using System.Net.Http.Json;
using BudgetTracker.Database.Api;
using BudgetTracker.Database.Data;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.Data.Sqlite;
using Microsoft.Extensions.DependencyInjection;

namespace BudgetTracker.Database.Tests;

public sealed class SeedTests
{
    [Fact]
    public async Task SeedIsIdempotentAndExceedsRequiredCounts()
    {
        var databasePath = Path.Combine(Path.GetTempPath(), $"student4-seed-{Guid.NewGuid():N}.db");
        try
        {
            await using var factory = new WebApplicationFactory<Program>().WithWebHostBuilder(builder =>
            {
                builder.UseSetting("ConnectionStrings:BudgetDatabase", $"Data Source={databasePath}");
                builder.UseSetting("DemoData:Seed", "true");
            });
            using var client = factory.CreateClient();

            var initialBudgets = await client.GetFromJsonAsync<BudgetResponse[]>("/api/data/budgets");
            var initialExpenses = await client.GetFromJsonAsync<ExpenseResponse[]>("/api/data/expenses");
            Assert.Equal(12, initialBudgets!.Length);
            Assert.Equal(24, initialExpenses!.Length);
            Assert.True(initialBudgets.Select(value => value.JourneyLabel).Distinct().Count() >= 2);
            Assert.True(initialExpenses.Select(value => value.OriginalCurrency).Distinct().Count() >= 4);
            var usdSnapshot = initialExpenses.Single(value => value.Description == "Harbour hotel balance");
            Assert.Equal(66346, usdSnapshot.ConvertedAmountMinor);
            Assert.Equal(153846154, usdSnapshot.ConversionRateScaled);
            var gbpSnapshot = initialExpenses.Single(value => value.Description == "London transit");
            Assert.Equal(10353, gbpSnapshot.ConvertedAmountMinor);
            Assert.Equal(117647059, gbpSnapshot.ConversionRateScaled);

            await using var scope = factory.Services.CreateAsyncScope();
            var database = scope.ServiceProvider.GetRequiredService<BudgetDbContext>();
            await DemoDataSeeder.SeedAsync(database);

            Assert.Equal(12, (await client.GetFromJsonAsync<BudgetResponse[]>("/api/data/budgets"))!.Length);
            Assert.Equal(24, (await client.GetFromJsonAsync<ExpenseResponse[]>("/api/data/expenses"))!.Length);
        }
        finally
        {
            SqliteConnection.ClearAllPools();
            File.Delete(databasePath);
        }
    }

    [Fact]
    public async Task SeedAllowsAnotherPeriodForAnExistingJourneyCategory()
    {
        var databasePath = Path.Combine(Path.GetTempPath(), $"student4-seed-period-{Guid.NewGuid():N}.db");
        try
        {
            await using var factory = new WebApplicationFactory<Program>().WithWebHostBuilder(builder =>
            {
                builder.UseSetting("ConnectionStrings:BudgetDatabase", $"Data Source={databasePath}");
                builder.UseSetting("DemoData:Seed", "true");
            });
            using var client = factory.CreateClient();
            var response = await client.PostAsJsonAsync("/api/data/budgets", new BudgetRequest(
                "Sydney Weekender", "food", 30000, "AUD", new(2027, 1, 1), new(2027, 1, 7)));
            response.EnsureSuccessStatusCode();

            await using var scope = factory.Services.CreateAsyncScope();
            var database = scope.ServiceProvider.GetRequiredService<BudgetDbContext>();
            await DemoDataSeeder.SeedAsync(database);

            Assert.Equal(13, (await client.GetFromJsonAsync<BudgetResponse[]>("/api/data/budgets"))!.Length);
            Assert.Equal(24, (await client.GetFromJsonAsync<ExpenseResponse[]>("/api/data/expenses"))!.Length);
        }
        finally
        {
            SqliteConnection.ClearAllPools();
            File.Delete(databasePath);
        }
    }

    [Fact]
    public async Task SeedHandlesCaseOnlyJourneyLabelChanges()
    {
        var databasePath = Path.Combine(Path.GetTempPath(), $"student4-seed-case-{Guid.NewGuid():N}.db");
        try
        {
            await using var factory = new WebApplicationFactory<Program>().WithWebHostBuilder(builder =>
            {
                builder.UseSetting("ConnectionStrings:BudgetDatabase", $"Data Source={databasePath}");
                builder.UseSetting("DemoData:Seed", "true");
            });
            using var client = factory.CreateClient();
            var budgets = await client.GetFromJsonAsync<BudgetResponse[]>("/api/data/budgets");
            var food = budgets!.Single(value => value.JourneyLabel == "Sydney Weekender" && value.Category == "food");
            var update = await client.PutAsJsonAsync($"/api/data/budgets/{food.Id}", new BudgetRequest(
                "sydney weekender", food.Category, food.LimitAmountMinor, food.BaseCurrency, food.StartDate, food.EndDate));
            update.EnsureSuccessStatusCode();

            await using var scope = factory.Services.CreateAsyncScope();
            var database = scope.ServiceProvider.GetRequiredService<BudgetDbContext>();
            await DemoDataSeeder.SeedAsync(database);

            Assert.Equal(12, (await client.GetFromJsonAsync<BudgetResponse[]>("/api/data/budgets"))!.Length);
            Assert.Equal(24, (await client.GetFromJsonAsync<ExpenseResponse[]>("/api/data/expenses"))!.Length);
        }
        finally
        {
            SqliteConnection.ClearAllPools();
            File.Delete(databasePath);
        }
    }
}
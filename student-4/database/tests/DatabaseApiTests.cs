using System.Net;
using System.Net.Http.Json;
using BudgetTracker.Database.Api;
using Microsoft.Data.Sqlite;

namespace BudgetTracker.Database.Tests;

public sealed class DatabaseApiTests : DatabaseApiTestBase
{
    [Fact]
    public async Task MigrationCreatesBothTablesAndHealthUsesSqlite()
    {
        var health = await Client.GetAsync("/health");
        health.EnsureSuccessStatusCode();

        await using var connection = new SqliteConnection($"Data Source={DatabasePath}");
        await connection.OpenAsync();
        await using var command = connection.CreateCommand();
        command.CommandText = "SELECT count(*) FROM sqlite_master WHERE type='table' AND name IN ('budgets','expenses')";
        Assert.Equal(2L, (long)(await command.ExecuteScalarAsync())!);
    }

    [Fact]
    public async Task BudgetCrudAndFiltersUseNormalizedValues()
    {
        var created = await CreateBudgetAsync("  Coastal Break  ", "FOOD");
        Assert.Equal("Coastal Break", created.JourneyLabel);
        Assert.Equal("food", created.Category);

        var found = await Client.GetFromJsonAsync<BudgetResponse>($"/api/data/budgets/{created.Id}", JsonOptions);
        Assert.Equal(created.Id, found!.Id);

        var update = await Client.PutAsJsonAsync($"/api/data/budgets/{created.Id}", new BudgetRequest(
            "Coastal Break", "food", 62000, "aud", new(2026, 9, 1), new(2026, 9, 8)));
        update.EnsureSuccessStatusCode();
        var updated = await update.Content.ReadFromJsonAsync<BudgetResponse>(JsonOptions);
        Assert.Equal(62000, updated!.LimitAmountMinor);
        Assert.Equal("AUD", updated.BaseCurrency);

        var filtered = await Client.GetFromJsonAsync<BudgetResponse[]>(
            "/api/data/budgets?journeyLabel=Coastal%20Break&category=food&fromDate=2026-09-04&toDate=2026-09-04",
            JsonOptions);
        Assert.Single(filtered!);

        Assert.Equal(HttpStatusCode.NoContent, (await Client.DeleteAsync($"/api/data/budgets/{created.Id}")).StatusCode);
        Assert.Equal(HttpStatusCode.NotFound, (await Client.GetAsync($"/api/data/budgets/{created.Id}")).StatusCode);
    }

    [Fact]
    public async Task ExpenseCrudFiltersAndExactIntegerStorageWork()
    {
        var budget = await CreateBudgetAsync("Ledger Journey", "food");
        var expense = await CreateExpenseAsync(budget.Id, "Cafe lunch", 1337);

        var update = await Client.PutAsJsonAsync($"/api/data/expenses/{expense.Id}", new ExpenseRequest(
            budget.Id, "Updated lunch", 1100, "sgd", 1401, 127363636,
            new(2026, 8, 1), new(2026, 9, 3), null));
        update.EnsureSuccessStatusCode();
        var updated = await update.Content.ReadFromJsonAsync<ExpenseResponse>(JsonOptions);
        Assert.Equal("SGD", updated!.OriginalCurrency);
        Assert.Null(updated.Notes);

        var filtered = await Client.GetFromJsonAsync<ExpenseResponse[]>(
            "/api/data/expenses?journeyLabel=Ledger%20Journey&category=food&fromDate=2026-09-03&toDate=2026-09-03",
            JsonOptions);
        Assert.Single(filtered!);

        await using var connection = new SqliteConnection($"Data Source={DatabasePath}");
        await connection.OpenAsync();
        await using var command = connection.CreateCommand();
        command.CommandText = "SELECT original_amount_minor, converted_amount_minor, conversion_rate_scaled FROM expenses WHERE id = $id";
        command.Parameters.AddWithValue("$id", expense.Id);
        await using var reader = await command.ExecuteReaderAsync();
        Assert.True(await reader.ReadAsync());
        Assert.Equal(1100L, reader.GetInt64(0));
        Assert.Equal(1401L, reader.GetInt64(1));
        Assert.Equal(127363636L, reader.GetInt64(2));

        Assert.Equal(HttpStatusCode.NoContent, (await Client.DeleteAsync($"/api/data/expenses/{expense.Id}")).StatusCode);
    }

    [Fact]
    public async Task DuplicateAndMixedCurrencyBudgetsReturnConflicts()
    {
        await CreateBudgetAsync("Conflict Journey", "food", currency: "AUD");
        var duplicate = await Client.PostAsJsonAsync("/api/data/budgets", new BudgetRequest(
            "conflict journey", "FOOD", 90000, "AUD", new(2026, 9, 1), new(2026, 9, 7)));
        var mixed = await Client.PostAsJsonAsync("/api/data/budgets", new BudgetRequest(
            "Conflict Journey", "transport", 30000, "USD", new(2026, 9, 1), new(2026, 9, 7)));

        Assert.Equal(HttpStatusCode.Conflict, duplicate.StatusCode);
        Assert.Equal("duplicate_budget", (await duplicate.Content.ReadFromJsonAsync<ApiErrorEnvelope>(JsonOptions))!.Error.Code);
        Assert.Equal(HttpStatusCode.Conflict, mixed.StatusCode);
        Assert.Equal("journey_currency_conflict", (await mixed.Content.ReadFromJsonAsync<ApiErrorEnvelope>(JsonOptions))!.Error.Code);
    }

    [Fact]
    public async Task SqliteAtomicallyRejectsMixedJourneyCurrencies()
    {
        await CreateBudgetAsync("Atomic Journey", "food", currency: "AUD");
        await using var connection = new SqliteConnection($"Data Source={DatabasePath}");
        await connection.OpenAsync();
        await using var command = connection.CreateCommand();
        command.CommandText =
            """
            INSERT INTO budgets (
                journey_label, category, limit_amount_minor, base_currency,
                start_date, end_date, created_at, updated_at)
            VALUES (
                'atomic journey', 'transport', 10000, 'USD',
                '2026-09-01', '2026-09-07', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """;

        var exception = await Assert.ThrowsAsync<SqliteException>(async () => await command.ExecuteNonQueryAsync());
        Assert.Contains("journey_currency_conflict", exception.Message);
    }

    [Fact]
    public async Task ValidationForeignKeyAndPeriodFailuresAreStable()
    {
        var invalid = await Client.PostAsJsonAsync("/api/data/budgets", new BudgetRequest(
            " ", "unknown", 0, "XYZ", new(2026, 9, 7), new(2026, 9, 1)));
        Assert.Equal(HttpStatusCode.BadRequest, invalid.StatusCode);
        var error = await invalid.Content.ReadFromJsonAsync<ApiErrorEnvelope>(JsonOptions);
        Assert.Equal("validation_error", error!.Error.Code);
        Assert.False(string.IsNullOrWhiteSpace(error.Error.CorrelationId));

        var missingParent = await Client.PostAsJsonAsync("/api/data/expenses", new ExpenseRequest(
            999, "Lunch", 100, "AUD", 100, 100000000, new(2026, 8, 1), new(2026, 9, 2), null));
        Assert.Equal(HttpStatusCode.NotFound, missingParent.StatusCode);

        var budget = await CreateBudgetAsync();
        var outside = await Client.PostAsJsonAsync("/api/data/expenses", new ExpenseRequest(
            budget.Id, "Late expense", 100, "AUD", 100, 100000000, new(2026, 8, 1), new(2026, 9, 8), null));
        Assert.Equal(HttpStatusCode.BadRequest, outside.StatusCode);
    }

    [Fact]
    public async Task OmittedDatesAreRejectedBeforePersistence()
    {
        var budget = await Client.PostAsJsonAsync("/api/data/budgets", new
        {
            journeyLabel = "Missing Dates",
            category = "food",
            limitAmountMinor = 1000,
            baseCurrency = "AUD"
        });
        var expense = await Client.PostAsJsonAsync("/api/data/expenses", new
        {
            budgetId = 1,
            description = "Missing dates",
            originalAmountMinor = 100,
            originalCurrency = "AUD",
            convertedAmountMinor = 100,
            conversionRateScaled = 100000000
        });

        Assert.Equal(HttpStatusCode.BadRequest, budget.StatusCode);
        Assert.Equal("validation_error", (await budget.Content.ReadFromJsonAsync<ApiErrorEnvelope>(JsonOptions))!.Error.Code);
        Assert.Equal(HttpStatusCode.BadRequest, expense.StatusCode);
        Assert.Equal("validation_error", (await expense.Content.ReadFromJsonAsync<ApiErrorEnvelope>(JsonOptions))!.Error.Code);
    }

    [Fact]
    public async Task DeletingBudgetCascadesExpenses()
    {
        var budget = await CreateBudgetAsync("Cascade Journey");
        await CreateExpenseAsync(budget.Id);

        (await Client.DeleteAsync($"/api/data/budgets/{budget.Id}")).EnsureSuccessStatusCode();

        var expenses = await Client.GetFromJsonAsync<ExpenseResponse[]>($"/api/data/expenses?budgetId={budget.Id}", JsonOptions);
        Assert.Empty(expenses!);
    }

    [Fact]
    public async Task BudgetWithExpensesCannotChangeBaseCurrencyOrExcludeExpenseDate()
    {
        var budget = await CreateBudgetAsync("Snapshot Journey");
        await CreateExpenseAsync(budget.Id);

        var currency = await Client.PutAsJsonAsync($"/api/data/budgets/{budget.Id}", new BudgetRequest(
            budget.JourneyLabel, budget.Category, budget.LimitAmountMinor, "USD", budget.StartDate, budget.EndDate));
        var period = await Client.PutAsJsonAsync($"/api/data/budgets/{budget.Id}", new BudgetRequest(
            budget.JourneyLabel, budget.Category, budget.LimitAmountMinor, budget.BaseCurrency, new(2026, 9, 3), budget.EndDate));

        Assert.Equal(HttpStatusCode.Conflict, currency.StatusCode);
        Assert.Equal("budget_currency_conflict", (await currency.Content.ReadFromJsonAsync<ApiErrorEnvelope>(JsonOptions))!.Error.Code);
        Assert.Equal(HttpStatusCode.Conflict, period.StatusCode);
        Assert.Equal("expense_period_conflict", (await period.Content.ReadFromJsonAsync<ApiErrorEnvelope>(JsonOptions))!.Error.Code);
    }
}
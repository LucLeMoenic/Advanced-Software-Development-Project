using System.Net.Http.Json;
using System.Text.Json;
using BudgetTracker.Database.Api;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.Data.Sqlite;

namespace BudgetTracker.Database.Tests;

public abstract class DatabaseApiTestBase : IAsyncLifetime
{
    private WebApplicationFactory<Program>? _factory;
    private HttpClient? _client;

    protected string DatabasePath { get; } = Path.Combine(Path.GetTempPath(), $"student4-{Guid.NewGuid():N}.db");
    protected HttpClient Client => _client ?? throw new InvalidOperationException("Test client is not initialized.");
    protected static JsonSerializerOptions JsonOptions { get; } = new(JsonSerializerDefaults.Web);

    public Task InitializeAsync()
    {
        _factory = new WebApplicationFactory<Program>().WithWebHostBuilder(builder =>
        {
            builder.UseSetting("ConnectionStrings:BudgetDatabase", $"Data Source={DatabasePath}");
            builder.UseSetting("DemoData:Seed", "false");
        });
        _client = _factory.CreateClient();
        return Task.CompletedTask;
    }

    public async Task DisposeAsync()
    {
        _client?.Dispose();
        if (_factory is not null)
        {
            await _factory.DisposeAsync();
        }
        SqliteConnection.ClearAllPools();
        File.Delete(DatabasePath);
    }

    protected async Task<BudgetResponse> CreateBudgetAsync(
        string journey = "Test Journey",
        string category = "food",
        long limit = 50000,
        string currency = "AUD",
        DateOnly? start = null,
        DateOnly? end = null)
    {
        var response = await Client.PostAsJsonAsync("/api/data/budgets", new BudgetRequest(
            journey,
            category,
            limit,
            currency,
            start ?? new DateOnly(2026, 9, 1),
            end ?? new DateOnly(2026, 9, 7)));
        response.EnsureSuccessStatusCode();
        return (await response.Content.ReadFromJsonAsync<BudgetResponse>(JsonOptions))!;
    }

    protected async Task<ExpenseResponse> CreateExpenseAsync(int budgetId, string description = "Lunch", long convertedAmount = 1250)
    {
        var response = await Client.PostAsJsonAsync("/api/data/expenses", new ExpenseRequest(
            budgetId,
            description,
            1000,
            "USD",
            convertedAmount,
            125000000,
            new DateOnly(2026, 8, 1),
            new DateOnly(2026, 9, 2),
            "Test note"));
        response.EnsureSuccessStatusCode();
        return (await response.Content.ReadFromJsonAsync<ExpenseResponse>(JsonOptions))!;
    }
}
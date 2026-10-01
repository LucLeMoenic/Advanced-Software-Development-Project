using System.Net;
using System.Net.Http.Json;
using BudgetTracker.Backend.Api;
using BudgetTracker.Backend.Clients;
using BudgetTracker.Backend.Services;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.AspNetCore.TestHost;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;

namespace BudgetTracker.Backend.Tests;

public sealed class EndpointTests
{
    [Theory]
    [InlineData(false, false, false)]
    [InlineData(false, false, true)]
    [InlineData(false, true, false)]
    [InlineData(false, true, true)]
    [InlineData(true, false, false)]
    [InlineData(true, false, true)]
    [InlineData(true, true, false)]
    [InlineData(true, true, true)]
    public async Task CapabilitiesReportConfiguredModes(bool aiEnabled, bool mcpEnabled, bool ragEnabled)
    {
        var settings = new Dictionary<string, string?>
        {
            ["AI_ENABLED"] = aiEnabled ? "true" : "false",
            ["MCP_ENABLED"] = mcpEnabled ? "true" : "false",
            ["RAG_ENABLED"] = ragEnabled ? "true" : "false"
        };
        using var factory = CreateFactory(new FakeDatabase(), new FakeAdvice(), settings);
        using var client = factory.CreateClient();

        var response = await client.GetFromJsonAsync<CapabilitiesResponse>("/api/capabilities");

        Assert.Equal(new CapabilitiesResponse(aiEnabled, mcpEnabled, ragEnabled), response);
    }

    [Fact]
    public async Task CapabilitiesUseDocumentedDefaultsWhenFlagsAreMissing()
    {
        var settings = new Dictionary<string, string?>
        {
            ["AI_ENABLED"] = null,
            ["MCP_ENABLED"] = null,
            ["RAG_ENABLED"] = null
        };
        using var factory = CreateFactory(new FakeDatabase(), new FakeAdvice(), settings);
        using var client = factory.CreateClient();

        var response = await client.GetFromJsonAsync<CapabilitiesResponse>("/api/capabilities");

        Assert.Equal(new CapabilitiesResponse(true, false, false), response);
    }

    [Theory]
    [InlineData("AI_ENABLED")]
    [InlineData("MCP_ENABLED")]
    [InlineData("RAG_ENABLED")]
    public void InvalidModeFlagFailsApplicationStartup(string name)
    {
        var settings = new Dictionary<string, string?> { [name] = "True" };
        using var factory = CreateFactory(new FakeDatabase(), new FakeAdvice(), settings);

        var exception = Assert.ThrowsAny<Exception>(() => factory.CreateClient());

        Assert.Contains(name, exception.ToString(), StringComparison.Ordinal);
    }

    [Theory]
    [InlineData("AI_ENABLED", "true", true)]
    [InlineData("AI_ENABLED", "false", false)]
    [InlineData("MCP_ENABLED", "true", true)]
    [InlineData("MCP_ENABLED", "false", false)]
    [InlineData("RAG_ENABLED", "true", true)]
    [InlineData("RAG_ENABLED", "false", false)]
    public void ModeFlagsAcceptOnlyExactBooleanSpellings(string name, string value, bool expected)
    {
        var configuration = new ConfigurationBuilder()
            .AddInMemoryCollection(new Dictionary<string, string?> { [name] = value })
            .Build();

        var settings = FeatureModeSettings.FromConfiguration(configuration);

        Assert.Equal(expected, name switch
        {
            "AI_ENABLED" => settings.AiEnabled,
            "MCP_ENABLED" => settings.McpEnabled,
            _ => settings.RagEnabled
        });
    }

    [Theory]
    [InlineData("AI_ENABLED", "TRUE")]
    [InlineData("AI_ENABLED", "False")]
    [InlineData("AI_ENABLED", " true")]
    [InlineData("AI_ENABLED", "false ")]
    [InlineData("AI_ENABLED", "1")]
    [InlineData("AI_ENABLED", "")]
    [InlineData("MCP_ENABLED", "TRUE")]
    [InlineData("MCP_ENABLED", "False")]
    [InlineData("MCP_ENABLED", " true")]
    [InlineData("MCP_ENABLED", "false ")]
    [InlineData("MCP_ENABLED", "1")]
    [InlineData("MCP_ENABLED", "")]
    [InlineData("RAG_ENABLED", "TRUE")]
    [InlineData("RAG_ENABLED", "False")]
    [InlineData("RAG_ENABLED", " true")]
    [InlineData("RAG_ENABLED", "false ")]
    [InlineData("RAG_ENABLED", "1")]
    [InlineData("RAG_ENABLED", "")]
    public void ModeFlagsRejectNonCanonicalValues(string name, string value)
    {
        var configuration = new ConfigurationBuilder()
            .AddInMemoryCollection(new Dictionary<string, string?> { [name] = value })
            .Build();

        Assert.Throws<InvalidOperationException>(() => FeatureModeSettings.FromConfiguration(configuration));
    }

    [Fact]
    public async Task ValidationHappensBeforeDatabaseCalls()
    {
        var database = new FakeDatabase();
        using var client = CreateClient(database, new FakeAdvice());

        var response = await client.PostAsJsonAsync("/api/budgets", new BudgetWriteRequest(" ", "bad", 0, "JPY", new(2026, 9, 2), new(2026, 9, 1)));

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.Equal(0, database.CallCount);
        Assert.Equal("validation_error", (await response.Content.ReadFromJsonAsync<ApiErrorEnvelope>())!.Error.Code);
    }

    [Fact]
    public async Task OmittedDatesAreRejectedBeforeDatabaseCalls()
    {
        var database = new FakeDatabase();
        using var client = CreateClient(database, new FakeAdvice());

        var budget = await client.PostAsJsonAsync("/api/budgets", new
        {
            journeyLabel = "Missing Dates",
            category = "food",
            limitAmountMinor = 1000,
            baseCurrency = "AUD"
        });
        var expense = await client.PostAsJsonAsync("/api/expenses", new
        {
            budgetId = 1,
            description = "Missing date",
            originalAmountMinor = 100,
            originalCurrency = "AUD"
        });

        Assert.Equal(HttpStatusCode.BadRequest, budget.StatusCode);
        Assert.Equal(HttpStatusCode.BadRequest, expense.StatusCode);
        Assert.Equal(0, database.CallCount);
    }

    [Fact]
    public async Task BudgetCrudMapsThroughDatabaseBoundary()
    {
        var database = new FakeDatabase();
        using var client = CreateClient(database, new FakeAdvice());
        var request = new BudgetWriteRequest(" New Journey ", "FOOD", 20000, "aud", new(2026, 9, 1), new(2026, 9, 7));

        var create = await client.PostAsJsonAsync("/api/budgets", request);
        Assert.Equal(HttpStatusCode.Created, create.StatusCode);
        var budget = await create.Content.ReadFromJsonAsync<BudgetResponse>();
        Assert.Equal("New Journey", budget!.JourneyLabel);
        Assert.Equal("food", budget.Category);
        Assert.NotNull(await client.GetFromJsonAsync<BudgetResponse>($"/api/budgets/{budget.Id}"));
        Assert.Equal(HttpStatusCode.NoContent, (await client.DeleteAsync($"/api/budgets/{budget.Id}")).StatusCode);
    }

    [Fact]
    public async Task ExpenseSaveRecomputesAndReturnsConversionSnapshot()
    {
        var database = FakeDatabase.WithJourney();
        using var client = CreateClient(database, new FakeAdvice());

        var response = await client.PostAsJsonAsync("/api/expenses", new ExpenseWriteRequest(1, " Lunch ", 101, "usd", new(2026, 9, 2), null));

        Assert.Equal(HttpStatusCode.Created, response.StatusCode);
        var expense = await response.Content.ReadFromJsonAsync<ExpenseResponse>();
        Assert.Equal(155, expense!.ConvertedAmountMinor);
        Assert.Equal(153846154, expense.ConversionRateScaled);
        Assert.Equal("AUD", expense.BaseCurrency);
        Assert.Equal(155, database.LastExpenseRequest!.ConvertedAmountMinor);
    }

    [Fact]
    public async Task ClientSuppliedConvertedAmountIsRejected()
    {
        var database = FakeDatabase.WithJourney();
        using var client = CreateClient(database, new FakeAdvice());
        var response = await client.PostAsJsonAsync("/api/expenses", new { budgetId = 1, description = "Lunch", originalAmountMinor = 100, originalCurrency = "AUD", convertedAmountMinor = 1, spentOn = "2026-09-02" });
        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.Null(database.LastExpenseRequest);
    }

    [Fact]
    public async Task DashboardAndAdviceUseDeterministicData()
    {
        var database = FakeDatabase.WithJourney(actual: 9000);
        var advice = new FakeAdvice();
        using var client = CreateClient(database, advice);

        var dashboard = await client.GetFromJsonAsync<DashboardResponse>("/api/dashboard?journeyLabel=Journey");
        var result = await (await client.PostAsJsonAsync("/api/insights", new InsightRequest("Journey"))).Content.ReadFromJsonAsync<AdviceResponse>();

        Assert.Equal(90, dashboard!.PercentageUsed);
        Assert.Equal("warning", dashboard.Categories.Single().Status);
        Assert.Equal("ai", result!.Source);
        Assert.Equal(1, advice.CallCount);
    }

    [Fact]
    public async Task NoBudgetDataDoesNotCallOllamaAdvice()
    {
        var advice = new FakeAdvice();
        using var client = CreateClient(new FakeDatabase(), advice);
        var response = await client.PostAsJsonAsync("/api/insights", new InsightRequest("Missing"));
        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.Equal(0, advice.CallCount);
    }

    [Fact]
    public async Task DatabaseUnavailableMapsToStable503()
    {
        using var client = CreateClient(new UnavailableDatabase(), new FakeAdvice());
        var response = await client.GetAsync("/api/budgets");
        Assert.Equal(HttpStatusCode.ServiceUnavailable, response.StatusCode);
        Assert.Equal("database_unavailable", (await response.Content.ReadFromJsonAsync<ApiErrorEnvelope>())!.Error.Code);
    }

    [Fact]
    public async Task InconsistentDashboardDataMapsToStable502()
    {
        using var client = CreateClient(FakeDatabase.WithInconsistentJourney(), new FakeAdvice());
        var response = await client.GetAsync("/api/dashboard?journeyLabel=Journey");
        Assert.Equal(HttpStatusCode.BadGateway, response.StatusCode);
        Assert.Equal("database_response_invalid", (await response.Content.ReadFromJsonAsync<ApiErrorEnvelope>())!.Error.Code);
    }

    private static HttpClient CreateClient(IDatabaseApiClient database, IAdviceService advice) => CreateFactory(database, advice).CreateClient();

    private static WebApplicationFactory<Program> CreateFactory(IDatabaseApiClient database, IAdviceService advice, IDictionary<string, string?>? configuration = null)
    {
        return new WebApplicationFactory<Program>().WithWebHostBuilder(builder =>
        {
            if (configuration is not null)
            {
                builder.ConfigureAppConfiguration((_, config) => config.AddInMemoryCollection(configuration));
            }
            builder.ConfigureTestServices(services =>
            {
                services.RemoveAll<IDatabaseApiClient>();
                services.RemoveAll<IAdviceService>();
                services.RemoveAll<IExchangeRateProvider>();
                services.AddSingleton(database);
                services.AddSingleton(advice);
                services.AddSingleton<IExchangeRateProvider>(new FixedExchangeRateProvider(new ExchangeRateSettings("test", new(2026, 8, 1), "Demo", new Dictionary<string, decimal> { ["AUD"] = 1m, ["USD"] = 0.65m, ["EUR"] = 0.6m, ["GBP"] = 0.51m, ["NZD"] = 1.08m, ["CAD"] = 0.89m, ["SGD"] = 0.86m })));
            });
        });
    }

    private sealed class FakeAdvice : IAdviceService
    {
        public int CallCount { get; private set; }
        public Task<AdviceResponse> GetAdviceAsync(DashboardResponse dashboard, CancellationToken cancellationToken) { CallCount++; return Task.FromResult(new AdviceResponse("Advice.", [new("food", "Track food.")], "ai")); }
    }

    private sealed record CapabilitiesResponse(bool AiEnabled, bool McpEnabled, bool RagEnabled);

    private sealed class FakeDatabase : IDatabaseApiClient
    {
        private readonly List<BudgetResponse> _budgets = [];
        private readonly List<ExpenseDataResponse> _expenses = [];
        public int CallCount { get; private set; }
        public ExpenseDataRequest? LastExpenseRequest { get; private set; }
        public static FakeDatabase WithJourney(long actual = 0)
        {
            var value = new FakeDatabase();
            value._budgets.Add(new(1, "Journey", "food", 10000, "AUD", new(2026, 9, 1), new(2026, 9, 7), DateTime.UtcNow, DateTime.UtcNow));
            if (actual > 0) value._expenses.Add(new(1, 1, "Meals", actual, "AUD", actual, 100000000, new(2026, 8, 1), new(2026, 9, 2), null, DateTime.UtcNow, DateTime.UtcNow));
            return value;
        }
        public static FakeDatabase WithInconsistentJourney()
        {
            var value = WithJourney();
            value._budgets.Add(new(2, "Journey", "transport", 10000, "USD", new(2026, 9, 1), new(2026, 9, 7), DateTime.UtcNow, DateTime.UtcNow));
            return value;
        }
        public Task<IReadOnlyList<BudgetResponse>> ListBudgetsAsync(string? journeyLabel, string? category, CancellationToken cancellationToken) { CallCount++; return Task.FromResult<IReadOnlyList<BudgetResponse>>(_budgets.Where(value => journeyLabel is null || value.JourneyLabel == journeyLabel).Where(value => category is null || value.Category == category).ToArray()); }
        public Task<BudgetResponse> GetBudgetAsync(int id, CancellationToken cancellationToken) { CallCount++; return Task.FromResult(_budgets.Single(value => value.Id == id)); }
        public Task<BudgetResponse> CreateBudgetAsync(BudgetWriteRequest request, CancellationToken cancellationToken) { CallCount++; var value = new BudgetResponse(_budgets.Count + 1, request.JourneyLabel!, request.Category!, request.LimitAmountMinor, request.BaseCurrency!, request.StartDate!.Value, request.EndDate!.Value, DateTime.UtcNow, DateTime.UtcNow); _budgets.Add(value); return Task.FromResult(value); }
        public Task<BudgetResponse> UpdateBudgetAsync(int id, BudgetWriteRequest request, CancellationToken cancellationToken) { CallCount++; return Task.FromResult(new BudgetResponse(id, request.JourneyLabel!, request.Category!, request.LimitAmountMinor, request.BaseCurrency!, request.StartDate!.Value, request.EndDate!.Value, DateTime.UtcNow, DateTime.UtcNow)); }
        public Task DeleteBudgetAsync(int id, CancellationToken cancellationToken) { CallCount++; _budgets.RemoveAll(value => value.Id == id); return Task.CompletedTask; }
        public Task<IReadOnlyList<ExpenseDataResponse>> ListExpensesAsync(int? budgetId, string? journeyLabel, string? category, CancellationToken cancellationToken) { CallCount++; return Task.FromResult<IReadOnlyList<ExpenseDataResponse>>(_expenses.Where(value => budgetId is null || value.BudgetId == budgetId).ToArray()); }
        public Task<ExpenseDataResponse> GetExpenseAsync(int id, CancellationToken cancellationToken) { CallCount++; return Task.FromResult(_expenses.Single(value => value.Id == id)); }
        public Task<ExpenseDataResponse> CreateExpenseAsync(ExpenseDataRequest request, CancellationToken cancellationToken) { CallCount++; LastExpenseRequest = request; var value = Data(_expenses.Count + 1, request); _expenses.Add(value); return Task.FromResult(value); }
        public Task<ExpenseDataResponse> UpdateExpenseAsync(int id, ExpenseDataRequest request, CancellationToken cancellationToken) { CallCount++; LastExpenseRequest = request; return Task.FromResult(Data(id, request)); }
        public Task DeleteExpenseAsync(int id, CancellationToken cancellationToken) { CallCount++; _expenses.RemoveAll(value => value.Id == id); return Task.CompletedTask; }
        private static ExpenseDataResponse Data(int id, ExpenseDataRequest request) => new(id, request.BudgetId, request.Description, request.OriginalAmountMinor, request.OriginalCurrency, request.ConvertedAmountMinor, request.ConversionRateScaled, request.RateAsOf, request.SpentOn, request.Notes, DateTime.UtcNow, DateTime.UtcNow);
    }

    private sealed class UnavailableDatabase : IDatabaseApiClient
    {
        private static Task<T> Fail<T>() => Task.FromException<T>(new DatabaseUnavailableException());
        public Task<IReadOnlyList<BudgetResponse>> ListBudgetsAsync(string? journeyLabel, string? category, CancellationToken cancellationToken) => Fail<IReadOnlyList<BudgetResponse>>();
        public Task<BudgetResponse> GetBudgetAsync(int id, CancellationToken cancellationToken) => Fail<BudgetResponse>();
        public Task<BudgetResponse> CreateBudgetAsync(BudgetWriteRequest request, CancellationToken cancellationToken) => Fail<BudgetResponse>();
        public Task<BudgetResponse> UpdateBudgetAsync(int id, BudgetWriteRequest request, CancellationToken cancellationToken) => Fail<BudgetResponse>();
        public Task DeleteBudgetAsync(int id, CancellationToken cancellationToken) => Fail<object>();
        public Task<IReadOnlyList<ExpenseDataResponse>> ListExpensesAsync(int? budgetId, string? journeyLabel, string? category, CancellationToken cancellationToken) => Fail<IReadOnlyList<ExpenseDataResponse>>();
        public Task<ExpenseDataResponse> GetExpenseAsync(int id, CancellationToken cancellationToken) => Fail<ExpenseDataResponse>();
        public Task<ExpenseDataResponse> CreateExpenseAsync(ExpenseDataRequest request, CancellationToken cancellationToken) => Fail<ExpenseDataResponse>();
        public Task<ExpenseDataResponse> UpdateExpenseAsync(int id, ExpenseDataRequest request, CancellationToken cancellationToken) => Fail<ExpenseDataResponse>();
        public Task DeleteExpenseAsync(int id, CancellationToken cancellationToken) => Fail<object>();
    }
}
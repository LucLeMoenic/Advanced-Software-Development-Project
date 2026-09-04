using System.Net;
using System.Text;
using BudgetTracker.Backend.Clients;

namespace BudgetTracker.Backend.Tests;

public sealed class DatabaseApiClientTests
{
    [Fact]
    public async Task MalformedSuccessfulResponseIsRejected()
    {
        var client = Create(new StubHandler(new HttpResponseMessage(HttpStatusCode.OK) { Content = new StringContent("{not-json", Encoding.UTF8, "application/json") }));
        await Assert.ThrowsAsync<DatabaseResponseException>(() => client.ListBudgetsAsync(null, null, default));
    }

    [Fact]
    public async Task StructurallyInvalidSuccessfulResponseIsRejected()
    {
        var response = new HttpResponseMessage(HttpStatusCode.OK) { Content = new StringContent("[{\"id\":0,\"journeyLabel\":\"Bad\",\"category\":\"food\",\"limitAmountMinor\":1,\"baseCurrency\":\"AUD\",\"startDate\":\"2026-09-01\",\"endDate\":\"2026-09-02\",\"createdAt\":\"2026-09-01T00:00:00Z\",\"updatedAt\":\"2026-09-01T00:00:00Z\"}]", Encoding.UTF8, "application/json") };
        await Assert.ThrowsAsync<DatabaseResponseException>(() => Create(new StubHandler(response)).ListBudgetsAsync(null, null, default));
    }

    [Fact]
    public async Task NullCollectionEntryIsRejectedWithoutNullReferenceFailure()
    {
        var response = new HttpResponseMessage(HttpStatusCode.OK) { Content = new StringContent("[null]", Encoding.UTF8, "application/json") };
        await Assert.ThrowsAsync<DatabaseResponseException>(() => Create(new StubHandler(response)).ListBudgetsAsync(null, null, default));
    }

    [Fact]
    public async Task DuplicateCollectionIdsAreRejected()
    {
        const string value = "{\"id\":1,\"journeyLabel\":\"Journey\",\"category\":\"food\",\"limitAmountMinor\":1000,\"baseCurrency\":\"AUD\",\"startDate\":\"2026-09-01\",\"endDate\":\"2026-09-07\",\"createdAt\":\"2026-09-01T00:00:00Z\",\"updatedAt\":\"2026-09-01T00:00:00Z\"}";
        var response = new HttpResponseMessage(HttpStatusCode.OK) { Content = new StringContent($"[{value},{value}]", Encoding.UTF8, "application/json") };
        await Assert.ThrowsAsync<DatabaseResponseException>(() => Create(new StubHandler(response)).ListBudgetsAsync(null, null, default));
    }

    [Fact]
    public async Task ValidExpenseWithNullNotesIsAccepted()
    {
        var response = new HttpResponseMessage(HttpStatusCode.OK)
        {
            Content = new StringContent(
                "{\"id\":1,\"budgetId\":2,\"description\":\"Lunch\",\"originalAmountMinor\":100,\"originalCurrency\":\"AUD\",\"convertedAmountMinor\":100,\"conversionRateScaled\":100000000,\"rateAsOf\":\"2026-08-01\",\"spentOn\":\"2026-09-02\",\"notes\":null,\"createdAt\":\"2026-09-01T00:00:00Z\",\"updatedAt\":\"2026-09-01T00:00:00Z\"}",
                Encoding.UTF8,
                "application/json")
        };

        var expense = await Create(new StubHandler(response)).GetExpenseAsync(1, default);

        Assert.Null(expense.Notes);
    }

    [Theory]
    [InlineData(true)]
    [InlineData(false)]
    public async Task TimeoutAndConnectionFailuresAreUnavailable(bool timeout)
    {
        await Assert.ThrowsAsync<DatabaseUnavailableException>(() => Create(new ThrowingHandler(timeout)).ListBudgetsAsync(null, null, default));
    }

    [Fact]
    public async Task StableConflictIsPreserved()
    {
        var response = new HttpResponseMessage(HttpStatusCode.Conflict) { Content = new StringContent("{\"error\":{\"code\":\"duplicate_budget\",\"message\":\"Duplicate.\",\"fields\":{},\"correlationId\":\"abc\"}}", Encoding.UTF8, "application/json") };
        var exception = await Assert.ThrowsAsync<DatabaseRejectedException>(() => Create(new StubHandler(response)).CreateBudgetAsync(new("Journey", "food", 100, "AUD", new(2026, 9, 1), new(2026, 9, 2)), default));
        Assert.Equal(409, exception.StatusCode);
        Assert.Equal("duplicate_budget", exception.Code);
    }

    private static DatabaseApiClient Create(HttpMessageHandler handler) => new(new HttpClient(handler) { BaseAddress = new Uri("http://student4-database:8080"), Timeout = TimeSpan.FromSeconds(1) });
    private sealed class StubHandler(HttpResponseMessage response) : HttpMessageHandler { protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken) => Task.FromResult(response); }
    private sealed class ThrowingHandler(bool timeout) : HttpMessageHandler { protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken) => timeout ? throw new TaskCanceledException() : throw new HttpRequestException(); }
}
using System.Globalization;
using System.Net;
using System.Net.Http.Json;
using System.Text.Json;
using BudgetTracker.Backend.Api;

namespace BudgetTracker.Backend.Clients;

public interface IDatabaseApiClient
{
    Task<IReadOnlyList<BudgetResponse>> ListBudgetsAsync(string? journeyLabel, string? category, CancellationToken cancellationToken);
    Task<BudgetResponse> GetBudgetAsync(int id, CancellationToken cancellationToken);
    Task<BudgetResponse> CreateBudgetAsync(BudgetWriteRequest request, CancellationToken cancellationToken);
    Task<BudgetResponse> UpdateBudgetAsync(int id, BudgetWriteRequest request, CancellationToken cancellationToken);
    Task DeleteBudgetAsync(int id, CancellationToken cancellationToken);
    Task<IReadOnlyList<ExpenseDataResponse>> ListExpensesAsync(int? budgetId, string? journeyLabel, string? category, CancellationToken cancellationToken);
    Task<ExpenseDataResponse> GetExpenseAsync(int id, CancellationToken cancellationToken);
    Task<ExpenseDataResponse> CreateExpenseAsync(ExpenseDataRequest request, CancellationToken cancellationToken);
    Task<ExpenseDataResponse> UpdateExpenseAsync(int id, ExpenseDataRequest request, CancellationToken cancellationToken);
    Task DeleteExpenseAsync(int id, CancellationToken cancellationToken);
}

public sealed class DatabaseApiClient(HttpClient client) : IDatabaseApiClient
{
    private static readonly JsonSerializerOptions JsonOptions = new(JsonSerializerDefaults.Web);
    private static readonly HashSet<string> Currencies = new(StringComparer.Ordinal)
        { "AUD", "USD", "EUR", "GBP", "NZD", "CAD", "SGD" };

    public async Task<IReadOnlyList<BudgetResponse>> ListBudgetsAsync(string? journeyLabel, string? category, CancellationToken cancellationToken)
    {
        var query = new List<string>();
        if (!string.IsNullOrWhiteSpace(journeyLabel)) query.Add($"journeyLabel={Uri.EscapeDataString(journeyLabel)}");
        if (!string.IsNullOrWhiteSpace(category)) query.Add($"category={Uri.EscapeDataString(category)}");
        var values = await JsonAsync<BudgetResponse?[]>(HttpMethod.Get, "/api/data/budgets" + Query(query), null, HttpStatusCode.OK, cancellationToken);
        if (values.Any(value => value is null || !Valid(value)) || values.Select(value => value!.Id).Distinct().Count() != values.Length) throw new DatabaseResponseException();
        return values.Select(value => value!).ToArray();
    }

    public async Task<BudgetResponse> GetBudgetAsync(int id, CancellationToken cancellationToken) => Validate(await JsonAsync<BudgetResponse>(HttpMethod.Get, $"/api/data/budgets/{id}", null, HttpStatusCode.OK, cancellationToken));
    public async Task<BudgetResponse> CreateBudgetAsync(BudgetWriteRequest request, CancellationToken cancellationToken) => Validate(await JsonAsync<BudgetResponse>(HttpMethod.Post, "/api/data/budgets", request, HttpStatusCode.Created, cancellationToken));
    public async Task<BudgetResponse> UpdateBudgetAsync(int id, BudgetWriteRequest request, CancellationToken cancellationToken) => Validate(await JsonAsync<BudgetResponse>(HttpMethod.Put, $"/api/data/budgets/{id}", request, HttpStatusCode.OK, cancellationToken));
    public Task DeleteBudgetAsync(int id, CancellationToken cancellationToken) => EmptyAsync(HttpMethod.Delete, $"/api/data/budgets/{id}", HttpStatusCode.NoContent, cancellationToken);

    public async Task<IReadOnlyList<ExpenseDataResponse>> ListExpensesAsync(int? budgetId, string? journeyLabel, string? category, CancellationToken cancellationToken)
    {
        var query = new List<string>();
        if (budgetId is not null) query.Add($"budgetId={budgetId.Value.ToString(CultureInfo.InvariantCulture)}");
        if (!string.IsNullOrWhiteSpace(journeyLabel)) query.Add($"journeyLabel={Uri.EscapeDataString(journeyLabel)}");
        if (!string.IsNullOrWhiteSpace(category)) query.Add($"category={Uri.EscapeDataString(category)}");
        var values = await JsonAsync<ExpenseDataResponse?[]>(HttpMethod.Get, "/api/data/expenses" + Query(query), null, HttpStatusCode.OK, cancellationToken);
        if (values.Any(value => value is null || !Valid(value)) || values.Select(value => value!.Id).Distinct().Count() != values.Length) throw new DatabaseResponseException();
        return values.Select(value => value!).ToArray();
    }

    public async Task<ExpenseDataResponse> GetExpenseAsync(int id, CancellationToken cancellationToken) => Validate(await JsonAsync<ExpenseDataResponse>(HttpMethod.Get, $"/api/data/expenses/{id}", null, HttpStatusCode.OK, cancellationToken));
    public async Task<ExpenseDataResponse> CreateExpenseAsync(ExpenseDataRequest request, CancellationToken cancellationToken) => Validate(await JsonAsync<ExpenseDataResponse>(HttpMethod.Post, "/api/data/expenses", request, HttpStatusCode.Created, cancellationToken));
    public async Task<ExpenseDataResponse> UpdateExpenseAsync(int id, ExpenseDataRequest request, CancellationToken cancellationToken) => Validate(await JsonAsync<ExpenseDataResponse>(HttpMethod.Put, $"/api/data/expenses/{id}", request, HttpStatusCode.OK, cancellationToken));
    public Task DeleteExpenseAsync(int id, CancellationToken cancellationToken) => EmptyAsync(HttpMethod.Delete, $"/api/data/expenses/{id}", HttpStatusCode.NoContent, cancellationToken);

    private async Task<T> JsonAsync<T>(HttpMethod method, string path, object? body, HttpStatusCode expected, CancellationToken cancellationToken)
    {
        using var request = new HttpRequestMessage(method, path);
        if (body is not null) request.Content = JsonContent.Create(body, options: JsonOptions);
        using var response = await SendAsync(request, expected, cancellationToken);
        try
        {
            return await response.Content.ReadFromJsonAsync<T>(JsonOptions, cancellationToken) ?? throw new DatabaseResponseException();
        }
        catch (JsonException exception)
        {
            throw new DatabaseResponseException(exception);
        }
    }

    private async Task EmptyAsync(HttpMethod method, string path, HttpStatusCode expected, CancellationToken cancellationToken)
    {
        using var response = await SendAsync(new HttpRequestMessage(method, path), expected, cancellationToken);
    }

    private async Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, HttpStatusCode expected, CancellationToken cancellationToken)
    {
        HttpResponseMessage response;
        try
        {
            response = await client.SendAsync(request, cancellationToken);
        }
        catch (TaskCanceledException exception) when (!cancellationToken.IsCancellationRequested)
        {
            throw new DatabaseUnavailableException(exception);
        }
        catch (HttpRequestException exception)
        {
            throw new DatabaseUnavailableException(exception);
        }

        if (response.StatusCode == expected) return response;
        if (response.StatusCode is HttpStatusCode.BadRequest or HttpStatusCode.NotFound or HttpStatusCode.Conflict)
        {
            ApiErrorEnvelope? envelope = null;
            try { envelope = await response.Content.ReadFromJsonAsync<ApiErrorEnvelope>(JsonOptions, cancellationToken); } catch (JsonException) { }
            response.Dispose();
            if (envelope?.Error is not null) throw new DatabaseRejectedException((int)response.StatusCode, envelope.Error.Code, envelope.Error.Message, envelope.Error.Fields);
        }
        response.Dispose();
        throw new DatabaseResponseException();
    }

    private static string Query(IReadOnlyList<string> values) => values.Count == 0 ? string.Empty : "?" + string.Join("&", values);
    private static BudgetResponse Validate(BudgetResponse value) => Valid(value) ? value : throw new DatabaseResponseException();
    private static ExpenseDataResponse Validate(ExpenseDataResponse value) => Valid(value) ? value : throw new DatabaseResponseException();
    private static bool Valid(BudgetResponse value) =>
        value.Id > 0
        && value.JourneyLabel is not null
        && value.JourneyLabel == value.JourneyLabel.Trim()
        && value.JourneyLabel.Length is >= 1 and <= 80
        && value.Category is not null
        && Validation.Categories.Contains(value.Category)
        && value.LimitAmountMinor > 0
        && value.BaseCurrency is not null
        && Currencies.Contains(value.BaseCurrency)
        && value.StartDate != default
        && value.EndDate >= value.StartDate
        && value.CreatedAt != default
        && value.UpdatedAt != default;

    private static bool Valid(ExpenseDataResponse value) =>
        value.Id > 0
        && value.BudgetId > 0
        && value.Description is not null
        && value.Description == value.Description.Trim()
        && value.Description.Length is >= 1 and <= 120
        && value.OriginalAmountMinor > 0
        && value.OriginalCurrency is not null
        && Currencies.Contains(value.OriginalCurrency)
        && value.ConvertedAmountMinor > 0
        && value.ConversionRateScaled > 0
        && value.RateAsOf != default
        && value.SpentOn != default
        && (value.Notes is null || value.Notes.Length <= 500)
        && value.CreatedAt != default
        && value.UpdatedAt != default;
}

public sealed class DatabaseUnavailableException(Exception? inner = null) : Exception("The database API is unavailable.", inner);
public sealed class DatabaseResponseException(Exception? inner = null) : Exception("The database API returned an unusable response.", inner);
public sealed class DatabaseRejectedException(int statusCode, string code, string message, object fields) : Exception(message)
{
    public int StatusCode { get; } = statusCode;
    public string Code { get; } = code;
    public object Fields { get; } = fields;
}
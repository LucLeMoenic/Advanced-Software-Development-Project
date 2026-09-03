using BudgetTracker.Backend.Clients;
using BudgetTracker.Backend.Services;

namespace BudgetTracker.Backend.Api;

public static class BudgetEndpoints
{
    public static void MapBudgetEndpoints(this WebApplication app)
    {
        app.MapGet("/api/currencies", (IExchangeRateProvider rates) => Results.Ok(new { rateAsOf = rates.Convert(1, "AUD", "AUD").RateAsOf, rateVersion = rates.Convert(1, "AUD", "AUD").RateVersion, disclaimer = rates.Convert(1, "AUD", "AUD").Disclaimer, currencies = rates.Currencies.Select(value => new CurrencyResponse(value)) }));
        app.MapPost("/api/conversions/preview", PreviewConversion);
        app.MapGet("/api/journeys", ListJourneysAsync);
        app.MapGet("/api/dashboard", GetDashboardAsync);
        app.MapGet("/api/budgets", ListBudgetsAsync);
        app.MapPost("/api/budgets", CreateBudgetAsync);
        app.MapGet("/api/budgets/{id:int}", GetBudgetAsync);
        app.MapPut("/api/budgets/{id:int}", UpdateBudgetAsync);
        app.MapDelete("/api/budgets/{id:int}", DeleteBudgetAsync);
        app.MapGet("/api/expenses", ListExpensesAsync);
        app.MapPost("/api/expenses", CreateExpenseAsync);
        app.MapGet("/api/expenses/{id:int}", GetExpenseAsync);
        app.MapPut("/api/expenses/{id:int}", UpdateExpenseAsync);
        app.MapDelete("/api/expenses/{id:int}", DeleteExpenseAsync);
        app.MapPost("/api/insights", GetInsightsAsync);
    }

    private static IResult PreviewConversion(ConversionPreviewRequest request, IExchangeRateProvider rates, HttpContext context)
    {
        var errors = new Dictionary<string, string[]>();
        if (request.OriginalAmountMinor <= 0) errors["originalAmountMinor"] = ["Original amount must be positive."];
        if (!rates.Supports(request.FromCurrency)) errors["fromCurrency"] = ["Source currency is not supported."];
        if (!rates.Supports(request.ToCurrency)) errors["toCurrency"] = ["Target currency is not supported."];
        return errors.Count > 0 ? Error(context, 400, "validation_error", "One or more fields are invalid.", errors) : Results.Ok(rates.Convert(request.OriginalAmountMinor, request.FromCurrency!, request.ToCurrency!));
    }

    private static async Task<IResult> ListJourneysAsync(IDatabaseApiClient database, CancellationToken cancellationToken)
    {
        var budgets = await database.ListBudgetsAsync(null, null, cancellationToken);
        return Results.Ok(budgets.GroupBy(value => new { value.JourneyLabel, value.BaseCurrency }).Select(group => new JourneyResponse(group.Key.JourneyLabel, group.Key.BaseCurrency, group.Min(value => value.StartDate), group.Max(value => value.EndDate))).OrderBy(value => value.JourneyLabel));
    }

    private static async Task<IResult> GetDashboardAsync(string? journeyLabel, IDatabaseApiClient database, HttpContext context, CancellationToken cancellationToken)
    {
        if (string.IsNullOrWhiteSpace(journeyLabel) || journeyLabel.Trim().Length > 80) return Error(context, 400, "validation_error", "A valid journey label is required.", new Dictionary<string, string[]> { ["journeyLabel"] = ["Journey label must contain 1 to 80 characters."] });
        var normalized = journeyLabel.Trim();
        var budgets = await database.ListBudgetsAsync(normalized, null, cancellationToken);
        if (budgets.Count == 0) return Error(context, 404, "journey_not_found", "The journey was not found.");
        var expenses = await database.ListExpensesAsync(null, normalized, null, cancellationToken);
        return Results.Ok(DashboardCalculator.Calculate(budgets[0].JourneyLabel, budgets, expenses));
    }

    private static async Task<IResult> ListBudgetsAsync(string? journeyLabel, string? category, IDatabaseApiClient database, CancellationToken cancellationToken) => Results.Ok(await database.ListBudgetsAsync(journeyLabel?.Trim(), category?.Trim().ToLowerInvariant(), cancellationToken));

    private static async Task<IResult> GetBudgetAsync(int id, IDatabaseApiClient database, CancellationToken cancellationToken) => Results.Ok(await database.GetBudgetAsync(id, cancellationToken));

    private static async Task<IResult> CreateBudgetAsync(BudgetWriteRequest request, IDatabaseApiClient database, IExchangeRateProvider rates, HttpContext context, CancellationToken cancellationToken)
    {
        request = Validation.Normalize(request);
        var errors = Validation.Budget(request);
        if (!rates.Supports(request.BaseCurrency)) errors["baseCurrency"] = ["Base currency is not supported."];
        return errors.Count > 0 ? Error(context, 400, "validation_error", "One or more fields are invalid.", errors) : Results.Json(await database.CreateBudgetAsync(request, cancellationToken), statusCode: 201);
    }

    private static async Task<IResult> UpdateBudgetAsync(int id, BudgetWriteRequest request, IDatabaseApiClient database, IExchangeRateProvider rates, HttpContext context, CancellationToken cancellationToken)
    {
        request = Validation.Normalize(request);
        var errors = Validation.Budget(request);
        if (!rates.Supports(request.BaseCurrency)) errors["baseCurrency"] = ["Base currency is not supported."];
        if (errors.Count > 0) return Error(context, 400, "validation_error", "One or more fields are invalid.", errors);
        var current = await database.GetBudgetAsync(id, cancellationToken);
        if (current.BaseCurrency != request.BaseCurrency && (await database.ListExpensesAsync(id, null, null, cancellationToken)).Count > 0) return Error(context, 409, "budget_currency_conflict", "A budget with expenses cannot change base currency.");
        return Results.Ok(await database.UpdateBudgetAsync(id, request, cancellationToken));
    }

    private static async Task<IResult> DeleteBudgetAsync(int id, IDatabaseApiClient database, CancellationToken cancellationToken)
    {
        await database.DeleteBudgetAsync(id, cancellationToken);
        return Results.NoContent();
    }

    private static async Task<IResult> ListExpensesAsync(int? budgetId, string? journeyLabel, string? category, IDatabaseApiClient database, CancellationToken cancellationToken)
    {
        var budgets = await database.ListBudgetsAsync(journeyLabel?.Trim(), category?.Trim().ToLowerInvariant(), cancellationToken);
        if (budgetId is not null) budgets = budgets.Where(value => value.Id == budgetId).ToArray();
        var expenses = await database.ListExpensesAsync(budgetId, journeyLabel?.Trim(), category?.Trim().ToLowerInvariant(), cancellationToken);
        var byId = budgets.ToDictionary(value => value.Id);
        return Results.Ok(expenses.Select(value => Enrich(value, byId.TryGetValue(value.BudgetId, out var budget) ? budget : throw new DatabaseResponseException())));
    }

    private static async Task<IResult> GetExpenseAsync(int id, IDatabaseApiClient database, CancellationToken cancellationToken)
    {
        var value = await database.GetExpenseAsync(id, cancellationToken);
        return Results.Ok(Enrich(value, await database.GetBudgetAsync(value.BudgetId, cancellationToken)));
    }

    private static async Task<IResult> CreateExpenseAsync(ExpenseWriteRequest request, IDatabaseApiClient database, IExchangeRateProvider rates, HttpContext context, CancellationToken cancellationToken)
    {
        request = Validation.Normalize(request);
        var errors = Validation.Expense(request);
        if (!rates.Supports(request.OriginalCurrency)) errors["originalCurrency"] = ["Original currency is not supported."];
        if (errors.Count > 0) return Error(context, 400, "validation_error", "One or more fields are invalid.", errors);
        var budget = await database.GetBudgetAsync(request.BudgetId, cancellationToken);
        if (request.SpentOn < budget.StartDate || request.SpentOn > budget.EndDate) return Error(context, 400, "validation_error", "One or more fields are invalid.", new Dictionary<string, string[]> { ["spentOn"] = ["Spent date must be within the budget period."] });
        var conversion = rates.Convert(request.OriginalAmountMinor, request.OriginalCurrency!, budget.BaseCurrency);
        var saved = await database.CreateExpenseAsync(ToData(request, conversion), cancellationToken);
        return Results.Json(Enrich(saved, budget), statusCode: 201);
    }

    private static async Task<IResult> UpdateExpenseAsync(int id, ExpenseWriteRequest request, IDatabaseApiClient database, IExchangeRateProvider rates, HttpContext context, CancellationToken cancellationToken)
    {
        request = Validation.Normalize(request);
        var errors = Validation.Expense(request);
        if (!rates.Supports(request.OriginalCurrency)) errors["originalCurrency"] = ["Original currency is not supported."];
        if (errors.Count > 0) return Error(context, 400, "validation_error", "One or more fields are invalid.", errors);
        var budget = await database.GetBudgetAsync(request.BudgetId, cancellationToken);
        if (request.SpentOn < budget.StartDate || request.SpentOn > budget.EndDate) return Error(context, 400, "validation_error", "One or more fields are invalid.", new Dictionary<string, string[]> { ["spentOn"] = ["Spent date must be within the budget period."] });
        var conversion = rates.Convert(request.OriginalAmountMinor, request.OriginalCurrency!, budget.BaseCurrency);
        return Results.Ok(Enrich(await database.UpdateExpenseAsync(id, ToData(request, conversion), cancellationToken), budget));
    }

    private static async Task<IResult> DeleteExpenseAsync(int id, IDatabaseApiClient database, CancellationToken cancellationToken)
    {
        await database.DeleteExpenseAsync(id, cancellationToken);
        return Results.NoContent();
    }

    private static async Task<IResult> GetInsightsAsync(InsightRequest request, IDatabaseApiClient database, IAdviceService advice, HttpContext context, CancellationToken cancellationToken)
    {
        if (string.IsNullOrWhiteSpace(request.JourneyLabel) || request.JourneyLabel.Trim().Length > 80) return Error(context, 400, "validation_error", "A valid journey label is required.");
        var label = request.JourneyLabel.Trim();
        var budgets = await database.ListBudgetsAsync(label, null, cancellationToken);
        if (budgets.Count == 0) return Error(context, 400, "no_budget_data", "Budget advice requires at least one budget.");
        var expenses = await database.ListExpensesAsync(null, label, null, cancellationToken);
        return Results.Ok(await advice.GetAdviceAsync(DashboardCalculator.Calculate(budgets[0].JourneyLabel, budgets, expenses), cancellationToken));
    }

    private static ExpenseDataRequest ToData(ExpenseWriteRequest request, ConversionResponse conversion) => new(request.BudgetId, request.Description!, request.OriginalAmountMinor, request.OriginalCurrency!, conversion.ConvertedAmountMinor, conversion.RateScaled, conversion.RateAsOf, request.SpentOn!.Value, request.Notes);
    private static ExpenseResponse Enrich(ExpenseDataResponse value, BudgetResponse budget) => new(value.Id, value.BudgetId, budget.JourneyLabel, budget.Category, value.Description, value.OriginalAmountMinor, value.OriginalCurrency, value.ConvertedAmountMinor, budget.BaseCurrency, value.ConversionRateScaled, value.RateAsOf, value.SpentOn, value.Notes, value.CreatedAt, value.UpdatedAt);
    public static IResult Error(HttpContext context, int status, string code, string message, object? fields = null) => Results.Json(new ApiErrorEnvelope(new ApiError(code, message, fields ?? new Dictionary<string, string[]>(), context.TraceIdentifier)), statusCode: status);
}
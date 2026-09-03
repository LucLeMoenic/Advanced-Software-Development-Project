using BudgetTracker.Database.Data;
using Microsoft.EntityFrameworkCore;

namespace BudgetTracker.Database.Api;

public static class DataEndpoints
{
    private static readonly HashSet<string> Categories = new(StringComparer.OrdinalIgnoreCase)
        { "accommodation", "food", "transport", "activities", "shopping", "other" };
    private static readonly HashSet<string> Currencies = new(StringComparer.OrdinalIgnoreCase)
        { "AUD", "USD", "EUR", "GBP", "NZD", "CAD", "SGD" };

    public static void MapDataEndpoints(this WebApplication app)
    {
        var budgets = app.MapGroup("/api/data/budgets");
        budgets.MapGet("/", ListBudgetsAsync);
        budgets.MapPost("/", CreateBudgetAsync);
        budgets.MapGet("/{id:int}", GetBudgetAsync);
        budgets.MapPut("/{id:int}", UpdateBudgetAsync);
        budgets.MapDelete("/{id:int}", DeleteBudgetAsync);

        var expenses = app.MapGroup("/api/data/expenses");
        expenses.MapGet("/", ListExpensesAsync);
        expenses.MapPost("/", CreateExpenseAsync);
        expenses.MapGet("/{id:int}", GetExpenseAsync);
        expenses.MapPut("/{id:int}", UpdateExpenseAsync);
        expenses.MapDelete("/{id:int}", DeleteExpenseAsync);
    }

    private static async Task<IResult> ListBudgetsAsync(
        BudgetDbContext database,
        string? journeyLabel,
        string? category,
        DateOnly? fromDate,
        DateOnly? toDate,
        CancellationToken cancellationToken)
    {
        var query = database.Budgets.AsNoTracking().AsQueryable();
        if (!string.IsNullOrWhiteSpace(journeyLabel))
        {
            var normalized = journeyLabel.Trim();
            query = query.Where(value => value.JourneyLabel == normalized);
        }
        if (!string.IsNullOrWhiteSpace(category))
        {
            var normalized = category.Trim().ToLowerInvariant();
            query = query.Where(value => value.Category == normalized);
        }
        if (fromDate is not null)
        {
            query = query.Where(value => value.EndDate >= fromDate);
        }
        if (toDate is not null)
        {
            query = query.Where(value => value.StartDate <= toDate);
        }

        var values = await query.OrderBy(value => value.JourneyLabel).ThenBy(value => value.Category).Select(value => ToResponse(value)).ToArrayAsync(cancellationToken);
        return Results.Ok(values);
    }

    private static async Task<IResult> GetBudgetAsync(int id, BudgetDbContext database, HttpContext context, CancellationToken cancellationToken)
    {
        var value = await database.Budgets.AsNoTracking().SingleOrDefaultAsync(item => item.Id == id, cancellationToken);
        return value is null ? NotFound(context, "budget_not_found", "The budget was not found.") : Results.Ok(ToResponse(value));
    }

    private static async Task<IResult> CreateBudgetAsync(BudgetRequest request, BudgetDbContext database, HttpContext context, CancellationToken cancellationToken)
    {
        var validation = ValidateBudget(request);
        if (validation.Errors.Count > 0)
        {
            return Validation(context, validation.Errors);
        }

        if (await HasCurrencyConflictAsync(database, validation.JourneyLabel, validation.BaseCurrency, null, cancellationToken))
        {
            return Conflict(context, "journey_currency_conflict", "All budgets for a journey must use the same base currency.");
        }
        if (await HasDuplicateBudgetAsync(database, validation, null, cancellationToken))
        {
            return Conflict(context, "duplicate_budget", "A budget already exists for this journey, category, and period.");
        }

        var now = DateTime.UtcNow;
        var value = new Budget
        {
            JourneyLabel = validation.JourneyLabel,
            Category = validation.Category,
            LimitAmountMinor = request.LimitAmountMinor,
            BaseCurrency = validation.BaseCurrency,
            StartDate = validation.StartDate,
            EndDate = validation.EndDate,
            CreatedAt = now,
            UpdatedAt = now
        };
        database.Budgets.Add(value);
        await database.SaveChangesAsync(cancellationToken);
        return Results.Created($"/api/data/budgets/{value.Id}", ToResponse(value));
    }

    private static async Task<IResult> UpdateBudgetAsync(int id, BudgetRequest request, BudgetDbContext database, HttpContext context, CancellationToken cancellationToken)
    {
        var validation = ValidateBudget(request);
        if (validation.Errors.Count > 0)
        {
            return Validation(context, validation.Errors);
        }

        var value = await database.Budgets.Include(item => item.Expenses).SingleOrDefaultAsync(item => item.Id == id, cancellationToken);
        if (value is null)
        {
            return NotFound(context, "budget_not_found", "The budget was not found.");
        }
        if (value.Expenses.Any(expense => expense.SpentOn < validation.StartDate || expense.SpentOn > validation.EndDate))
        {
            return Conflict(context, "expense_period_conflict", "The period would exclude an existing expense.");
        }
        if (value.Expenses.Count > 0 && value.BaseCurrency != validation.BaseCurrency)
        {
            return Conflict(context, "budget_currency_conflict", "A budget with expenses cannot change base currency.");
        }
        if (await HasCurrencyConflictAsync(database, validation.JourneyLabel, validation.BaseCurrency, id, cancellationToken))
        {
            return Conflict(context, "journey_currency_conflict", "All budgets for a journey must use the same base currency.");
        }
        if (await HasDuplicateBudgetAsync(database, validation, id, cancellationToken))
        {
            return Conflict(context, "duplicate_budget", "A budget already exists for this journey, category, and period.");
        }

        value.JourneyLabel = validation.JourneyLabel;
        value.Category = validation.Category;
        value.LimitAmountMinor = request.LimitAmountMinor;
        value.BaseCurrency = validation.BaseCurrency;
        value.StartDate = validation.StartDate;
        value.EndDate = validation.EndDate;
        value.UpdatedAt = DateTime.UtcNow;
        await database.SaveChangesAsync(cancellationToken);
        return Results.Ok(ToResponse(value));
    }

    private static async Task<IResult> DeleteBudgetAsync(int id, BudgetDbContext database, HttpContext context, CancellationToken cancellationToken)
    {
        var value = await database.Budgets.SingleOrDefaultAsync(item => item.Id == id, cancellationToken);
        if (value is null)
        {
            return NotFound(context, "budget_not_found", "The budget was not found.");
        }
        database.Budgets.Remove(value);
        await database.SaveChangesAsync(cancellationToken);
        return Results.NoContent();
    }

    private static async Task<IResult> ListExpensesAsync(
        BudgetDbContext database,
        int? budgetId,
        string? journeyLabel,
        string? category,
        DateOnly? fromDate,
        DateOnly? toDate,
        CancellationToken cancellationToken)
    {
        var query = database.Expenses.AsNoTracking().Include(value => value.Budget).AsQueryable();
        if (budgetId is not null)
        {
            query = query.Where(value => value.BudgetId == budgetId);
        }
        if (!string.IsNullOrWhiteSpace(journeyLabel))
        {
            var normalized = journeyLabel.Trim();
            query = query.Where(value => value.Budget.JourneyLabel == normalized);
        }
        if (!string.IsNullOrWhiteSpace(category))
        {
            var normalized = category.Trim().ToLowerInvariant();
            query = query.Where(value => value.Budget.Category == normalized);
        }
        if (fromDate is not null)
        {
            query = query.Where(value => value.SpentOn >= fromDate);
        }
        if (toDate is not null)
        {
            query = query.Where(value => value.SpentOn <= toDate);
        }

        var values = await query.OrderByDescending(value => value.SpentOn).ThenByDescending(value => value.Id).Select(value => ToResponse(value)).ToArrayAsync(cancellationToken);
        return Results.Ok(values);
    }

    private static async Task<IResult> GetExpenseAsync(int id, BudgetDbContext database, HttpContext context, CancellationToken cancellationToken)
    {
        var value = await database.Expenses.AsNoTracking().SingleOrDefaultAsync(item => item.Id == id, cancellationToken);
        return value is null ? NotFound(context, "expense_not_found", "The expense was not found.") : Results.Ok(ToResponse(value));
    }

    private static async Task<IResult> CreateExpenseAsync(ExpenseRequest request, BudgetDbContext database, HttpContext context, CancellationToken cancellationToken)
    {
        var validation = ValidateExpense(request);
        if (validation.Errors.Count > 0)
        {
            return Validation(context, validation.Errors);
        }
        var budget = await database.Budgets.SingleOrDefaultAsync(value => value.Id == request.BudgetId, cancellationToken);
        if (budget is null)
        {
            return NotFound(context, "budget_not_found", "The budget was not found.");
        }
        if (validation.SpentOn < budget.StartDate || validation.SpentOn > budget.EndDate)
        {
            return Validation(context, new Dictionary<string, string[]> { ["spentOn"] = ["Spent date must be within the budget period."] });
        }

        var now = DateTime.UtcNow;
        var value = new Expense
        {
            BudgetId = request.BudgetId,
            Description = validation.Description,
            OriginalAmountMinor = request.OriginalAmountMinor,
            OriginalCurrency = validation.OriginalCurrency,
            ConvertedAmountMinor = request.ConvertedAmountMinor,
            ConversionRateScaled = request.ConversionRateScaled,
            RateAsOf = validation.RateAsOf,
            SpentOn = validation.SpentOn,
            Notes = validation.Notes,
            CreatedAt = now,
            UpdatedAt = now
        };
        database.Expenses.Add(value);
        await database.SaveChangesAsync(cancellationToken);
        return Results.Created($"/api/data/expenses/{value.Id}", ToResponse(value));
    }

    private static async Task<IResult> UpdateExpenseAsync(int id, ExpenseRequest request, BudgetDbContext database, HttpContext context, CancellationToken cancellationToken)
    {
        var validation = ValidateExpense(request);
        if (validation.Errors.Count > 0)
        {
            return Validation(context, validation.Errors);
        }
        var value = await database.Expenses.SingleOrDefaultAsync(item => item.Id == id, cancellationToken);
        if (value is null)
        {
            return NotFound(context, "expense_not_found", "The expense was not found.");
        }
        var budget = await database.Budgets.SingleOrDefaultAsync(item => item.Id == request.BudgetId, cancellationToken);
        if (budget is null)
        {
            return NotFound(context, "budget_not_found", "The budget was not found.");
        }
        if (validation.SpentOn < budget.StartDate || validation.SpentOn > budget.EndDate)
        {
            return Validation(context, new Dictionary<string, string[]> { ["spentOn"] = ["Spent date must be within the budget period."] });
        }

        value.BudgetId = request.BudgetId;
        value.Description = validation.Description;
        value.OriginalAmountMinor = request.OriginalAmountMinor;
        value.OriginalCurrency = validation.OriginalCurrency;
        value.ConvertedAmountMinor = request.ConvertedAmountMinor;
        value.ConversionRateScaled = request.ConversionRateScaled;
        value.RateAsOf = validation.RateAsOf;
        value.SpentOn = validation.SpentOn;
        value.Notes = validation.Notes;
        value.UpdatedAt = DateTime.UtcNow;
        await database.SaveChangesAsync(cancellationToken);
        return Results.Ok(ToResponse(value));
    }

    private static async Task<IResult> DeleteExpenseAsync(int id, BudgetDbContext database, HttpContext context, CancellationToken cancellationToken)
    {
        var value = await database.Expenses.SingleOrDefaultAsync(item => item.Id == id, cancellationToken);
        if (value is null)
        {
            return NotFound(context, "expense_not_found", "The expense was not found.");
        }
        database.Expenses.Remove(value);
        await database.SaveChangesAsync(cancellationToken);
        return Results.NoContent();
    }

    private static BudgetValidation ValidateBudget(BudgetRequest request)
    {
        var errors = new Dictionary<string, string[]>();
        var journeyLabel = request.JourneyLabel?.Trim() ?? string.Empty;
        var category = request.Category?.Trim().ToLowerInvariant() ?? string.Empty;
        var currency = request.BaseCurrency?.Trim().ToUpperInvariant() ?? string.Empty;
        if (journeyLabel.Length is < 1 or > 80) errors["journeyLabel"] = ["Journey label must contain 1 to 80 characters."];
        if (!Categories.Contains(category)) errors["category"] = ["Category is not supported."];
        if (request.LimitAmountMinor <= 0) errors["limitAmountMinor"] = ["Limit amount must be positive."];
        if (!Currencies.Contains(currency)) errors["baseCurrency"] = ["Base currency is not supported."];
        if (request.StartDate is null) errors["startDate"] = ["Start date is required."];
        if (request.EndDate is null) errors["endDate"] = ["End date is required."];
        if (request.StartDate is not null && request.EndDate is not null && request.EndDate < request.StartDate) errors["endDate"] = ["End date must not be before start date."];
        return new(journeyLabel, category, currency, request.StartDate ?? default, request.EndDate ?? default, errors);
    }

    private static ExpenseValidation ValidateExpense(ExpenseRequest request)
    {
        var errors = new Dictionary<string, string[]>();
        var description = request.Description?.Trim() ?? string.Empty;
        var currency = request.OriginalCurrency?.Trim().ToUpperInvariant() ?? string.Empty;
        var notes = string.IsNullOrWhiteSpace(request.Notes) ? null : request.Notes.Trim();
        if (request.BudgetId <= 0) errors["budgetId"] = ["Budget id must be positive."];
        if (description.Length is < 1 or > 120) errors["description"] = ["Description must contain 1 to 120 characters."];
        if (request.OriginalAmountMinor <= 0) errors["originalAmountMinor"] = ["Original amount must be positive."];
        if (!Currencies.Contains(currency)) errors["originalCurrency"] = ["Original currency is not supported."];
        if (request.ConvertedAmountMinor <= 0) errors["convertedAmountMinor"] = ["Converted amount must be positive."];
        if (request.ConversionRateScaled <= 0) errors["conversionRateScaled"] = ["Conversion rate must be positive."];
        if (request.RateAsOf is null) errors["rateAsOf"] = ["Rate date is required."];
        if (request.SpentOn is null) errors["spentOn"] = ["Spent date is required."];
        if (notes?.Length > 500) errors["notes"] = ["Notes must contain at most 500 characters."];
        return new(description, currency, request.RateAsOf ?? default, request.SpentOn ?? default, notes, errors);
    }

    private static Task<bool> HasCurrencyConflictAsync(BudgetDbContext database, string journeyLabel, string currency, int? excludedId, CancellationToken cancellationToken) =>
        database.Budgets.AnyAsync(value => value.JourneyLabel == journeyLabel && value.BaseCurrency != currency && (!excludedId.HasValue || value.Id != excludedId), cancellationToken);

    private static Task<bool> HasDuplicateBudgetAsync(BudgetDbContext database, BudgetValidation request, int? excludedId, CancellationToken cancellationToken) =>
        database.Budgets.AnyAsync(value => value.JourneyLabel == request.JourneyLabel && value.Category == request.Category && value.StartDate == request.StartDate && value.EndDate == request.EndDate && (!excludedId.HasValue || value.Id != excludedId), cancellationToken);

    private static BudgetResponse ToResponse(Budget value) => new(value.Id, value.JourneyLabel, value.Category, value.LimitAmountMinor, value.BaseCurrency, value.StartDate, value.EndDate, value.CreatedAt, value.UpdatedAt);
    private static ExpenseResponse ToResponse(Expense value) => new(value.Id, value.BudgetId, value.Description, value.OriginalAmountMinor, value.OriginalCurrency, value.ConvertedAmountMinor, value.ConversionRateScaled, value.RateAsOf, value.SpentOn, value.Notes, value.CreatedAt, value.UpdatedAt);

    private static IResult Validation(HttpContext context, object fields) => Error(context, 400, "validation_error", "One or more fields are invalid.", fields);
    private static IResult NotFound(HttpContext context, string code, string message) => Error(context, 404, code, message);
    private static IResult Conflict(HttpContext context, string code, string message) => Error(context, 409, code, message);
    public static IResult Error(HttpContext context, int status, string code, string message, object? fields = null) =>
        Results.Json(new ApiErrorEnvelope(new ApiError(code, message, fields ?? new Dictionary<string, string[]>(), context.TraceIdentifier)), statusCode: status);

    private sealed record BudgetValidation(string JourneyLabel, string Category, string BaseCurrency, DateOnly StartDate, DateOnly EndDate, Dictionary<string, string[]> Errors);
    private sealed record ExpenseValidation(string Description, string OriginalCurrency, DateOnly RateAsOf, DateOnly SpentOn, string? Notes, Dictionary<string, string[]> Errors);
}
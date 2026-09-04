namespace BudgetTracker.Database.Api;

public sealed record BudgetRequest(
    string? JourneyLabel,
    string? Category,
    long LimitAmountMinor,
    string? BaseCurrency,
    DateOnly? StartDate,
    DateOnly? EndDate);
// Budget response record
public sealed record BudgetResponse(
    int Id,
    string JourneyLabel,
    string Category,
    long LimitAmountMinor,
    string BaseCurrency,
    DateOnly StartDate,
    DateOnly EndDate,
    DateTime CreatedAt,
    DateTime UpdatedAt);

public sealed record ExpenseRequest(
    int BudgetId,
    string? Description,
    long OriginalAmountMinor,
    string? OriginalCurrency,
    long ConvertedAmountMinor,
    long ConversionRateScaled,
    DateOnly? RateAsOf,
    DateOnly? SpentOn,
    string? Notes);

public sealed record ExpenseResponse(
    int Id,
    int BudgetId,
    string Description,
    long OriginalAmountMinor,
    string OriginalCurrency,
    long ConvertedAmountMinor,
    long ConversionRateScaled,
    DateOnly RateAsOf,
    DateOnly SpentOn,
    string? Notes,
    DateTime CreatedAt,
    DateTime UpdatedAt);

public sealed record ApiError(string Code, string Message, object Fields, string CorrelationId);
public sealed record ApiErrorEnvelope(ApiError Error);
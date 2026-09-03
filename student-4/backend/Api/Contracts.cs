namespace BudgetTracker.Backend.Api;

public sealed record BudgetWriteRequest(
    string? JourneyLabel,
    string? Category,
    long LimitAmountMinor,
    string? BaseCurrency,
    DateOnly? StartDate,
    DateOnly? EndDate);

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

public sealed record ExpenseWriteRequest(
    int BudgetId,
    string? Description,
    long OriginalAmountMinor,
    string? OriginalCurrency,
    DateOnly? SpentOn,
    string? Notes);

public sealed record ExpenseDataRequest(
    int BudgetId,
    string Description,
    long OriginalAmountMinor,
    string OriginalCurrency,
    long ConvertedAmountMinor,
    long ConversionRateScaled,
    DateOnly RateAsOf,
    DateOnly SpentOn,
    string? Notes);

public sealed record ExpenseDataResponse(
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

public sealed record ExpenseResponse(
    int Id,
    int BudgetId,
    string JourneyLabel,
    string Category,
    string Description,
    long OriginalAmountMinor,
    string OriginalCurrency,
    long ConvertedAmountMinor,
    string BaseCurrency,
    long ConversionRateScaled,
    DateOnly RateAsOf,
    DateOnly SpentOn,
    string? Notes,
    DateTime CreatedAt,
    DateTime UpdatedAt);

public sealed record ConversionPreviewRequest(long OriginalAmountMinor, string? FromCurrency, string? ToCurrency);
public sealed record ConversionResponse(long OriginalAmountMinor, string FromCurrency, long ConvertedAmountMinor, string ToCurrency, decimal Rate, long RateScaled, DateOnly RateAsOf, string RateVersion, string Disclaimer);
public sealed record CurrencyResponse(string Code);
public sealed record JourneyResponse(string JourneyLabel, string BaseCurrency, DateOnly StartDate, DateOnly EndDate);
public sealed record CategoryDashboardResponse(string Category, long PlannedAmountMinor, long ActualAmountMinor, long RemainingAmountMinor, decimal PercentageUsed, string Status);
public sealed record DashboardResponse(string JourneyLabel, string BaseCurrency, long PlannedAmountMinor, long ActualAmountMinor, long RemainingAmountMinor, decimal PercentageUsed, IReadOnlyList<CategoryDashboardResponse> Categories);
public sealed record InsightRequest(string? JourneyLabel);
public sealed record AdviceSuggestion(string Category, string Text);
public sealed record AdviceResponse(string Summary, IReadOnlyList<AdviceSuggestion> Suggestions, string Source);
public sealed record ApiError(string Code, string Message, object Fields, string CorrelationId);
public sealed record ApiErrorEnvelope(ApiError Error);
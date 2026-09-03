namespace BudgetTracker.Backend.Api;

public static class Validation
{
    public static readonly HashSet<string> Categories = new(StringComparer.OrdinalIgnoreCase)
        { "accommodation", "food", "transport", "activities", "shopping", "other" };

    public static Dictionary<string, string[]> Budget(BudgetWriteRequest request)
    {
        var errors = new Dictionary<string, string[]>();
        if (request.JourneyLabel?.Trim().Length is not (>= 1 and <= 80)) errors["journeyLabel"] = ["Journey label must contain 1 to 80 characters."];
        if (request.Category is null || !Categories.Contains(request.Category.Trim())) errors["category"] = ["Category is not supported."];
        if (request.LimitAmountMinor <= 0) errors["limitAmountMinor"] = ["Limit amount must be positive."];
        if (request.BaseCurrency is null || request.BaseCurrency.Trim().Length != 3) errors["baseCurrency"] = ["Base currency is not supported."];
        if (request.StartDate is null) errors["startDate"] = ["Start date is required."];
        if (request.EndDate is null) errors["endDate"] = ["End date is required."];
        if (request.StartDate is not null && request.EndDate is not null && request.EndDate < request.StartDate) errors["endDate"] = ["End date must not be before start date."];
        return errors;
    }

    public static Dictionary<string, string[]> Expense(ExpenseWriteRequest request)
    {
        var errors = new Dictionary<string, string[]>();
        if (request.BudgetId <= 0) errors["budgetId"] = ["Budget id must be positive."];
        if (request.Description?.Trim().Length is not (>= 1 and <= 120)) errors["description"] = ["Description must contain 1 to 120 characters."];
        if (request.OriginalAmountMinor <= 0) errors["originalAmountMinor"] = ["Original amount must be positive."];
        if (request.OriginalCurrency?.Trim().Length != 3) errors["originalCurrency"] = ["Original currency is not supported."];
        if (request.SpentOn is null) errors["spentOn"] = ["Spent date is required."];
        if (request.Notes?.Trim().Length > 500) errors["notes"] = ["Notes must contain at most 500 characters."];
        return errors;
    }

    public static BudgetWriteRequest Normalize(BudgetWriteRequest request) => request with
    {
        JourneyLabel = request.JourneyLabel?.Trim(),
        Category = request.Category?.Trim().ToLowerInvariant(),
        BaseCurrency = request.BaseCurrency?.Trim().ToUpperInvariant()
    };

    public static ExpenseWriteRequest Normalize(ExpenseWriteRequest request) => request with
    {
        Description = request.Description?.Trim(),
        OriginalCurrency = request.OriginalCurrency?.Trim().ToUpperInvariant(),
        Notes = string.IsNullOrWhiteSpace(request.Notes) ? null : request.Notes.Trim()
    };
}
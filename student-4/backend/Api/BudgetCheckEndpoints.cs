using System.Text.Json;
using System.Text;
using BudgetTracker.Backend.Clients;
using BudgetTracker.Backend.Services;

namespace BudgetTracker.Backend.Api;

public static class BudgetCheckEndpoints
{
    private const int MaxRequestBytes = 8 * 1024;
    private const long MaxSafeInteger = 9_007_199_254_740_991;
    private static readonly HashSet<string> AllowedCategories = new(StringComparer.OrdinalIgnoreCase)
    {
        "accommodation", "food", "transport", "activities", "shopping", "other"
    };

    public static void MapBudgetCheckEndpoints(this WebApplication app) =>
        app.MapPost("/api/budget-check", HandleAsync);

    private static async Task<IResult> HandleAsync(
        HttpContext context,
        FeatureModeSettings modes,
        IMcpBudgetCheckClient mcp,
        IExchangeRateProvider rates,
        CancellationToken cancellationToken)
    {
        if (!modes.McpEnabled)
        {
            return BudgetEndpoints.Error(context, 503, "feature_disabled", "Budget check is disabled.");
        }

        var journeyLabel = await ReadJourneyLabelAsync(context.Request, cancellationToken);
        if (journeyLabel is null)
        {
            return BudgetEndpoints.Error(context, 400, "invalid_request", "The request body must contain only a valid journeyLabel.");
        }

        try
        {
            var summary = await mcp.CallAsync(journeyLabel, cancellationToken);
            var validated = ValidateSummary(summary, journeyLabel, rates.Currencies);
            return Results.Ok(new BudgetCheckResponse("budget.get_summary", new BudgetCheckResult(true, validated)));
        }
        catch (BudgetCheckFailureException exception)
        {
            return BudgetEndpoints.Error(context, exception.StatusCode, exception.Code, exception.Message);
        }
    }

    private static async Task<string?> ReadJourneyLabelAsync(HttpRequest request, CancellationToken cancellationToken)
    {
        if (request.ContentLength is > MaxRequestBytes) return null;

        using var body = new MemoryStream();
        var buffer = new byte[4096];
        while (true)
        {
            var count = await request.Body.ReadAsync(buffer.AsMemory(0, Math.Min(buffer.Length, MaxRequestBytes + 1 - (int)body.Length)), cancellationToken);
            if (count == 0) break;
            if (body.Length + count > MaxRequestBytes) return null;
            body.Write(buffer, 0, count);
        }

        try
        {
            using var document = JsonDocument.Parse(body.ToArray());
            if (document.RootElement.ValueKind != JsonValueKind.Object) return null;

            var seen = false;
            string? label = null;
            foreach (var property in document.RootElement.EnumerateObject())
            {
                if (property.Name != "journeyLabel" || seen || property.Value.ValueKind != JsonValueKind.String) return null;
                seen = true;
                label = property.Value.GetString()?.Trim();
            }

            return seen && IsValidLabel(label) ? label : null;
        }
        catch (JsonException)
        {
            return null;
        }
    }

    private static bool IsValidLabel(string? label)
    {
        if (string.IsNullOrWhiteSpace(label)) return false;
        var characterCount = 0;
        foreach (var _ in label.EnumerateRunes()) characterCount++;
        return characterCount is >= 1 and <= 80;
    }

    private static DashboardResponse ValidateSummary(JsonElement summary, string requestedLabel, IReadOnlyList<string> currencies)
    {
        if (!HasExactProperties(summary,
                "journeyLabel", "baseCurrency", "plannedAmountMinor", "actualAmountMinor",
                "remainingAmountMinor", "percentageUsed", "categories"))
        {
            throw InvalidDependencyResponse();
        }

        var label = ReadString(summary, "journeyLabel");
        var currency = ReadString(summary, "baseCurrency");
        if (!IsValidLabel(label) || label != label.Trim()
            || !string.Equals(label, requestedLabel, StringComparison.OrdinalIgnoreCase)
            || !currencies.Contains(currency, StringComparer.OrdinalIgnoreCase))
        {
            throw InvalidDependencyResponse();
        }

        var planned = ReadMoney(summary, "plannedAmountMinor");
        var actual = ReadMoney(summary, "actualAmountMinor");
        var remaining = ReadMoney(summary, "remainingAmountMinor");
        var percentage = ReadPercentage(summary, "percentageUsed");
        if (planned <= 0 || actual < 0 || remaining != planned - actual
            || percentage != Percentage(actual, planned))
        {
            throw InvalidDependencyResponse();
        }

        var categoryValues = summary.GetProperty("categories");
        if (categoryValues.ValueKind != JsonValueKind.Array || categoryValues.GetArrayLength() is < 1 or > 6)
        {
            throw InvalidDependencyResponse();
        }

        var categories = new List<CategoryDashboardResponse>();
        var names = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        long plannedSum = 0;
        long actualSum = 0;
        long remainingSum = 0;
        try
        {
            checked
            {
                foreach (var category in categoryValues.EnumerateArray())
                {
                    if (!HasExactProperties(category,
                            "category", "plannedAmountMinor", "actualAmountMinor", "remainingAmountMinor", "percentageUsed", "status"))
                    {
                        throw InvalidDependencyResponse();
                    }

                    var name = ReadString(category, "category");
                    var categoryPlanned = ReadMoney(category, "plannedAmountMinor");
                    var categoryActual = ReadMoney(category, "actualAmountMinor");
                    var categoryRemaining = ReadMoney(category, "remainingAmountMinor");
                    var categoryPercentage = ReadPercentage(category, "percentageUsed");
                    var status = ReadString(category, "status");
                    if (name != name.Trim() || !AllowedCategories.Contains(name) || !names.Add(name)
                        || categoryPlanned <= 0 || categoryActual < 0
                        || categoryRemaining != categoryPlanned - categoryActual
                        || categoryPercentage != Percentage(categoryActual, categoryPlanned)
                        || status != Status(categoryActual, categoryPlanned))
                    {
                        throw InvalidDependencyResponse();
                    }

                    EnsureSafe(categoryPlanned);
                    EnsureSafe(categoryActual);
                    EnsureSafe(categoryRemaining);
                    categories.Add(new(name, categoryPlanned, categoryActual, categoryRemaining, categoryPercentage, status));
                    plannedSum += categoryPlanned;
                    actualSum += categoryActual;
                    remainingSum += categoryRemaining;
                }
            }
        }
        catch (OverflowException exception)
        {
            throw InvalidDependencyResponse(exception);
        }

        if (plannedSum != planned || actualSum != actual || remainingSum != remaining)
        {
            throw InvalidDependencyResponse();
        }

        EnsureSafe(planned);
        EnsureSafe(actual);
        EnsureSafe(remaining);
        return new(label, currency, planned, actual, remaining, percentage, categories);
    }

    private static bool HasExactProperties(JsonElement value, params string[] expected)
    {
        if (value.ValueKind != JsonValueKind.Object) return false;
        var seen = new HashSet<string>(StringComparer.Ordinal);
        foreach (var property in value.EnumerateObject())
        {
            if (!seen.Add(property.Name) || !expected.Contains(property.Name, StringComparer.Ordinal)) return false;
        }

        return seen.Count == expected.Length;
    }

    private static string ReadString(JsonElement value, string name)
    {
        var field = value.GetProperty(name);
        if (field.ValueKind != JsonValueKind.String) throw InvalidDependencyResponse();
        return field.GetString() ?? throw InvalidDependencyResponse();
    }

    private static long ReadMoney(JsonElement value, string name)
    {
        var field = value.GetProperty(name);
        if (field.ValueKind != JsonValueKind.Number || !field.TryGetInt64(out var amount)) throw InvalidDependencyResponse();
        EnsureSafe(amount);
        return amount;
    }

    private static decimal ReadPercentage(JsonElement value, string name)
    {
        var field = value.GetProperty(name);
        if (field.ValueKind != JsonValueKind.Number || !field.TryGetDecimal(out var percentage)) throw InvalidDependencyResponse();
        return percentage;
    }

    private static decimal Percentage(long actual, long planned) =>
        Math.Round(actual * 100m / planned, 2, MidpointRounding.AwayFromZero);

    private static string Status(long actual, long planned)
    {
        var ratio = actual * 100m / planned;
        return ratio > 100m ? "overspent" : ratio >= 80m ? "warning" : "within_budget";
    }

    private static void EnsureSafe(long amount)
    {
        if (amount is < -MaxSafeInteger or > MaxSafeInteger)
        {
            throw new BudgetCheckFailureException(502, "summary_out_of_display_range", "The budget summary exceeds the browser's exact integer range.");
        }
    }

    private static BudgetCheckFailureException InvalidDependencyResponse(Exception? innerException = null) =>
        new(502, "dependency_response_invalid", "The MCP service returned an unusable budget summary.", innerException);
}

public sealed record BudgetCheckResponse(string Tool, BudgetCheckResult Result);
public sealed record BudgetCheckResult(bool Ok, DashboardResponse Summary);
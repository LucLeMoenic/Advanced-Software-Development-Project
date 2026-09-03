using BudgetTracker.Backend.Api;
using BudgetTracker.Backend.Clients;

namespace BudgetTracker.Backend.Services;

public interface IAdviceService
{
    Task<AdviceResponse> GetAdviceAsync(DashboardResponse dashboard, CancellationToken cancellationToken);
}

public sealed class AdviceService(IOllamaInsightsClient ollama) : IAdviceService
{
    public async Task<AdviceResponse> GetAdviceAsync(DashboardResponse dashboard, CancellationToken cancellationToken)
    {
        try
        {
            return await ollama.GenerateAsync(dashboard, false, cancellationToken);
        }
        catch (OllamaResponseException)
        {
            try { return await ollama.GenerateAsync(dashboard, true, cancellationToken); }
            catch (OllamaResponseException) { return Fallback(dashboard); }
            catch (OllamaUnavailableException) { return Fallback(dashboard); }
        }
        catch (OllamaUnavailableException)
        {
            return Fallback(dashboard);
        }
    }

    public static AdviceResponse Fallback(DashboardResponse dashboard)
    {
        var ordered = dashboard.Categories
            .OrderByDescending(value => value.Status == "overspent")
            .ThenByDescending(value => value.Status == "warning")
            .ThenByDescending(value => value.PercentageUsed)
            .Take(3)
            .ToArray();
        var overspent = dashboard.Categories.Where(value => value.Status == "overspent").Select(value => value.Category).ToArray();
        var warning = dashboard.Categories.Where(value => value.Status == "warning").Select(value => value.Category).ToArray();
        var summary = overspent.Length > 0
            ? $"{string.Join(", ", overspent)} spending is over its planned limit."
            : warning.Length > 0
                ? $"{string.Join(", ", warning)} spending is approaching its planned limit."
                : "Recorded spending remains below the warning threshold in every category.";
        var suggestions = ordered.Select(value => new AdviceSuggestion(value.Category, value.Status switch
        {
            "overspent" => $"Pause discretionary {value.Category} spending and review recent entries.",
            "warning" => $"Set aside the remaining {value.Category} amount before adding new costs.",
            _ => $"Keep tracking {value.Category} expenses against the available balance."
        })).ToArray();
        return new(summary, suggestions, "fallback");
    }
}
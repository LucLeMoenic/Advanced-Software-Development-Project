using System.Net.Http.Json;
using System.Text.Json;
using System.Text.Json.Serialization;
using BudgetTracker.Backend.Api;

namespace BudgetTracker.Backend.Clients;

public interface IOllamaInsightsClient
{
    Task<AdviceResponse> GenerateAsync(DashboardResponse dashboard, bool correctiveRetry, CancellationToken cancellationToken);
}

public sealed record OllamaInsightsSettings(string Model, string Prompt);

public sealed class OllamaInsightsClient(HttpClient client, OllamaInsightsSettings settings) : IOllamaInsightsClient
{
    private static readonly JsonSerializerOptions JsonOptions = new(JsonSerializerDefaults.Web);

    public async Task<AdviceResponse> GenerateAsync(DashboardResponse dashboard, bool correctiveRetry, CancellationToken cancellationToken)
    {
        var categories = dashboard.Categories.Select(value => value.Category).ToArray();
        var input = new
        {
            journeyLabel = dashboard.JourneyLabel,
            baseCurrency = dashboard.BaseCurrency,
            totals = new { dashboard.PlannedAmountMinor, dashboard.ActualAmountMinor, dashboard.RemainingAmountMinor, dashboard.PercentageUsed },
            categories = dashboard.Categories.Select(value => new { value.Category, value.PlannedAmountMinor, value.ActualAmountMinor, value.RemainingAmountMinor, value.PercentageUsed, value.Status })
        };
        var correction = correctiveRetry
            ? "\nCORRECTION: The previous response was invalid. Return one complete JSON object matching the schema exactly.\n"
            : "\n";
        var prompt = settings.Prompt + correction + JsonSerializer.Serialize(input, JsonOptions);
        var format = JsonSerializer.SerializeToElement(new
        {
            type = "object",
            properties = new
            {
                summary = new { type = "string", minLength = 1, maxLength = 240 },
                suggestions = new
                {
                    type = "array",
                    minItems = 1,
                    maxItems = 3,
                    items = new
                    {
                        type = "object",
                        properties = new
                        {
                            category = new { type = "string", @enum = categories },
                            text = new { type = "string", minLength = 1, maxLength = 180 }
                        },
                        required = new[] { "category", "text" },
                        additionalProperties = false
                    }
                }
            },
            required = new[] { "summary", "suggestions" },
            additionalProperties = false
        }, JsonOptions);

        HttpResponseMessage response;
        try
        {
            response = await client.PostAsJsonAsync("/api/generate", new GenerateRequest(settings.Model, prompt, false, format, new GenerateOptions(0, 500), "30m"), JsonOptions, cancellationToken);
        }
        catch (TaskCanceledException exception) when (!cancellationToken.IsCancellationRequested)
        {
            throw new OllamaUnavailableException("timeout", exception);
        }
        catch (HttpRequestException exception)
        {
            throw new OllamaUnavailableException("connection", exception);
        }

        using (response)
        {
            if (!response.IsSuccessStatusCode) throw new OllamaUnavailableException("http_status");
            GenerateResponse? generated;
            try { generated = await response.Content.ReadFromJsonAsync<GenerateResponse>(JsonOptions, cancellationToken); }
            catch (JsonException exception) { throw new OllamaResponseException(exception); }
            if (generated?.Done != true || string.IsNullOrWhiteSpace(generated.Response)) throw new OllamaResponseException();
            return Validate(generated.Response, categories, correctiveRetry ? "ai_retry" : "ai");
        }
    }

    private static AdviceResponse Validate(string content, IReadOnlyCollection<string> categories, string source)
    {
        ModelAdvice? value;
        try { value = JsonSerializer.Deserialize<ModelAdvice>(content, JsonOptions); }
        catch (JsonException exception) { throw new OllamaResponseException(exception); }
        if (value is null || !Text(value.Summary, 240) || value.Suggestions is null || value.Suggestions.Length is < 1 or > 3)
        {
            throw new OllamaResponseException();
        }
        foreach (var suggestion in value.Suggestions)
        {
            if (suggestion is null || !categories.Contains(suggestion.Category, StringComparer.OrdinalIgnoreCase) || !Text(suggestion.Text, 180)) throw new OllamaResponseException();
        }
        return new(value.Summary!, value.Suggestions.Select(value => new AdviceSuggestion(value!.Category!, value.Text!)).ToArray(), source);
    }

    private static bool Text(string? value, int maximum) => value is not null && value == value.Trim() && value.Length is >= 1 && value.Length <= maximum && !value.Contains('\n') && !value.Contains('\r');

    private sealed record GenerateRequest(string Model, string Prompt, bool Stream, JsonElement Format, GenerateOptions Options, [property: JsonPropertyName("keep_alive")] string KeepAlive);
    private sealed record GenerateOptions(double Temperature, [property: JsonPropertyName("num_predict")] int NumPredict);
    private sealed record GenerateResponse(string? Response, bool? Done);
    [JsonUnmappedMemberHandling(JsonUnmappedMemberHandling.Disallow)]
    private sealed record ModelAdvice(string? Summary, ModelSuggestion?[]? Suggestions);
    [JsonUnmappedMemberHandling(JsonUnmappedMemberHandling.Disallow)]
    private sealed record ModelSuggestion(string? Category, string? Text);
}

public sealed class OllamaUnavailableException(string category, Exception? inner = null) : Exception("Ollama is unavailable.", inner)
{
    public string Category { get; } = category;
}
public sealed class OllamaResponseException(Exception? inner = null) : Exception("Ollama returned unusable advice.", inner);
using System.Net.Http.Json;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Text.RegularExpressions;
using Accommodation.Backend.Api;

namespace Accommodation.Backend.Clients;

public interface ILookupArgumentExtractor
{
    Task<LookupCall> ExtractAsync(string question, CancellationToken cancellationToken);
}

public sealed record LookupExtractorSettings(string Model, string Prompt);

public sealed class OllamaLookupExtractor(
    HttpClient client,
    LookupExtractorSettings settings) : ILookupArgumentExtractor
{
    private const string Dependency = "assistant_model";
    private static readonly JsonSerializerOptions JsonOptions = new(JsonSerializerDefaults.Web);
    private static readonly string[] Fields = ["tool", "destination", "guests", "max_nightly_price", "search_id"];

    private static readonly JsonElement Format = JsonSerializer.SerializeToElement(new
    {
        type = "object",
        additionalProperties = false,
        required = new[] { "tool" },
        properties = new Dictionary<string, object>
        {
            ["tool"] = new { type = "string", @enum = AssistantTools.Allowed.Order().ToArray() },
            ["destination"] = new { type = "string", minLength = 1, maxLength = 100 },
            ["guests"] = new { type = "integer", minimum = 1, maximum = 20 },
            ["max_nightly_price"] = new { type = "number", exclusiveMinimum = 0, maximum = 100000 },
            ["search_id"] = new { type = "integer", minimum = 1 }
        }
    });

    public async Task<LookupCall> ExtractAsync(string question, CancellationToken cancellationToken)
    {
        HttpResponseMessage response;
        try
        {
            response = await client.PostAsJsonAsync(
                "/api/generate",
                new GenerateRequest(
                    settings.Model,
                    settings.Prompt,
                    JsonSerializer.Serialize(new { question }),
                    false,
                    Format,
                    new GenerateOptions(0, 120),
                    "30m"),
                JsonOptions,
                cancellationToken);
        }
        catch (TaskCanceledException exception) when (!cancellationToken.IsCancellationRequested)
        {
            throw new AssistantException(AssistantFailure.Timeout, Dependency, exception);
        }
        catch (HttpRequestException exception)
        {
            throw new AssistantException(AssistantFailure.Unavailable, Dependency, exception);
        }

        using (response)
        {
            if (!response.IsSuccessStatusCode)
            {
                throw new AssistantException(AssistantFailure.Unavailable, Dependency);
            }

            try
            {
                var generated = await response.Content.ReadFromJsonAsync<GenerateResponse>(JsonOptions, cancellationToken);
                if (generated is not { Done: true } || string.IsNullOrWhiteSpace(generated.Response))
                {
                    throw new AssistantException(AssistantFailure.InvalidResponse, Dependency);
                }

                using var document = JsonDocument.Parse(generated.Response);
                return Validate(document.RootElement, question);
            }
            catch (JsonException exception)
            {
                throw new AssistantException(AssistantFailure.InvalidResponse, Dependency, exception);
            }
            catch (TaskCanceledException exception) when (!cancellationToken.IsCancellationRequested)
            {
                throw new AssistantException(AssistantFailure.Timeout, Dependency, exception);
            }
        }
    }

    public static LookupCall Validate(JsonElement root, string question)
    {
        if (root.ValueKind != JsonValueKind.Object
            || root.EnumerateObject().Any(property => !Fields.Contains(property.Name))
            || !root.TryGetProperty("tool", out var toolElement)
            || toolElement.ValueKind != JsonValueKind.String
            || !AssistantTools.Allowed.Contains(toolElement.GetString()!))
        {
            throw new AssistantException(AssistantFailure.InvalidResponse, Dependency);
        }

        // Nulls are treated as omitted optional values; any other wrong type is a model format failure.
        var values = root.EnumerateObject()
            .Where(property => property.Name != "tool" && property.Value.ValueKind != JsonValueKind.Null)
            .ToDictionary(property => property.Name, property => property.Value);
        var arguments = new Dictionary<string, object>(StringComparer.Ordinal);

        if (toolElement.GetString() == AssistantTools.GetSearch)
        {
            if (values.Keys.Any(name => name != "search_id")
                || !values.TryGetValue("search_id", out var searchId)
                || !TryInteger(searchId, 1, int.MaxValue, out var id)
                || !Regex.IsMatch(question, $@"(?<!\d){id}(?!\d)"))
            {
                throw NotUnderstood();
            }

            arguments["search_id"] = id;
            return new LookupCall(AssistantTools.GetSearch, arguments);
        }

        if (values.ContainsKey("search_id")
            || !values.TryGetValue("destination", out var destinationElement)
            || destinationElement.ValueKind != JsonValueKind.String)
        {
            throw NotUnderstood();
        }

        var destination = destinationElement.GetString()!.Trim();
        if (destination.Length is < 1 or > 100
            || !question.Contains(destination, StringComparison.OrdinalIgnoreCase))
        {
            throw NotUnderstood();
        }

        arguments["destination"] = destination;
        if (values.TryGetValue("guests", out var guestsElement))
        {
            arguments["guests"] = TryInteger(guestsElement, 1, 20, out var guests) ? guests : throw NotUnderstood();
        }

        if (values.TryGetValue("max_nightly_price", out var priceElement))
        {
            arguments["max_nightly_price"] =
                priceElement.ValueKind == JsonValueKind.Number
                && priceElement.TryGetDecimal(out var price)
                && price is > 0 and <= 100000
                    ? price
                    : throw NotUnderstood();
        }

        return new LookupCall(AssistantTools.Find, arguments);
    }

    private static bool TryInteger(JsonElement element, int minimum, int maximum, out int value)
    {
        value = 0;
        return element.ValueKind == JsonValueKind.Number
            && element.TryGetInt32(out value)
            && value >= minimum
            && value <= maximum;
    }

    private static AssistantException NotUnderstood()
    {
        return new AssistantException(AssistantFailure.NotUnderstood, Dependency);
    }

    private sealed record GenerateRequest(
        string Model,
        string System,
        string Prompt,
        bool Stream,
        JsonElement Format,
        GenerateOptions Options,
        [property: JsonPropertyName("keep_alive")] string KeepAlive);

    private sealed record GenerateOptions(
        double Temperature,
        [property: JsonPropertyName("num_predict")] int NumPredict);

    private sealed record GenerateResponse(string? Response, bool? Done);
}

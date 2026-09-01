using System.Net.Http.Json;
using System.Text.Json;
using System.Text.Json.Serialization;
using Accommodation.Backend.Api;

namespace Accommodation.Backend.Clients;

public interface IOllamaRankingClient
{
    Task<IReadOnlyList<SearchResult>> RankAsync(
        ValidatedSearch search,
        IReadOnlyList<AccommodationCandidate> candidates,
        CancellationToken cancellationToken);
}

public sealed record OllamaRankingSettings(string Model, string Prompt);

public sealed class OllamaRankingClient(
    HttpClient client,
    OllamaRankingSettings settings) : IOllamaRankingClient
{
    private static readonly JsonSerializerOptions JsonOptions =
        new(JsonSerializerDefaults.Web);

    public async Task<IReadOnlyList<SearchResult>> RankAsync(
        ValidatedSearch search,
        IReadOnlyList<AccommodationCandidate> candidates,
        CancellationToken cancellationToken)
    {
        var input = new RankingInput(
            new RankingCriteria(
                search.Destination,
                search.CheckIn,
                search.CheckOut,
                search.Guests,
                search.MinimumPrice,
                search.MaximumPrice,
                search.Preferences),
            ["id", "name", "destination", "description", "nightlyPrice", "maxGuests", "amenities"],
            candidates.Select(candidate => new object?[]
            {
                candidate.Id,
                candidate.Name,
                candidate.Destination,
                candidate.Description,
                candidate.NightlyPrice,
                candidate.MaxGuests,
                candidate.Amenities
            }).ToArray());
        var prompt = string.Concat(
            settings.Prompt,
            "\n",
            JsonSerializer.Serialize(input, JsonOptions));

        HttpResponseMessage response;
        try
        {
            response = await client.PostAsJsonAsync(
                "/api/generate",
                new GenerateRequest(
                    settings.Model,
                    prompt,
                    false,
                    CreateRankingFormat(candidates),
                    new GenerateOptions(0, 700),
                    "30m"),
                JsonOptions,
                cancellationToken);
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
            if (!response.IsSuccessStatusCode)
            {
                throw new OllamaUnavailableException("http_status");
            }

            GenerateResponse? generated;
            try
            {
                generated = await response.Content.ReadFromJsonAsync<GenerateResponse>(
                    JsonOptions,
                    cancellationToken);
            }
            catch (JsonException exception)
            {
                throw new OllamaResponseException(exception);
            }

            if (generated is null
                || generated.Done != true
                || string.IsNullOrWhiteSpace(generated.Response))
            {
                throw new OllamaResponseException();
            }

            return ValidateRanking(generated.Response, candidates);
        }
    }

    private static JsonElement CreateRankingFormat(
        IReadOnlyList<AccommodationCandidate> candidates)
    {
        return JsonSerializer.SerializeToElement(new
        {
            type = "array",
            minItems = candidates.Count,
            maxItems = candidates.Count,
            uniqueItems = true,
            items = new
            {
                type = "object",
                properties = new
                {
                    accommodationId = new
                    {
                        type = "integer",
                        @enum = candidates.Select(candidate => candidate.Id).ToArray()
                    },
                    rank = new
                    {
                        type = "integer",
                        minimum = 1,
                        maximum = candidates.Count
                    },
                    reason = new
                    {
                        type = "string",
                        minLength = 1,
                        maxLength = 160,
                        pattern = "^[A-Z][^\\r\\n]{0,158}\\.$"
                    }
                },
                required = new[] { "accommodationId", "rank", "reason" },
                additionalProperties = false
            }
        }, JsonOptions);
    }

    private static IReadOnlyList<SearchResult> ValidateRanking(
        string content,
        IReadOnlyList<AccommodationCandidate> candidates)
    {
        RankingEntry?[] entries;
        try
        {
            entries = JsonSerializer.Deserialize<RankingEntry?[]>(content, JsonOptions)
                ?? throw new OllamaResponseException();
        }
        catch (JsonException exception)
        {
            throw new OllamaResponseException(exception);
        }

        if (entries.Length != candidates.Count)
        {
            throw new OllamaResponseException();
        }

        var candidatesById = candidates.ToDictionary(candidate => candidate.Id);
        var candidateIds = candidatesById.Keys.ToHashSet();
        var entryIds = new HashSet<int>();
        var ranks = new HashSet<int>();
        var reasons = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

        foreach (var entry in entries)
        {
            var wordCount = entry?.Reason?.Split(
                ' ',
                StringSplitOptions.RemoveEmptyEntries).Length ?? 0;

            if (entry is null
                || !candidateIds.Contains(entry.AccommodationId)
                || !entryIds.Add(entry.AccommodationId)
                || entry.Rank < 1
                || entry.Rank > candidates.Count
                || !ranks.Add(entry.Rank)
                || string.IsNullOrWhiteSpace(entry.Reason)
                || entry.Reason != entry.Reason.Trim()
                || !char.IsUpper(entry.Reason[0])
                || !entry.Reason.EndsWith('.')
                || wordCount < 8
                || wordCount > 18
                || entry.Reason.Length > 160
                || !reasons.Add(entry.Reason))
            {
                throw new OllamaResponseException();
            }
        }

        if (!entryIds.SetEquals(candidateIds)
            || !ranks.SetEquals(Enumerable.Range(1, candidates.Count)))
        {
            throw new OllamaResponseException();
        }

        return entries
            .OrderBy(entry => entry!.Rank)
            .Select(entry =>
            {
                var candidate = candidatesById[entry!.AccommodationId];
                return new SearchResult(
                    candidate.Id,
                    candidate.Name,
                    candidate.Destination,
                    candidate.NightlyPrice,
                    candidate.MaxGuests,
                    entry.Rank,
                    entry.Reason!);
            })
            .ToArray();
    }

    private sealed record GenerateRequest(
        string Model,
        string Prompt,
        bool Stream,
        JsonElement Format,
        GenerateOptions Options,
        [property: JsonPropertyName("keep_alive")] string KeepAlive);

    private sealed record GenerateOptions(
        double Temperature,
        [property: JsonPropertyName("num_predict")] int NumPredict);

    private sealed record GenerateResponse(string? Response, bool? Done);

    private sealed record RankingInput(
        RankingCriteria Criteria,
        IReadOnlyList<string> CandidateFields,
        IReadOnlyList<object?[]> Candidates);

    private sealed record RankingCriteria(
        string Destination,
        DateOnly CheckIn,
        DateOnly CheckOut,
        int Guests,
        decimal MinimumPrice,
        decimal MaximumPrice,
        string Preferences);

    [JsonUnmappedMemberHandling(JsonUnmappedMemberHandling.Disallow)]
    private sealed record RankingEntry(
        int AccommodationId,
        int Rank,
        string? Reason);
}

public abstract class OllamaRankingException(
    string message,
    string failureCategory,
    Exception? innerException = null) : Exception(message, innerException)
{
    public string FailureCategory { get; } = failureCategory;
}

public sealed class OllamaUnavailableException(
    string failureCategory,
    Exception? innerException = null)
    : OllamaRankingException(
        "Ollama is unavailable.",
        $"ollama_{failureCategory}",
        innerException);

public sealed class OllamaResponseException(Exception? innerException = null)
    : OllamaRankingException(
        "Ollama returned an unusable ranking.",
        "ollama_response",
        innerException);

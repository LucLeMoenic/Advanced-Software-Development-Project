using System.Text.Json;
using System.Text.Json.Serialization;

namespace Accommodation.Backend.Api;

public static class LookupResultValidator
{
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
        UnmappedMemberHandling = JsonUnmappedMemberHandling.Disallow
    };

    private static readonly HashSet<string> RankingModes = ["programmatic", "ai", "fallback"];

    public static object Validate(LookupCall call, JsonElement body)
    {
        try
        {
            object? validated = call.Tool switch
            {
                AssistantTools.Find => ValidFind(body.Deserialize<FindResult>(JsonOptions), call.Arguments),
                AssistantTools.GetSearch => ValidSearch(body.Deserialize<SearchResult>(JsonOptions), (int)call.Arguments["search_id"]),
                _ => null
            };
            return validated ?? throw Invalid();
        }
        catch (JsonException exception)
        {
            throw Invalid(exception);
        }
    }

    private static FindResult? ValidFind(FindResult? result, IReadOnlyDictionary<string, object> arguments)
    {
        var destination = (string)arguments["destination"];
        var guests = arguments.TryGetValue("guests", out var g) ? (int)g : 1;
        var maximum = arguments.TryGetValue("max_nightly_price", out var p) ? (decimal)p : 100000m;
        return result is { Ok: true, Accommodations: not null }
            && result.Count == result.Accommodations.Count
            && result.Count <= 20
            && result.Accommodations.Select(item => item.Id).Distinct().Count() == result.Count
            && result.Accommodations.All(item =>
                item is { Amenities: not null }
                && item.Id > 0
                && Text(item.Name, 120)
                && string.Equals(item.Destination, destination, StringComparison.OrdinalIgnoreCase)
                && item.NightlyPrice is >= 0 && item.NightlyPrice <= maximum
                && item.MaxGuests >= guests && item.MaxGuests <= 20
                && item.Amenities.Count <= 30
                && item.Amenities.All(amenity => Text(amenity, 100)))
                ? result
                : null;
    }

    private static SearchResult? ValidSearch(SearchResult? result, int searchId)
    {
        // System.Text.Json "required" checks presence, not non-null, so nested values are guarded here.
        if (result is not { Ok: true, Search: { Criteria: not null, Results: not null } search }
            || search.Id != searchId)
        {
            return null;
        }

        var criteria = search.Criteria;
        return Text(search.Title, 80)
            && RankingModes.Contains(search.RankingMode)
            && Text(criteria.Destination, 100)
            && DateOnly.TryParseExact(criteria.CheckIn, "yyyy-MM-dd", out var checkIn)
            && DateOnly.TryParseExact(criteria.CheckOut, "yyyy-MM-dd", out var checkOut)
            && checkOut > checkIn
            && criteria.Guests is >= 1 and <= 20
            && criteria.MinimumPrice >= 0 && criteria.MinimumPrice <= criteria.MaximumPrice
            && criteria.MaximumPrice <= 100000
            && search.Results.Select(item => item.Rank).SequenceEqual(Enumerable.Range(1, search.Results.Count))
            && search.Results.All(item =>
                item is not null
                && item.AccommodationId > 0
                && Text(item.Name, 120)
                && item.NightlyPrice is >= 0 and <= 100000
                && Text(item.Reason, 200))
                ? result
                : null;
    }

    private static bool Text(string? value, int maximum)
    {
        return !string.IsNullOrWhiteSpace(value) && value.Length <= maximum;
    }

    private static AssistantException Invalid(Exception? inner = null)
    {
        return new AssistantException(AssistantFailure.InvalidResponse, "mcp", inner);
    }

    public sealed class FindResult
    {
        public required bool Ok { get; init; }
        public required int Count { get; init; }
        public required IReadOnlyList<CatalogueStay> Accommodations { get; init; }
    }

    public sealed class CatalogueStay
    {
        public required int Id { get; init; }
        public required string Name { get; init; }
        public required string Destination { get; init; }
        public required decimal NightlyPrice { get; init; }
        public required int MaxGuests { get; init; }
        public required IReadOnlyList<string> Amenities { get; init; }
    }

    public sealed class SearchResult
    {
        public required bool Ok { get; init; }
        public required SavedSearch Search { get; init; }
    }

    public sealed class SavedSearch
    {
        public required int Id { get; init; }
        public required string Title { get; init; }
        public required SearchCriteria Criteria { get; init; }
        public required string RankingMode { get; init; }
        public required IReadOnlyList<RankedStay> Results { get; init; }
    }

    public sealed class SearchCriteria
    {
        public required string Destination { get; init; }
        public required string CheckIn { get; init; }
        public required string CheckOut { get; init; }
        public required int Guests { get; init; }
        public required decimal MinimumPrice { get; init; }
        public required decimal MaximumPrice { get; init; }
    }

    public sealed class RankedStay
    {
        public required int Rank { get; init; }
        public required int AccommodationId { get; init; }
        public required string Name { get; init; }
        public required decimal NightlyPrice { get; init; }
        public required string Reason { get; init; }
    }
}

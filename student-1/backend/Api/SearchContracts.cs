namespace Accommodation.Backend.Api;

public sealed record SearchRequest(
    string? Destination,
    DateOnly? CheckIn,
    DateOnly? CheckOut,
    int? Guests,
    decimal? MinimumPrice,
    decimal? MaximumPrice,
    string? Preferences,
    bool? UseAi);

public sealed record SearchRenameRequest(string? Title);

public sealed record AccommodationCandidate(
    int Id,
    string Name,
    string Destination,
    string Description,
    decimal NightlyPrice,
    int MaxGuests,
    IReadOnlyList<string> Amenities,
    string? ImageUrl,
    string? BookingUrl);

public sealed record SearchResult(
    int AccommodationId,
    string Name,
    string Destination,
    decimal NightlyPrice,
    int MaxGuests,
    int Rank,
    string Reason);

public sealed record SearchSummaryResponse(
    int Id,
    string Title,
    string Destination,
    DateOnly CheckIn,
    DateOnly CheckOut,
    int Guests,
    string RankingMode,
    DateTime CreatedAt,
    DateTime UpdatedAt);

public sealed record SearchResponse(
    int Id,
    string Title,
    string Destination,
    DateOnly CheckIn,
    DateOnly CheckOut,
    int Guests,
    decimal MinimumPrice,
    decimal MaximumPrice,
    string Preferences,
    string RankingMode,
    IReadOnlyList<SearchResult> Results,
    DateTime CreatedAt,
    DateTime UpdatedAt,
    string? Notice = null,
    bool ImportedProviderData = false);

public sealed record PersistSearchRequest(
    string Title,
    string Destination,
    DateOnly CheckIn,
    DateOnly CheckOut,
    int Guests,
    decimal MinimumPrice,
    decimal MaximumPrice,
    string Preferences,
    string RankingMode,
    IReadOnlyList<SearchResult> Results);

public sealed record CandidateQuery(
    string Destination,
    int Guests,
    decimal MinimumPrice,
    decimal MaximumPrice);

public sealed record AccommodationImportRequest(
    string Name,
    string Destination,
    string Description,
    decimal NightlyPrice,
    int MaxGuests,
    IReadOnlyList<string> Amenities,
    string? ImageUrl,
    string? BookingUrl,
    bool IsActive);

public sealed record ApiError(
    string Code,
    string Message,
    IReadOnlyDictionary<string, string> Fields,
    string CorrelationId);

public sealed record ApiErrorEnvelope(ApiError Error);

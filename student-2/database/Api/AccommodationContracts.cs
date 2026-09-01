namespace Accommodation.Database.Api;

public sealed record AccommodationRequest(
    string? Name,
    string? Destination,
    string? Description,
    decimal? NightlyPrice,
    int? MaxGuests,
    IReadOnlyList<string>? Amenities,
    string? ImageUrl,
    string? BookingUrl,
    bool? IsActive);

public sealed record AccommodationResponse(
    int Id,
    string Name,
    string Destination,
    string Description,
    decimal NightlyPrice,
    int MaxGuests,
    IReadOnlyList<string> Amenities,
    string? ImageUrl,
    string? BookingUrl,
    bool IsActive,
    DateTime CreatedAt,
    DateTime UpdatedAt);

public sealed record ApiError(
    string Code,
    string Message,
    IReadOnlyDictionary<string, string> Fields,
    string CorrelationId);

public sealed record ApiErrorEnvelope(ApiError Error);

using System.Text.Json;

namespace Accommodation.Database.Api;

public sealed record SearchCreateRequest(
    string? Title,
    string? Destination,
    DateOnly? CheckIn,
    DateOnly? CheckOut,
    int? Guests,
    decimal? MinimumPrice,
    decimal? MaximumPrice,
    string? Preferences,
    string? RankingMode,
    JsonElement Results);

public sealed record SearchRenameRequest(string? Title);

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
    JsonElement Results,
    DateTime CreatedAt,
    DateTime UpdatedAt);

using System.Globalization;
using System.Net;
using System.Net.Http.Json;
using System.Text.Json;
using Accommodation.Backend.Api;

namespace Accommodation.Backend.Clients;

public interface IDatabaseApiClient
{
    Task<IReadOnlyList<AccommodationCandidate>> ListCandidatesAsync(
        CandidateQuery query,
        CancellationToken cancellationToken);

    Task ImportAccommodationAsync(
        AccommodationImportRequest request,
        CancellationToken cancellationToken);

    Task<SearchResponse> CreateSearchAsync(
        PersistSearchRequest request,
        CancellationToken cancellationToken);

    Task<IReadOnlyList<SearchSummaryResponse>> ListSearchesAsync(
        CancellationToken cancellationToken);

    Task<SearchResponse> GetSearchAsync(int id, CancellationToken cancellationToken);

    Task<SearchResponse> RenameSearchAsync(
        int id,
        SearchRenameRequest request,
        CancellationToken cancellationToken);

    Task DeleteSearchAsync(int id, CancellationToken cancellationToken);
}

public sealed class DatabaseApiClient(HttpClient client) : IDatabaseApiClient
{
    private static readonly JsonSerializerOptions JsonOptions =
        new(JsonSerializerDefaults.Web);

    public async Task<IReadOnlyList<AccommodationCandidate>> ListCandidatesAsync(
        CandidateQuery query,
        CancellationToken cancellationToken)
    {
        var path = string.Create(
            CultureInfo.InvariantCulture,
            $"/api/data/accommodations?destination={Uri.EscapeDataString(query.Destination)}&minPrice={query.MinimumPrice}&maxPrice={query.MaximumPrice}&guests={query.Guests}&active=true");

        var values = await SendForJsonAsync<AccommodationDataResponse?[]>(
            new HttpRequestMessage(HttpMethod.Get, path),
            HttpStatusCode.OK,
            notFoundIsRecordMissing: false,
            cancellationToken);

        return values.Select(value => ToCandidate(value, query)).ToArray();
    }

    public async Task ImportAccommodationAsync(
        AccommodationImportRequest request,
        CancellationToken cancellationToken)
    {
        using var message = new HttpRequestMessage(
            HttpMethod.Post,
            "/api/data/accommodations")
        {
            Content = JsonContent.Create(request, options: JsonOptions)
        };

        HttpResponseMessage response;
        try
        {
            response = await client.SendAsync(message, cancellationToken);
        }
        catch (TaskCanceledException exception) when (!cancellationToken.IsCancellationRequested)
        {
            throw new DatabaseUnavailableException(exception);
        }
        catch (HttpRequestException exception)
        {
            throw new DatabaseUnavailableException(exception);
        }

        using (response)
        {
            if (response.StatusCode is not HttpStatusCode.Created
                and not HttpStatusCode.Conflict)
            {
                throw new DatabaseResponseException();
            }
        }
    }

    public async Task<SearchResponse> CreateSearchAsync(
        PersistSearchRequest request,
        CancellationToken cancellationToken)
    {
        var value = await SendForJsonAsync<SearchDataResponse>(
            new HttpRequestMessage(HttpMethod.Post, "/api/data/searches")
            {
                Content = JsonContent.Create(request, options: JsonOptions)
            },
            HttpStatusCode.Created,
            notFoundIsRecordMissing: false,
            cancellationToken);

        return ToSearch(value);
    }

    public async Task<IReadOnlyList<SearchSummaryResponse>> ListSearchesAsync(
        CancellationToken cancellationToken)
    {
        var values = await SendForJsonAsync<SearchSummaryDataResponse?[]>(
            new HttpRequestMessage(HttpMethod.Get, "/api/data/searches"),
            HttpStatusCode.OK,
            notFoundIsRecordMissing: false,
            cancellationToken);

        return values
            .Select(ToSummary)
            .OrderByDescending(search => search.CreatedAt)
            .ThenByDescending(search => search.Id)
            .ToArray();
    }

    public async Task<SearchResponse> GetSearchAsync(
        int id,
        CancellationToken cancellationToken)
    {
        var value = await SendForJsonAsync<SearchDataResponse>(
            new HttpRequestMessage(HttpMethod.Get, $"/api/data/searches/{id}"),
            HttpStatusCode.OK,
            notFoundIsRecordMissing: true,
            cancellationToken);

        return ToSearch(value);
    }

    public async Task<SearchResponse> RenameSearchAsync(
        int id,
        SearchRenameRequest request,
        CancellationToken cancellationToken)
    {
        var value = await SendForJsonAsync<SearchDataResponse>(
            new HttpRequestMessage(HttpMethod.Patch, $"/api/data/searches/{id}")
            {
                Content = JsonContent.Create(request, options: JsonOptions)
            },
            HttpStatusCode.OK,
            notFoundIsRecordMissing: true,
            cancellationToken);

        return ToSearch(value);
    }

    public Task DeleteSearchAsync(int id, CancellationToken cancellationToken)
    {
        return SendAsync(
            new HttpRequestMessage(HttpMethod.Delete, $"/api/data/searches/{id}"),
            HttpStatusCode.NoContent,
            notFoundIsRecordMissing: true,
            cancellationToken);
    }

    private async Task<T> SendForJsonAsync<T>(
        HttpRequestMessage request,
        HttpStatusCode expectedStatus,
        bool notFoundIsRecordMissing,
        CancellationToken cancellationToken)
    {
        using var response = await SendCoreAsync(
            request,
            expectedStatus,
            notFoundIsRecordMissing,
            cancellationToken);

        try
        {
            return await response.Content.ReadFromJsonAsync<T>(
                    JsonOptions,
                    cancellationToken)
                ?? throw new DatabaseResponseException();
        }
        catch (JsonException exception)
        {
            throw new DatabaseResponseException(exception);
        }
    }

    private async Task SendAsync(
        HttpRequestMessage request,
        HttpStatusCode expectedStatus,
        bool notFoundIsRecordMissing,
        CancellationToken cancellationToken)
    {
        using var response = await SendCoreAsync(
            request,
            expectedStatus,
            notFoundIsRecordMissing,
            cancellationToken);
    }

    private async Task<HttpResponseMessage> SendCoreAsync(
        HttpRequestMessage request,
        HttpStatusCode expectedStatus,
        bool notFoundIsRecordMissing,
        CancellationToken cancellationToken)
    {
        HttpResponseMessage response;
        try
        {
            response = await client.SendAsync(request, cancellationToken);
        }
        catch (TaskCanceledException exception) when (!cancellationToken.IsCancellationRequested)
        {
            throw new DatabaseUnavailableException(exception);
        }
        catch (HttpRequestException exception)
        {
            throw new DatabaseUnavailableException(exception);
        }

        if (response.StatusCode == HttpStatusCode.NotFound && notFoundIsRecordMissing)
        {
            response.Dispose();
            throw new DatabaseRecordNotFoundException();
        }

        if (response.StatusCode != expectedStatus)
        {
            response.Dispose();
            throw new DatabaseResponseException();
        }

        return response;
    }

    private static AccommodationCandidate ToCandidate(
        AccommodationDataResponse? value,
        CandidateQuery query)
    {
        if (value is null
            || value.Id is null or <= 0
            || !RequiredText(value.Name, 1, 120)
            || !RequiredText(value.Destination, 2, 100)
            || !RequiredText(value.Description, 1, 1000)
            || value.NightlyPrice is null or < 0 or > 100000
            || value.MaxGuests is null or < 1 or > 20
            || !ValidAmenities(value.Amenities)
            || value.IsActive != true
            || !string.Equals(
                value.Destination,
                query.Destination,
                StringComparison.OrdinalIgnoreCase)
            || value.NightlyPrice < query.MinimumPrice
            || value.NightlyPrice > query.MaximumPrice
            || value.MaxGuests < query.Guests
            || !OptionalUrl(value.ImageUrl)
            || !OptionalUrl(value.BookingUrl))
        {
            throw new DatabaseResponseException();
        }

        return new(
            value.Id.Value,
            value.Name!,
            value.Destination!,
            value.Description!,
            value.NightlyPrice.Value,
            value.MaxGuests.Value,
            value.Amenities!,
            value.ImageUrl,
            value.BookingUrl);
    }

    private static SearchSummaryResponse ToSummary(SearchSummaryDataResponse? value)
    {
        if (value is null
            || value.Id is null or <= 0
            || !RequiredText(value.Title, 1, 80)
            || !RequiredText(value.Destination, 2, 100)
            || value.CheckIn is null
            || value.CheckOut is null
            || value.CheckOut <= value.CheckIn
            || value.Guests is null or < 1 or > 20
            || !RankingMode(value.RankingMode)
            || value.CreatedAt is null
            || value.UpdatedAt is null)
        {
            throw new DatabaseResponseException();
        }

        return new(
            value.Id.Value,
            value.Title!,
            value.Destination!,
            value.CheckIn.Value,
            value.CheckOut.Value,
            value.Guests.Value,
            value.RankingMode!,
            value.CreatedAt.Value,
            value.UpdatedAt.Value);
    }

    private static SearchResponse ToSearch(SearchDataResponse value)
    {
        if (value.Id is null or <= 0
            || !RequiredText(value.Title, 1, 80)
            || !RequiredText(value.Destination, 2, 100)
            || value.CheckIn is null
            || value.CheckOut is null
            || value.CheckOut <= value.CheckIn
            || value.Guests is null or < 1 or > 20
            || value.MinimumPrice is null or < 0 or > 100000
            || value.MaximumPrice is null or < 0 or > 100000
            || value.MinimumPrice > value.MaximumPrice
            || value.Preferences is null
            || value.Preferences.Length > 500
            || !RankingMode(value.RankingMode)
            || value.Results.ValueKind != JsonValueKind.Array
            || value.CreatedAt is null
            || value.UpdatedAt is null)
        {
            throw new DatabaseResponseException();
        }

        SearchResultDataResponse?[] resultValues;
        try
        {
            resultValues = value.Results.Deserialize<SearchResultDataResponse?[]>(JsonOptions)
                ?? throw new DatabaseResponseException();
        }
        catch (JsonException exception)
        {
            throw new DatabaseResponseException(exception);
        }

        var results = resultValues.Select(ToResult).OrderBy(result => result.Rank).ToArray();
        if (results.Select(result => result.AccommodationId).Distinct().Count() != results.Length
            || results.Select(result => result.Rank).Distinct().Count() != results.Length
            || !results.Select(result => result.Rank).SequenceEqual(
                Enumerable.Range(1, results.Length)))
        {
            throw new DatabaseResponseException();
        }

        return new(
            value.Id.Value,
            value.Title!,
            value.Destination!,
            value.CheckIn.Value,
            value.CheckOut.Value,
            value.Guests.Value,
            value.MinimumPrice.Value,
            value.MaximumPrice.Value,
            value.Preferences,
            value.RankingMode!,
            results,
            value.CreatedAt.Value,
            value.UpdatedAt.Value);
    }

    private static SearchResult ToResult(SearchResultDataResponse? value)
    {
        if (value is null
            || value.AccommodationId is null or <= 0
            || !RequiredText(value.Name, 1, 120)
            || !RequiredText(value.Destination, 2, 100)
            || value.NightlyPrice is null or < 0 or > 100000
            || value.MaxGuests is null or < 1 or > 20
            || value.Rank is null or <= 0
            || !RequiredText(value.Reason, 1, 200))
        {
            throw new DatabaseResponseException();
        }

        return new(
            value.AccommodationId.Value,
            value.Name!,
            value.Destination!,
            value.NightlyPrice.Value,
            value.MaxGuests.Value,
            value.Rank.Value,
            value.Reason!);
    }

    private static bool RequiredText(string? value, int minimum, int maximum)
    {
        return value is not null
            && value == value.Trim()
            && value.Length >= minimum
            && value.Length <= maximum;
    }

    private static bool ValidAmenities(IReadOnlyList<string>? values)
    {
        return values is not null
            && values.Count <= 30
            && values.All(value =>
                !string.IsNullOrWhiteSpace(value)
                && value == value.Trim())
            && values.Distinct(StringComparer.OrdinalIgnoreCase).Count() == values.Count;
    }

    private static bool RankingMode(string? value)
    {
        return value is "ai" or "fallback";
    }

    private static bool OptionalUrl(string? value)
    {
        return value is null
            || value.Length <= 2048
            && Uri.TryCreate(value, UriKind.Absolute, out var uri)
            && (uri.Scheme == Uri.UriSchemeHttp || uri.Scheme == Uri.UriSchemeHttps);
    }

    private sealed record AccommodationDataResponse(
        int? Id,
        string? Name,
        string? Destination,
        string? Description,
        decimal? NightlyPrice,
        int? MaxGuests,
        IReadOnlyList<string>? Amenities,
        string? ImageUrl,
        string? BookingUrl,
        bool? IsActive);

    private sealed record SearchSummaryDataResponse(
        int? Id,
        string? Title,
        string? Destination,
        DateOnly? CheckIn,
        DateOnly? CheckOut,
        int? Guests,
        string? RankingMode,
        DateTime? CreatedAt,
        DateTime? UpdatedAt);

    private sealed record SearchDataResponse(
        int? Id,
        string? Title,
        string? Destination,
        DateOnly? CheckIn,
        DateOnly? CheckOut,
        int? Guests,
        decimal? MinimumPrice,
        decimal? MaximumPrice,
        string? Preferences,
        string? RankingMode,
        JsonElement Results,
        DateTime? CreatedAt,
        DateTime? UpdatedAt);

    private sealed record SearchResultDataResponse(
        int? AccommodationId,
        string? Name,
        string? Destination,
        decimal? NightlyPrice,
        int? MaxGuests,
        int? Rank,
        string? Reason);
}

public sealed class DatabaseUnavailableException : Exception
{
    public DatabaseUnavailableException(Exception? innerException = null)
        : base("The database API is unavailable.", innerException)
    {
    }
}

public sealed class DatabaseResponseException : Exception
{
    public DatabaseResponseException(Exception? innerException = null)
        : base("The database API returned an unusable response.", innerException)
    {
    }
}

public sealed class DatabaseRecordNotFoundException : Exception
{
    public DatabaseRecordNotFoundException()
        : base("The requested database record was not found.")
    {
    }
}

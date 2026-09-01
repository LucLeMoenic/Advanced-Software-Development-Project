using System.Net.Http.Json;
using System.Text.Json;
using System.Text.Json.Serialization;
using Accommodation.Backend.Api;

namespace Accommodation.Backend.Clients;

public interface ILiteApiClient
{
    Task<IReadOnlyList<AccommodationImportRequest>> SearchAsync(
        ValidatedSearch search,
        CancellationToken cancellationToken);
}

public sealed record LiteApiSettings(string ApiKey);

public sealed class LiteApiClient(
    HttpClient client,
    LiteApiSettings settings) : ILiteApiClient
{
    private static readonly JsonSerializerOptions JsonOptions =
        new(JsonSerializerDefaults.Web);

    public async Task<IReadOnlyList<AccommodationImportRequest>> SearchAsync(
        ValidatedSearch search,
        CancellationToken cancellationToken)
    {
        if (string.IsNullOrWhiteSpace(settings.ApiKey))
        {
            throw new LiteApiUnavailableException("configuration");
        }

        using var request = new HttpRequestMessage(
            HttpMethod.Post,
            "/v3.0/hotels/rates")
        {
            Content = JsonContent.Create(
                new RateRequest(
                    [new Occupancy(search.Guests)],
                    "AUD",
                    "AU",
                    search.CheckIn,
                    search.CheckOut,
                    search.Destination,

                    true,
                    10,
                    8,
                    1,
                    false),
                options: JsonOptions)
        };
        request.Headers.Add("X-API-Key", settings.ApiKey);

        HttpResponseMessage response;
        try
        {
            response = await client.SendAsync(request, cancellationToken);
        }
        catch (TaskCanceledException exception) when (!cancellationToken.IsCancellationRequested)
        {
            throw new LiteApiUnavailableException("timeout", exception);
        }
        catch (HttpRequestException exception)
        {
            throw new LiteApiUnavailableException("connection", exception);
        }

        using (response)
        {
            if (!response.IsSuccessStatusCode)
            {
                throw new LiteApiUnavailableException(
                    $"http_{(int)response.StatusCode}");
            }

            RateResponse? rates;
            try
            {
                rates = await response.Content.ReadFromJsonAsync<RateResponse>(
                    JsonOptions,
                    cancellationToken);
            }
            catch (JsonException exception)
            {
                throw new LiteApiResponseException(exception);
            }

            return ValidateAndMap(rates, search);
        }
    }

    private static IReadOnlyList<AccommodationImportRequest> ValidateAndMap(
        RateResponse? response,
        ValidatedSearch search)
    {
        if (response?.Data is null
            || response.Hotels is null
            || response.Data.Count > 10
            || response.Hotels.Count > 10)
        {
            throw new LiteApiResponseException();
        }

        var hotels = new Dictionary<string, HotelDetails>(StringComparer.Ordinal);
        foreach (var hotel in response.Hotels)
        {
            if (hotel is null
                || string.IsNullOrWhiteSpace(hotel.Id)
                || !hotels.TryAdd(hotel.Id, hotel))
            {
                throw new LiteApiResponseException();
            }
        }
        var hotelIds = new HashSet<string>(StringComparer.Ordinal);
        var nights = search.CheckOut.DayNumber - search.CheckIn.DayNumber;
        var imports = new List<AccommodationImportRequest>();

        foreach (var result in response.Data)
        {
            if (result is null
                || string.IsNullOrWhiteSpace(result.HotelId)
                || !hotelIds.Add(result.HotelId))
            {
                throw new LiteApiResponseException();
            }

            if (!hotels.TryGetValue(result.HotelId, out var hotel))
            {
                continue;
            }

            var import = ToImport(result, hotel, search, nights);
            if (import is not null)
            {
                imports.Add(import);
            }
        }

        if (response.Data.Count > 0 && imports.Count == 0)
        {
            throw new LiteApiResponseException();
        }

        return imports;
    }

    private static AccommodationImportRequest? ToImport(
        HotelRateResult result,
        HotelDetails hotel,
        ValidatedSearch search,
        int nights)
    {
        if (string.IsNullOrWhiteSpace(hotel.Id)
            || string.IsNullOrWhiteSpace(hotel.Name)
            || hotel.Name != hotel.Name.Trim()
            || hotel.Name.Length > 120
            || !OptionalUrl(hotel.MainPhoto))
        {
            return null;
        }

        var offer = result.RoomTypes?
            .Where(room => room?.OfferRetailRate is not null)
            .OrderBy(room => room!.OfferRetailRate!.Amount)
            .FirstOrDefault();
        var offerPrice = offer?.OfferRetailRate;
        var totalAmount = offerPrice?.Amount;
        var currency = offerPrice?.Currency;
        var maxGuests = offer?.Rates?
            .Select(rate => rate?.MaxOccupancy)
            .Where(value => value is not null)
            .Select(value => value!.Value)
            .DefaultIfEmpty()
            .Max();

        if (totalAmount is null or <= 0 or > 1000000
            || !string.Equals(currency, "AUD", StringComparison.OrdinalIgnoreCase)
            || maxGuests is null or < 1 or > 20
            || maxGuests < search.Guests)
        {
            return null;
        }

        var nightlyPrice = decimal.Round(
            totalAmount.Value / nights,
            2,
            MidpointRounding.AwayFromZero);
        if (nightlyPrice is <= 0 or > 100000)
        {
            return null;
        }

        var address = hotel.Address?.Trim();
        var description = string.IsNullOrEmpty(address) || address.Length > 900
            ? "LiteAPI accommodation rate."
            : $"LiteAPI accommodation rate for {address}.";

        return new(
            hotel.Name,
            search.Destination,
            description,
            nightlyPrice,
            maxGuests.Value,
            [],
            hotel.MainPhoto,
            null,
            true);
    }

    private static bool OptionalUrl(string? value)
    {
        return value is null
            || value.Length <= 2048
            && Uri.TryCreate(value, UriKind.Absolute, out var uri)
            && (uri.Scheme == Uri.UriSchemeHttp || uri.Scheme == Uri.UriSchemeHttps);
    }

    private sealed record RateRequest(
        IReadOnlyList<Occupancy> Occupancies,
        string Currency,
        string GuestNationality,
        DateOnly Checkin,
        DateOnly Checkout,
        string AiSearch,
        bool IncludeHotelData,
        int Limit,
        int Timeout,
        int MaxRatesPerHotel,
        bool Stream);

    private sealed record Occupancy(int Adults);

    private sealed record RateResponse(
        IReadOnlyList<HotelRateResult?>? Data,
        IReadOnlyList<HotelDetails?>? Hotels);

    private sealed record HotelRateResult(
        string? HotelId,
        IReadOnlyList<RoomType?>? RoomTypes);

    private sealed record RoomType(
        IReadOnlyList<RoomRate?>? Rates,
        Money? OfferRetailRate);

    private sealed record RoomRate(int? MaxOccupancy);

    private sealed record Money(decimal? Amount, string? Currency);

    private sealed record HotelDetails(
        string? Id,
        string? Name,
        [property: JsonPropertyName("main_photo")] string? MainPhoto,
        string? Address);
}

public abstract class LiteApiException(
    string message,
    string failureCategory,
    Exception? innerException = null) : Exception(message, innerException)
{
    public string FailureCategory { get; } = failureCategory;
}

public sealed class LiteApiUnavailableException(
    string failureCategory,
    Exception? innerException = null)
    : LiteApiException(
        "LiteAPI is unavailable.",
        $"liteapi_{failureCategory}",
        innerException);

public sealed class LiteApiResponseException(Exception? innerException = null)
    : LiteApiException(
        "LiteAPI returned an unusable response.",
        "liteapi_response",
        innerException);

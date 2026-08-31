using System.Globalization;
using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using Accommodation.Database.Data;
using AccommodationEntity = Accommodation.Database.Data.Accommodation;

namespace Accommodation.Database.Api;

public static class AccommodationEndpoints
{
    private const string Route = "/api/data/accommodations";

    public static IEndpointRouteBuilder MapAccommodationEndpoints(
        this IEndpointRouteBuilder endpoints)
    {
        var group = endpoints.MapGroup(Route);
        group.MapGet("/", ListAsync);
        group.MapPost("/", CreateAsync);
        group.MapGet("/{id:int}", GetAsync);
        group.MapPut("/{id:int}", ReplaceAsync);
        group.MapDelete("/{id:int}", DeleteAsync);
        return endpoints;
    }

    private static async Task<IResult> ListAsync(
        HttpContext context,
        AccommodationDbContext database)
    {
        var queryResult = ParseFilters(context);
        if (queryResult.Error is not null)
        {
            return queryResult.Error;
        }

        var filters = queryResult.Filters!;
        var query = database.Accommodations.AsNoTracking();

        if (filters.Destination is not null)
        {
            query = query.Where(item =>
                EF.Functions.Collate(item.Destination, "NOCASE") == filters.Destination);
        }

        if (filters.MinimumPrice is not null)
        {
            query = query.Where(item => item.NightlyPrice >= filters.MinimumPrice);
        }

        if (filters.MaximumPrice is not null)
        {
            query = query.Where(item => item.NightlyPrice <= filters.MaximumPrice);
        }

        if (filters.Guests is not null)
        {
            query = query.Where(item => item.MaxGuests >= filters.Guests);
        }

        if (filters.IsActive is not null)
        {
            query = query.Where(item => item.IsActive == filters.IsActive);
        }

        var accommodations = await query
            .OrderBy(item => item.Id)
            .ToListAsync();

        return Results.Ok(accommodations.Select(ToResponse));
    }

    private static async Task<IResult> CreateAsync(
        HttpContext context,
        AccommodationDbContext database)
    {
        var readResult = await ReadRequestAsync(context);
        if (readResult.Error is not null)
        {
            return readResult.Error;
        }

        var validation = Validate(readResult.Request!);
        if (validation.Error is not null)
        {
            return ValidationError(context, validation.Error);
        }

        var value = validation.Value!;
        if (await DuplicateExistsAsync(database, value.Name, value.Destination))
        {
            return Conflict(context);
        }

        var now = DateTime.UtcNow;
        var accommodation = new AccommodationEntity
        {
            Name = value.Name,
            Destination = value.Destination,
            Description = value.Description,
            NightlyPrice = value.NightlyPrice,
            MaxGuests = value.MaxGuests,
            AmenitiesJson = JsonSerializer.Serialize(value.Amenities),
            ImageUrl = value.ImageUrl,
            BookingUrl = value.BookingUrl,
            IsActive = value.IsActive,
            CreatedAt = now,
            UpdatedAt = now
        };

        database.Accommodations.Add(accommodation);
        var saveError = await SaveAsync(context, database);
        if (saveError is not null)
        {
            return saveError;
        }

        return Results.Created($"{Route}/{accommodation.Id}", ToResponse(accommodation));
    }

    private static async Task<IResult> GetAsync(
        int id,
        HttpContext context,
        AccommodationDbContext database)
    {
        var accommodation = await database.Accommodations
            .AsNoTracking()
            .SingleOrDefaultAsync(item => item.Id == id);

        return accommodation is null
            ? NotFound(context)
            : Results.Ok(ToResponse(accommodation));
    }

    private static async Task<IResult> ReplaceAsync(
        int id,
        HttpContext context,
        AccommodationDbContext database)
    {
        var accommodation = await database.Accommodations
            .SingleOrDefaultAsync(item => item.Id == id);
        if (accommodation is null)
        {
            return NotFound(context);
        }

        var readResult = await ReadRequestAsync(context);
        if (readResult.Error is not null)
        {
            return readResult.Error;
        }

        var validation = Validate(readResult.Request!);
        if (validation.Error is not null)
        {
            return ValidationError(context, validation.Error);
        }

        var value = validation.Value!;
        if (await DuplicateExistsAsync(database, value.Name, value.Destination, id))
        {
            return Conflict(context);
        }

        accommodation.Name = value.Name;
        accommodation.Destination = value.Destination;
        accommodation.Description = value.Description;
        accommodation.NightlyPrice = value.NightlyPrice;
        accommodation.MaxGuests = value.MaxGuests;
        accommodation.AmenitiesJson = JsonSerializer.Serialize(value.Amenities);
        accommodation.ImageUrl = value.ImageUrl;
        accommodation.BookingUrl = value.BookingUrl;
        accommodation.IsActive = value.IsActive;
        accommodation.UpdatedAt = DateTime.UtcNow;

        var saveError = await SaveAsync(context, database);
        return saveError ?? Results.Ok(ToResponse(accommodation));
    }

    private static async Task<IResult> DeleteAsync(
        int id,
        HttpContext context,
        AccommodationDbContext database)
    {
        var accommodation = await database.Accommodations
            .SingleOrDefaultAsync(item => item.Id == id);
        if (accommodation is null)
        {
            return NotFound(context);
        }

        database.Accommodations.Remove(accommodation);
        await database.SaveChangesAsync();
        return Results.NoContent();
    }

    private static async Task<RequestReadResult> ReadRequestAsync(HttpContext context)
    {
        try
        {
            var request = await context.Request.ReadFromJsonAsync<AccommodationRequest>();
            return request is null
                ? new(null, ValidationError(context, new Dictionary<string, string>
                {
                    ["body"] = "A JSON request body is required."
                }))
                : new(request, null);
        }
        catch (JsonException)
        {
            return new(null, ValidationError(context, new Dictionary<string, string>
            {
                ["body"] = "The request body must be valid JSON."
            }));
        }
    }

    private static ValidationResult Validate(AccommodationRequest request)
    {
        var fields = new Dictionary<string, string>();
        var name = RequiredText(request.Name, 1, 120, "name", fields);
        var destination = RequiredText(request.Destination, 2, 100, "destination", fields);
        var description = RequiredText(request.Description, 1, 1000, "description", fields);

        if (request.NightlyPrice is null or < 0 or > 100000)
        {
            fields["nightlyPrice"] = "Must be between 0 and 100000.";
        }

        if (request.MaxGuests is null or < 1 or > 20)
        {
            fields["maxGuests"] = "Must be between 1 and 20.";
        }

        var amenities = NormalizeAmenities(request.Amenities, fields);
        var imageUrl = OptionalUrl(request.ImageUrl, "imageUrl", fields);
        var bookingUrl = OptionalUrl(request.BookingUrl, "bookingUrl", fields);

        if (fields.Count > 0)
        {
            return new(null, fields);
        }

        return new(
            new ValidAccommodation(
                name!,
                destination!,
                description!,
                decimal.Round(request.NightlyPrice!.Value, 2),
                request.MaxGuests!.Value,
                amenities!,
                imageUrl,
                bookingUrl,
                request.IsActive ?? true),
            null);
    }

    private static string? RequiredText(
        string? value,
        int minimumLength,
        int maximumLength,
        string field,
        IDictionary<string, string> errors)
    {
        var trimmed = value?.Trim();
        if (trimmed is null || trimmed.Length < minimumLength || trimmed.Length > maximumLength)
        {
            errors[field] = $"Must be between {minimumLength} and {maximumLength} characters.";
            return null;
        }

        return trimmed;
    }

    private static string[]? NormalizeAmenities(
        IReadOnlyList<string>? values,
        IDictionary<string, string> errors)
    {
        if (values is null || values.Count > 30)
        {
            errors["amenities"] = "Must contain between 0 and 30 unique non-empty values.";
            return null;
        }

        var normalized = values.Select(value => value?.Trim()).ToArray();
        if (normalized.Any(string.IsNullOrEmpty)
            || normalized.Distinct(StringComparer.OrdinalIgnoreCase).Count() != normalized.Length)
        {
            errors["amenities"] = "Values must be non-empty and unique.";
            return null;
        }

        return normalized!;
    }

    private static string? OptionalUrl(
        string? value,
        string field,
        IDictionary<string, string> errors)
    {
        var trimmed = value?.Trim();
        if (string.IsNullOrEmpty(trimmed))
        {
            return null;
        }

        if (trimmed.Length > 2048
            || !Uri.TryCreate(trimmed, UriKind.Absolute, out var uri)
            || (uri.Scheme != Uri.UriSchemeHttp && uri.Scheme != Uri.UriSchemeHttps))
        {
            errors[field] = "Must be an HTTP or HTTPS URL with at most 2048 characters.";
            return null;
        }

        return trimmed;
    }

    private static QueryResult ParseFilters(HttpContext context)
    {
        var fields = new Dictionary<string, string>();
        var query = context.Request.Query;

        var destination = query["destination"].ToString().Trim();
        if (destination.Length is > 0 and < 2 or > 100)
        {
            fields["destination"] = "Must be between 2 and 100 characters.";
        }

        var minimumPrice = ParseDecimal(query["minPrice"], "minPrice", fields);
        var maximumPrice = ParseDecimal(query["maxPrice"], "maxPrice", fields);
        if (minimumPrice is not null && maximumPrice is not null && minimumPrice > maximumPrice)
        {
            fields["minPrice"] = "Must not be greater than maxPrice.";
        }

        var guests = ParseInteger(query["guests"], "guests", 1, 20, fields);
        var isActive = ParseBoolean(query["active"], "active", fields);

        return fields.Count > 0
            ? new(null, ValidationError(context, fields))
            : new(
                new CatalogueFilters(
                    string.IsNullOrEmpty(destination) ? null : destination,
                    minimumPrice,
                    maximumPrice,
                    guests,
                    isActive),
                null);
    }

    private static decimal? ParseDecimal(
        string? value,
        string field,
        IDictionary<string, string> errors)
    {
        if (string.IsNullOrWhiteSpace(value))
        {
            return null;
        }

        if (!decimal.TryParse(
                value,
                NumberStyles.Number,
                CultureInfo.InvariantCulture,
                out var parsed)
            || parsed is < 0 or > 100000)
        {
            errors[field] = "Must be a number between 0 and 100000.";
            return null;
        }

        return parsed;
    }

    private static int? ParseInteger(
        string? value,
        string field,
        int minimum,
        int maximum,
        IDictionary<string, string> errors)
    {
        if (string.IsNullOrWhiteSpace(value))
        {
            return null;
        }

        if (!int.TryParse(value, NumberStyles.Integer, CultureInfo.InvariantCulture, out var parsed)
            || parsed < minimum
            || parsed > maximum)
        {
            errors[field] = $"Must be an integer between {minimum} and {maximum}.";
            return null;
        }

        return parsed;
    }

    private static bool? ParseBoolean(
        string? value,
        string field,
        IDictionary<string, string> errors)
    {
        if (string.IsNullOrWhiteSpace(value))
        {
            return null;
        }

        if (!bool.TryParse(value, out var parsed))
        {
            errors[field] = "Must be true or false.";
            return null;
        }

        return parsed;
    }

    private static Task<bool> DuplicateExistsAsync(
        AccommodationDbContext database,
        string name,
        string destination,
        int? excludedId = null)
    {
        return database.Accommodations.AnyAsync(item =>
            (!excludedId.HasValue || item.Id != excludedId.Value)
            && EF.Functions.Collate(item.Name, "NOCASE") == name
            && EF.Functions.Collate(item.Destination, "NOCASE") == destination);
    }

    private static async Task<IResult?> SaveAsync(
        HttpContext context,
        AccommodationDbContext database)
    {
        try
        {
            await database.SaveChangesAsync();
            return null;
        }
        catch (DbUpdateException)
        {
            return Conflict(context);
        }
    }

    private static AccommodationResponse ToResponse(AccommodationEntity accommodation)
    {
        return new(
            accommodation.Id,
            accommodation.Name,
            accommodation.Destination,
            accommodation.Description,
            accommodation.NightlyPrice,
            accommodation.MaxGuests,
            JsonSerializer.Deserialize<string[]>(accommodation.AmenitiesJson) ?? [],
            accommodation.ImageUrl,
            accommodation.BookingUrl,
            accommodation.IsActive,
            accommodation.CreatedAt,
            accommodation.UpdatedAt);
    }

    private static IResult ValidationError(
        HttpContext context,
        IReadOnlyDictionary<string, string> fields)
    {
        return Error(
            context,
            StatusCodes.Status400BadRequest,
            "validation_error",
            "One or more fields are invalid.",
            fields);
    }

    private static IResult NotFound(HttpContext context)
    {
        return Error(
            context,
            StatusCodes.Status404NotFound,
            "not_found",
            "Accommodation was not found.");
    }

    private static IResult Conflict(HttpContext context)
    {
        return Error(
            context,
            StatusCodes.Status409Conflict,
            "accommodation_conflict",
            "An accommodation with this name and destination already exists.");
    }

    private static IResult Error(
        HttpContext context,
        int statusCode,
        string code,
        string message,
        IReadOnlyDictionary<string, string>? fields = null)
    {
        return Results.Json(
            new ApiErrorEnvelope(
                new ApiError(
                    code,
                    message,
                    fields ?? new Dictionary<string, string>(),
                    context.TraceIdentifier)),
            statusCode: statusCode);
    }

    private sealed record RequestReadResult(AccommodationRequest? Request, IResult? Error);

    private sealed record ValidationResult(
        ValidAccommodation? Value,
        IReadOnlyDictionary<string, string>? Error);

    private sealed record QueryResult(CatalogueFilters? Filters, IResult? Error);

    private sealed record ValidAccommodation(
        string Name,
        string Destination,
        string Description,
        decimal NightlyPrice,
        int MaxGuests,
        string[] Amenities,
        string? ImageUrl,
        string? BookingUrl,
        bool IsActive);

    private sealed record CatalogueFilters(
        string? Destination,
        decimal? MinimumPrice,
        decimal? MaximumPrice,
        int? Guests,
        bool? IsActive);
}

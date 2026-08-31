using System.Text.Json;
using Accommodation.Database.Repositories;
using SearchEntity = Accommodation.Database.Data.Search;

namespace Accommodation.Database.Api;

public static class SearchEndpoints
{
    private const string Route = "/api/data/searches";

    public static IEndpointRouteBuilder MapSearchEndpoints(this IEndpointRouteBuilder endpoints)
    {
        var group = endpoints.MapGroup(Route);
        group.MapGet("/", ListAsync);
        group.MapPost("/", CreateAsync);
        group.MapGet("/{id:int}", GetAsync);
        group.MapPatch("/{id:int}", RenameAsync);
        group.MapDelete("/{id:int}", DeleteAsync);
        return endpoints;
    }

    private static async Task<IResult> ListAsync(
        HttpContext context,
        ISearchRepository repository)
    {
        var searches = await repository.ListAsync(context.RequestAborted);
        return Results.Ok(searches.Select(ToSummaryResponse));
    }

    private static async Task<IResult> CreateAsync(
        HttpContext context,
        ISearchRepository repository)
    {
        var readResult = await ReadAsync<SearchCreateRequest>(context);
        if (readResult.Error is not null)
        {
            return readResult.Error;
        }

        var validation = ValidateCreate(readResult.Value!);
        if (validation.Error is not null)
        {
            return ValidationError(context, validation.Error);
        }

        var value = validation.Value!;
        var now = DateTime.UtcNow;
        var search = new SearchEntity
        {
            Title = value.Title,
            Destination = value.Destination,
            CheckIn = value.CheckIn,
            CheckOut = value.CheckOut,
            Guests = value.Guests,
            MinimumPrice = value.MinimumPrice,
            MaximumPrice = value.MaximumPrice,
            Preferences = value.Preferences,
            RankingMode = value.RankingMode,
            ResultsJson = value.ResultsJson,
            CreatedAt = now,
            UpdatedAt = now
        };

        repository.Add(search);
        await repository.SaveChangesAsync(context.RequestAborted);

        return Results.Created($"{Route}/{search.Id}", ToResponse(search));
    }

    private static async Task<IResult> GetAsync(
        int id,
        HttpContext context,
        ISearchRepository repository)
    {
        var search = await repository.GetAsync(
            id,
            trackChanges: false,
            context.RequestAborted);

        return search is null
            ? NotFound(context)
            : Results.Ok(ToResponse(search));
    }

    private static async Task<IResult> RenameAsync(
        int id,
        HttpContext context,
        ISearchRepository repository)
    {
        var search = await repository.GetAsync(
            id,
            trackChanges: true,
            context.RequestAborted);
        if (search is null)
        {
            return NotFound(context);
        }

        var readResult = await ReadAsync<SearchRenameRequest>(context);
        if (readResult.Error is not null)
        {
            return readResult.Error;
        }

        var title = NormalizeRequiredText(
            readResult.Value!.Title,
            1,
            80);
        if (title is null)
        {
            return ValidationError(context, new Dictionary<string, string>
            {
                ["title"] = "Must be between 1 and 80 characters."
            });
        }

        search.Title = title;
        search.UpdatedAt = DateTime.UtcNow;
        await repository.SaveChangesAsync(context.RequestAborted);

        return Results.Ok(ToResponse(search));
    }

    private static async Task<IResult> DeleteAsync(
        int id,
        HttpContext context,
        ISearchRepository repository)
    {
        var search = await repository.GetAsync(
            id,
            trackChanges: true,
            context.RequestAborted);
        if (search is null)
        {
            return NotFound(context);
        }

        repository.Remove(search);
        await repository.SaveChangesAsync(context.RequestAborted);
        return Results.NoContent();
    }

    private static async Task<ReadResult<T>> ReadAsync<T>(HttpContext context)
        where T : class
    {
        try
        {
            var request = await context.Request.ReadFromJsonAsync<T>();
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

    private static CreateValidationResult ValidateCreate(SearchCreateRequest request)
    {
        var fields = new Dictionary<string, string>();
        var title = ValidateRequiredText(request.Title, 1, 80, "title", fields);
        var destination = ValidateRequiredText(
            request.Destination,
            2,
            100,
            "destination",
            fields);

        var today = DateOnly.FromDateTime(DateTime.Today);
        if (request.CheckIn is null)
        {
            fields["checkIn"] = "A valid ISO date is required.";
        }
        else if (request.CheckIn < today)
        {
            fields["checkIn"] = "Must not be before the current local date.";
        }

        if (request.CheckOut is null)
        {
            fields["checkOut"] = "A valid ISO date is required.";
        }
        else if (request.CheckIn is not null && request.CheckOut <= request.CheckIn)
        {
            fields["checkOut"] = "Must be after check-in.";
        }

        if (request.Guests is null or < 1 or > 20)
        {
            fields["guests"] = "Must be between 1 and 20.";
        }

        if (request.MinimumPrice is null or < 0 or > 100000)
        {
            fields["minimumPrice"] = "Must be between 0 and 100000.";
        }

        if (request.MaximumPrice is null or < 0 or > 100000)
        {
            fields["maximumPrice"] = "Must be between 0 and 100000.";
        }
        else if (request.MinimumPrice is not null
            && request.MaximumPrice < request.MinimumPrice)
        {
            fields["maximumPrice"] = "Must not be less than minimumPrice.";
        }

        var preferences = request.Preferences ?? string.Empty;
        if (preferences.Length > 500)
        {
            fields["preferences"] = "Must contain at most 500 characters.";
        }

        var rankingMode = request.RankingMode?.Trim().ToLowerInvariant();
        if (rankingMode is not ("ai" or "fallback"))
        {
            fields["rankingMode"] = "Must be either ai or fallback.";
        }

        string? resultsJson = null;
        if (request.Results.ValueKind != JsonValueKind.Array)
        {
            fields["results"] = "Must be a JSON array.";
        }
        else
        {
            resultsJson = request.Results.GetRawText();
        }

        if (fields.Count > 0)
        {
            return new(null, fields);
        }

        return new(
            new ValidSearch(
                title!,
                destination!,
                request.CheckIn!.Value,
                request.CheckOut!.Value,
                request.Guests!.Value,
                decimal.Round(request.MinimumPrice!.Value, 2),
                decimal.Round(request.MaximumPrice!.Value, 2),
                preferences,
                rankingMode!,
                resultsJson!),
            null);
    }

    private static string? ValidateRequiredText(
        string? value,
        int minimumLength,
        int maximumLength,
        string field,
        IDictionary<string, string> fields)
    {
        var normalized = NormalizeRequiredText(value, minimumLength, maximumLength);
        if (normalized is null)
        {
            fields[field] = $"Must be between {minimumLength} and {maximumLength} characters.";
        }

        return normalized;
    }

    private static string? NormalizeRequiredText(
        string? value,
        int minimumLength,
        int maximumLength)
    {
        var trimmed = value?.Trim();
        return trimmed is not null
            && trimmed.Length >= minimumLength
            && trimmed.Length <= maximumLength
                ? trimmed
                : null;
    }

    private static SearchSummaryResponse ToSummaryResponse(SearchEntity search)
    {
        return new(
            search.Id,
            search.Title,
            search.Destination,
            search.CheckIn,
            search.CheckOut,
            search.Guests,
            search.RankingMode,
            search.CreatedAt,
            search.UpdatedAt);
    }

    private static SearchResponse ToResponse(SearchEntity search)
    {
        return new(
            search.Id,
            search.Title,
            search.Destination,
            search.CheckIn,
            search.CheckOut,
            search.Guests,
            search.MinimumPrice,
            search.MaximumPrice,
            search.Preferences,
            search.RankingMode,
            JsonSerializer.Deserialize<JsonElement>(search.ResultsJson),
            search.CreatedAt,
            search.UpdatedAt);
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
            "Search was not found.");
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

    private sealed record ReadResult<T>(T? Value, IResult? Error)
        where T : class;

    private sealed record CreateValidationResult(
        ValidSearch? Value,
        IReadOnlyDictionary<string, string>? Error);

    private sealed record ValidSearch(
        string Title,
        string Destination,
        DateOnly CheckIn,
        DateOnly CheckOut,
        int Guests,
        decimal MinimumPrice,
        decimal MaximumPrice,
        string Preferences,
        string RankingMode,
        string ResultsJson);
}

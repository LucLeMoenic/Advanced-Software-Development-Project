using System.Diagnostics;
using System.Text.Json;
using Accommodation.Backend.Clients;

namespace Accommodation.Backend.Api;

public static class SearchEndpoints
{
    private const string Route = "/api/searches";

    public static IEndpointRouteBuilder MapSearchEndpoints(
        this IEndpointRouteBuilder endpoints)
    {
        var group = endpoints.MapGroup(Route);
        group.MapPost("/", CreateAsync);
        group.MapGet("/", ListAsync);
        group.MapGet("/{id:int}", GetAsync);
        group.MapPatch("/{id:int}", RenameAsync);
        group.MapDelete("/{id:int}", DeleteAsync);
        return endpoints;
    }

    private static async Task<IResult> CreateAsync(
        HttpContext context,
        IDatabaseApiClient database,
        ILiteApiClient liteApi,
        IOllamaRankingClient ollama,
        TimeProvider timeProvider,
        ILoggerFactory loggerFactory)
    {
        var stopwatch = Stopwatch.StartNew();
        var logger = loggerFactory.CreateLogger("Accommodation.Backend.Search");
        var readResult = await ReadAsync<SearchRequest>(context);
        if (readResult.Error is not null)
        {
            LogRejected(logger, context, stopwatch);
            return readResult.Error;
        }

        var today = DateOnly.FromDateTime(timeProvider.GetLocalNow().DateTime);
        var validation = SearchValidator.Validate(readResult.Value!, today);
        if (validation.Errors is not null)
        {
            LogRejected(logger, context, stopwatch);
            return ValidationError(context, validation.Errors);
        }

        var search = validation.Value!;
        var stage = "candidate_retrieval";
        var candidateCount = 0;

        try
        {
            var candidates = await database.ListCandidatesAsync(
                new CandidateQuery(
                    search.Destination,
                    search.Guests,
                    search.MinimumPrice,
                    search.MaximumPrice),
                context.RequestAborted);
            candidateCount = candidates.Count;
            var importedProviderData = false;

            if (candidates.Count == 0)
            {
                stage = "liteapi_import";
                var imports = await liteApi.SearchAsync(
                    search,
                    context.RequestAborted);
                foreach (var accommodation in imports)
                {
                    await database.ImportAccommodationAsync(
                        accommodation,
                        context.RequestAborted);
                }

                candidates = await database.ListCandidatesAsync(
                    new CandidateQuery(
                        search.Destination,
                        search.Guests,
                        search.MinimumPrice,
                        search.MaximumPrice),
                    context.RequestAborted);
                candidateCount = candidates.Count;
                importedProviderData = imports.Count > 0;
            }

            var rankingMode = "fallback";
            string? notice = null;
            IReadOnlyList<SearchResult> results = [];

            if (candidates.Count > 0)
            {
                stage = "ranking";
                try
                {
                    results = await ollama.RankAsync(
                        search,
                        candidates,
                        context.RequestAborted);
                    rankingMode = "ai";
                }
                catch (OllamaRankingException exception)
                {
                    results = DeterministicRanker.Rank(
                        candidates,
                        search.MinimumPrice,
                        search.MaximumPrice);
                    notice = "AI ranking was unavailable, so deterministic fallback ranking was used.";

                    logger.LogWarning(
                        "Search {CorrelationId} stage {Stage} outcome {Outcome} continued in {DurationMs}ms with {CandidateCount} candidates using {RankingMode}; failure category {FailureCategory}",
                        context.TraceIdentifier,
                        stage,
                        "fallback",
                        stopwatch.ElapsedMilliseconds,
                        candidates.Count,
                        rankingMode,
                        exception.FailureCategory);
                }
            }

            stage = "persistence";
            var persisted = await database.CreateSearchAsync(
                new PersistSearchRequest(
                    CreateTitle(search.Destination),
                    search.Destination,
                    search.CheckIn,
                    search.CheckOut,
                    search.Guests,
                    search.MinimumPrice,
                    search.MaximumPrice,
                    search.Preferences,
                    rankingMode,
                    results),
                context.RequestAborted);

            logger.LogInformation(
                "Search {CorrelationId} stage {Stage} outcome {Outcome} completed in {DurationMs}ms with {CandidateCount} candidates using {RankingMode}",
                context.TraceIdentifier,
                "completed",
                "success",
                stopwatch.ElapsedMilliseconds,
                candidates.Count,
                rankingMode);

            var response = persisted with
            {
                Notice = notice,
                ImportedProviderData = importedProviderData
            };

            return candidates.Count == 0
                ? Results.Ok(response)
                : Results.Created(
                    $"{Route}/{persisted.Id}",
                    response);
        }
        catch (DatabaseUnavailableException)
        {
            logger.LogWarning(
                "Search {CorrelationId} stage {Stage} outcome {Outcome} failed in {DurationMs}ms with {CandidateCount} candidates using {RankingMode}; failure category {FailureCategory}",
                context.TraceIdentifier,
                stage,
                "failure",
                stopwatch.ElapsedMilliseconds,
                candidateCount,
                "fallback",
                "database_unavailable");
            return DependencyUnavailable(context);
        }
        catch (DatabaseResponseException)
        {
            logger.LogWarning(
                "Search {CorrelationId} stage {Stage} outcome {Outcome} failed in {DurationMs}ms with {CandidateCount} candidates using {RankingMode}; failure category {FailureCategory}",
                context.TraceIdentifier,
                stage,
                "failure",
                stopwatch.ElapsedMilliseconds,
                candidateCount,
                "fallback",
                "database_response");
            return DependencyResponseError(context);
        }
        catch (LiteApiUnavailableException exception)
        {
            logger.LogWarning(
                "Search {CorrelationId} stage {Stage} outcome {Outcome} failed in {DurationMs}ms with {CandidateCount} candidates using {RankingMode}; failure category {FailureCategory}",
                context.TraceIdentifier,
                stage,
                "failure",
                stopwatch.ElapsedMilliseconds,
                candidateCount,
                "none",
                exception.FailureCategory);
            return AccommodationProviderUnavailable(context);
        }
        catch (LiteApiResponseException exception)
        {
            logger.LogWarning(
                "Search {CorrelationId} stage {Stage} outcome {Outcome} failed in {DurationMs}ms with {CandidateCount} candidates using {RankingMode}; failure category {FailureCategory}",
                context.TraceIdentifier,
                stage,
                "failure",
                stopwatch.ElapsedMilliseconds,
                candidateCount,
                "none",
                exception.FailureCategory);
            return AccommodationProviderResponseError(context);
        }
    }

    private static async Task<IResult> ListAsync(
        HttpContext context,
        IDatabaseApiClient database)
    {
        try
        {
            return Results.Ok(await database.ListSearchesAsync(context.RequestAborted));
        }
        catch (DatabaseUnavailableException)
        {
            return DependencyUnavailable(context);
        }
        catch (DatabaseResponseException)
        {
            return DependencyResponseError(context);
        }
    }

    private static async Task<IResult> GetAsync(
        int id,
        HttpContext context,
        IDatabaseApiClient database)
    {
        try
        {
            return Results.Ok(await database.GetSearchAsync(id, context.RequestAborted));
        }
        catch (DatabaseRecordNotFoundException)
        {
            return NotFound(context);
        }
        catch (DatabaseUnavailableException)
        {
            return DependencyUnavailable(context);
        }
        catch (DatabaseResponseException)
        {
            return DependencyResponseError(context);
        }
    }

    private static async Task<IResult> RenameAsync(
        int id,
        HttpContext context,
        IDatabaseApiClient database)
    {
        var readResult = await ReadAsync<SearchRenameRequest>(context);
        if (readResult.Error is not null)
        {
            return readResult.Error;
        }

        var title = readResult.Value!.Title?.Trim();
        if (title is null || title.Length is < 1 or > 80)
        {
            return ValidationError(context, new Dictionary<string, string>
            {
                ["title"] = "Must be between 1 and 80 characters."
            });
        }

        try
        {
            return Results.Ok(await database.RenameSearchAsync(
                id,
                new SearchRenameRequest(title),
                context.RequestAborted));
        }
        catch (DatabaseRecordNotFoundException)
        {
            return NotFound(context);
        }
        catch (DatabaseUnavailableException)
        {
            return DependencyUnavailable(context);
        }
        catch (DatabaseResponseException)
        {
            return DependencyResponseError(context);
        }
    }

    private static async Task<IResult> DeleteAsync(
        int id,
        HttpContext context,
        IDatabaseApiClient database)
    {
        try
        {
            await database.DeleteSearchAsync(id, context.RequestAborted);
            return Results.NoContent();
        }
        catch (DatabaseRecordNotFoundException)
        {
            return NotFound(context);
        }
        catch (DatabaseUnavailableException)
        {
            return DependencyUnavailable(context);
        }
        catch (DatabaseResponseException)
        {
            return DependencyResponseError(context);
        }
    }

    private static async Task<ReadResult<T>> ReadAsync<T>(HttpContext context)
        where T : class
    {
        if (!context.Request.HasJsonContentType())
        {
            return new(null, ValidationError(context, new Dictionary<string, string>
            {
                ["body"] = "The request body must use application/json."
            }));
        }

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

    private static void LogRejected(
        ILogger logger,
        HttpContext context,
        Stopwatch stopwatch)
    {
        logger.LogInformation(
            "Search {CorrelationId} stage {Stage} outcome {Outcome} completed in {DurationMs}ms with {CandidateCount} candidates using {RankingMode}",
            context.TraceIdentifier,
            "validation",
            "rejected",
            stopwatch.ElapsedMilliseconds,
            0,
            "none");
    }

    private static string CreateTitle(string destination)
    {
        return destination.Length <= 80
            ? destination
            : destination[..80];
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

    private static IResult DependencyResponseError(HttpContext context)
    {
        return Error(
            context,
            StatusCodes.Status502BadGateway,
            "dependency_response_error",
            "The database service returned an unusable response.");
    }

    private static IResult DependencyUnavailable(HttpContext context)
    {
        return Error(
            context,
            StatusCodes.Status503ServiceUnavailable,
            "dependency_unavailable",
            "The database service is unavailable.");
    }

    private static IResult AccommodationProviderResponseError(HttpContext context)
    {
        return Error(
            context,
            StatusCodes.Status502BadGateway,
            "accommodation_provider_response_error",
            "The accommodation provider returned an unusable response.");
    }

    private static IResult AccommodationProviderUnavailable(HttpContext context)
    {
        return Error(
            context,
            StatusCodes.Status503ServiceUnavailable,
            "accommodation_provider_unavailable",
            "The accommodation provider is unavailable.");
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
}

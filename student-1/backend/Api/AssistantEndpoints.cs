using System.Diagnostics;
using System.Text.Json;
using Accommodation.Backend.Clients;

namespace Accommodation.Backend.Api;

public static class AssistantEndpoints
{
    private const int MaximumBodyBytes = 8192;
    private static readonly HashSet<string> Modes = ["lookup", "guide"];

    public static IEndpointRouteBuilder MapAssistantEndpoints(this IEndpointRouteBuilder endpoints)
    {
        endpoints.MapPost("/api/assistant", AskAsync);
        return endpoints;
    }

    private static async Task<IResult> AskAsync(
        HttpContext context,
        AssistantModes modes,
        ILookupArgumentExtractor extractor,
        IMcpToolClient mcp,
        IRagClient rag,
        ILoggerFactory loggerFactory)
    {
        var stopwatch = Stopwatch.StartNew();
        var logger = loggerFactory.CreateLogger("Accommodation.Backend.Assistant");
        var (request, error) = await ReadAsync(context);
        if (request is null)
        {
            Log(logger, context, "none", "validation", "rejected", stopwatch);
            return error!;
        }

        var guide = request.Mode == "guide";
        if (guide ? !modes.GuideEnabled : !modes.LookupEnabled)
        {
            Log(logger, context, request.Mode, "flags", "mode_disabled", stopwatch);
            return SearchEndpoints.Error(
                context,
                StatusCodes.Status503ServiceUnavailable,
                "mode_disabled",
                guide ? "Destination guide is disabled." : "Catalogue lookup is disabled.");
        }

        var stage = guide ? "retrieval" : "extraction";
        try
        {
            if (guide)
            {
                var answer = GuideResponseValidator.Validate(await rag.AskAsync(request.Question, context.RequestAborted));
                Log(logger, context, request.Mode, answer.Confidence, "success", stopwatch);
                return Results.Ok(answer);
            }

            var call = await extractor.ExtractAsync(request.Question, context.RequestAborted);
            stage = "tool_call";
            var body = await mcp.CallAsync(call, context.RequestAborted);
            stage = "result_validation";
            var result = LookupResultValidator.Validate(call, body);
            Log(logger, context, request.Mode, call.Tool, "success", stopwatch);
            return Results.Ok(new LookupResponse("lookup", call.Tool, call.Arguments, result));
        }
        catch (AssistantException exception)
        {
            logger.LogWarning(
                "Assistant {CorrelationId} mode {Mode} stage {Stage} failed in {DurationMs}ms; dependency {Dependency} failure {Failure}",
                context.TraceIdentifier,
                request.Mode,
                stage,
                stopwatch.ElapsedMilliseconds,
                exception.Dependency,
                exception.Failure);
            return Failure(context, exception.Failure);
        }
    }

    private static IResult Failure(HttpContext context, AssistantFailure failure)
    {
        return failure switch
        {
            AssistantFailure.NotUnderstood => SearchEndpoints.Error(
                context,
                StatusCodes.Status422UnprocessableEntity,
                "lookup_not_understood",
                "Please rephrase, e.g. \"Find stays in Tokyo for 2 guests under $200\" or \"Show saved search 11\"."),
            AssistantFailure.SearchNotFound => SearchEndpoints.Error(
                context,
                StatusCodes.Status404NotFound,
                "search_not_found",
                "That saved search was not found."),
            AssistantFailure.Unavailable => SearchEndpoints.Error(
                context,
                StatusCodes.Status503ServiceUnavailable,
                "dependency_unavailable",
                "The assistant service is unavailable. Try again shortly."),
            AssistantFailure.Timeout => SearchEndpoints.Error(
                context,
                StatusCodes.Status504GatewayTimeout,
                "dependency_timeout",
                "The assistant service timed out. Try again shortly."),
            _ => SearchEndpoints.Error(
                context,
                StatusCodes.Status502BadGateway,
                "dependency_response_error",
                "The assistant service returned an unusable response.")
        };
    }

    private static async Task<(AssistantRequest? Request, IResult? Error)> ReadAsync(HttpContext context)
    {
        if (!context.Request.HasJsonContentType())
        {
            return Invalid(context, "body", "The request body must use application/json.");
        }

        if (context.Request.ContentLength > MaximumBodyBytes)
        {
            return Invalid(context, "body", $"The request body must be at most {MaximumBodyBytes} bytes.");
        }

        using var buffer = new MemoryStream();
        var chunk = new byte[4096];
        int read;
        while ((read = await context.Request.Body.ReadAsync(chunk, context.RequestAborted)) > 0)
        {
            if (buffer.Length + read > MaximumBodyBytes)
            {
                return Invalid(context, "body", $"The request body must be at most {MaximumBodyBytes} bytes.");
            }

            buffer.Write(chunk, 0, read);
        }

        try
        {
            using var document = JsonDocument.Parse(buffer.ToArray());
            var root = document.RootElement;
            var names = root.ValueKind == JsonValueKind.Object
                ? root.EnumerateObject().Select(property => property.Name).ToArray()
                : [];
            if (names.Length != 2 || !names.Contains("mode") || !names.Contains("question"))
            {
                return Invalid(context, "body", "Send exactly the fields mode and question.");
            }

            var mode = root.GetProperty("mode");
            if (mode.ValueKind != JsonValueKind.String || !Modes.Contains(mode.GetString()!))
            {
                return Invalid(context, "mode", "Must be lookup or guide.");
            }

            var question = root.GetProperty("question");
            var text = question.ValueKind == JsonValueKind.String ? question.GetString()!.Trim() : "";
            if (text.Length is < 1 or > 1000)
            {
                return Invalid(context, "question", "Must be between 1 and 1000 characters.");
            }

            return (new AssistantRequest(mode.GetString()!, text), null);
        }
        catch (JsonException)
        {
            return Invalid(context, "body", "The request body must be valid JSON.");
        }
    }

    private static (AssistantRequest?, IResult?) Invalid(HttpContext context, string field, string message)
    {
        return (null, SearchEndpoints.Error(
            context,
            StatusCodes.Status400BadRequest,
            "validation_error",
            "One or more fields are invalid.",
            new Dictionary<string, string> { [field] = message }));
    }

    private static void Log(
        ILogger logger,
        HttpContext context,
        string mode,
        string stage,
        string outcome,
        Stopwatch stopwatch)
    {
        logger.LogInformation(
            "Assistant {CorrelationId} mode {Mode} stage {Stage} outcome {Outcome} in {DurationMs}ms",
            context.TraceIdentifier,
            mode,
            stage,
            outcome,
            stopwatch.ElapsedMilliseconds);
    }

    private sealed record AssistantRequest(string Mode, string Question);
}

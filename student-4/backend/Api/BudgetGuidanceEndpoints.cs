using System.Text.Json;
using System.Text.RegularExpressions;
using BudgetTracker.Backend.Clients;
using BudgetTracker.Backend.Services;

namespace BudgetTracker.Backend.Api;

public static class BudgetGuidanceEndpoints
{
    private const string InsufficientAnswer = "Not enough information in the knowledge base to answer this.";
    private const double MinimumRelevance = 0.15d;
    private const double CitationScoreRoundingTolerance = 0.00005d;
    private static readonly IReadOnlyDictionary<string, string> KnownSources = new Dictionary<string, string>(StringComparer.Ordinal)
    {
        ["category-budgets#1"] = "Category budgets and spending statuses",
        ["category-budgets#2"] = "Category budgets and spending statuses",
        ["expense-conversion#1"] = "Expense entry and conversion snapshots",
        ["expense-conversion#2"] = "Expense entry and conversion snapshots",
        ["budgeting-workflow#1"] = "Practical budgeting workflow in the tracker",
        ["budgeting-workflow#2"] = "Practical budgeting workflow in the tracker"
    };
    private static readonly Regex CitationMarker = new(@"\[([A-Za-z0-9_-]+#\d+)\]", RegexOptions.Compiled | RegexOptions.CultureInvariant);

    public static void MapBudgetGuidanceEndpoints(this WebApplication app) =>
        app.MapPost("/api/budget-guidance", HandleAsync);

    private static async Task<IResult> HandleAsync(
        HttpContext context,
        FeatureModeSettings modes,
        IRagClient rag,
        CancellationToken cancellationToken)
    {
        if (!modes.RagEnabled)
        {
            return BudgetEndpoints.Error(context, 503, "feature_disabled", "Budgeting guidance is disabled.");
        }

        var question = await BudgetCheckEndpoints.ReadStrictStringAsync(context.Request, "question", 1000, cancellationToken);
        if (question is null)
        {
            return BudgetEndpoints.Error(context, 400, "invalid_request", "The request body must contain only a valid question.");
        }

        try
        {
            var response = await rag.AskAsync(question, cancellationToken);
            return Results.Ok(ValidateResponse(response));
        }
        catch (RagFailureException exception)
        {
            return BudgetEndpoints.Error(context, exception.StatusCode, exception.Code, exception.Message);
        }
    }

    private static BudgetGuidanceResponse ValidateResponse(JsonElement response)
    {
        if (!HasExactProperties(response, "answer", "citations", "confidence")) throw InvalidResponse();
        var answer = ReadString(response, "answer", 2000);
        var confidence = ReadString(response, "confidence", 20);
        var citationValues = response.GetProperty("citations");
        if (citationValues.ValueKind != JsonValueKind.Array) throw InvalidResponse();

        if (confidence == "insufficient")
        {
            if (answer != InsufficientAnswer || citationValues.GetArrayLength() != 0) throw InvalidResponse();
            return new(answer, [], confidence);
        }

        if (confidence is not ("high" or "medium" or "low") || string.IsNullOrWhiteSpace(answer)
            || answer.Contains('<') || answer.Contains('>') || answer.Contains('\0')
            || citationValues.GetArrayLength() is < 1 or > 3)
        {
            throw InvalidResponse();
        }

        var citations = new List<BudgetGuidanceCitation>();
        var identifiers = new HashSet<string>(StringComparer.Ordinal);
        var minimumScore = 1d;
        foreach (var value in citationValues.EnumerateArray())
        {
            if (!HasExactProperties(value, "source", "chunk_id", "snippet", "score")) throw InvalidResponse();
            var source = ReadString(value, "source", 200);
            var chunkId = ReadString(value, "chunk_id", 160);
            var snippet = ReadString(value, "snippet", 280);
            var scoreValue = value.GetProperty("score");
            if (scoreValue.ValueKind != JsonValueKind.Number || !scoreValue.TryGetDouble(out var score)
                || !double.IsFinite(score) || score is < MinimumRelevance or > 1d
                || !KnownSources.TryGetValue(chunkId, out var expectedSource)
                || source != expectedSource || !identifiers.Add(chunkId))
            {
                throw InvalidResponse();
            }

            minimumScore = Math.Min(minimumScore, score);
            citations.Add(new(source, chunkId, snippet, score));
        }

        var markers = CitationMarker.Matches(answer);
        var withoutMarkers = CitationMarker.Replace(answer, string.Empty);
        if (withoutMarkers.Contains('[') || withoutMarkers.Contains(']')
            || !markers.Select(match => match.Groups[1].Value).ToHashSet(StringComparer.Ordinal).SetEquals(identifiers)
            || !ConfidenceMatchesRoundedScore(confidence, minimumScore))
        {
            throw InvalidResponse();
        }

        return new(answer, citations, confidence);
    }

    private static bool ConfidenceMatchesRoundedScore(string confidence, double score)
    {
        var lowestPossibleScore = Math.Max(MinimumRelevance, score - CitationScoreRoundingTolerance);
        var highestPossibleScore = Math.Min(1d, score + CitationScoreRoundingTolerance);
        return confidence switch
        {
            "low" => lowestPossibleScore < 0.30d,
            "medium" => highestPossibleScore >= 0.30d && lowestPossibleScore < 0.40d,
            "high" => highestPossibleScore >= 0.40d,
            _ => false
        };
    }

    private static bool HasExactProperties(JsonElement value, params string[] expected)
    {
        if (value.ValueKind != JsonValueKind.Object) return false;
        var seen = new HashSet<string>(StringComparer.Ordinal);
        foreach (var property in value.EnumerateObject())
        {
            if (!seen.Add(property.Name) || !expected.Contains(property.Name, StringComparer.Ordinal)) return false;
        }

        return seen.Count == expected.Length;
    }

    private static string ReadString(JsonElement value, string name, int maximumCharacters)
    {
        var field = value.GetProperty(name);
        if (field.ValueKind != JsonValueKind.String) throw InvalidResponse();
        var result = field.GetString();
        if (string.IsNullOrWhiteSpace(result) || CountCharacters(result) > maximumCharacters) throw InvalidResponse();
        return result;
    }

    private static int CountCharacters(string value) => value.EnumerateRunes().Count();

    private static RagFailureException InvalidResponse() =>
        new(502, "dependency_response_invalid", "The RAG service returned an unusable grounded response.");
}

public sealed record BudgetGuidanceCitation(string Source, string ChunkId, string Snippet, double Score);
public sealed record BudgetGuidanceResponse(string Answer, IReadOnlyList<BudgetGuidanceCitation> Citations, string Confidence);
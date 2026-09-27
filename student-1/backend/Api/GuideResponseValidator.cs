using System.Text.Json;
using System.Text.RegularExpressions;

namespace Accommodation.Backend.Api;

// Port of Student 2's validate_advice rules for the shared RAG envelope.
public static partial class GuideResponseValidator
{
    public const string InsufficientAnswer = "Not enough information in the knowledge base to answer this.";

    private static readonly string[] EnvelopeFields = ["answer", "citations", "confidence"];
    private static readonly string[] CitationFields = ["source", "chunk_id", "snippet", "score"];
    private static readonly HashSet<string> GroundedConfidence = ["high", "medium", "low"];

    public static GuideResponse Validate(JsonElement body)
    {
        if (!HasExactly(body, EnvelopeFields)
            || body.GetProperty("answer") is not { ValueKind: JsonValueKind.String } answerElement
            || body.GetProperty("citations") is not { ValueKind: JsonValueKind.Array } citationsElement
            || body.GetProperty("confidence") is not { ValueKind: JsonValueKind.String } confidenceElement)
        {
            throw Invalid();
        }

        var answer = answerElement.GetString()!;
        var confidence = confidenceElement.GetString()!;
        if (answer.Trim().Length is < 1 or > 2000)
        {
            throw Invalid();
        }

        if (confidence == "insufficient")
        {
            return citationsElement.GetArrayLength() == 0 && answer == InsufficientAnswer
                ? new GuideResponse("guide", answer, [], confidence)
                : throw Invalid();
        }

        if (!GroundedConfidence.Contains(confidence) || citationsElement.GetArrayLength() is < 1 or > 3)
        {
            throw Invalid();
        }

        var citations = citationsElement.EnumerateArray().Select(ValidateCitation).ToArray();
        var identifiers = citations.Select(citation => citation.ChunkId).ToHashSet(StringComparer.Ordinal);
        var markers = MarkerPattern().Matches(answer).Select(match => match.Groups[1].Value).ToHashSet(StringComparer.Ordinal);
        if (identifiers.Count != citations.Length || !markers.SetEquals(identifiers))
        {
            throw Invalid();
        }

        return new GuideResponse("guide", answer, citations, confidence);
    }

    private static GuideCitation ValidateCitation(JsonElement citation)
    {
        if (!HasExactly(citation, CitationFields)
            || citation.GetProperty("source") is not { ValueKind: JsonValueKind.String } source
            || citation.GetProperty("chunk_id") is not { ValueKind: JsonValueKind.String } chunkId
            || citation.GetProperty("snippet") is not { ValueKind: JsonValueKind.String } snippet
            || citation.GetProperty("score") is not { ValueKind: JsonValueKind.Number } score
            || source.GetString()!.Length is < 1 or > 200
            || chunkId.GetString()!.Length > 160
            || !ChunkIdPattern().IsMatch(chunkId.GetString()!)
            || snippet.GetString()!.Length is < 1 or > 280
            || !score.TryGetDouble(out var value)
            || !double.IsFinite(value) || value <= 0 || value > 1)
        {
            throw Invalid();
        }

        return new GuideCitation(source.GetString()!, chunkId.GetString()!, snippet.GetString()!, value);
    }

    private static bool HasExactly(JsonElement element, string[] fields)
    {
        if (element.ValueKind != JsonValueKind.Object)
        {
            return false;
        }

        var names = element.EnumerateObject().Select(property => property.Name).ToArray();
        return names.Length == fields.Length && fields.All(names.Contains);
    }

    private static AssistantException Invalid()
    {
        return new AssistantException(AssistantFailure.InvalidResponse, "rag");
    }

    [GeneratedRegex(@"^[a-zA-Z0-9_-]+#\d+\z")]
    private static partial Regex ChunkIdPattern();

    [GeneratedRegex(@"\[([^\[\]]+)\]")]
    private static partial Regex MarkerPattern();
}

using System.Net.Http.Json;
using System.Text;
using System.Text.Json;

namespace AgenticLoop;

internal static class ServiceValidation
{
    private static readonly HashSet<string> Student1Tools = ["accommodation.find", "accommodation.get_search"];

    internal static string DefaultBackendUrl(string feature) =>
        feature == "student-1" ? "http://127.0.0.1:5201" : "http://127.0.0.1:5202";

    internal static string DefaultQuestion(string feature, string mode) => (feature, mode) switch
    {
        ("student-1", "mcp") => "Find stays in Tokyo for 2 guests under $200",
        ("student-1", _) => "Is Tokyo safe for families?",
        _ => "Is budget the total for the trip?"
    };

    internal static async Task<TestEvidence> CaptureAsync(
        HttpClient client, string mode, string backendUrl, int tripId, string question, string feature = "student-2")
    {
        if (mode is not ("mcp" or "rag"))
            throw new LoopException("Validation mode must be mcp or rag.");
        if (feature is not ("student-1" or "student-2"))
            throw new LoopException("Validation feature must be student-1 or student-2.");
        if (!Uri.TryCreate(backendUrl, UriKind.Absolute, out var backend)
            || backend.Scheme != "http" || !backend.IsLoopback
            || backend.AbsolutePath != "/" || backend.UserInfo.Length != 0
            || backend.Query.Length != 0 || backend.Fragment.Length != 0)
            throw new LoopException("Validation requires a loopback HTTP backend origin without credentials or a path.");
        if (tripId <= 0 || string.IsNullOrWhiteSpace(question) || question.Length > 1000)
            throw new LoopException("Use a positive trip ID and a question of 1-1000 characters.");

        var path = feature == "student-1" ? "/api/assistant"
            : mode == "mcp" ? $"/api/trips/{tripId}/mcp-summary" : "/api/itinerary-advice";
        using var deadline = new CancellationTokenSource(TimeSpan.FromSeconds(35));
        using var request = new HttpRequestMessage(HttpMethod.Post, new Uri(backend, path))
        {
            Content = feature == "student-1" ? JsonContent.Create(new { mode = mode == "mcp" ? "lookup" : "guide", question })
                : mode == "rag" ? JsonContent.Create(new { question }) : JsonContent.Create(new { })
        };
        using var response = await client.SendAsync(request, HttpCompletionOption.ResponseHeadersRead, deadline.Token);
        await using var stream = await response.Content.ReadAsStreamAsync(deadline.Token);
        using var buffer = new MemoryStream();
        var bytes = new byte[4096];
        int count;
        while ((count = await stream.ReadAsync(bytes, deadline.Token)) != 0)
        {
            if (buffer.Length + count > 16000)
                throw new LoopException("Validation response exceeds 16000 bytes.");
            await buffer.WriteAsync(bytes.AsMemory(0, count), deadline.Token);
        }
        var body = Encoding.UTF8.GetString(buffer.ToArray());
        var passed = response.IsSuccessStatusCode && IsValid(mode, body, tripId, feature);
        var result = JsonSerializer.Serialize(new
        {
            feature, mode, capturedAt = DateTimeOffset.UtcNow, endpoint = request.RequestUri,
            statusCode = (int)response.StatusCode, contractPassed = passed,
            response = body,
            limitation = "Contract checks do not prove claim entailment, protocol discovery, or browser behavior. Review cited sources and capture those checks separately."
        });
        return new TestEvidence($"POST {request.RequestUri}", result);
    }

    internal static bool IsValid(string mode, string body, int tripId, string feature = "student-2")
    {
        try
        {
            using var document = JsonDocument.Parse(body);
            var root = document.RootElement;
            if (feature == "student-1" && mode == "mcp")
                return IsValidStudent1Lookup(root);
            if (feature == "student-1" && root.GetProperty("mode").GetString() != "guide")
                return false;
            if (mode == "mcp")
            {
                var summary = root.GetProperty("summary");
                var dayCount = summary.GetProperty("dayCount").GetInt32();
                var plannedDays = summary.GetProperty("plannedDayCount").GetInt32();
                var missingDays = summary.GetProperty("unplannedDays").EnumerateArray()
                    .Select(day => day.GetInt32()).ToArray();
                return root.GetProperty("tool").GetString() == "itinerary.get_summary"
                    && summary.GetProperty("tripId").GetInt32() == tripId
                    && dayCount is >= 1 and <= 31 && plannedDays >= 0 && plannedDays <= dayCount
                    && missingDays.Length == dayCount - plannedDays
                    && missingDays.Distinct().Count() == missingDays.Length
                    && missingDays.All(day => day >= 1 && day <= dayCount)
                    && summary.GetProperty("stopCount").GetInt32() >= plannedDays;
            }
            if (mode != "rag") return false;
            var answer = root.GetProperty("answer").GetString();
            var confidence = root.GetProperty("confidence").GetString();
            var citations = root.GetProperty("citations").EnumerateArray().ToArray();
            if (string.IsNullOrWhiteSpace(answer) || answer.Length > 2000
                || confidence is not ("high" or "medium" or "low")
                || citations.Length is < 1 or > 3) return false;
            var identifiers = new HashSet<string>();
            foreach (var citation in citations)
            {
                var identifier = citation.GetProperty("chunk_id").GetString();
                var score = citation.GetProperty("score").GetDouble();
                if (string.IsNullOrWhiteSpace(identifier) || !identifiers.Add(identifier)
                    || !answer.Contains($"[{identifier}]", StringComparison.Ordinal)
                    || string.IsNullOrWhiteSpace(citation.GetProperty("source").GetString())
                    || string.IsNullOrWhiteSpace(citation.GetProperty("snippet").GetString())
                    || !double.IsFinite(score) || score <= 0 || score > 1) return false;
            }
            return true;
        }
        catch (Exception exception) when (exception is JsonException or KeyNotFoundException
            or InvalidOperationException or FormatException or OverflowException)
        {
            return false;
        }
    }
    private static bool IsValidStudent1Lookup(JsonElement root)
    {
        var tool = root.GetProperty("tool").GetString();
        var arguments = root.GetProperty("arguments");
        var result = root.GetProperty("result");
        if (root.GetProperty("mode").GetString() != "lookup" || tool is null || !Student1Tools.Contains(tool)
            || arguments.ValueKind != JsonValueKind.Object || !result.GetProperty("ok").GetBoolean())
            return false;
        if (tool == "accommodation.get_search")
        {
            var search = result.GetProperty("search");
            var ranks = search.GetProperty("results").EnumerateArray()
                .Select(item => item.GetProperty("rank").GetInt32()).ToArray();
            return search.GetProperty("id").GetInt32() == arguments.GetProperty("search_id").GetInt32()
                && !string.IsNullOrWhiteSpace(search.GetProperty("title").GetString())
                && ranks.SequenceEqual(Enumerable.Range(1, ranks.Length));
        }
        var destination = arguments.GetProperty("destination").GetString();
        var stays = result.GetProperty("accommodations").EnumerateArray().ToArray();
        return result.GetProperty("count").GetInt32() == stays.Length && stays.Length <= 20
            && stays.All(stay => stay.GetProperty("id").GetInt32() > 0
                && !string.IsNullOrWhiteSpace(stay.GetProperty("name").GetString())
                && string.Equals(stay.GetProperty("destination").GetString(), destination, StringComparison.OrdinalIgnoreCase)
                && stay.GetProperty("nightlyPrice").GetDouble() is var price && double.IsFinite(price) && price >= 0
                && stay.GetProperty("maxGuests").GetInt32() is >= 1 and <= 20
                && stay.GetProperty("amenities").ValueKind == JsonValueKind.Array);
    }
}
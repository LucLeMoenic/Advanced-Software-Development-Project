using System.Net.Http.Json;
using System.Text;
using System.Text.Json;

namespace AgenticLoop;

internal static class ServiceValidation
{
    internal static async Task<TestEvidence> CaptureAsync(
        HttpClient client, string mode, string backendUrl, int tripId, string question)
    {
        if (mode is not ("mcp" or "rag"))
            throw new LoopException("Validation mode must be mcp or rag.");
        if (!Uri.TryCreate(backendUrl, UriKind.Absolute, out var backend)
            || backend.Scheme != "http" || !backend.IsLoopback
            || backend.AbsolutePath != "/" || backend.UserInfo.Length != 0
            || backend.Query.Length != 0 || backend.Fragment.Length != 0)
            throw new LoopException("Validation requires a loopback HTTP backend origin without credentials or a path.");
        if (tripId <= 0 || string.IsNullOrWhiteSpace(question) || question.Length > 1000)
            throw new LoopException("Use a positive trip ID and a question of 1-1000 characters.");

        var path = mode == "mcp" ? $"/api/trips/{tripId}/mcp-summary" : "/api/itinerary-advice";
        using var deadline = new CancellationTokenSource(TimeSpan.FromSeconds(35));
        using var request = new HttpRequestMessage(HttpMethod.Post, new Uri(backend, path))
        {
            Content = mode == "rag" ? JsonContent.Create(new { question }) : JsonContent.Create(new { })
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
        var passed = response.IsSuccessStatusCode && IsValid(mode, body, tripId);
        var result = JsonSerializer.Serialize(new
        {
            mode, capturedAt = DateTimeOffset.UtcNow, endpoint = request.RequestUri,
            statusCode = (int)response.StatusCode, contractPassed = passed,
            response = body,
            limitation = "Contract checks do not prove claim entailment, protocol discovery, or browser behavior. Review cited sources and capture those checks separately."
        });
        return new TestEvidence($"POST {request.RequestUri}", result);
    }

    internal static bool IsValid(string mode, string body, int tripId)
    {
        try
        {
            using var document = JsonDocument.Parse(body);
            var root = document.RootElement;
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
}
using System.Net.Http.Json;
using System.Globalization;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;

namespace AgenticLoop;

internal static class ServiceValidation
{
    private static readonly HashSet<string> Student1Tools = ["accommodation.find", "accommodation.get_search"];

    internal static string DefaultBackendUrl(string feature) => feature switch
    {
        "student-1" => "http://127.0.0.1:5201",
        "student-3" => "http://127.0.0.1:5203",
        _ => "http://127.0.0.1:5202"
    };

    internal static string DefaultQuestion(string feature, string mode) => (feature, mode) switch
    {
        ("student-1", "mcp") => "Find stays in Tokyo for 2 guests under $200",
        ("student-1", _) => "Is Tokyo safe for families?",
        // Student 3's mcp validation invokes attractions.search directly (see
        // CaptureAsync) rather than routing a natural-language question through
        // an assistant endpoint like student-1 does, so this value is unused
        // for ("student-3", "mcp") - kept only so the switch stays exhaustive
        // and DefaultQuestion never returns null for a supported feature.
        ("student-3", "mcp") => "attractions.search {category: restaurant}",
        ("student-3", _) => "Is Chin Chin busy? Do I need to book?",
        ("student-2", "mcp") => "Add a Coffee break to day 1",
        _ => "Is budget the total for the trip?"
    };

    internal static async Task<TestEvidence> CaptureAsync(
        HttpClient client, string mode, string backendUrl, int tripId, string question, string feature = "student-2")
    {
        if (mode is not ("mcp" or "rag"))
            throw new LoopException("Validation mode must be mcp or rag.");
        if (feature is not ("student-1" or "student-2" or "student-3"))
            throw new LoopException("Validation feature must be student-1, student-2, or student-3.");
        if (!Uri.TryCreate(backendUrl, UriKind.Absolute, out var backend)
            || backend.Scheme != "http" || !backend.IsLoopback
            || backend.AbsolutePath != "/" || backend.UserInfo.Length != 0
            || backend.Query.Length != 0 || backend.Fragment.Length != 0)
            throw new LoopException("Validation requires a loopback HTTP backend origin without credentials or a path.");
        if (tripId <= 0 || string.IsNullOrWhiteSpace(question) || question.Length > 1000)
            throw new LoopException("Use a positive trip ID and a question of 1-1000 characters.");

        var path = feature switch
        {
            "student-1" => "/api/assistant",
            // Student 3 has its own direct-invoke MCP/RAG routes (Stage 2),
            // unlike student-1's single natural-language assistant endpoint or
            // student-2's trip-scoped edit-preview/itinerary-advice routes.
            "student-3" => mode == "mcp" ? "/api/mcp/invoke" : "/api/rag/ask",
            _ => mode == "mcp" ? $"/api/trips/{tripId}/edit-preview" : "/api/itinerary-advice"
        };
        using var deadline = new CancellationTokenSource(TimeSpan.FromSeconds(feature == "student-2" && mode == "rag" ? 55 : 35));
        using var request = new HttpRequestMessage(HttpMethod.Post, new Uri(backend, path))
        {
            Content = feature == "student-1" ? JsonContent.Create(new { mode = mode == "mcp" ? "lookup" : "guide", question })
                // The handoff's fixed Student 3 mcp case: attractions.search
                // filtered to category=restaurant, via the backend's allow-listed
                // {tool, arguments} invoke contract rather than a bare POST body.
                : feature == "student-3" && mode == "mcp"
                    ? JsonContent.Create(new { tool = "attractions.search", arguments = new { category = "restaurant" } })
                : feature == "student-2" && mode == "rag" ? JsonContent.Create(new { question, tripId })
                : JsonContent.Create(new { question })
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
        if (feature == "student-2" && mode == "mcp")
        {
            try
            {
                var captured = JsonNode.Parse(body);
                if (captured is JsonObject envelope && envelope["preview"] is JsonObject preview)
                    preview.Remove("token");
                body = captured?.ToJsonString() ?? "null";
            }
            catch (JsonException) { body = "Invalid JSON preview response omitted."; }
        }
        var result = JsonSerializer.Serialize(new
        {
            feature, mode, capturedAt = DateTimeOffset.UtcNow, endpoint = request.RequestUri,
            statusCode = (int)response.StatusCode, contractPassed = passed,
            response = body,
            limitation = "Contract checks do not prove intent, claim entailment, protocol discovery, confirmation/undo, or browser behavior. Preview tokens are omitted; no edit is confirmed. Review cited sources and capture those checks separately."
        });
        return new TestEvidence($"POST {request.RequestUri}", result);
    }

    internal static bool IsValid(string mode, string body, int tripId, string feature = "student-2")
    {
        try
        {
            using var document = JsonDocument.Parse(body);
            var root = document.RootElement;
            if (feature == "student-3")
                return mode == "mcp" ? IsValidStudent3Mcp(root) : IsValidStudent3Rag(root);
            if (feature == "student-1" && mode == "mcp")
                return IsValidStudent1Lookup(root);
            if (feature == "student-1" && root.GetProperty("mode").GetString() != "guide")
                return false;
            if (mode == "mcp")
                return IsValidStudent2Preview(root, tripId);
            if (mode != "rag") return false;
            if (feature == "student-2" && (root.GetProperty("tripId").GetInt32() != tripId
                || !HasText(root, "contextNotice", 1000))) return false;
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
    // The attractions.search allow-listed call this file hardcodes must be
    // filtered to category=restaurant (the request body sent above), so a
    // passing contract check also confirms the tool actually applied that
    // filter rather than returning every attraction.
    private static bool IsValidStudent3Mcp(JsonElement root)
    {
        if (root.GetProperty("tool").GetString() != "attractions.search") return false;
        var result = root.GetProperty("result");
        var attractions = result.GetProperty("attractions").EnumerateArray().ToArray();
        var totalMatches = result.GetProperty("total_matches").GetInt32();
        return totalMatches >= attractions.Length
            && attractions.All(attraction =>
                attraction.GetProperty("id").GetInt32() > 0
                && !string.IsNullOrWhiteSpace(attraction.GetProperty("name").GetString())
                && attraction.GetProperty("category").GetString() == "restaurant");
    }

    // Unlike the shared rag block below (reused by student-1's guide mode and
    // student-2), Student 3's RAG contract treats "insufficient" as a valid,
    // correct outcome for an unanswerable question, not a failure - so this
    // cannot reuse that block, which explicitly rejects "insufficient".
    private static bool IsValidStudent3Rag(JsonElement root)
    {
        var confidence = root.GetProperty("confidence").GetString();
        var answer = root.GetProperty("answer").GetString();
        var citations = root.GetProperty("citations").EnumerateArray().ToArray();
        if (confidence == "insufficient")
            return citations.Length == 0
                && answer == "Not enough information in the knowledge base to answer this.";
        if (confidence is not ("high" or "medium" or "low") || string.IsNullOrWhiteSpace(answer)
            || answer.Length > 2000 || citations.Length is < 1 or > 3) return false;
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

    private static bool HasText(JsonElement value, string name, int maximum, bool allowEmpty = false)
    {
        var text = value.GetProperty(name).GetString();
        return text is not null && text.Length <= maximum && (allowEmpty || !string.IsNullOrWhiteSpace(text));
    }

    private static bool IsValidStudent2Preview(JsonElement root, int tripId)
    {
        var preview = root.GetProperty("preview");
        if (root.GetProperty("tool").GetString() != "itinerary.preview_edit"
            || root.GetProperty("tripId").GetInt32() != tripId
            || root.GetProperty("clarification").GetString() != ""
            || preview.GetProperty("tripId").GetInt32() != tripId
            || preview.GetProperty("expiresIn").GetInt32() != 600
            || !HasText(preview, "token", 4096)) return false;
        var changes = preview.GetProperty("changes").EnumerateArray().ToArray();
        if (changes.Length is < 1 or > 200) return false;
        var identifiers = new HashSet<int>();
        foreach (var change in changes)
        {
            if (change.TryGetProperty("kind", out var kind) && kind.GetString() == "shift_dates")
            {
                var names = new[] { "fromStartDate", "fromEndDate", "toStartDate", "toEndDate" };
                var dates = new List<DateOnly>();
                foreach (var name in names)
                {
                    if (!DateOnly.TryParseExact(change.GetProperty(name).GetString(), "yyyy-MM-dd",
                        CultureInfo.InvariantCulture, DateTimeStyles.None, out var date)) return false;
                    dates.Add(date);
                }
                return changes.Length == 1 && dates[1].DayNumber - dates[0].DayNumber is >= 0 and <= 30
                    && dates[1].DayNumber - dates[0].DayNumber == dates[3].DayNumber - dates[2].DayNumber
                    && dates[0] != dates[2];
            }
            var identifier = change.GetProperty("id").GetInt32();
            if (!identifiers.Add(identifier)) return false;
            if (kind.ValueKind == JsonValueKind.Undefined)
            {
                if (identifier <= 0 || !HasText(change, "activity", 160) || !HasText(change, "notes", 1000, true)
                    || change.GetProperty("fromDay").GetInt32() is < 1 or > 31
                    || change.GetProperty("toDay").GetInt32() is < 1 or > 31
                    || change.GetProperty("fromOrder").GetInt32() < 0
                    || change.GetProperty("toOrder").GetInt32() < 0) return false;
                continue;
            }
            var action = kind.GetString();
            if (action is not ("add_stop" or "remove_stop" or "update_stop") || identifier < 0
                || (identifier == 0 && action != "add_stop")) return false;
            var before = change.GetProperty("before");
            var after = change.GetProperty("after");
            if ((before.ValueKind == JsonValueKind.Null) != (action == "add_stop")
                || (after.ValueKind == JsonValueKind.Null) != (action == "remove_stop")) return false;
            foreach (var stop in new[] { before, after }.Where(stop => stop.ValueKind != JsonValueKind.Null))
            {
                if (stop.GetProperty("id").GetInt32() != identifier || stop.GetProperty("day").GetInt32() is < 1 or > 31
                    || stop.GetProperty("sortOrder").GetInt32() < 0 || !HasText(stop, "activity", 160)
                    || !HasText(stop, "notes", 1000, true)) return false;
            }
            if (action == "update_stop" && (before.GetProperty("day").GetInt32() != after.GetProperty("day").GetInt32()
                || before.GetProperty("sortOrder").GetInt32() != after.GetProperty("sortOrder").GetInt32()
                || (before.GetProperty("activity").GetString() == after.GetProperty("activity").GetString()
                    && before.GetProperty("notes").GetString() == after.GetProperty("notes").GetString()))) return false;
        }
        return true;
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
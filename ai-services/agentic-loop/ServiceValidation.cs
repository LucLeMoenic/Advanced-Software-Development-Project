using System.Net.Http.Json;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;

namespace AgenticLoop;

internal static class ServiceValidation
{
    private static readonly HashSet<string> Student1Tools = ["accommodation.find", "accommodation.get_search"];
    private static readonly HashSet<string> Student4Categories = ["accommodation", "food", "transport", "activities", "shopping", "other"];
    private static readonly HashSet<string> Student4Currencies = ["AUD", "USD", "EUR", "GBP", "NZD", "CAD", "SGD"];
    private static readonly IReadOnlyDictionary<string, string> Student4RagSources = new Dictionary<string, string>(StringComparer.Ordinal)
    {
        ["category-budgets#1"] = "Category budgets and spending statuses",
        ["category-budgets#2"] = "Category budgets and spending statuses",
        ["expense-conversion#1"] = "Expense entry and conversion snapshots",
        ["expense-conversion#2"] = "Expense entry and conversion snapshots",
        ["budgeting-workflow#1"] = "Practical budgeting workflow in the tracker",
        ["budgeting-workflow#2"] = "Practical budgeting workflow in the tracker"
    };
    private const long MaxSafeInteger = 9_007_199_254_740_991;

    internal static string DefaultBackendUrl(string feature) => feature switch
    {
        "student-1" => "http://127.0.0.1:5201",
        "student-3" => "http://127.0.0.1:5203",
        "student-4" => "http://127.0.0.1:5204",
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
        ("student-4", _) => "What does the 80% category budget warning mean?",
        _ => "Is budget the total for the trip?"
    };

    internal static async Task<TestEvidence> CaptureAsync(
        HttpClient client, string mode, string backendUrl, int tripId, string question,
        string feature = "student-2", string? journeyLabel = null)
    {
        if (mode is not ("mcp" or "rag"))
            throw new LoopException("Validation mode must be mcp or rag.");
        if (feature is not ("student-1" or "student-2" or "student-3" or "student-4"))
            throw new LoopException("Validation feature must be student-1, student-2, student-3, or student-4.");
        if (!Uri.TryCreate(backendUrl, UriKind.Absolute, out var backend)
            || backend.Scheme != "http" || !backend.IsLoopback
            || backend.AbsolutePath != "/" || backend.UserInfo.Length != 0
            || backend.Query.Length != 0 || backend.Fragment.Length != 0)
            throw new LoopException("Validation requires a loopback HTTP backend origin without credentials or a path.");
        var student4Mcp = feature == "student-4" && mode == "mcp";
        if (student4Mcp ? !IsValidJourneyLabel(journeyLabel)
            : journeyLabel is not null || tripId <= 0 || string.IsNullOrWhiteSpace(question) || question.Length > 1000)
        {
            throw new LoopException(student4Mcp
                ? "Use a journey label of 1-80 characters for Student 4 MCP validation."
                : "Use a positive trip ID and a question of 1-1000 characters.");
        }

        var path = feature switch
        {
            "student-1" => "/api/assistant",
            // Student 3 has its own direct-invoke MCP/RAG routes (Stage 2),
            // unlike student-1's single natural-language assistant endpoint or
            // student-2's trip-scoped mcp-summary/itinerary-advice routes.
            "student-3" => mode == "mcp" ? "/api/mcp/invoke" : "/api/rag/ask",
            "student-4" => mode == "mcp" ? "/api/budget-check" : "/api/budget-guidance",
            _ => mode == "mcp" ? $"/api/trips/{tripId}/mcp-summary" : "/api/itinerary-advice"
        };
        using var deadline = new CancellationTokenSource(TimeSpan.FromSeconds(35));
        using var request = new HttpRequestMessage(HttpMethod.Post, new Uri(backend, path))
        {
            Content = student4Mcp ? JsonContent.Create(new { journeyLabel })
                : feature == "student-1" ? JsonContent.Create(new { mode = mode == "mcp" ? "lookup" : "guide", question })
                // The handoff's fixed Student 3 mcp case: attractions.search
                // filtered to category=restaurant, via the backend's allow-listed
                // {tool, arguments} invoke contract rather than a bare POST body.
                : feature == "student-3" && mode == "mcp"
                    ? JsonContent.Create(new { tool = "attractions.search", arguments = new { category = "restaurant" } })
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
        var passed = response.IsSuccessStatusCode && IsValid(mode, body, tripId, feature, journeyLabel);
        var result = JsonSerializer.Serialize(new
        {
            feature, mode, capturedAt = DateTimeOffset.UtcNow, endpoint = request.RequestUri,
            statusCode = (int)response.StatusCode, contractPassed = passed,
            response = body,
            limitation = "Contract checks do not prove claim entailment, protocol discovery, or browser behavior. Review cited sources and capture those checks separately."
        });
        return new TestEvidence($"POST {request.RequestUri}", result);
    }

    internal static bool IsValid(
        string mode, string body, int tripId, string feature = "student-2", string? journeyLabel = null)
    {
        try
        {
            using var document = JsonDocument.Parse(body);
            var root = document.RootElement;
            if (feature == "student-3")
                return mode == "mcp" ? IsValidStudent3Mcp(root) : IsValidStudent3Rag(root);
            if (feature == "student-4")
                return mode == "mcp" ? IsValidStudent4Mcp(root, journeyLabel) : IsValidStudent4Rag(root);
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
            or InvalidOperationException or FormatException or OverflowException or ArgumentOutOfRangeException)
        {
            return false;
        }
    }

    private static bool IsValidStudent4Mcp(JsonElement root, string? requestedLabel)
    {
        if (!IsValidJourneyLabel(requestedLabel)
            || !HasExactProperties(root, "tool", "result")
            || root.GetProperty("tool").GetString() != "budget.get_summary")
        {
            return false;
        }

        var result = root.GetProperty("result");
        if (!HasExactProperties(result, "ok", "summary") || !result.GetProperty("ok").GetBoolean())
            return false;

        var summary = result.GetProperty("summary");
        if (!HasExactProperties(summary,
                "journeyLabel", "baseCurrency", "plannedAmountMinor", "actualAmountMinor",
                "remainingAmountMinor", "percentageUsed", "categories"))
        {
            return false;
        }

        var journeyLabel = summary.GetProperty("journeyLabel").GetString();
        var currency = summary.GetProperty("baseCurrency").GetString();
        if (!string.Equals(journeyLabel, requestedLabel, StringComparison.OrdinalIgnoreCase)
            || currency is null || !Student4Currencies.Contains(currency))
        {
            return false;
        }

        var planned = ReadMinor(summary, "plannedAmountMinor");
        var actual = ReadMinor(summary, "actualAmountMinor");
        var remaining = ReadMinor(summary, "remainingAmountMinor");
        var percentage = ReadPercentage(summary, "percentageUsed");
        if (planned <= 0 || actual < 0 || remaining != planned - actual
            || percentage != Percentage(actual, planned))
        {
            return false;
        }

        var categories = summary.GetProperty("categories");
        if (categories.ValueKind != JsonValueKind.Array || categories.GetArrayLength() is < 1 or > 6)
            return false;

        var names = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        long plannedSum = 0;
        long actualSum = 0;
        long remainingSum = 0;
        foreach (var category in categories.EnumerateArray())
        {
            if (!HasExactProperties(category,
                    "category", "plannedAmountMinor", "actualAmountMinor", "remainingAmountMinor", "percentageUsed", "status"))
            {
                return false;
            }

            var name = category.GetProperty("category").GetString();
            var categoryPlanned = ReadMinor(category, "plannedAmountMinor");
            var categoryActual = ReadMinor(category, "actualAmountMinor");
            var categoryRemaining = ReadMinor(category, "remainingAmountMinor");
            var categoryPercentage = ReadPercentage(category, "percentageUsed");
            var status = category.GetProperty("status").GetString();
            if (name is null || !Student4Categories.Contains(name) || !names.Add(name)
                || categoryPlanned <= 0 || categoryActual < 0
                || categoryRemaining != categoryPlanned - categoryActual
                || categoryPercentage != Percentage(categoryActual, categoryPlanned)
                || status != BudgetStatus(categoryActual, categoryPlanned))
            {
                return false;
            }

            plannedSum = checked(plannedSum + categoryPlanned);
            actualSum = checked(actualSum + categoryActual);
            remainingSum = checked(remainingSum + categoryRemaining);
        }

        return plannedSum == planned && actualSum == actual && remainingSum == remaining;
    }

    private static bool IsValidStudent4Rag(JsonElement root)
    {
        if (!HasExactProperties(root, "answer", "citations", "confidence")) return false;
        var answer = root.GetProperty("answer").GetString();
        var confidence = root.GetProperty("confidence").GetString();
        var citations = root.GetProperty("citations");
        if (string.IsNullOrWhiteSpace(answer) || answer.Length > 2000
            || answer.Contains('<') || answer.Contains('>') || answer.Contains('\0')
            || confidence is not ("high" or "medium" or "low")
            || citations.ValueKind != JsonValueKind.Array || citations.GetArrayLength() is < 1 or > 3)
        {
            return false;
        }

        var identifiers = new HashSet<string>(StringComparer.Ordinal);
        var minimumScore = 1d;
        foreach (var citation in citations.EnumerateArray())
        {
            if (!HasExactProperties(citation, "source", "chunkId", "snippet", "score")) return false;
            var source = citation.GetProperty("source").GetString();
            var identifier = citation.GetProperty("chunkId").GetString();
            var snippet = citation.GetProperty("snippet").GetString();
            var scoreValue = citation.GetProperty("score");
            if (string.IsNullOrWhiteSpace(identifier) || identifier.Length > 160
                || string.IsNullOrWhiteSpace(snippet) || snippet.Length > 280
                || !Student4RagSources.TryGetValue(identifier, out var expectedSource) || source != expectedSource
                || !identifiers.Add(identifier) || !answer.Contains($"[{identifier}]", StringComparison.Ordinal)
                || scoreValue.ValueKind != JsonValueKind.Number || !scoreValue.TryGetDouble(out var score)
                || !double.IsFinite(score) || score < 0.15 || score > 1)
            {
                return false;
            }

            minimumScore = Math.Min(minimumScore, score);
        }

        var markers = Regex.Matches(answer, @"\[([A-Za-z0-9_-]+#\d+)\]");
        var markerIds = markers.Select(match => match.Groups[1].Value).ToHashSet(StringComparer.Ordinal);
        var withoutMarkers = Regex.Replace(answer, @"\[([A-Za-z0-9_-]+#\d+)\]", string.Empty);
        if (withoutMarkers.Contains('[') || withoutMarkers.Contains(']') || !markerIds.SetEquals(identifiers)) return false;

        return confidence switch
        {
            "low" => minimumScore < 0.30005,
            "medium" => minimumScore >= 0.29995 && minimumScore < 0.40005,
            "high" => minimumScore >= 0.39995,
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

    private static long ReadMinor(JsonElement value, string property)
    {
        var field = value.GetProperty(property);
        if (field.ValueKind != JsonValueKind.Number || !field.TryGetInt64(out var amount)
            || amount is < -MaxSafeInteger or > MaxSafeInteger)
        {
            throw new FormatException("Budget amount is outside the safe integer range.");
        }

        return amount;
    }

    private static decimal ReadPercentage(JsonElement value, string property)
    {
        var field = value.GetProperty(property);
        if (field.ValueKind != JsonValueKind.Number || !field.TryGetDecimal(out var percentage)
            || percentage < 0 || percentage > (decimal)MaxSafeInteger)
        {
            throw new FormatException("Budget percentage is invalid.");
        }

        return percentage;
    }

    private static decimal Percentage(long actual, long planned) =>
        Math.Round(actual * 100m / planned, 2, MidpointRounding.AwayFromZero);

    private static string BudgetStatus(long actual, long planned)
    {
        var ratio = actual * 100m / planned;
        return ratio > 100m ? "overspent" : ratio >= 80m ? "warning" : "within_budget";
    }

    private static bool IsValidJourneyLabel(string? value) =>
        !string.IsNullOrWhiteSpace(value) && value == value.Trim()
        && value.EnumerateRunes().Count() is >= 1 and <= 80;
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
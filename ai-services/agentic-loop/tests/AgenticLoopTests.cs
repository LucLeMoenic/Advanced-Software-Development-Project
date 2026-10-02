using AgenticLoop;
using System.Text.Json;
using System.Text.Json.Nodes;
using Xunit;

namespace AgenticLoop.Tests;

public sealed class AgenticLoopTests
{
    [Fact]
    public void WorkspaceResolution_FindsRepositoryFromProjectWorkingDirectory()
    {
        var workspace = CreateTemporaryDirectory();
        try
        {
            var projectDirectory = Path.Combine(workspace, "ai-services", "agentic-loop");
            Directory.CreateDirectory(projectDirectory);
            File.WriteAllText(Path.Combine(projectDirectory, "AgenticLoop.csproj"), "<Project />");
            Assert.Equal(workspace, AgenticLoopApplication.ResolveWorkspace(null, projectDirectory));
            Assert.Equal(workspace, AgenticLoopApplication.ResolveWorkspace(workspace, projectDirectory));
        }
        finally { Directory.Delete(workspace, true); }
    }

    [Fact]
    public async Task DocumentedValidationContexts_FitSafetyLimits()
    {
        var workspace = AgenticLoopApplication.ResolveWorkspace(null, AppContext.BaseDirectory);
        var context = await AgenticLoopApplication.LoadContextAsync(workspace,
            ["ai-services/mcp-server/tools/itinerary.py", "ai-services/rag-server/knowledge/student-2/budget-basics.md"]);
        Assert.Equal(2, context.Paths.Count);
        var student1 = await AgenticLoopApplication.LoadContextAsync(workspace,
            ["ai-services/mcp-server/tools/accommodation.py", "student-1/backend/Prompts/assistant-lookup-v1.txt"]);
        Assert.Equal(2, student1.Paths.Count);
        var student1Guide = await AgenticLoopApplication.LoadContextAsync(workspace,
            ["ai-services/rag-server/knowledge/student-1/tokyo.md"]);
        Assert.Single(student1Guide.Paths);
        var student4Mcp = await AgenticLoopApplication.LoadContextAsync(workspace,
            ["ai-services/mcp-server/tools/budget.py", "student-4/backend/Api/BudgetCheckEndpoints.cs"]);
        Assert.Equal(2, student4Mcp.Paths.Count);
        var student4Rag = await AgenticLoopApplication.LoadContextAsync(workspace,
            ["ai-services/rag-server/knowledge/student-4/category-budgets.md", "student-4/backend/Api/BudgetGuidanceEndpoints.cs"]);
        Assert.Equal(2, student4Rag.Paths.Count);
    }

    [Fact]
    public void ValidationModes_CheckStructuredResultsAndRejectInsufficientAsGroundedSuccess()
    {
        Assert.False(ServiceValidation.IsValid("mcp", """
            {"tool":"itinerary.get_summary","summary":{"tripId":10,"dayCount":2,"plannedDayCount":1,"stopCount":2,"unplannedDays":[2]}}
            """, 10));
        Assert.False(ServiceValidation.IsValid("mcp", "{}", 10));
        Assert.False(ServiceValidation.IsValid("rag", """
            {"answer":"Not enough information","citations":[],"confidence":"insufficient"}
            """, 10));
        Assert.True(ServiceValidation.IsValid("rag", """
            {"tripId":10,"contextNotice":"Advice used 2 saved stops.","answer":"Budget is total. [budget#1]","confidence":"high","citations":[{"source":"Budget","chunk_id":"budget#1","snippet":"Budget is total.","score":0.5}]}
            """, 10));
    }

    [Theory]
    [InlineData("https://example.org")]
    [InlineData("http://127.0.0.1:5202/api/trips")]
    [InlineData("http://user:password@localhost:5202")]
    public async Task ValidationModes_RejectNonlocalOrNonoriginUrls(string url)
    {
        using var client = new HttpClient();
        await Assert.ThrowsAsync<LoopException>(() => ServiceValidation.CaptureAsync(client, "mcp", url, 10, "budget"));
    }

    private static JsonObject Student2Preview(string kind = "add_stop")
    {
        var before = new { id = 12, day = 1, activity = "Walk", notes = "Morning", sortOrder = 0 };
        object change = kind switch
        {
            "add_stop" => new { kind, id = 0, before = (object?)null, after = new { id = 0, day = 1, activity = "Coffee break", notes = "", sortOrder = 1 } },
            "remove_stop" => new { kind, id = 12, before, after = (object?)null },
            "update_stop" => new { kind, id = 12, before, after = new { id = 12, day = 1, activity = "Walk", notes = "Bring tickets", sortOrder = 0 } },
            "shift_dates" => new { kind, fromStartDate = "2026-11-01", fromEndDate = "2026-11-02", toStartDate = "2027-06-01", toEndDate = "2027-06-02" },
            _ => new { id = 12, activity = "Walk", notes = "Morning", fromDay = 1, toDay = 2, fromOrder = 0, toOrder = 1 }
        };
        return JsonSerializer.SerializeToNode(new
        {
            tripId = 10, tool = "itinerary.preview_edit", clarification = "",
            preview = new { tripId = 10, token = "private-confirmation-token", expiresIn = 600, changes = new[] { change } }
        })!.AsObject();
    }

    [Theory]
    [InlineData("add_stop")]
    [InlineData("remove_stop")]
    [InlineData("update_stop")]
    [InlineData("shift_dates")]
    [InlineData("move_stop")]
    public void Student2PreviewValidation_AcceptsCurrentChangeShapes(string kind)
    {
        Assert.True(ServiceValidation.IsValid("mcp", Student2Preview(kind).ToJsonString(), 10));
    }

    [Theory]
    [InlineData("trip")]
    [InlineData("preview-trip")]
    [InlineData("token")]
    [InlineData("expiry")]
    [InlineData("clarification")]
    [InlineData("empty")]
    [InlineData("duplicate")]
    [InlineData("unknown-kind")]
    [InlineData("wrong-id")]
    [InlineData("wrong-day")]
    [InlineData("null-after")]
    [InlineData("unchanged-update")]
    [InlineData("moved-update")]
    [InlineData("duration")]
    [InlineData("invalid-date")]
    public void Student2PreviewValidation_RejectsMalformedChanges(string defect)
    {
        var root = Student2Preview(defect.Contains("update") ? "update_stop"
            : defect is "duration" or "invalid-date" ? "shift_dates" : "add_stop");
        var preview = root["preview"]!.AsObject();
        var changes = preview["changes"]!.AsArray();
        var change = changes[0]!.AsObject();
        switch (defect)
        {
            case "trip": root["tripId"] = 11; break;
            case "preview-trip": preview["tripId"] = 11; break;
            case "token": preview["token"] = ""; break;
            case "expiry": preview["expiresIn"] = 3600; break;
            case "clarification": root["clarification"] = "Which day?"; break;
            case "empty": changes.Clear(); break;
            case "duplicate": changes.Add(change.DeepClone()); break;
            case "unknown-kind": change["kind"] = "delete_trip"; break;
            case "wrong-id": change["after"]!["id"] = 44; break;
            case "wrong-day": change["after"]!["day"] = 32; break;
            case "null-after": change["after"] = null; break;
            case "unchanged-update": change["after"] = change["before"]!.DeepClone(); break;
            case "moved-update": change["after"]!["day"] = 2; break;
            case "duration": change["toEndDate"] = "2027-06-03"; break;
            case "invalid-date": change["toStartDate"] = "2027-02-30"; break;
        }
        Assert.False(ServiceValidation.IsValid("mcp", root.ToJsonString(), 10));
    }

    [Fact]
    public async Task Student2Validation_PostsOnlyPreviewAndRedactsConfirmationToken()
    {
        var handler = new RecordingHandler(Student2Preview().ToJsonString());
        using var client = new HttpClient(handler);
        var question = ServiceValidation.DefaultQuestion("student-2", "mcp");
        var evidence = await ServiceValidation.CaptureAsync(client, "mcp", "http://127.0.0.1:5202", 10, question);
        Assert.Equal("http://127.0.0.1:5202/api/trips/10/edit-preview", handler.Uri);
        Assert.Equal(JsonSerializer.Serialize(new { question }), handler.Body);
        using var result = JsonDocument.Parse(evidence.Result);
        Assert.True(result.RootElement.GetProperty("contractPassed").GetBoolean());
        Assert.DoesNotContain("private-confirmation-token", evidence.Result);
        using var captured = JsonDocument.Parse(result.RootElement.GetProperty("response").GetString()!);
        Assert.False(captured.RootElement.GetProperty("preview").TryGetProperty("token", out _));
        Assert.Equal(1, captured.RootElement.GetProperty("preview").GetProperty("changes").GetArrayLength());
    }

    [Fact]
    public async Task Student2GuideValidation_PostsSelectedTripAndRejectsOtherTripResponses()
    {
        const string body = """
            {"tripId":10,"contextNotice":"Advice used 2 saved stops.","answer":"Budget is total. [budget#1]","confidence":"high","citations":[{"source":"Budget","chunk_id":"budget#1","snippet":"Budget is total.","score":0.5}]}
            """;
        var handler = new RecordingHandler(body);
        using var client = new HttpClient(handler);
        var evidence = await ServiceValidation.CaptureAsync(client, "rag", "http://127.0.0.1:5202", 10, "Budget?");
        Assert.Equal("http://127.0.0.1:5202/api/itinerary-advice", handler.Uri);
        Assert.Equal("""{"question":"Budget?","tripId":10}""", handler.Body);
        using var result = JsonDocument.Parse(evidence.Result);
        Assert.True(result.RootElement.GetProperty("contractPassed").GetBoolean());
        Assert.False(ServiceValidation.IsValid("rag", body, 11));
        var missingContext = JsonNode.Parse(body)!.AsObject();
        missingContext.Remove("contextNotice");
        Assert.False(ServiceValidation.IsValid("rag", missingContext.ToJsonString(), 10));
    }

    [Fact]
    public void Student1LookupValidation_ChecksAllowListedToolAndResultShape()
    {
        Assert.True(ServiceValidation.IsValid("mcp", """
            {"mode":"lookup","tool":"accommodation.find","arguments":{"destination":"Tokyo","guests":2},"result":{"ok":true,"count":1,"accommodations":[{"id":55,"name":"Lodge","destination":"Tokyo","nightlyPrice":145,"maxGuests":4,"amenities":["Free WiFi"]}]}}
            """, 1, "student-1"));
        Assert.True(ServiceValidation.IsValid("mcp", """
            {"mode":"lookup","tool":"accommodation.get_search","arguments":{"search_id":11},"result":{"ok":true,"search":{"id":11,"title":"Tokyo","results":[{"rank":1},{"rank":2}]}}}
            """, 1, "student-1"));
        Assert.False(ServiceValidation.IsValid("mcp", """
            {"mode":"lookup","tool":"itinerary.get_summary","arguments":{},"result":{"ok":true}}
            """, 1, "student-1"));
        Assert.False(ServiceValidation.IsValid("mcp", """
            {"mode":"lookup","tool":"accommodation.find","arguments":{"destination":"Tokyo"},"result":{"ok":true,"count":2,"accommodations":[]}}
            """, 1, "student-1"));
        Assert.False(ServiceValidation.IsValid("mcp", """
            {"mode":"lookup","tool":"accommodation.find","arguments":{"destination":"Tokyo"},"result":{"ok":true,"count":1,"accommodations":[{"id":1,"name":"X","destination":"Paris","nightlyPrice":1,"maxGuests":2,"amenities":[]}]}}
            """, 1, "student-1"));
        Assert.False(ServiceValidation.IsValid("mcp", """
            {"mode":"lookup","tool":"accommodation.get_search","arguments":{"search_id":11},"result":{"ok":true,"search":{"id":12,"title":"T","results":[]}}}
            """, 1, "student-1"));
        Assert.False(ServiceValidation.IsValid("mcp", """
            {"error":{"code":"lookup_not_understood","message":"Please rephrase"}}
            """, 1, "student-1"));
        Assert.False(ServiceValidation.IsValid("mcp", """
            {"tool":"itinerary.get_summary","summary":{"tripId":10,"dayCount":2,"plannedDayCount":1,"stopCount":2,"unplannedDays":[2]}}
            """, 10, "student-1"));
    }

    [Fact]
    public async Task Student1Validation_PostsLookupQuestionToAssistantEndpoint()
    {
        var handler = new RecordingHandler("""
            {"mode":"lookup","tool":"accommodation.find","arguments":{"destination":"Tokyo"},"result":{"ok":true,"count":0,"accommodations":[]}}
            """);
        using var client = new HttpClient(handler);

        var evidence = await ServiceValidation.CaptureAsync(
            client, "mcp", "http://127.0.0.1:5201", 1, "Stays in Tokyo", "student-1");

        Assert.Equal("http://127.0.0.1:5201/api/assistant", handler.Uri);
        Assert.Equal("""{"mode":"lookup","question":"Stays in Tokyo"}""", handler.Body);
        using var result = JsonDocument.Parse(evidence.Result);
        Assert.True(result.RootElement.GetProperty("contractPassed").GetBoolean());
        Assert.Equal("student-1", result.RootElement.GetProperty("feature").GetString());
        Assert.Equal("http://127.0.0.1:5201", ServiceValidation.DefaultBackendUrl("student-1"));
        Assert.Equal("http://127.0.0.1:5202", ServiceValidation.DefaultBackendUrl("student-2"));
    }

    [Fact]
    public void Student4McpArguments_RequireJourneyLabelAndRejectTripOptions()
    {
        var options = AgenticLoopApplication.ParseValidationOptions(
            ParsedArguments.Parse(["--feature", "student-4", "--journey-label", "Sydney Weekender"]),
            "mcp");

        Assert.Equal("student-4", options.Feature);
        Assert.Equal("http://127.0.0.1:5204", options.BackendUrl);
        Assert.Equal("Sydney Weekender", options.JourneyLabel);
        Assert.Equal("What does the 80% category budget warning mean?", options.Question);
        Assert.Throws<LoopException>(() => AgenticLoopApplication.ParseValidationOptions(
            ParsedArguments.Parse(["--feature", "student-4"]), "mcp"));
        Assert.Throws<LoopException>(() => AgenticLoopApplication.ParseValidationOptions(
            ParsedArguments.Parse(["--feature", "student-4", "--journey-label", "Sydney Weekender", "--trip-id", "10"]), "mcp"));
        Assert.Throws<LoopException>(() => AgenticLoopApplication.ParseValidationOptions(
            ParsedArguments.Parse(["--feature", "student-1", "--journey-label", "Sydney Weekender"]), "mcp"));
        Assert.Throws<LoopException>(() => AgenticLoopApplication.ParseValidationOptions(
            ParsedArguments.Parse(["--feature", "student-4", "--question", "budget?", "--journey-label", "Sydney Weekender"]), "mcp"));
        Assert.Throws<LoopException>(() => AgenticLoopApplication.ParseValidationOptions(
            ParsedArguments.Parse(["--feature", "student-4", "--journey-label", "Sydney Weekender"]), "rag"));
        Assert.Throws<LoopException>(() => AgenticLoopApplication.ParseValidationOptions(
            ParsedArguments.Parse(["--feature", "student-4", "--trip-id", "10"]), "rag"));
    }

    [Fact]
    public async Task Student1GuideValidation_ReusesRagContractAndRejectsInsufficient()
    {
        const string grounded = """
            {"mode":"guide","answer":"Tokyo is very safe. [tokyo#3]","citations":[{"source":"Tokyo — Where to Stay","chunk_id":"tokyo#3","snippet":"Tokyo safety: safe.","score":0.46}],"confidence":"high"}
            """;
        Assert.True(ServiceValidation.IsValid("rag", grounded, 1, "student-1"));
        Assert.False(ServiceValidation.IsValid("rag", """
            {"mode":"guide","answer":"Not enough information in the knowledge base to answer this.","citations":[],"confidence":"insufficient"}
            """, 1, "student-1"));
        Assert.False(ServiceValidation.IsValid("rag", """
            {"mode":"lookup","answer":"Tokyo is very safe. [tokyo#3]","citations":[{"source":"T","chunk_id":"tokyo#3","snippet":"s","score":0.46}],"confidence":"high"}
            """, 1, "student-1"));
        Assert.False(ServiceValidation.IsValid("rag", """
            {"mode":"guide","answer":"Tokyo is very safe.","citations":[{"source":"T","chunk_id":"tokyo#3","snippet":"s","score":0.46}],"confidence":"high"}
            """, 1, "student-1"));

        var handler = new RecordingHandler(grounded);
        using var client = new HttpClient(handler);
        var evidence = await ServiceValidation.CaptureAsync(client, "rag", "http://127.0.0.1:5201", 1, "Is Tokyo safe?", "student-1");

        Assert.Equal("http://127.0.0.1:5201/api/assistant", handler.Uri);
        Assert.Equal("""{"mode":"guide","question":"Is Tokyo safe?"}""", handler.Body);
        using var result = JsonDocument.Parse(evidence.Result);
        Assert.True(result.RootElement.GetProperty("contractPassed").GetBoolean());
        Assert.Equal("Is Tokyo safe for families?", ServiceValidation.DefaultQuestion("student-1", "rag"));
        Assert.Equal("Is budget the total for the trip?", ServiceValidation.DefaultQuestion("student-2", "rag"));
    }

    [Theory]
    [InlineData("student-6", "mcp")]
    [InlineData("student-6", "rag")]
    public async Task ValidationModes_RejectUnsupportedFeatureFixtures(string feature, string mode)
    {
        using var client = new HttpClient(new RecordingHandler("{}"));
        await Assert.ThrowsAsync<LoopException>(() =>
            ServiceValidation.CaptureAsync(client, mode, "http://127.0.0.1:5201", 1, "Tokyo", feature));
    }

    [Fact]
    public async Task Student4McpValidation_PostsRequestedJourneyAndChecksAuthoritativeSummary()
    {
        var response = BudgetCheckResponse("Sydney Weekender", 10000, 8000, 80, "warning");
        var handler = new RecordingHandler(response);
        using var client = new HttpClient(handler);

        var evidence = await ServiceValidation.CaptureAsync(
            client, "mcp", "http://127.0.0.1:5204", 1, "unused", "student-4", "Sydney Weekender");

        Assert.Equal("http://127.0.0.1:5204/api/budget-check", handler.Uri);
        Assert.Equal("""{"journeyLabel":"Sydney Weekender"}""", handler.Body);
        using var result = JsonDocument.Parse(evidence.Result);
        Assert.True(result.RootElement.GetProperty("contractPassed").GetBoolean());
        Assert.Equal("http://127.0.0.1:5204", ServiceValidation.DefaultBackendUrl("student-4"));
    }

    [Theory]
    [InlineData(7999, 79.99, "within_budget")]
    [InlineData(8000, 80, "warning")]
    [InlineData(10000, 100, "warning")]
    [InlineData(10001, 100.01, "overspent")]
    public void Student4McpValidation_EnforcesBudgetStatusBoundaries(int actualMinor, double percentage, string status)
    {
        var response = BudgetCheckResponse("Sydney Weekender", 10000, actualMinor, percentage, status);

        Assert.True(ServiceValidation.IsValid("mcp", response, 1, "student-4", "Sydney Weekender"));
    }

    [Theory]
    [InlineData("{\"tool\":\"budget.get_summary\",\"result\":{\"ok\":false,\"error\":{\"code\":\"not_found\"}}}")]
    [InlineData("{\"tool\":\"budget.get_summary\",\"result\":{\"ok\":true,\"summary\":{\"journeyLabel\":\"Other Journey\"}}}")]
    [InlineData("{\"tool\":\"other.tool\",\"result\":{\"ok\":true,\"summary\":{}}}")]
    [InlineData("not-json")]
    public void Student4McpValidation_RejectsErrorsMismatchesAndMalformedResults(string response)
    {
        Assert.False(ServiceValidation.IsValid("mcp", response, 1, "student-4", "Sydney Weekender"));
    }

    [Fact]
    public void Student4McpValidation_RejectsInconsistentCategoryStatus()
    {
        var response = BudgetCheckResponse("Sydney Weekender", 10000, 8000, 80, "overspent");

        Assert.False(ServiceValidation.IsValid("mcp", response, 1, "student-4", "Sydney Weekender"));
    }

    [Fact]
    public void Student4RagValidation_RequiresGroundedAnswerAndStudent4CitationContract()
    {
        Assert.True(ServiceValidation.IsValid("rag", """
            {"answer":"At 80% of a category budget, the application shows a warning. [category-budgets#1]","citations":[{"source":"Category budgets and spending statuses","chunkId":"category-budgets#1","snippet":"From 80 percent through exactly 100 percent is warning.","score":0.35}],"confidence":"medium"}
            """, 1, "student-4"));
        Assert.False(ServiceValidation.IsValid("rag", """
            {"answer":"Not enough information in the knowledge base to answer this.","citations":[],"confidence":"insufficient"}
            """, 1, "student-4"));
        Assert.False(ServiceValidation.IsValid("rag", """
            {"answer":"At 80% the application warns. [category-budgets#1]","citations":[{"source":"Category budgets and spending statuses","chunk_id":"category-budgets#1","snippet":"80% to 100% is a warning.","score":0.35}],"confidence":"medium"}
            """, 1, "student-4"));
    }

    [Fact]
    public async Task Student4Validation_UsesBudgetDefaultsAndEnforcesJourneyLabelLength()
    {
        const string grounded = """
            {"answer":"At 80% of a category budget, the application shows a warning. [category-budgets#1]","citations":[{"source":"Category budgets and spending statuses","chunkId":"category-budgets#1","snippet":"From 80 percent through exactly 100 percent is warning.","score":0.35}],"confidence":"medium"}
            """;
        var ragHandler = new RecordingHandler(grounded);
        using var ragClient = new HttpClient(ragHandler);
        var ragEvidence = await ServiceValidation.CaptureAsync(
            ragClient, "rag", "http://127.0.0.1:5204", 1,
            ServiceValidation.DefaultQuestion("student-4", "rag"), "student-4");

        Assert.Equal("http://127.0.0.1:5204/api/budget-guidance", ragHandler.Uri);
        Assert.Equal("""{"question":"What does the 80% category budget warning mean?"}""", ragHandler.Body);
        Assert.True(JsonDocument.Parse(ragEvidence.Result).RootElement.GetProperty("contractPassed").GetBoolean());
        Assert.Equal("What does the 80% category budget warning mean?", ServiceValidation.DefaultQuestion("student-4", "rag"));

        var label = new string('A', 80);
        using var validClient = new HttpClient(new RecordingHandler("{}"));
        await ServiceValidation.CaptureAsync(validClient, "mcp", "http://127.0.0.1:5204", 1, "unused", "student-4", label);

        using var invalidClient = new HttpClient(new RecordingHandler("{}"));
        await Assert.ThrowsAsync<LoopException>(() => ServiceValidation.CaptureAsync(
            invalidClient, "mcp", "http://127.0.0.1:5204", 1, "unused", "student-4", label + "A"));
        using var missingClient = new HttpClient(new RecordingHandler("{}"));
        await Assert.ThrowsAsync<LoopException>(() => ServiceValidation.CaptureAsync(
            missingClient, "mcp", "http://127.0.0.1:5204", 1, "unused", "student-4", " "));
    }

    [Fact]
    public void Student3SearchValidation_ChecksToolNameAndCategoryFilterApplied()
    {
        Assert.True(ServiceValidation.IsValid("mcp", """
            {"tool":"attractions.search","result":{"attractions":[{"id":3,"name":"Mr. Wong","category":"restaurant","description":"d","rating":4.6}],"total_matches":1}}
            """, 1, "student-3"));
        Assert.True(ServiceValidation.IsValid("mcp", """
            {"tool":"attractions.search","result":{"attractions":[],"total_matches":0}}
            """, 1, "student-3"));
        Assert.False(ServiceValidation.IsValid("mcp", """
            {"tool":"attractions.get_reviews","result":{"attractions":[],"total_matches":0}}
            """, 1, "student-3"));
        Assert.False(ServiceValidation.IsValid("mcp", """
            {"tool":"attractions.search","result":{"attractions":[{"id":1,"name":"Opera House","category":"sight","description":"d","rating":4.7}],"total_matches":1}}
            """, 1, "student-3"));
        Assert.False(ServiceValidation.IsValid("mcp", """
            {"tool":"attractions.search","result":{"attractions":[{"id":1,"name":"X","category":"restaurant","description":"d","rating":4}],"total_matches":0}}
            """, 1, "student-3"));
        Assert.False(ServiceValidation.IsValid("mcp", """{"error":"mcp_disabled","message":"MCP is disabled."}""", 1, "student-3"));
    }

    [Fact]
    public void Student3RagValidation_AcceptsInsufficientAsAValidOutcomeNotAFailure()
    {
        const string grounded = """
            {"answer":"Chin Chin is busy on weekends. [melbourne-attractions-overview#3]","citations":[{"source":"Melbourne Attractions Overview","chunk_id":"melbourne-attractions-overview#3","snippet":"Chin Chin is busy.","score":0.35}],"confidence":"medium"}
            """;
        const string insufficient = """
            {"answer":"Not enough information in the knowledge base to answer this.","citations":[],"confidence":"insufficient"}
            """;
        Assert.True(ServiceValidation.IsValid("rag", grounded, 1, "student-3"));
        Assert.True(ServiceValidation.IsValid("rag", insufficient, 1, "student-3"));
        // An "insufficient" verdict must still have no citations and the exact
        // fixed sentence - a model can't claim abstention while also citing
        // sources or answering with something else.
        Assert.False(ServiceValidation.IsValid("rag", """
            {"answer":"Not enough information in the knowledge base to answer this.","citations":[{"source":"S","chunk_id":"s#1","snippet":"s","score":0.2}],"confidence":"insufficient"}
            """, 1, "student-3"));
        Assert.False(ServiceValidation.IsValid("rag", """
            {"answer":"Maybe, I'm not sure.","citations":[],"confidence":"insufficient"}
            """, 1, "student-3"));
        Assert.False(ServiceValidation.IsValid("rag", """
            {"answer":"Chin Chin is busy.","citations":[{"source":"S","chunk_id":"s#1","snippet":"s","score":0.35}],"confidence":"medium"}
            """, 1, "student-3"));
    }

    [Fact]
    public async Task Student3McpValidation_PostsAttractionsSearchInvokeToBackend()
    {
        var handler = new RecordingHandler("""
            {"tool":"attractions.search","result":{"attractions":[],"total_matches":0}}
            """);
        using var client = new HttpClient(handler);

        var evidence = await ServiceValidation.CaptureAsync(
            client, "mcp", "http://127.0.0.1:5203", 1, "unused", "student-3");

        Assert.Equal("http://127.0.0.1:5203/api/mcp/invoke", handler.Uri);
        Assert.Equal("""{"tool":"attractions.search","arguments":{"category":"restaurant"}}""", handler.Body);
        using var result = JsonDocument.Parse(evidence.Result);
        Assert.True(result.RootElement.GetProperty("contractPassed").GetBoolean());
        Assert.Equal("student-3", result.RootElement.GetProperty("feature").GetString());
        Assert.Equal("http://127.0.0.1:5203", ServiceValidation.DefaultBackendUrl("student-3"));
    }

    [Fact]
    public async Task Student3RagValidation_PostsQuestionToRagAskEndpoint()
    {
        const string grounded = """
            {"answer":"Chin Chin is busy. [melbourne-attractions-overview#3]","citations":[{"source":"Melbourne Attractions Overview","chunk_id":"melbourne-attractions-overview#3","snippet":"Busy.","score":0.35}],"confidence":"medium"}
            """;
        var handler = new RecordingHandler(grounded);
        using var client = new HttpClient(handler);

        var evidence = await ServiceValidation.CaptureAsync(
            client, "rag", "http://127.0.0.1:5203", 1, "Is Chin Chin busy?", "student-3");

        Assert.Equal("http://127.0.0.1:5203/api/rag/ask", handler.Uri);
        Assert.Equal("""{"question":"Is Chin Chin busy?"}""", handler.Body);
        using var result = JsonDocument.Parse(evidence.Result);
        Assert.True(result.RootElement.GetProperty("contractPassed").GetBoolean());
        Assert.Equal("Is Chin Chin busy? Do I need to book?", ServiceValidation.DefaultQuestion("student-3", "rag"));
    }

    private const string Student5Visa = """
        {"tool":"logistics.check_visa_requirement","result":{"ok":true,"destination":{"id":1,"country":"Japan","visa_requirement":"visa-free","notes":null},"official_source_reminder":"General guidance only. Confirm entry requirements with Smartraveller and the destination's official immigration authority before booking."}}
        """;

    [Fact]
    public void Student5VisaValidation_ChecksToolDestinationAndOfficialSourceReminder()
    {
        Assert.True(ServiceValidation.IsValid("mcp", Student5Visa, 1, "student-5"));
        Assert.False(ServiceValidation.IsValid("mcp", Student5Visa.Replace("check_visa_requirement", "get_weather"), 1, "student-5"));
        Assert.False(ServiceValidation.IsValid("mcp", Student5Visa.Replace("\"id\":1", "\"id\":2"), 1, "student-5"));
        Assert.False(ServiceValidation.IsValid("mcp", Student5Visa.Replace("Smartraveller", "a travel agent"), 1, "student-5"));
        Assert.False(ServiceValidation.IsValid("mcp", Student5Visa.Replace("\"visa-free\"", "\"  \""), 1, "student-5"));
        Assert.False(ServiceValidation.IsValid("mcp", """
            {"tool":"logistics.check_visa_requirement","result":{"ok":false,"error":{"code":"destination_not_found","message":"Destination not found."}}}
            """, 1, "student-5"));
        Assert.False(ServiceValidation.IsValid("mcp", """{"error":"mcp_disabled","message":"MCP is disabled."}""", 1, "student-5"));
    }

    [Fact]
    public void Student5RagValidation_AcceptsGroundedOrExactInsufficientAnswers()
    {
        const string grounded = """
            {"answer":"An eVisa is approved online before travel. [visa-categories#3]","citations":[{"source":"Visa Categories","chunk_id":"visa-categories#3","snippet":"An eVisa is applied for online.","score":0.38}],"confidence":"medium"}
            """;
        Assert.True(ServiceValidation.IsValid("rag", grounded, 1, "student-5"));
        Assert.True(ServiceValidation.IsValid("rag", """
            {"answer":"Not enough information in the knowledge base to answer this.","citations":[],"confidence":"insufficient"}
            """, 1, "student-5"));
        Assert.False(ServiceValidation.IsValid("rag", grounded.Replace(" [visa-categories#3]", ""), 1, "student-5"));
        Assert.False(ServiceValidation.IsValid("rag", """
            {"answer":"Probably fine.","citations":[],"confidence":"insufficient"}
            """, 1, "student-5"));
        Assert.False(ServiceValidation.IsValid("rag", """{"error":"rag_disabled","message":"RAG is disabled."}""", 1, "student-5"));
    }

    [Fact]
    public async Task Student5McpValidation_PostsFixedVisaInvokeToBackend()
    {
        var handler = new RecordingHandler(Student5Visa);
        using var client = new HttpClient(handler);

        var evidence = await ServiceValidation.CaptureAsync(
            client, "mcp", "http://127.0.0.1:5205", 1, "unused", "student-5");

        Assert.Equal("http://127.0.0.1:5205/api/mcp/invoke", handler.Uri);
        Assert.Equal("""{"tool":"logistics.check_visa_requirement","arguments":{"destination_id":1}}""", handler.Body);
        using var result = JsonDocument.Parse(evidence.Result);
        Assert.True(result.RootElement.GetProperty("contractPassed").GetBoolean());
        Assert.Equal("student-5", result.RootElement.GetProperty("feature").GetString());
        Assert.Equal("http://127.0.0.1:5205", ServiceValidation.DefaultBackendUrl("student-5"));
    }

    [Fact]
    public async Task Student5RagValidation_PostsQuestionToRagAskEndpoint()
    {
        var handler = new RecordingHandler("""
            {"answer":"Not enough information in the knowledge base to answer this.","citations":[],"confidence":"insufficient"}
            """);
        using var client = new HttpClient(handler);

        var evidence = await ServiceValidation.CaptureAsync(
            client, "rag", "http://127.0.0.1:5205", 1, "What is the capital of France?", "student-5");

        Assert.Equal("http://127.0.0.1:5205/api/rag/ask", handler.Uri);
        Assert.Equal("""{"question":"What is the capital of France?"}""", handler.Body);
        using var result = JsonDocument.Parse(evidence.Result);
        Assert.True(result.RootElement.GetProperty("contractPassed").GetBoolean());
        Assert.Equal("What is the difference between visa on arrival and an eVisa?",
            ServiceValidation.DefaultQuestion("student-5", "rag"));
    }

    [Fact]
    public void ValidateRunInput_RejectsEqualModels()
    {
        var exception = Assert.Throws<LoopException>(() =>
            AgenticLoopApplication.ValidateRunInput(
                "Implement one change.",
                ["context.md"],
                "same-model",
                "same-model"));

        Assert.Contains("must be different", exception.Message);
    }

    [Fact]
    public void ValidateRunInput_RejectsAliasesForSameModel()
    {
        var exception = Assert.Throws<LoopException>(() =>
            AgenticLoopApplication.ValidateRunInput(
                "Implement one change.",
                ["context.md"],
                "same-model",
                "same-model:latest"));

        Assert.Contains("must be different", exception.Message);
    }

    [Fact]
    public async Task LoadContextAsync_RejectsPathOutsideWorkspace()
    {
        var workspace = CreateTemporaryDirectory();
        try
        {
            var exception = await Assert.ThrowsAsync<LoopException>(() =>
                AgenticLoopApplication.LoadContextAsync(workspace, ["../outside.txt"]));

            Assert.Contains("escapes the workspace", exception.Message);
        }
        finally
        {
            Directory.Delete(workspace, true);
        }
    }

    [Fact]
    public async Task LoadContextAsync_RejectsSensitiveFile()
    {
        var workspace = CreateTemporaryDirectory();
        try
        {
            await File.WriteAllTextAsync(Path.Combine(workspace, ".env"), "TOKEN=secret");

            var exception = await Assert.ThrowsAsync<LoopException>(() =>
                AgenticLoopApplication.LoadContextAsync(workspace, [".env"]));

            Assert.Contains("Sensitive context path", exception.Message);
        }
        finally
        {
            Directory.Delete(workspace, true);
        }
    }

    [Fact]
    public async Task LoadContextAsync_LoadsAllowListedUtf8File()
    {
        var workspace = CreateTemporaryDirectory();
        try
        {
            await File.WriteAllTextAsync(Path.Combine(workspace, "context.md"), "requirement");

            var context = await AgenticLoopApplication.LoadContextAsync(
                workspace,
                ["context.md"]);

            Assert.Equal(["context.md"], context.Paths);
            Assert.Contains("requirement", context.Content);
        }
        finally
        {
            Directory.Delete(workspace, true);
        }
    }

    [Fact]
    public async Task LoadContextAsync_RejectsInvalidUtf8()
    {
        var workspace = CreateTemporaryDirectory();
        try
        {
            await File.WriteAllBytesAsync(
                Path.Combine(workspace, "context.md"),
                [0xC3, 0x28]);

            var exception = await Assert.ThrowsAsync<LoopException>(() =>
                AgenticLoopApplication.LoadContextAsync(workspace, ["context.md"]));

            Assert.Contains("not valid UTF-8", exception.Message);
        }
        finally
        {
            Directory.Delete(workspace, true);
        }
    }

    [Fact]
    public async Task LoadContextAsync_RejectsSecretLikeContentInAllowedFile()
    {
        var workspace = CreateTemporaryDirectory();
        try
        {
            await File.WriteAllTextAsync(
                Path.Combine(workspace, "context.md"),
                "api_key = \"actual-secret-value\"");

            var exception = await Assert.ThrowsAsync<LoopException>(() =>
                AgenticLoopApplication.LoadContextAsync(workspace, ["context.md"]));

            Assert.Contains("Secret-like context content", exception.Message);
        }
        finally
        {
            Directory.Delete(workspace, true);
        }
    }

    [Theory]
    [InlineData("TOKEN=actualSecretValue123")]
    [InlineData("const apiKey = \"actual-secret-value\";")]
    [InlineData("Authorization: Bearer abcdefghijklmnopqrstuvwxyz")]
    [InlineData("Server=db;Password=actual-secret-value;Database=app")]
    [InlineData("github_pat_abcdefghijklmnopqrstuvwxyz123456")]
    public async Task LoadContextAsync_RejectsCommonCredentialContent(string content)
    {
        var workspace = CreateTemporaryDirectory();
        try
        {
            await File.WriteAllTextAsync(Path.Combine(workspace, "context.md"), content);

            await Assert.ThrowsAsync<LoopException>(() =>
                AgenticLoopApplication.LoadContextAsync(workspace, ["context.md"]));
        }
        finally
        {
            Directory.Delete(workspace, true);
        }
    }

    [Fact]
    public async Task LoadContextAsync_AllowsCredentialPlaceholders()
    {
        var workspace = CreateTemporaryDirectory();
        try
        {
            await File.WriteAllTextAsync(
                Path.Combine(workspace, "context.md"),
                "API_KEY=<redacted>");

            var context = await AgenticLoopApplication.LoadContextAsync(
                workspace,
                ["context.md"]);

            Assert.Contains("API_KEY=<redacted>", context.Content);
        }
        finally
        {
            Directory.Delete(workspace, true);
        }
    }

    [Fact]
    public async Task LoadContextAsync_RejectsSensitiveSymbolicLinkTarget()
    {
        var workspace = CreateTemporaryDirectory();
        try
        {
            var target = Path.Combine(workspace, ".env");
            var link = Path.Combine(workspace, "context.md");
            await File.WriteAllTextAsync(target, "TOKEN=actualSecretValue123");
            File.CreateSymbolicLink(link, target);

            var exception = await Assert.ThrowsAsync<LoopException>(() =>
                AgenticLoopApplication.LoadContextAsync(workspace, ["context.md"]));

            Assert.Contains("Sensitive context path", exception.Message);
        }
        finally
        {
            Directory.Delete(workspace, true);
        }
    }

    [Fact]
    public async Task LoadContextAsync_RejectsBinaryOrDisallowedFile()
    {
        var workspace = CreateTemporaryDirectory();
        try
        {
            await File.WriteAllBytesAsync(
                Path.Combine(workspace, "binary.txt"),
                [65, 0, 66]);
            await File.WriteAllTextAsync(Path.Combine(workspace, "script.exe"), "not executable");

            var binaryException = await Assert.ThrowsAsync<LoopException>(() =>
                AgenticLoopApplication.LoadContextAsync(workspace, ["binary.txt"]));
            var typeException = await Assert.ThrowsAsync<LoopException>(() =>
                AgenticLoopApplication.LoadContextAsync(workspace, ["script.exe"]));

            Assert.Contains("Binary context", binaryException.Message);
            Assert.Contains("file type is not allowed", typeException.Message);
        }
        finally
        {
            Directory.Delete(workspace, true);
        }
    }

    [Theory]
    [InlineData("ACCEPT")]
    [InlineData("revise")]
    [InlineData("REJECT")]
    public void ParseVerdict_ReturnsStructuredVerdict(string verdict)
    {
        Assert.Equal(
            verdict.ToUpperInvariant(),
            AgenticLoopApplication.ParseVerdict(ReviewerResponse(verdict)));
    }

    [Fact]
    public void ParseVerdict_RejectsObserveSectionWithoutVerdict()
    {
        var exception = Assert.Throws<LoopException>(() =>
            AgenticLoopApplication.ParseVerdict("[OBSERVE]\nNo decision"));

        Assert.Contains("exactly one", exception.Message);
    }

    [Fact]
    public void ParseVerdict_RejectsTemplateEchoOrMultipleVerdicts()
    {
        var exception = Assert.Throws<LoopException>(() =>
            AgenticLoopApplication.ParseVerdict(
                "[OBSERVE]\nVerdict: ACCEPT | REVISE | REJECT\nVerdict: ACCEPT\nVerdict: REJECT"));

        Assert.Contains("exactly one", exception.Message);
    }

    [Fact]
    public void ParseVerdict_RejectsNestedRequiredHeadings()
    {
        var exception = Assert.Throws<LoopException>(() => AgenticLoopApplication.ParseVerdict(
            """
            [OBSERVE]
            Verdict: ACCEPT

            - Findings:
              - None

            Validation gaps:
            - None

            - Scope check:
              The proposal stays in scope.
            """));

        Assert.Contains("Findings:", exception.Message);
    }

    [Fact]
    public void ParseVerdict_RejectsSeverityEnumEcho()
    {
        var exception = Assert.Throws<LoopException>(() => AgenticLoopApplication.ParseVerdict(
            """
            [OBSERVE]
            Verdict: REVISE

            Findings:
            - Severity: BLOCKING | REQUIRED | SUGGESTION
              Evidence: The route does not validate the request.
              Failure mode: Invalid journeys reach the backend.
              Required correction: Add request validation.

            Validation gaps:
            - None

            Scope check:
            The proposal stays in scope.
            """));

        Assert.Contains("valid Severity", exception.Message);
    }

    [Fact]
    public async Task ReviewerPrompt_UsesConcreteStandaloneHeadingsWithoutPlaceholderEnums()
    {
        var workspace = AgenticLoopApplication.ResolveWorkspace(null, AppContext.BaseDirectory);
        var prompt = await File.ReadAllTextAsync(
            Path.Combine(workspace, "ai-services", "agentic-loop", "prompts", "reviewer.md"));
        var normalizedPrompt = prompt.Replace("\r\n", "\n", StringComparison.Ordinal);

        Assert.Contains("Each heading below must start at the first", normalizedPrompt);
        Assert.Contains("[OBSERVE]\nVerdict: ACCEPT", normalizedPrompt);
        Assert.DoesNotContain("Verdict: ACCEPT | REVISE | REJECT", normalizedPrompt);
        Assert.DoesNotContain("Severity: BLOCKING | REQUIRED | SUGGESTION", normalizedPrompt);
    }

    [Fact]
    public void ParseVerdict_RejectsMissingReviewSections()
    {
        var exception = Assert.Throws<LoopException>(() =>
            AgenticLoopApplication.ParseVerdict(
                "[OBSERVE]\nVerdict: ACCEPT\nFindings:\n- None"));

        Assert.Contains("Validation gaps:", exception.Message);
    }

    [Fact]
    public void ParseVerdict_RejectsSectionsOutsideObserve()
    {
        var exception = Assert.Throws<LoopException>(() =>
            AgenticLoopApplication.ParseVerdict(
                """
                Findings:
                - None
                Validation gaps:
                - None
                Scope check:
                aligned
                [OBSERVE]
                Verdict: ACCEPT
                """));

        Assert.Contains("Findings:", exception.Message);
    }

    [Theory]
    [InlineData("- Severity: REQUIRED")]
    [InlineData("Severity: REQUIRED")]
    public void ParseVerdict_RejectsAcceptWithRequiredFinding(string severityLine)
    {
        var review = ReviewerResponse("ACCEPT", includeRequiredFinding: true)
            .Replace("- Severity: REQUIRED", severityLine, StringComparison.Ordinal);

        var exception = Assert.Throws<LoopException>(() =>
            AgenticLoopApplication.ParseVerdict(review));

        Assert.Contains("cannot ACCEPT", exception.Message);
    }

    [Fact]
    public void ValidateImplementerOutput_RejectsMissingPlanOrAct()
    {
        var exception = Assert.Throws<LoopException>(() =>
            AgenticLoopApplication.ValidateImplementerOutput("[ACT]\nProposal"));

        Assert.Contains("exactly one [PLAN] and one [ACT]", exception.Message);
    }

    [Fact]
    public async Task ExecuteLoopAsync_UsesReviewerAndProducesOneRevision()
    {
        var client = new FakeModelClient(
            [
                ImplementerResponse("Initial proposal"),
                ReviewerResponse("REVISE"),
                ImplementerResponse("Corrected proposal", "Revision"),
                ReviewerResponse("ACCEPT")
            ]);
        var input = CreateExecutionInput();

        var record = await AgenticLoopApplication.ExecuteLoopAsync(input, client);

        Assert.Equal("REVISE", record.ReviewerVerdict);
        Assert.Equal("Corrected proposal", record.AdaptedProposal?.Split('\n').Last());
        Assert.Equal("ACCEPT", record.FinalReviewerVerdict);
        Assert.Equal("shared-implementer-v1", record.PromptVersions?.Implementer);
        Assert.Equal("shared-reviewer-v1", record.PromptVersions?.Reviewer);
        Assert.Equal("qwen-implementer:latest", record.Models.Implementer);
        Assert.Equal("llama-reviewer:latest", record.Models.Reviewer);
        Assert.Collection(
            client.Calls,
            call => Assert.Equal("qwen-implementer:latest", call.Model),
            call => Assert.Equal("llama-reviewer:latest", call.Model),
            call => Assert.Equal("qwen-implementer:latest", call.Model),
            call => Assert.Equal("llama-reviewer:latest", call.Model));
        Assert.Contains("Initial proposal", client.Calls[1].Prompt);
        Assert.Contains("Address the stated requirement", client.Calls[2].Prompt);
        Assert.Contains("Corrected proposal", client.Calls[3].Prompt);
    }

    [Fact]
    public async Task ExecuteLoopAsync_StopsWhenRequiredModelIsMissing()
    {
        var client = new FakeModelClient([], ["qwen-implementer:latest"]);

        var exception = await Assert.ThrowsAsync<LoopException>(() =>
            AgenticLoopApplication.ExecuteLoopAsync(CreateExecutionInput(), client));

        Assert.Contains("llama-reviewer", exception.Message);
        Assert.Empty(client.Calls);
    }

    [Fact]
    public async Task ExecuteLoopAsync_AcceptVerdictDoesNotGenerateRevision()
    {
        var client = new FakeModelClient(
            [
                ImplementerResponse("Proposal"),
                ReviewerResponse("ACCEPT")
            ]);

        var record = await AgenticLoopApplication.ExecuteLoopAsync(
            CreateExecutionInput(),
            client);

        Assert.Equal("ACCEPT", record.FinalReviewerVerdict);
        Assert.Null(record.AdaptedProposal);
        Assert.Null(record.AdaptedProposalReview);
        Assert.Equal(2, client.Calls.Count);
    }

    [Fact]
    public async Task ExecuteLoopAsync_RetriesOneMalformedReviewerResponse()
    {
        var client = new FakeModelClient(
            [
                ImplementerResponse("Proposal"),
                "Verdict: ACCEPT",
                ReviewerResponse("ACCEPT")
            ]);

        var record = await AgenticLoopApplication.ExecuteLoopAsync(
            CreateExecutionInput(),
            client);

        Assert.Equal("ACCEPT", record.FinalReviewerVerdict);
        Assert.Equal(3, client.Calls.Count);
        Assert.Contains("FORMAT_CORRECTION_REQUIRED", client.Calls[2].Prompt);
        Assert.Contains("exactly one [OBSERVE] section", client.Calls[2].Prompt);
    }

    [Fact]
    public async Task FinaliseRecordAsync_StoresHumanDecisionAndPostTestOnce()
    {
        var directory = CreateTemporaryDirectory();
        try
        {
            var recordPath = Path.Combine(directory, "record.json");
            var record = await AgenticLoopApplication.ExecuteLoopAsync(
                CreateExecutionInput(),
                new FakeModelClient(
                    [
                        ImplementerResponse("Proposal"),
                        ReviewerResponse("ACCEPT")
                    ]));
            await File.WriteAllTextAsync(
                recordPath,
                System.Text.Json.JsonSerializer.Serialize(
                    record,
                    new System.Text.Json.JsonSerializerOptions(
                        System.Text.Json.JsonSerializerDefaults.Web)
                    {
                        WriteIndented = true
                    }));

            await AgenticLoopApplication.FinaliseRecordAsync(
                recordPath,
                "changed",
                "Applied the reviewed proposal.",
                "dotnet test",
                "All tests passed.");

            var json = await File.ReadAllTextAsync(recordPath);
            Assert.Contains("\"humanDecision\": \"changed\"", json);
            Assert.Contains("\"command\": \"dotnet test\"", json);
            await Assert.ThrowsAsync<LoopException>(() =>
                AgenticLoopApplication.FinaliseRecordAsync(
                    recordPath,
                    "kept",
                    "Duplicate finalisation.",
                    "dotnet test",
                    "Passed."));
        }
        finally
        {
            Directory.Delete(directory, true);
        }
    }

    [Fact]
    public async Task FinaliseRecordAsync_AcceptsSchemaOneRecordWithoutPromptVersions()
    {
        var directory = CreateTemporaryDirectory();
        try
        {
            var recordPath = Path.Combine(directory, "record.json");
            var record = await AgenticLoopApplication.ExecuteLoopAsync(
                CreateExecutionInput(),
                new FakeModelClient(
                    [
                        ImplementerResponse("Proposal"),
                        ReviewerResponse("ACCEPT")
                    ]));
            var json = JsonSerializer.SerializeToNode(
                record,
                new JsonSerializerOptions(JsonSerializerDefaults.Web))!.AsObject();
            json["schemaVersion"] = 1;
            json.Remove("promptVersions");
            await File.WriteAllTextAsync(recordPath, json.ToJsonString());

            await AgenticLoopApplication.FinaliseRecordAsync(
                recordPath,
                "kept",
                "Finalised a legacy pending record.",
                "dotnet test",
                "All tests passed.");

            var finalised = await File.ReadAllTextAsync(recordPath);
            Assert.Contains("\"schemaVersion\": 1", finalised);
            Assert.Contains("\"humanDecision\": \"kept\"", finalised);
        }
        finally
        {
            Directory.Delete(directory, true);
        }
    }

    private static LoopExecutionInput CreateExecutionInput()
    {
        return new LoopExecutionInput(
            "Implement one bounded change.",
            new LoadedContext(
                ["context.md"],
                new Dictionary<string, string> { ["context.md"] = "ABC123" },
                "FILE: context.md\nrequirement\nEND_FILE"),
            "qwen-implementer",
            "llama-reviewer",
            "/app/prompts/implementer.md",
            "/app/prompts/reviewer.md",
            "# Shared Implementer Prompt\n\nVersion: `shared-implementer-v1`",
            "# Shared Reviewer Prompt\n\nVersion: `shared-reviewer-v1`",
            "dotnet test",
            "All baseline tests passed.");
    }

    private static string ImplementerResponse(
        string proposedChange,
        string plan = "Implement the bounded change.")
    {
        return $"[PLAN]\n{plan}\n[ACT]\n{proposedChange}";
    }

    private static string ReviewerResponse(
        string verdict,
        bool includeRequiredFinding = false)
    {
        var findings = verdict.Equals("ACCEPT", StringComparison.OrdinalIgnoreCase)
            && !includeRequiredFinding
            ? "- None"
            : """
              - Severity: REQUIRED
                Evidence: context.md
                Failure mode: The proposal misses a requirement.
                Required correction: Address the stated requirement.
              """;

        return $"""
            [OBSERVE]
            Verdict: {verdict}

            Findings:
            {findings}

            Validation gaps:
            - None

            Scope check:
            aligned
            """;
    }

    private static string BudgetCheckResponse(string journeyLabel, long plannedMinor, long actualMinor, double percentage, string status)
    {
        var remainingMinor = plannedMinor - actualMinor;
        return JsonSerializer.Serialize(new
        {
            tool = "budget.get_summary",
            result = new
            {
                ok = true,
                summary = new
                {
                    journeyLabel,
                    baseCurrency = "AUD",
                    plannedAmountMinor = plannedMinor,
                    actualAmountMinor = actualMinor,
                    remainingAmountMinor = remainingMinor,
                    percentageUsed = percentage,
                    categories = new[]
                    {
                        new
                        {
                            category = "food",
                            plannedAmountMinor = plannedMinor,
                            actualAmountMinor = actualMinor,
                            remainingAmountMinor = remainingMinor,
                            percentageUsed = percentage,
                            status
                        }
                    }
                }
            }
        }, new JsonSerializerOptions(JsonSerializerDefaults.Web));
    }

    private static string CreateTemporaryDirectory()
    {
        var path = Path.Combine(Path.GetTempPath(), Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(path);
        return path;
    }

    private sealed class FakeModelClient : IModelClient
    {
        private readonly Queue<string> _responses;
        private readonly HashSet<string> _models;

        public FakeModelClient(
            IEnumerable<string> responses,
            IEnumerable<string>? models = null)
        {
            _responses = new Queue<string>(responses);
            _models = (models ?? ["qwen-implementer:latest", "llama-reviewer:latest"])
                .ToHashSet(StringComparer.Ordinal);
        }

        public List<ModelCall> Calls { get; } = [];

        public Task<HashSet<string>> GetAvailableModelsAsync()
        {
            return Task.FromResult(_models);
        }

        public Task<string> GetRuntimeVersionAsync()
        {
            return Task.FromResult("0.11.0-test");
        }

        public Task<string> GenerateAsync(string model, string prompt)
        {
            Calls.Add(new ModelCall(model, prompt));
            return Task.FromResult(_responses.Dequeue());
        }
    }

    private sealed record ModelCall(string Model, string Prompt);

    private sealed class RecordingHandler(string body) : HttpMessageHandler
    {
        public string? Uri { get; private set; }
        public string? Body { get; private set; }

        protected override async Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken)
        {
            Uri = request.RequestUri?.ToString();
            Body = request.Content is null ? null : await request.Content.ReadAsStringAsync(cancellationToken);
            return new HttpResponseMessage(System.Net.HttpStatusCode.OK) { Content = new StringContent(body) };
        }
    }
}

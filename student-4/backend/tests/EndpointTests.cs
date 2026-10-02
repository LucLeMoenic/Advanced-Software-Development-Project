using System.Net;
using System.Net.Http.Json;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using BudgetTracker.Backend.Api;
using BudgetTracker.Backend.Clients;
using BudgetTracker.Backend.Services;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.AspNetCore.TestHost;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;

namespace BudgetTracker.Backend.Tests;

public sealed class EndpointTests
{
    [Fact]
    public void McpEndpointUsesTheComposeConfigurationKey()
    {
        var configuration = new Dictionary<string, string?>
        {
            ["MCP_SERVER_URL"] = "http://host.docker.internal:5400/mcp"
        };
        using var factory = CreateFactory(new FakeDatabase(), new FakeAdvice(), configuration);

        var settings = factory.Services.GetRequiredService<McpBudgetCheckSettings>();

        Assert.Equal(new Uri("http://host.docker.internal:5400/mcp"), settings.Endpoint);
    }

    [Theory]
    [InlineData(false, false, false)]
    [InlineData(false, false, true)]
    [InlineData(false, true, false)]
    [InlineData(false, true, true)]
    [InlineData(true, false, false)]
    [InlineData(true, false, true)]
    [InlineData(true, true, false)]
    [InlineData(true, true, true)]
    public async Task CapabilitiesReportConfiguredModes(bool aiEnabled, bool mcpEnabled, bool ragEnabled)
    {
        var settings = new Dictionary<string, string?>
        {
            ["AI_ENABLED"] = aiEnabled ? "true" : "false",
            ["MCP_ENABLED"] = mcpEnabled ? "true" : "false",
            ["RAG_ENABLED"] = ragEnabled ? "true" : "false"
        };
        using var factory = CreateFactory(new FakeDatabase(), new FakeAdvice(), settings);
        using var client = factory.CreateClient();

        var response = await client.GetFromJsonAsync<CapabilitiesResponse>("/api/capabilities");

        Assert.Equal(new CapabilitiesResponse(aiEnabled, mcpEnabled, ragEnabled), response);
    }

    [Fact]
    public async Task CapabilitiesUseDocumentedDefaultsWhenFlagsAreMissing()
    {
        var settings = new Dictionary<string, string?>
        {
            ["AI_ENABLED"] = null,
            ["MCP_ENABLED"] = null,
            ["RAG_ENABLED"] = null
        };
        using var factory = CreateFactory(new FakeDatabase(), new FakeAdvice(), settings);
        using var client = factory.CreateClient();

        var response = await client.GetFromJsonAsync<CapabilitiesResponse>("/api/capabilities");

        Assert.Equal(new CapabilitiesResponse(true, false, false), response);
    }

    [Theory]
    [InlineData("AI_ENABLED")]
    [InlineData("MCP_ENABLED")]
    [InlineData("RAG_ENABLED")]
    public void InvalidModeFlagFailsApplicationStartup(string name)
    {
        var settings = new Dictionary<string, string?> { [name] = "True" };
        using var factory = CreateFactory(new FakeDatabase(), new FakeAdvice(), settings);

        var exception = Assert.ThrowsAny<Exception>(() => factory.CreateClient());

        Assert.Contains(name, exception.ToString(), StringComparison.Ordinal);
    }

    [Theory]
    [InlineData("AI_ENABLED", "true", true)]
    [InlineData("AI_ENABLED", "false", false)]
    [InlineData("MCP_ENABLED", "true", true)]
    [InlineData("MCP_ENABLED", "false", false)]
    [InlineData("RAG_ENABLED", "true", true)]
    [InlineData("RAG_ENABLED", "false", false)]
    public void ModeFlagsAcceptOnlyExactBooleanSpellings(string name, string value, bool expected)
    {
        var configuration = new ConfigurationBuilder()
            .AddInMemoryCollection(new Dictionary<string, string?> { [name] = value })
            .Build();

        var settings = FeatureModeSettings.FromConfiguration(configuration);

        Assert.Equal(expected, name switch
        {
            "AI_ENABLED" => settings.AiEnabled,
            "MCP_ENABLED" => settings.McpEnabled,
            _ => settings.RagEnabled
        });
    }

    [Theory]
    [InlineData("AI_ENABLED", "TRUE")]
    [InlineData("AI_ENABLED", "False")]
    [InlineData("AI_ENABLED", " true")]
    [InlineData("AI_ENABLED", "false ")]
    [InlineData("AI_ENABLED", "1")]
    [InlineData("AI_ENABLED", "")]
    [InlineData("MCP_ENABLED", "TRUE")]
    [InlineData("MCP_ENABLED", "False")]
    [InlineData("MCP_ENABLED", " true")]
    [InlineData("MCP_ENABLED", "false ")]
    [InlineData("MCP_ENABLED", "1")]
    [InlineData("MCP_ENABLED", "")]
    [InlineData("RAG_ENABLED", "TRUE")]
    [InlineData("RAG_ENABLED", "False")]
    [InlineData("RAG_ENABLED", " true")]
    [InlineData("RAG_ENABLED", "false ")]
    [InlineData("RAG_ENABLED", "1")]
    [InlineData("RAG_ENABLED", "")]
    public void ModeFlagsRejectNonCanonicalValues(string name, string value)
    {
        var configuration = new ConfigurationBuilder()
            .AddInMemoryCollection(new Dictionary<string, string?> { [name] = value })
            .Build();

        Assert.Throws<InvalidOperationException>(() => FeatureModeSettings.FromConfiguration(configuration));
    }

    [Fact]
    public async Task ValidationHappensBeforeDatabaseCalls()
    {
        var database = new FakeDatabase();
        using var client = CreateClient(database, new FakeAdvice());

        var response = await client.PostAsJsonAsync("/api/budgets", new BudgetWriteRequest(" ", "bad", 0, "JPY", new(2026, 9, 2), new(2026, 9, 1)));

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.Equal(0, database.CallCount);
        Assert.Equal("validation_error", (await response.Content.ReadFromJsonAsync<ApiErrorEnvelope>())!.Error.Code);
    }

    [Fact]
    public async Task OmittedDatesAreRejectedBeforeDatabaseCalls()
    {
        var database = new FakeDatabase();
        using var client = CreateClient(database, new FakeAdvice());

        var budget = await client.PostAsJsonAsync("/api/budgets", new
        {
            journeyLabel = "Missing Dates",
            category = "food",
            limitAmountMinor = 1000,
            baseCurrency = "AUD"
        });
        var expense = await client.PostAsJsonAsync("/api/expenses", new
        {
            budgetId = 1,
            description = "Missing date",
            originalAmountMinor = 100,
            originalCurrency = "AUD"
        });

        Assert.Equal(HttpStatusCode.BadRequest, budget.StatusCode);
        Assert.Equal(HttpStatusCode.BadRequest, expense.StatusCode);
        Assert.Equal(0, database.CallCount);
    }

    [Fact]
    public async Task BudgetCrudMapsThroughDatabaseBoundary()
    {
        var database = new FakeDatabase();
        using var client = CreateClient(database, new FakeAdvice());
        var request = new BudgetWriteRequest(" New Journey ", "FOOD", 20000, "aud", new(2026, 9, 1), new(2026, 9, 7));

        var create = await client.PostAsJsonAsync("/api/budgets", request);
        Assert.Equal(HttpStatusCode.Created, create.StatusCode);
        var budget = await create.Content.ReadFromJsonAsync<BudgetResponse>();
        Assert.Equal("New Journey", budget!.JourneyLabel);
        Assert.Equal("food", budget.Category);
        Assert.NotNull(await client.GetFromJsonAsync<BudgetResponse>($"/api/budgets/{budget.Id}"));
        Assert.Equal(HttpStatusCode.NoContent, (await client.DeleteAsync($"/api/budgets/{budget.Id}")).StatusCode);
    }

    [Fact]
    public async Task ExpenseSaveRecomputesAndReturnsConversionSnapshot()
    {
        var database = FakeDatabase.WithJourney();
        using var client = CreateClient(database, new FakeAdvice());

        var response = await client.PostAsJsonAsync("/api/expenses", new ExpenseWriteRequest(1, " Lunch ", 101, "usd", new(2026, 9, 2), null));

        Assert.Equal(HttpStatusCode.Created, response.StatusCode);
        var expense = await response.Content.ReadFromJsonAsync<ExpenseResponse>();
        Assert.Equal(155, expense!.ConvertedAmountMinor);
        Assert.Equal(153846154, expense.ConversionRateScaled);
        Assert.Equal("AUD", expense.BaseCurrency);
        Assert.Equal(155, database.LastExpenseRequest!.ConvertedAmountMinor);
    }

    [Fact]
    public async Task ClientSuppliedConvertedAmountIsRejected()
    {
        var database = FakeDatabase.WithJourney();
        using var client = CreateClient(database, new FakeAdvice());
        var response = await client.PostAsJsonAsync("/api/expenses", new { budgetId = 1, description = "Lunch", originalAmountMinor = 100, originalCurrency = "AUD", convertedAmountMinor = 1, spentOn = "2026-09-02" });
        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.Null(database.LastExpenseRequest);
    }

    [Fact]
    public async Task DashboardAndAdviceUseDeterministicData()
    {
        var database = FakeDatabase.WithJourney(actual: 9000);
        var advice = new FakeAdvice();
        using var client = CreateClient(database, advice);

        var dashboard = await client.GetFromJsonAsync<DashboardResponse>("/api/dashboard?journeyLabel=Journey");
        var result = await (await client.PostAsJsonAsync("/api/insights", new InsightRequest("Journey"))).Content.ReadFromJsonAsync<AdviceResponse>();

        Assert.Equal(90, dashboard!.PercentageUsed);
        Assert.Equal("warning", dashboard.Categories.Single().Status);
        Assert.Equal("ai", result!.Source);
        Assert.Equal(1, advice.CallCount);
    }

    [Fact]
    public async Task BudgetCheckCallsOnlyTheFixedToolAndReturnsValidatedSummary()
    {
        var mcp = new FakeBudgetCheck(ValidBudgetSummary());
        using var client = CreateBudgetCheckClient(mcp);

        using var response = await client.PostAsJsonAsync("/api/budget-check", new { journeyLabel = "  Journey  " });
        var body = await response.Content.ReadFromJsonAsync<BudgetCheckResponse>();

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.Equal("Journey", mcp.JourneyLabel);
        Assert.Equal("budget.get_summary", body!.Tool);
        Assert.True(body.Result.Ok);
        Assert.Equal(1000, body.Result.Summary.PlannedAmountMinor);
        Assert.Equal(1, mcp.CallCount);
    }

    [Fact]
    public async Task DisabledBudgetCheckDoesNotConnectToMcp()
    {
        var mcp = new FakeBudgetCheck(ValidBudgetSummary());
        using var client = CreateBudgetCheckClient(mcp, mcpEnabled: false);

        using var response = await client.PostAsJsonAsync("/api/budget-check", new { journeyLabel = "Journey" });
        var error = await response.Content.ReadFromJsonAsync<ApiErrorEnvelope>();

        Assert.Equal(HttpStatusCode.ServiceUnavailable, response.StatusCode);
        Assert.Equal("feature_disabled", error!.Error.Code);
        Assert.Equal(0, mcp.CallCount);
    }

    [Theory]
    [InlineData("{}")]
    [InlineData("{\"journeyLabel\":\"Journey\",\"url\":\"http://elsewhere\"}")]
    [InlineData("{\"journeyLabel\":\"Journey\",\"journeyLabel\":\"Other\"}")]
    [InlineData("{\"journeyLabel\":42}")]
    [InlineData("{\"journeyLabel\":\"   \"}")]
    [InlineData("{\"JourneyLabel\":\"Journey\"}")]
    public async Task BudgetCheckRejectsInvalidJsonContractsBeforeMcp(string json)
    {
        var mcp = new FakeBudgetCheck(ValidBudgetSummary());
        using var client = CreateBudgetCheckClient(mcp);

        using var response = await client.PostAsync("/api/budget-check", new StringContent(json, Encoding.UTF8, "application/json"));

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.Equal(0, mcp.CallCount);
    }

    [Fact]
    public async Task BudgetCheckRejectsOversizedRequestBeforeMcp()
    {
        var mcp = new FakeBudgetCheck(ValidBudgetSummary());
        using var client = CreateBudgetCheckClient(mcp);
        var json = "{\"journeyLabel\":\"" + new string('x', 8193) + "\"}";

        using var response = await client.PostAsync("/api/budget-check", new StringContent(json, Encoding.UTF8, "application/json"));

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.Equal(0, mcp.CallCount);
    }

    [Theory]
    [InlineData(HttpStatusCode.BadRequest, "validation_error")]
    [InlineData(HttpStatusCode.NotFound, "journey_not_found")]
    [InlineData(HttpStatusCode.ServiceUnavailable, "dependency_unavailable")]
    [InlineData(HttpStatusCode.GatewayTimeout, "dependency_timeout")]
    [InlineData(HttpStatusCode.BadGateway, "dependency_response_invalid")]
    public async Task BudgetCheckMapsStableMcpFailures(HttpStatusCode status, string expectedCode)
    {
        var mcp = new FakeBudgetCheck(ValidBudgetSummary()) { Failure = new BudgetCheckFailureException((int)status, expectedCode, "safe message") };
        using var client = CreateBudgetCheckClient(mcp);

        using var response = await client.PostAsJsonAsync("/api/budget-check", new { journeyLabel = "Journey" });
        var error = await response.Content.ReadFromJsonAsync<ApiErrorEnvelope>();

        Assert.Equal(status, response.StatusCode);
        Assert.Equal(expectedCode, error!.Error.Code);
        Assert.Equal("safe message", error.Error.Message);
    }

    [Theory]
    [InlineData("\"JPY\"", "baseCurrency")]
    [InlineData("\"Other\"", "journeyLabel")]
    [InlineData("true", "plannedAmountMinor")]
    [InlineData("9007199254740992", "plannedAmountMinor")]
    [InlineData("1001", "remainingAmountMinor")]
    [InlineData("\"secret\"", "unexpected")]
    public async Task BudgetCheckRejectsMalformedOrUnsafeSummaries(string replacement, string field)
    {
        var summary = ValidBudgetSummary();
        using var document = JsonDocument.Parse(summary);
        var body = JsonSerializer.Deserialize<Dictionary<string, JsonElement>>(document.RootElement.GetRawText())!;
        body[field] = JsonDocument.Parse(replacement).RootElement.Clone();
        var mcp = new FakeBudgetCheck(JsonSerializer.Serialize(body));
        using var client = CreateBudgetCheckClient(mcp);

        using var response = await client.PostAsJsonAsync("/api/budget-check", new { journeyLabel = "Journey" });
        var error = await response.Content.ReadFromJsonAsync<ApiErrorEnvelope>();

        Assert.Equal(HttpStatusCode.BadGateway, response.StatusCode);
        Assert.Equal(field == "plannedAmountMinor" && replacement == "9007199254740992" ? "summary_out_of_display_range" : "dependency_response_invalid", error!.Error.Code);
    }

    [Fact]
    public async Task BudgetCheckAcceptsSafeIntegerBoundaryAndNegativeRemainder()
    {
        const long safeMax = 9_007_199_254_740_991;
        var safeSummary = JsonSerializer.Serialize(new
        {
            journeyLabel = "Journey",
            baseCurrency = "AUD",
            plannedAmountMinor = safeMax,
            actualAmountMinor = 0,
            remainingAmountMinor = safeMax,
            percentageUsed = 0m,
            categories = new[] { new { category = "food", plannedAmountMinor = safeMax, actualAmountMinor = 0L, remainingAmountMinor = safeMax, percentageUsed = 0m, status = "within_budget" } }
        });
        var safeMcp = new FakeBudgetCheck(safeSummary);
        using var safeClient = CreateBudgetCheckClient(safeMcp);
        using var safeResponse = await safeClient.PostAsJsonAsync("/api/budget-check", new { journeyLabel = "Journey" });
        Assert.Equal(HttpStatusCode.OK, safeResponse.StatusCode);

        var overspentMcp = new FakeBudgetCheck(ValidBudgetSummary(planned: 1000, actual: 1001));
        using var overspentClient = CreateBudgetCheckClient(overspentMcp);
        using var overspentResponse = await overspentClient.PostAsJsonAsync("/api/budget-check", new { journeyLabel = "Journey" });
        var overspent = await overspentResponse.Content.ReadFromJsonAsync<BudgetCheckResponse>();
        Assert.Equal(HttpStatusCode.OK, overspentResponse.StatusCode);
        Assert.Equal(-1, overspent!.Result.Summary.RemainingAmountMinor);
        Assert.Equal("overspent", overspent.Result.Summary.Categories.Single().Status);
    }

    [Theory]
    [InlineData("duplicate")]
    [InlineData("unsupported")]
    [InlineData("incorrect-status")]
    public async Task BudgetCheckRejectsInvalidCategorySummaries(string mutation)
    {
        var summary = JsonNode.Parse(ValidBudgetSummary())!.AsObject();
        var categories = summary["categories"]!.AsArray();
        if (mutation == "duplicate") categories.Add(categories[0]!.DeepClone());
        if (mutation == "unsupported") categories[0]!["category"] = "medical";
        if (mutation == "incorrect-status") categories[0]!["status"] = "overspent";
        var mcp = new FakeBudgetCheck(summary.ToJsonString());
        using var client = CreateBudgetCheckClient(mcp);

        using var response = await client.PostAsJsonAsync("/api/budget-check", new { journeyLabel = "Journey" });
        var error = await response.Content.ReadFromJsonAsync<ApiErrorEnvelope>();

        Assert.Equal(HttpStatusCode.BadGateway, response.StatusCode);
        Assert.Equal("dependency_response_invalid", error!.Error.Code);
    }

    [Fact]
    public async Task BudgetGuidanceReturnsValidatedCitationsFromTheStudent4Feature()
    {
        var rag = new FakeRag(GuidanceAnswer());
        using var client = CreateBudgetGuidanceClient(rag);

        using var response = await client.PostAsJsonAsync("/api/budget-guidance", new { question = "  How are category limits used?  " });
        var body = await response.Content.ReadFromJsonAsync<BudgetGuidanceResponse>();

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.Equal("How are category limits used?", rag.Question);
        Assert.Equal("Budget status is based on actual spending. [category-budgets#1]", body!.Answer);
        Assert.Equal("high", body.Confidence);
        Assert.Equal("Category budgets and spending statuses", body.Citations.Single().Source);
        Assert.Equal("category-budgets#1", body.Citations.Single().ChunkId);
        Assert.Equal(0.45, body.Citations.Single().Score);
        Assert.Equal(1, rag.CallCount);
    }

    [Fact]
    public async Task BudgetGuidancePreservesTheExactStrictInsufficientResponse()
    {
        var rag = new FakeRag("""{"answer":"Not enough information in the knowledge base to answer this.","citations":[],"confidence":"insufficient"}""");
        using var client = CreateBudgetGuidanceClient(rag);

        using var response = await client.PostAsJsonAsync("/api/budget-guidance", new { question = "What is the current balance?" });
        var body = await response.Content.ReadFromJsonAsync<BudgetGuidanceResponse>();

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.Equal("Not enough information in the knowledge base to answer this.", body!.Answer);
        Assert.Empty(body.Citations);
        Assert.Equal("insufficient", body.Confidence);
    }

    [Theory]
    [InlineData(0.3, "low")]
    [InlineData(0.4, "medium")]
    [InlineData(0.4, "high")]
    public async Task BudgetGuidanceAcceptsConfidenceConsistentWithRoundedBoundaryScore(double score, string confidence)
    {
        var json = JsonNode.Parse(GuidanceAnswer())!.AsObject();
        json["citations"]![0]!["score"] = score;
        json["confidence"] = confidence;
        var rag = new FakeRag(json.ToJsonString());
        using var client = CreateBudgetGuidanceClient(rag);

        using var response = await client.PostAsJsonAsync("/api/budget-guidance", new { question = "budget status" });

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
    }

    [Theory]
    [InlineData("{}")]
    [InlineData("{\"question\":\"budget\",\"feature\":\"student-1\"}")]
    [InlineData("{\"question\":\"budget\",\"question\":\"other\"}")]
    [InlineData("{\"question\":42}")]
    [InlineData("{\"question\":\"   \"}")]
    [InlineData("{\"Question\":\"budget\"}")]
    public async Task BudgetGuidanceRejectsInvalidRequestsBeforeRag(string json)
    {
        var rag = new FakeRag(GuidanceAnswer());
        using var client = CreateBudgetGuidanceClient(rag);

        using var response = await client.PostAsync("/api/budget-guidance", new StringContent(json, Encoding.UTF8, "application/json"));

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.Equal(0, rag.CallCount);
    }

    [Theory]
    [InlineData(1001)]
    [InlineData(8193)]
    public async Task BudgetGuidanceRejectsOversizedQuestionOrBodyBeforeRag(int length)
    {
        var rag = new FakeRag(GuidanceAnswer());
        using var client = CreateBudgetGuidanceClient(rag);
        var json = "{\"question\":\"" + new string('x', length) + "\"}";

        using var response = await client.PostAsync("/api/budget-guidance", new StringContent(json, Encoding.UTF8, "application/json"));

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.Equal(0, rag.CallCount);
    }

    [Fact]
    public async Task DisabledBudgetGuidanceDoesNotCallRag()
    {
        var rag = new FakeRag(GuidanceAnswer());
        using var client = CreateBudgetGuidanceClient(rag, ragEnabled: false);

        using var response = await client.PostAsync("/api/budget-guidance", new StringContent("{}", Encoding.UTF8, "application/json"));
        var error = await response.Content.ReadFromJsonAsync<ApiErrorEnvelope>();

        Assert.Equal(HttpStatusCode.ServiceUnavailable, response.StatusCode);
        Assert.Equal("feature_disabled", error!.Error.Code);
        Assert.Equal(0, rag.CallCount);
    }

    [Theory]
    [InlineData("\"foreign#1\"", "Category budgets and spending statuses", "0.45", "high", "[foreign#1]")]
    [InlineData("\"category-budgets#1\"", "Other feature source", "0.45", "high", "[category-budgets#1]")]
    [InlineData("\"category-budgets#1\"", "Category budgets and spending statuses", "1.1", "high", "[category-budgets#1]")]
    [InlineData("\"category-budgets#1\"", "Category budgets and spending statuses", "0.45", "low", "[category-budgets#1]")]
    [InlineData("\"category-budgets#1\"", "Category budgets and spending statuses", "0.45", "high", "[other#1]")]
    public async Task BudgetGuidanceRejectsForeignOrMismatchedCitations(string chunkId, string source, string score, string confidence, string marker)
    {
        var json = $"{{\"answer\":\"Claim {marker}\",\"citations\":[{{\"source\":\"{source}\",\"chunk_id\":{chunkId},\"snippet\":\"A bounded source snippet.\",\"score\":{score}}}],\"confidence\":\"{confidence}\"}}";
        var rag = new FakeRag(json);
        using var client = CreateBudgetGuidanceClient(rag);

        using var response = await client.PostAsJsonAsync("/api/budget-guidance", new { question = "budget status" });
        var error = await response.Content.ReadFromJsonAsync<ApiErrorEnvelope>();

        Assert.Equal(HttpStatusCode.BadGateway, response.StatusCode);
        Assert.Equal("dependency_response_invalid", error!.Error.Code);
    }

    [Fact]
    public async Task BudgetGuidanceRejectsDuplicateCitationIdsAndUnusableAbstention()
    {
        var duplicate = """{"answer":"One. [category-budgets#1]","citations":[{"source":"Category budgets and spending statuses","chunk_id":"category-budgets#1","snippet":"First.","score":0.45},{"source":"Category budgets and spending statuses","chunk_id":"category-budgets#1","snippet":"Second.","score":0.45}],"confidence":"high"}""";
        var invalidRefusal = """{"answer":"Not enough information in the knowledge base to answer this.","citations":[{"source":"Category budgets and spending statuses","chunk_id":"category-budgets#1","snippet":"A snippet.","score":0.45}],"confidence":"insufficient"}""";
        foreach (var json in new[] { duplicate, invalidRefusal })
        {
            var rag = new FakeRag(json);
            using var client = CreateBudgetGuidanceClient(rag);
            using var response = await client.PostAsJsonAsync("/api/budget-guidance", new { question = "budget" });
            Assert.Equal(HttpStatusCode.BadGateway, response.StatusCode);
        }
    }

    [Theory]
    [InlineData(503, "dependency_unavailable")]
    [InlineData(504, "dependency_timeout")]
    [InlineData(502, "dependency_response_invalid")]
    public async Task BudgetGuidanceMapsRagFailuresToStableErrors(int statusCode, string code)
    {
        var rag = new FakeRag(GuidanceAnswer()) { Failure = new RagFailureException(statusCode, code, "safe message") };
        using var client = CreateBudgetGuidanceClient(rag);

        using var response = await client.PostAsJsonAsync("/api/budget-guidance", new { question = "budget" });
        var error = await response.Content.ReadFromJsonAsync<ApiErrorEnvelope>();

        Assert.Equal((HttpStatusCode)statusCode, response.StatusCode);
        Assert.Equal(code, error!.Error.Code);
        Assert.Equal("safe message", error.Error.Message);
    }

    private static string GuidanceAnswer() =>
        """{"answer":"Budget status is based on actual spending. [category-budgets#1]","citations":[{"source":"Category budgets and spending statuses","chunk_id":"category-budgets#1","snippet":"Set a positive limit for each budget category.","score":0.45}],"confidence":"high"}""";

    private static HttpClient CreateBudgetGuidanceClient(FakeRag rag, bool ragEnabled = true)
    {
        var factory = CreateFactory(new FakeDatabase(), new FakeAdvice(), new Dictionary<string, string?>
        {
            ["RAG_ENABLED"] = ragEnabled ? "true" : "false"
        }).WithWebHostBuilder(builder => builder.ConfigureTestServices(services =>
        {
            services.RemoveAll<IRagClient>();
            services.AddSingleton<IRagClient>(rag);
        }));
        return factory.CreateClient();
    }

    private sealed class FakeRag(string json) : IRagClient
    {
        public int CallCount { get; private set; }
        public string? Question { get; private set; }
        public RagFailureException? Failure { get; init; }

        public Task<JsonElement> AskAsync(string question, CancellationToken cancellationToken)
        {
            CallCount++;
            Question = question;
            if (Failure is not null) throw Failure;
            return Task.FromResult(JsonDocument.Parse(json).RootElement.Clone());
        }
    }

    private static HttpClient CreateBudgetCheckClient(FakeBudgetCheck mcp, bool mcpEnabled = true)
    {
        var factory = CreateFactory(new FakeDatabase(), new FakeAdvice(), new Dictionary<string, string?>
        {
            ["MCP_ENABLED"] = mcpEnabled ? "true" : "false"
        }).WithWebHostBuilder(builder => builder.ConfigureTestServices(services =>
        {
            services.RemoveAll<IMcpBudgetCheckClient>();
            services.AddSingleton<IMcpBudgetCheckClient>(mcp);
        }));
        return factory.CreateClient();
    }

    private static string ValidBudgetSummary(long planned = 1000, long actual = 800)
    {
        var remaining = planned - actual;
        var percentage = Math.Round(actual * 100m / planned, 2, MidpointRounding.AwayFromZero);
        var status = actual > planned ? "overspent" : actual * 100m / planned >= 80m ? "warning" : "within_budget";
        return JsonSerializer.Serialize(new
        {
            journeyLabel = "Journey",
            baseCurrency = "AUD",
            plannedAmountMinor = planned,
            actualAmountMinor = actual,
            remainingAmountMinor = remaining,
            percentageUsed = percentage,
            categories = new[] { new { category = "food", plannedAmountMinor = planned, actualAmountMinor = actual, remainingAmountMinor = remaining, percentageUsed = percentage, status } }
        });
    }

    private sealed class FakeBudgetCheck(string json) : IMcpBudgetCheckClient
    {
        public int CallCount { get; private set; }
        public string? JourneyLabel { get; private set; }
        public BudgetCheckFailureException? Failure { get; init; }

        public Task<JsonElement> CallAsync(string journeyLabel, CancellationToken cancellationToken)
        {
            CallCount++;
            JourneyLabel = journeyLabel;
            if (Failure is not null) throw Failure;
            return Task.FromResult(JsonDocument.Parse(json).RootElement.Clone());
        }
    }

    [Fact]
    public async Task NoBudgetDataDoesNotCallOllamaAdvice()
    {
        var advice = new FakeAdvice();
        using var client = CreateClient(new FakeDatabase(), advice);
        var response = await client.PostAsJsonAsync("/api/insights", new InsightRequest("Missing"));
        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.Equal(0, advice.CallCount);
    }

    [Fact]
    public async Task DatabaseUnavailableMapsToStable503()
    {
        using var client = CreateClient(new UnavailableDatabase(), new FakeAdvice());
        var response = await client.GetAsync("/api/budgets");
        Assert.Equal(HttpStatusCode.ServiceUnavailable, response.StatusCode);
        Assert.Equal("database_unavailable", (await response.Content.ReadFromJsonAsync<ApiErrorEnvelope>())!.Error.Code);
    }

    [Fact]
    public async Task InconsistentDashboardDataMapsToStable502()
    {
        using var client = CreateClient(FakeDatabase.WithInconsistentJourney(), new FakeAdvice());
        var response = await client.GetAsync("/api/dashboard?journeyLabel=Journey");
        Assert.Equal(HttpStatusCode.BadGateway, response.StatusCode);
        Assert.Equal("database_response_invalid", (await response.Content.ReadFromJsonAsync<ApiErrorEnvelope>())!.Error.Code);
    }

    private static HttpClient CreateClient(IDatabaseApiClient database, IAdviceService advice) => CreateFactory(database, advice).CreateClient();

    private static WebApplicationFactory<Program> CreateFactory(IDatabaseApiClient database, IAdviceService advice, IDictionary<string, string?>? configuration = null)
    {
        return new WebApplicationFactory<Program>().WithWebHostBuilder(builder =>
        {
            if (configuration is not null)
            {
                builder.ConfigureAppConfiguration((_, config) => config.AddInMemoryCollection(configuration));
            }
            builder.ConfigureTestServices(services =>
            {
                services.RemoveAll<IDatabaseApiClient>();
                services.RemoveAll<IAdviceService>();
                services.RemoveAll<IExchangeRateProvider>();
                services.AddSingleton(database);
                services.AddSingleton(advice);
                services.AddSingleton<IExchangeRateProvider>(new FixedExchangeRateProvider(new ExchangeRateSettings("test", new(2026, 8, 1), "Demo", new Dictionary<string, decimal> { ["AUD"] = 1m, ["USD"] = 0.65m, ["EUR"] = 0.6m, ["GBP"] = 0.51m, ["NZD"] = 1.08m, ["CAD"] = 0.89m, ["SGD"] = 0.86m })));
            });
        });
    }

    private sealed class FakeAdvice : IAdviceService
    {
        public int CallCount { get; private set; }
        public Task<AdviceResponse> GetAdviceAsync(DashboardResponse dashboard, CancellationToken cancellationToken) { CallCount++; return Task.FromResult(new AdviceResponse("Advice.", [new("food", "Track food.")], "ai")); }
    }

    private sealed record CapabilitiesResponse(bool AiEnabled, bool McpEnabled, bool RagEnabled);

    private sealed class FakeDatabase : IDatabaseApiClient
    {
        private readonly List<BudgetResponse> _budgets = [];
        private readonly List<ExpenseDataResponse> _expenses = [];
        public int CallCount { get; private set; }
        public ExpenseDataRequest? LastExpenseRequest { get; private set; }
        public static FakeDatabase WithJourney(long actual = 0)
        {
            var value = new FakeDatabase();
            value._budgets.Add(new(1, "Journey", "food", 10000, "AUD", new(2026, 9, 1), new(2026, 9, 7), DateTime.UtcNow, DateTime.UtcNow));
            if (actual > 0) value._expenses.Add(new(1, 1, "Meals", actual, "AUD", actual, 100000000, new(2026, 8, 1), new(2026, 9, 2), null, DateTime.UtcNow, DateTime.UtcNow));
            return value;
        }
        public static FakeDatabase WithInconsistentJourney()
        {
            var value = WithJourney();
            value._budgets.Add(new(2, "Journey", "transport", 10000, "USD", new(2026, 9, 1), new(2026, 9, 7), DateTime.UtcNow, DateTime.UtcNow));
            return value;
        }
        public Task<IReadOnlyList<BudgetResponse>> ListBudgetsAsync(string? journeyLabel, string? category, CancellationToken cancellationToken) { CallCount++; return Task.FromResult<IReadOnlyList<BudgetResponse>>(_budgets.Where(value => journeyLabel is null || value.JourneyLabel == journeyLabel).Where(value => category is null || value.Category == category).ToArray()); }
        public Task<BudgetResponse> GetBudgetAsync(int id, CancellationToken cancellationToken) { CallCount++; return Task.FromResult(_budgets.Single(value => value.Id == id)); }
        public Task<BudgetResponse> CreateBudgetAsync(BudgetWriteRequest request, CancellationToken cancellationToken) { CallCount++; var value = new BudgetResponse(_budgets.Count + 1, request.JourneyLabel!, request.Category!, request.LimitAmountMinor, request.BaseCurrency!, request.StartDate!.Value, request.EndDate!.Value, DateTime.UtcNow, DateTime.UtcNow); _budgets.Add(value); return Task.FromResult(value); }
        public Task<BudgetResponse> UpdateBudgetAsync(int id, BudgetWriteRequest request, CancellationToken cancellationToken) { CallCount++; return Task.FromResult(new BudgetResponse(id, request.JourneyLabel!, request.Category!, request.LimitAmountMinor, request.BaseCurrency!, request.StartDate!.Value, request.EndDate!.Value, DateTime.UtcNow, DateTime.UtcNow)); }
        public Task DeleteBudgetAsync(int id, CancellationToken cancellationToken) { CallCount++; _budgets.RemoveAll(value => value.Id == id); return Task.CompletedTask; }
        public Task<IReadOnlyList<ExpenseDataResponse>> ListExpensesAsync(int? budgetId, string? journeyLabel, string? category, CancellationToken cancellationToken) { CallCount++; return Task.FromResult<IReadOnlyList<ExpenseDataResponse>>(_expenses.Where(value => budgetId is null || value.BudgetId == budgetId).ToArray()); }
        public Task<ExpenseDataResponse> GetExpenseAsync(int id, CancellationToken cancellationToken) { CallCount++; return Task.FromResult(_expenses.Single(value => value.Id == id)); }
        public Task<ExpenseDataResponse> CreateExpenseAsync(ExpenseDataRequest request, CancellationToken cancellationToken) { CallCount++; LastExpenseRequest = request; var value = Data(_expenses.Count + 1, request); _expenses.Add(value); return Task.FromResult(value); }
        public Task<ExpenseDataResponse> UpdateExpenseAsync(int id, ExpenseDataRequest request, CancellationToken cancellationToken) { CallCount++; LastExpenseRequest = request; return Task.FromResult(Data(id, request)); }
        public Task DeleteExpenseAsync(int id, CancellationToken cancellationToken) { CallCount++; _expenses.RemoveAll(value => value.Id == id); return Task.CompletedTask; }
        private static ExpenseDataResponse Data(int id, ExpenseDataRequest request) => new(id, request.BudgetId, request.Description, request.OriginalAmountMinor, request.OriginalCurrency, request.ConvertedAmountMinor, request.ConversionRateScaled, request.RateAsOf, request.SpentOn, request.Notes, DateTime.UtcNow, DateTime.UtcNow);
    }

    private sealed class UnavailableDatabase : IDatabaseApiClient
    {
        private static Task<T> Fail<T>() => Task.FromException<T>(new DatabaseUnavailableException());
        public Task<IReadOnlyList<BudgetResponse>> ListBudgetsAsync(string? journeyLabel, string? category, CancellationToken cancellationToken) => Fail<IReadOnlyList<BudgetResponse>>();
        public Task<BudgetResponse> GetBudgetAsync(int id, CancellationToken cancellationToken) => Fail<BudgetResponse>();
        public Task<BudgetResponse> CreateBudgetAsync(BudgetWriteRequest request, CancellationToken cancellationToken) => Fail<BudgetResponse>();
        public Task<BudgetResponse> UpdateBudgetAsync(int id, BudgetWriteRequest request, CancellationToken cancellationToken) => Fail<BudgetResponse>();
        public Task DeleteBudgetAsync(int id, CancellationToken cancellationToken) => Fail<object>();
        public Task<IReadOnlyList<ExpenseDataResponse>> ListExpensesAsync(int? budgetId, string? journeyLabel, string? category, CancellationToken cancellationToken) => Fail<IReadOnlyList<ExpenseDataResponse>>();
        public Task<ExpenseDataResponse> GetExpenseAsync(int id, CancellationToken cancellationToken) => Fail<ExpenseDataResponse>();
        public Task<ExpenseDataResponse> CreateExpenseAsync(ExpenseDataRequest request, CancellationToken cancellationToken) => Fail<ExpenseDataResponse>();
        public Task<ExpenseDataResponse> UpdateExpenseAsync(int id, ExpenseDataRequest request, CancellationToken cancellationToken) => Fail<ExpenseDataResponse>();
        public Task DeleteExpenseAsync(int id, CancellationToken cancellationToken) => Fail<object>();
    }
}
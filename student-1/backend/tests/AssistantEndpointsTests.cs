using System.Net;
using System.Net.Http.Json;
using System.Text;
using System.Text.Json;
using Accommodation.Backend.Api;
using Accommodation.Backend.Clients;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.AspNetCore.TestHost;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;

namespace Accommodation.Backend.Tests;

public sealed class AssistantEndpointsTests
{
    private const string FindBody = """
        {"ok":true,"count":1,"accommodations":[{"id":55,"name":"Akihabara City Lodge","destination":"Tokyo","nightlyPrice":145,"maxGuests":4,"amenities":["Free WiFi"]}]}
        """;

    private const string SearchBody = """
        {"ok":true,"search":{"id":11,"title":"Tokyo Culture and Food","criteria":{"destination":"Tokyo","checkIn":"2026-09-15","checkOut":"2026-09-20","guests":2,"minimumPrice":140,"maximumPrice":260},"rankingMode":"ai","results":[{"rank":1,"accommodationId":51,"name":"Asakusa Lantern Hotel","nightlyPrice":168,"reason":"Best overall match."}]}}
        """;

    [Fact]
    public async Task LookupReturnsToolArgumentsAndValidatedResult()
    {
        var extractor = new FakeExtractor { Call = FindCall() };
        var mcp = new FakeMcp { Body = FindBody };
        using var factory = CreateFactory(extractor, mcp);
        using var client = factory.CreateClient();

        var response = await client.PostAsJsonAsync("/api/assistant", new { mode = "lookup", question = "  Stays in Tokyo for 2 under 200  " });
        var body = await response.Content.ReadFromJsonAsync<JsonElement>();

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.Equal("Stays in Tokyo for 2 under 200", extractor.LastQuestion);
        Assert.Equal("lookup", body.GetProperty("mode").GetString());
        Assert.Equal("accommodation.find", body.GetProperty("tool").GetString());
        Assert.Equal("Tokyo", body.GetProperty("arguments").GetProperty("destination").GetString());
        Assert.Equal(200, body.GetProperty("arguments").GetProperty("max_nightly_price").GetDecimal());
        Assert.True(body.GetProperty("result").GetProperty("ok").GetBoolean());
        Assert.Equal(55, body.GetProperty("result").GetProperty("accommodations")[0].GetProperty("id").GetInt32());
        Assert.Equal(1, mcp.CallCount);
    }

    [Fact]
    public async Task LookupReturnsSavedSearch()
    {
        var mcp = new FakeMcp { Body = SearchBody };
        using var factory = CreateFactory(
            new FakeExtractor { Call = new LookupCall(AssistantTools.GetSearch, new Dictionary<string, object> { ["search_id"] = 11 }) },
            mcp);
        using var client = factory.CreateClient();

        var response = await client.PostAsJsonAsync("/api/assistant", new { mode = "lookup", question = "Show saved search 11" });
        var body = await response.Content.ReadFromJsonAsync<JsonElement>();

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.Equal("accommodation.get_search", body.GetProperty("tool").GetString());
        Assert.Equal("Tokyo Culture and Food", body.GetProperty("result").GetProperty("search").GetProperty("title").GetString());
    }

    [Fact]
    public async Task DisabledModeMakesNoDependencyCall()
    {
        var extractor = new FakeExtractor { Call = FindCall() };
        var mcp = new FakeMcp { Body = FindBody };
        using var factory = CreateFactory(extractor, mcp, lookupEnabled: false);
        using var client = factory.CreateClient();

        var response = await client.PostAsJsonAsync("/api/assistant", new { mode = "lookup", question = "Stays in Tokyo" });
        var error = await response.Content.ReadFromJsonAsync<ApiErrorEnvelope>();

        Assert.Equal(HttpStatusCode.ServiceUnavailable, response.StatusCode);
        Assert.Equal("mode_disabled", error!.Error.Code);
        Assert.Equal(0, extractor.CallCount);
        Assert.Equal(0, mcp.CallCount);
    }

    public static TheoryData<string, string> InvalidBodies => new()
    {
        { """{"mode":"lookup"}""", "body" },
        { """{"question":"Tokyo"}""", "body" },
        { """{"mode":"lookup","question":"Tokyo","tool":"accommodation.find"}""", "body" },
        { """{"Mode":"lookup","question":"Tokyo"}""", "body" },
        { """["lookup","Tokyo"]""", "body" },
        { """{"mode":"lookup","question":""", "body" },
        { """{"mode":"chat","question":"Tokyo"}""", "mode" },
        { """{"mode":"Guide","question":"Tokyo"}""", "mode" },
        { """{"mode":1,"question":"Tokyo"}""", "mode" },
        { """{"mode":"lookup","question":"   "}""", "question" },
        { """{"mode":"lookup","question":7}""", "question" },
        { $$"""{"mode":"lookup","question":"{{new string('a', 1001)}}"}""", "question" }
    };

    [Theory]
    [MemberData(nameof(InvalidBodies))]
    public async Task InvalidRequestsAreRejectedBeforeAnyCall(string json, string field)
    {
        var extractor = new FakeExtractor { Call = FindCall() };
        using var factory = CreateFactory(extractor, new FakeMcp { Body = FindBody });
        using var client = factory.CreateClient();

        var response = await client.PostAsync("/api/assistant", new StringContent(json, Encoding.UTF8, "application/json"));
        var error = await response.Content.ReadFromJsonAsync<ApiErrorEnvelope>();

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.Equal("validation_error", error!.Error.Code);
        Assert.Contains(field, error.Error.Fields.Keys);
        Assert.Equal(0, extractor.CallCount);
    }

    [Fact]
    public async Task OversizedAndNonJsonBodiesAreRejected()
    {
        var extractor = new FakeExtractor { Call = FindCall() };
        using var factory = CreateFactory(extractor, new FakeMcp { Body = FindBody });
        using var client = factory.CreateClient();
        var oversized = $$"""{"mode":"lookup","question":"Tokyo","padding":"{{new string(' ', 8200)}}"}""";

        var large = await client.PostAsync("/api/assistant", new StringContent(oversized, Encoding.UTF8, "application/json"));
        var text = await client.PostAsync("/api/assistant", new StringContent("""{"mode":"lookup","question":"Tokyo"}"""));

        Assert.Equal(HttpStatusCode.BadRequest, large.StatusCode);
        Assert.Contains("8192", await large.Content.ReadAsStringAsync());
        Assert.Equal(HttpStatusCode.BadRequest, text.StatusCode);
        Assert.Equal(0, extractor.CallCount);
    }

    [Theory]
    [InlineData(AssistantFailure.NotUnderstood, HttpStatusCode.UnprocessableEntity, "lookup_not_understood")]
    [InlineData(AssistantFailure.Unavailable, HttpStatusCode.ServiceUnavailable, "dependency_unavailable")]
    [InlineData(AssistantFailure.Timeout, HttpStatusCode.GatewayTimeout, "dependency_timeout")]
    [InlineData(AssistantFailure.InvalidResponse, HttpStatusCode.BadGateway, "dependency_response_error")]
    public async Task ExtractionFailuresAreMappedWithoutCallingMcp(AssistantFailure failure, HttpStatusCode status, string code)
    {
        var mcp = new FakeMcp { Body = FindBody };
        using var factory = CreateFactory(new FakeExtractor { Failure = failure }, mcp);
        using var client = factory.CreateClient();

        var response = await client.PostAsJsonAsync("/api/assistant", new { mode = "lookup", question = "What is the weather?" });
        var error = await response.Content.ReadFromJsonAsync<ApiErrorEnvelope>();

        Assert.Equal(status, response.StatusCode);
        Assert.Equal(code, error!.Error.Code);
        Assert.Equal(0, mcp.CallCount);
    }

    [Theory]
    [InlineData(AssistantFailure.SearchNotFound, HttpStatusCode.NotFound, "search_not_found")]
    [InlineData(AssistantFailure.Unavailable, HttpStatusCode.ServiceUnavailable, "dependency_unavailable")]
    [InlineData(AssistantFailure.Timeout, HttpStatusCode.GatewayTimeout, "dependency_timeout")]
    [InlineData(AssistantFailure.InvalidResponse, HttpStatusCode.BadGateway, "dependency_response_error")]
    public async Task ToolFailuresAreMapped(AssistantFailure failure, HttpStatusCode status, string code)
    {
        using var factory = CreateFactory(new FakeExtractor { Call = FindCall() }, new FakeMcp { Failure = failure });
        using var client = factory.CreateClient();

        var response = await client.PostAsJsonAsync("/api/assistant", new { mode = "lookup", question = "Stays in Tokyo" });
        var error = await response.Content.ReadFromJsonAsync<ApiErrorEnvelope>();

        Assert.Equal(status, response.StatusCode);
        Assert.Equal(code, error!.Error.Code);
        Assert.DoesNotContain("mcp", error.Error.Message, StringComparison.OrdinalIgnoreCase);
    }

    [Theory]
    [InlineData("""{"ok":true,"count":2,"accommodations":[]}""")]
    [InlineData("""{"ok":true,"count":0,"accommodations":[],"note":"extra"}""")]
    [InlineData("""{"ok":true,"count":1,"accommodations":[{"id":1,"name":"X","destination":"Paris","nightlyPrice":100,"maxGuests":2,"amenities":[]}]}""")]
    [InlineData("""{"ok":true,"count":1,"accommodations":[{"id":1,"name":"X","destination":"Tokyo","nightlyPrice":250,"maxGuests":2,"amenities":[]}]}""")]
    [InlineData("""{"search":{}}""")]
    [InlineData("""[]""")]
    public async Task MalformedToolResultsAreRejected(string body)
    {
        using var factory = CreateFactory(new FakeExtractor { Call = FindCall() }, new FakeMcp { Body = body });
        using var client = factory.CreateClient();

        var response = await client.PostAsJsonAsync("/api/assistant", new { mode = "lookup", question = "Stays in Tokyo" });

        Assert.Equal(HttpStatusCode.BadGateway, response.StatusCode);
    }

    private static LookupCall FindCall()
    {
        return new LookupCall(AssistantTools.Find, new Dictionary<string, object>
        {
            ["destination"] = "Tokyo",
            ["guests"] = 2,
            ["max_nightly_price"] = 200m
        });
    }

    private static WebApplicationFactory<Program> CreateFactory(
        FakeExtractor extractor,
        FakeMcp mcp,
        bool lookupEnabled = true)
    {
        return new WebApplicationFactory<Program>().WithWebHostBuilder(builder =>
        {
            builder.UseSetting("MCP_ENABLED", lookupEnabled ? "true" : "false");
            builder.ConfigureTestServices(services =>
            {
                services.RemoveAll<ILookupArgumentExtractor>();
                services.RemoveAll<IMcpToolClient>();
                services.AddSingleton<ILookupArgumentExtractor>(extractor);
                services.AddSingleton<IMcpToolClient>(mcp);
            });
        });
    }

    private sealed class FakeExtractor : ILookupArgumentExtractor
    {
        public LookupCall? Call { get; init; }
        public AssistantFailure? Failure { get; init; }
        public int CallCount { get; private set; }
        public string? LastQuestion { get; private set; }

        public Task<LookupCall> ExtractAsync(string question, CancellationToken cancellationToken)
        {
            CallCount++;
            LastQuestion = question;
            return Failure is { } failure
                ? throw new AssistantException(failure, "assistant_model")
                : Task.FromResult(Call!);
        }
    }

    private sealed class FakeMcp : IMcpToolClient
    {
        public string? Body { get; init; }
        public AssistantFailure? Failure { get; init; }
        public int CallCount { get; private set; }

        public Task<JsonElement> CallAsync(LookupCall call, CancellationToken cancellationToken)
        {
            CallCount++;
            return Failure is { } failure
                ? throw new AssistantException(failure, "mcp")
                : Task.FromResult(JsonDocument.Parse(Body!).RootElement.Clone());
        }
    }
}

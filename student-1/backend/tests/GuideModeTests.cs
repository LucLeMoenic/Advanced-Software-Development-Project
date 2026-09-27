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

public sealed class GuideModeTests
{
    private const string Grounded = """
        {"answer":"Tokyo is generally considered very safe. [tokyo#3]","citations":[{"source":"Tokyo — Where to Stay","chunk_id":"tokyo#3","snippet":"Tokyo safety: Tokyo is generally considered a very safe city.","score":0.4632}],"confidence":"high"}
        """;

    private const string Insufficient = """
        {"answer":"Not enough information in the knowledge base to answer this.","citations":[],"confidence":"insufficient"}
        """;

    [Fact]
    public async Task GuideReturnsGroundedAnswerAtTheRoot()
    {
        var rag = new FakeRag { Body = Grounded };
        using var factory = CreateFactory(rag);
        using var client = factory.CreateClient();

        var response = await client.PostAsJsonAsync("/api/assistant", new { mode = "guide", question = " Is Tokyo safe for families? " });
        var body = await response.Content.ReadFromJsonAsync<JsonElement>();

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.Equal("Is Tokyo safe for families?", rag.LastQuestion);
        Assert.Equal("guide", body.GetProperty("mode").GetString());
        Assert.Equal("high", body.GetProperty("confidence").GetString());
        Assert.Contains("[tokyo#3]", body.GetProperty("answer").GetString());
        var citation = body.GetProperty("citations")[0];
        Assert.Equal("tokyo#3", citation.GetProperty("chunk_id").GetString());
        Assert.Equal("Tokyo — Where to Stay", citation.GetProperty("source").GetString());
        Assert.Equal(0.4632, citation.GetProperty("score").GetDouble());
    }

    [Fact]
    public async Task GuideReturnsInsufficientContext()
    {
        using var factory = CreateFactory(new FakeRag { Body = Insufficient });
        using var client = factory.CreateClient();

        var response = await client.PostAsJsonAsync("/api/assistant", new { mode = "guide", question = "Tell me about Bali" });
        var body = await response.Content.ReadFromJsonAsync<JsonElement>();

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.Equal("insufficient", body.GetProperty("confidence").GetString());
        Assert.Equal(0, body.GetProperty("citations").GetArrayLength());
    }

    [Fact]
    public async Task DisabledGuideMakesNoRagCallAndLeavesLookupIndependent()
    {
        var rag = new FakeRag { Body = Grounded };
        using var factory = CreateFactory(rag, guideEnabled: false);
        using var client = factory.CreateClient();

        var response = await client.PostAsJsonAsync("/api/assistant", new { mode = "guide", question = "Is Tokyo safe?" });
        var error = await response.Content.ReadFromJsonAsync<ApiErrorEnvelope>();

        Assert.Equal(HttpStatusCode.ServiceUnavailable, response.StatusCode);
        Assert.Equal("mode_disabled", error!.Error.Code);
        Assert.Equal("Destination guide is disabled.", error.Error.Message);
        Assert.Equal(0, rag.CallCount);
    }

    [Theory]
    [InlineData(AssistantFailure.Unavailable, HttpStatusCode.ServiceUnavailable, "dependency_unavailable")]
    [InlineData(AssistantFailure.Timeout, HttpStatusCode.GatewayTimeout, "dependency_timeout")]
    [InlineData(AssistantFailure.InvalidResponse, HttpStatusCode.BadGateway, "dependency_response_error")]
    public async Task RagFailuresAreMapped(AssistantFailure failure, HttpStatusCode status, string code)
    {
        using var factory = CreateFactory(new FakeRag { Failure = failure });
        using var client = factory.CreateClient();

        var response = await client.PostAsJsonAsync("/api/assistant", new { mode = "guide", question = "Is Tokyo safe?" });
        var error = await response.Content.ReadFromJsonAsync<ApiErrorEnvelope>();

        Assert.Equal(status, response.StatusCode);
        Assert.Equal(code, error!.Error.Code);
    }

    public static TheoryData<string> InvalidEnvelopes => new()
    {
        """{"answer":"Not enough information.","citations":[],"confidence":"insufficient"}""",
        """{"answer":"Not enough information in the knowledge base to answer this.","citations":[{"source":"S","chunk_id":"a#1","snippet":"x","score":0.2}],"confidence":"insufficient"}""",
        """{"answer":"Safe. [tokyo#3]","citations":[],"confidence":"high"}""",
        """{"answer":"Safe.","citations":[{"source":"S","chunk_id":"tokyo#3","snippet":"x","score":0.4}],"confidence":"high"}""",
        """{"answer":"Safe. [tokyo#3] [paris#3]","citations":[{"source":"S","chunk_id":"tokyo#3","snippet":"x","score":0.4}],"confidence":"high"}""",
        """{"answer":"Safe. [tokyo#3]","citations":[{"source":"S","chunk_id":"tokyo#3","snippet":"x","score":0.4},{"source":"S","chunk_id":"tokyo#3","snippet":"x","score":0.4}],"confidence":"high"}""",
        """{"answer":"Safe. [tokyo 3]","citations":[{"source":"S","chunk_id":"tokyo 3","snippet":"x","score":0.4}],"confidence":"high"}""",
        """{"answer":"Safe. [tokyo#3]","citations":[{"source":"S","chunk_id":"tokyo#3","snippet":"x","score":0}],"confidence":"high"}""",
        """{"answer":"Safe. [tokyo#3]","citations":[{"source":"S","chunk_id":"tokyo#3","snippet":"x","score":1.5}],"confidence":"high"}""",
        """{"answer":"Safe. [tokyo#3]","citations":[{"source":"S","chunk_id":"tokyo#3","snippet":"x","score":"0.4"}],"confidence":"high"}""",
        """{"answer":"Safe. [tokyo#3]","citations":[{"source":"","chunk_id":"tokyo#3","snippet":"x","score":0.4}],"confidence":"high"}""",
        """{"answer":"Safe. [tokyo#3]","citations":[{"source":"S","chunk_id":"tokyo#3","snippet":"x","score":0.4,"url":"http://x"}],"confidence":"high"}""",
        """{"answer":"Safe. [tokyo#3]","citations":[{"source":"S","chunk_id":"tokyo#3","snippet":"x","score":0.4}],"confidence":"certain"}""",
        """{"answer":"Safe. [tokyo#3]","citations":[{"source":"S","chunk_id":"tokyo#3","snippet":"x","score":0.4}],"confidence":"high","extra":1}""",
        """{"answer":"   ","citations":[],"confidence":"insufficient"}""",
        """{"answer":"a [a#1] [b#2] [c#3] [d#4]","citations":[{"source":"S","chunk_id":"a#1","snippet":"x","score":0.4},{"source":"S","chunk_id":"b#2","snippet":"x","score":0.4},{"source":"S","chunk_id":"c#3","snippet":"x","score":0.4},{"source":"S","chunk_id":"d#4","snippet":"x","score":0.4}],"confidence":"high"}""",
        """[]"""
    };

    [Theory]
    [MemberData(nameof(InvalidEnvelopes))]
    public void InvalidRagEnvelopesAreRejected(string json)
    {
        var exception = Assert.Throws<AssistantException>(() => GuideResponseValidator.Validate(JsonDocument.Parse(json).RootElement));

        Assert.Equal(AssistantFailure.InvalidResponse, exception.Failure);
    }

    [Fact]
    public void ChunkIdWithTrailingNewlineIsRejected()
    {
        var json = JsonSerializer.Serialize(new
        {
            answer = "Safe. [tokyo#3\n]",
            citations = new[] { new { source = "S", chunk_id = "tokyo#3\n", snippet = "x", score = 0.4 } },
            confidence = "high"
        });

        Assert.Throws<AssistantException>(() => GuideResponseValidator.Validate(JsonDocument.Parse(json).RootElement));
    }

    [Fact]
    public async Task RagClientPostsFixedFeatureAndParsesResponse()
    {
        var handler = new StubHandler(_ => Json(Grounded));
        var client = CreateRagClient(handler);

        var body = await client.AskAsync("Is Tokyo safe?", CancellationToken.None);

        Assert.Equal("http://rag.test/query", handler.LastUri);
        Assert.Equal("""{"feature":"student-1","question":"Is Tokyo safe?"}""", handler.LastBody);
        Assert.Equal("high", body.GetProperty("confidence").GetString());
    }

    [Theory]
    [InlineData(HttpStatusCode.ServiceUnavailable, AssistantFailure.Unavailable)]
    [InlineData(HttpStatusCode.GatewayTimeout, AssistantFailure.Timeout)]
    [InlineData(HttpStatusCode.BadGateway, AssistantFailure.InvalidResponse)]
    [InlineData(HttpStatusCode.BadRequest, AssistantFailure.InvalidResponse)]
    public async Task RagClientMapsStatusCodes(HttpStatusCode status, AssistantFailure expected)
    {
        var client = CreateRagClient(new StubHandler(_ => new HttpResponseMessage(status)));

        var exception = await Assert.ThrowsAsync<AssistantException>(() => client.AskAsync("Q", CancellationToken.None));

        Assert.Equal(expected, exception.Failure);
    }

    [Fact]
    public async Task RagClientRejectsOversizedInvalidAndUnreachableResponses()
    {
        var oversized = await Assert.ThrowsAsync<AssistantException>(() =>
            CreateRagClient(new StubHandler(_ => Json($$"""{"answer":"{{new string('a', 16100)}}"}"""))).AskAsync("Q", CancellationToken.None));
        var invalid = await Assert.ThrowsAsync<AssistantException>(() =>
            CreateRagClient(new StubHandler(_ => Json("<html>"))).AskAsync("Q", CancellationToken.None));
        var unreachable = await Assert.ThrowsAsync<AssistantException>(() =>
            CreateRagClient(new StubHandler(_ => throw new HttpRequestException("refused"))).AskAsync("Q", CancellationToken.None));

        Assert.Equal(AssistantFailure.InvalidResponse, oversized.Failure);
        Assert.Equal(AssistantFailure.InvalidResponse, invalid.Failure);
        Assert.Equal(AssistantFailure.Unavailable, unreachable.Failure);
    }

    [Fact]
    public async Task RagClientEnforcesItsDeadline()
    {
        var client = new RagClient(
            new HttpClient(new HangingHandler()),
            new RagSettings(new Uri("http://rag.test"), TimeSpan.FromMilliseconds(200)));

        var exception = await Assert.ThrowsAsync<AssistantException>(() => client.AskAsync("Q", CancellationToken.None));

        Assert.Equal(AssistantFailure.Timeout, exception.Failure);
    }

    [Fact]
    public void ProductionRagDeadlineIsThirtySeconds()
    {
        using var factory = new WebApplicationFactory<Program>();

        var settings = factory.Services.GetRequiredService<RagSettings>();

        Assert.Equal(TimeSpan.FromSeconds(30), settings.Deadline);
        Assert.Equal(new Uri("http://localhost:5500"), settings.BaseAddress);
    }

    private static RagClient CreateRagClient(HttpMessageHandler handler)
    {
        return new RagClient(new HttpClient(handler), new RagSettings(new Uri("http://rag.test"), TimeSpan.FromSeconds(30)));
    }

    private static HttpResponseMessage Json(string body)
    {
        return new HttpResponseMessage(HttpStatusCode.OK) { Content = new StringContent(body, Encoding.UTF8, "application/json") };
    }

    private static WebApplicationFactory<Program> CreateFactory(FakeRag rag, bool guideEnabled = true)
    {
        return new WebApplicationFactory<Program>().WithWebHostBuilder(builder =>
        {
            builder.UseSetting("MCP_ENABLED", "false");
            builder.UseSetting("RAG_ENABLED", guideEnabled ? "true" : "false");
            builder.ConfigureTestServices(services =>
            {
                services.RemoveAll<IRagClient>();
                services.AddSingleton<IRagClient>(rag);
            });
        });
    }

    private sealed class FakeRag : IRagClient
    {
        public string? Body { get; init; }
        public AssistantFailure? Failure { get; init; }
        public int CallCount { get; private set; }
        public string? LastQuestion { get; private set; }

        public Task<JsonElement> AskAsync(string question, CancellationToken cancellationToken)
        {
            CallCount++;
            LastQuestion = question;
            return Failure is { } failure
                ? throw new AssistantException(failure, "rag")
                : Task.FromResult(JsonDocument.Parse(Body!).RootElement.Clone());
        }
    }

    private sealed class StubHandler(Func<HttpRequestMessage, HttpResponseMessage> respond) : HttpMessageHandler
    {
        public string? LastUri { get; private set; }
        public string? LastBody { get; private set; }

        protected override async Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken)
        {
            LastUri = request.RequestUri?.ToString();
            LastBody = request.Content is null ? null : await request.Content.ReadAsStringAsync(cancellationToken);
            return respond(request);
        }
    }

    private sealed class HangingHandler : HttpMessageHandler
    {
        protected override async Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken)
        {
            await Task.Delay(Timeout.Infinite, cancellationToken);
            throw new InvalidOperationException("Unreachable.");
        }
    }
}

using System.Net;
using System.Text;
using System.Text.Json;
using BudgetTracker.Backend.Clients;

namespace BudgetTracker.Backend.Tests;

public sealed class RagClientTests
{
    [Fact]
    public async Task PostsOnlyTheQuestionToTheFixedStudent4Query()
    {
        var handler = new StubHandler(async (request, cancellationToken) =>
        {
            Assert.Equal(HttpMethod.Post, request.Method);
            Assert.Equal("/query", request.RequestUri!.AbsolutePath);
            using var body = JsonDocument.Parse(await request.Content!.ReadAsStringAsync(cancellationToken));
            Assert.Equal("student-4", body.RootElement.GetProperty("feature").GetString());
            Assert.Equal("category status", body.RootElement.GetProperty("question").GetString());
            Assert.Equal(2, body.RootElement.EnumerateObject().Count());
            return JsonResponse("{}" );
        });
        using var httpClient = new HttpClient(handler);
        var rag = new RagClient(httpClient, Settings());

        var result = await rag.AskAsync("category status", CancellationToken.None);

        Assert.Equal(JsonValueKind.Object, result.ValueKind);
        Assert.Equal("http://rag.test/query", handler.LastUri!.ToString());
    }

    [Theory]
    [InlineData(HttpStatusCode.ServiceUnavailable, 503, "dependency_unavailable")]
    [InlineData(HttpStatusCode.GatewayTimeout, 504, "dependency_timeout")]
    [InlineData(HttpStatusCode.BadRequest, 502, "dependency_response_invalid")]
    public async Task MapsDependencyHttpStatuses(HttpStatusCode status, int expectedStatus, string expectedCode)
    {
        using var httpClient = new HttpClient(new StubHandler((_, _) => Task.FromResult(JsonResponse("{}", status))));
        var rag = new RagClient(httpClient, Settings());

        var failure = await Assert.ThrowsAsync<RagFailureException>(() => rag.AskAsync("question", CancellationToken.None));

        Assert.Equal(expectedStatus, failure.StatusCode);
        Assert.Equal(expectedCode, failure.Code);
    }

    [Fact]
    public async Task RejectsMalformedJsonAndOversizedStream()
    {
        using var malformedClient = new HttpClient(new StubHandler((_, _) => Task.FromResult(JsonResponse("{"))));
        var malformed = await Assert.ThrowsAsync<RagFailureException>(() => new RagClient(malformedClient, Settings()).AskAsync("question", CancellationToken.None));
        Assert.Equal("dependency_response_invalid", malformed.Code);

        using var oversizedClient = new HttpClient(new StubHandler((_, _) => Task.FromResult(new HttpResponseMessage(HttpStatusCode.OK)
        {
            Content = new UnknownLengthContent(Encoding.UTF8.GetBytes(new string('x', 16 * 1024 + 1)))
        })));
        var oversized = await Assert.ThrowsAsync<RagFailureException>(() => new RagClient(oversizedClient, Settings()).AskAsync("question", CancellationToken.None));
        Assert.Equal(502, oversized.StatusCode);
        Assert.Equal("dependency_response_too_large", oversized.Code);
    }

    [Fact]
    public async Task MapsConnectionFailureAndDeadlineButPropagatesCallerCancellation()
    {
        using var unavailableClient = new HttpClient(new StubHandler((_, _) => throw new HttpRequestException("offline")));
        var unavailable = await Assert.ThrowsAsync<RagFailureException>(() => new RagClient(unavailableClient, Settings()).AskAsync("question", CancellationToken.None));
        Assert.Equal(503, unavailable.StatusCode);

        using var hangingClient = new HttpClient(new StubHandler(async (_, cancellationToken) =>
        {
            await Task.Delay(Timeout.Infinite, cancellationToken);
            return JsonResponse("{}");
        }));
        var timed = await Assert.ThrowsAsync<RagFailureException>(() => new RagClient(hangingClient, Settings(TimeSpan.FromMilliseconds(50))).AskAsync("question", CancellationToken.None));
        Assert.Equal(504, timed.StatusCode);

        using var callerCancellation = new CancellationTokenSource(TimeSpan.FromMilliseconds(50));
        await Assert.ThrowsAnyAsync<OperationCanceledException>(() => new RagClient(hangingClient, Settings(TimeSpan.FromSeconds(5))).AskAsync("question", callerCancellation.Token));
    }

    private static RagSettings Settings(TimeSpan? deadline = null) => new(new Uri("http://rag.test/prefix"), deadline ?? TimeSpan.FromSeconds(2));

    private static HttpResponseMessage JsonResponse(string body, HttpStatusCode status = HttpStatusCode.OK) => new(status)
    {
        Content = new StringContent(body, Encoding.UTF8, "application/json")
    };

    private sealed class StubHandler(Func<HttpRequestMessage, CancellationToken, Task<HttpResponseMessage>> respond) : HttpMessageHandler
    {
        public Uri? LastUri { get; private set; }

        protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken)
        {
            LastUri = request.RequestUri;
            return respond(request, cancellationToken);
        }
    }

    private sealed class UnknownLengthContent(byte[] content) : HttpContent
    {
        protected override Task SerializeToStreamAsync(Stream stream, System.Net.TransportContext? context) => stream.WriteAsync(content).AsTask();

        protected override bool TryComputeLength(out long length)
        {
            length = 0;
            return false;
        }
    }
}
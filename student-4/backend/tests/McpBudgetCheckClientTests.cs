using System.Net;
using System.Text;
using System.Text.Json;
using BudgetTracker.Backend.Clients;
using Microsoft.Extensions.Logging.Abstractions;

namespace BudgetTracker.Backend.Tests;

public sealed class McpBudgetCheckClientTests
{
    private const string Summary = """{"journeyLabel":"Journey","baseCurrency":"AUD","plannedAmountMinor":1000,"actualAmountMinor":800,"remainingAmountMinor":200,"percentageUsed":80,"categories":[{"category":"food","plannedAmountMinor":1000,"actualAmountMinor":800,"remainingAmountMinor":200,"percentageUsed":80,"status":"warning"}]}""";

    [Fact]
    public async Task OfficialSdkInitializesAndCallsTheFixedBudgetToolInProcess()
    {
        var handler = new InProcessMcpHandler { ToolResult = $"{{\"ok\":true,\"summary\":{Summary}}}" };
        using var httpClient = CreateClient(handler);
        var client = CreateMcpClient(httpClient);

        var result = await client.CallAsync("Journey", CancellationToken.None);

        Assert.Equal("Journey", result.GetProperty("journeyLabel").GetString());
        var call = handler.LastToolCall!.Value;
        Assert.Equal("budget.get_summary", call.GetProperty("params").GetProperty("name").GetString());
        Assert.Equal("Journey", call.GetProperty("params").GetProperty("arguments").GetProperty("params").GetProperty("journey_label").GetString());
    }

    [Theory]
    [InlineData("journey_not_found", 404, "journey_not_found")]
    [InlineData("invalid_input", 400, "validation_error")]
    [InlineData("response_too_large", 502, "dependency_response_too_large")]
    [InlineData("dependency_timeout", 504, "dependency_timeout")]
    [InlineData("dependency_unavailable", 503, "dependency_unavailable")]
    public async Task StructuredToolFailuresMapToStableApiErrors(string code, int statusCode, string expectedCode)
    {
        using var httpClient = CreateClient(new InProcessMcpHandler
        {
            ToolResult = $"{{\"ok\":false,\"error\":{{\"code\":\"{code}\",\"message\":\"private detail\"}}}}"
        });
        var client = CreateMcpClient(httpClient);

        var error = await Assert.ThrowsAsync<BudgetCheckFailureException>(() => client.CallAsync("Journey", CancellationToken.None));

        Assert.Equal(statusCode, error.StatusCode);
        Assert.Equal(expectedCode, error.Code);
        Assert.DoesNotContain("private detail", error.Message, StringComparison.Ordinal);
    }

    [Theory]
    [InlineData("{}", true, false)]
    [InlineData("{}", false, true)]
    public async Task IsErrorMalformedJsonAndMissingStructuredContentFailClosed(string toolResult, bool isError, bool omitStructuredContent)
    {
        using var httpClient = CreateClient(new InProcessMcpHandler
        {
            ToolResult = toolResult,
            IsError = isError,
            OmitStructuredContent = omitStructuredContent
        });
        var client = CreateMcpClient(httpClient);

        var error = await Assert.ThrowsAsync<BudgetCheckFailureException>(() => client.CallAsync("Journey", CancellationToken.None));

        Assert.Equal(502, error.StatusCode);
        Assert.Equal("dependency_response_invalid", error.Code);
    }

    [Fact]
    public async Task MalformedProtocolJsonFailsClosed()
    {
        using var httpClient = CreateClient(new InProcessMcpHandler { MalformedToolResponse = true });
        var client = CreateMcpClient(httpClient);
        var error = await Assert.ThrowsAsync<BudgetCheckFailureException>(() => client.CallAsync("Journey", CancellationToken.None));

        Assert.Equal(502, error.StatusCode);
        Assert.Equal("dependency_response_invalid", error.Code);
    }

    [Fact]
    public async Task ConnectionFailureMapsToUnavailable()
    {
        using var httpClient = CreateClient(new ConnectionFailureHandler());
        var client = CreateMcpClient(httpClient);

        var error = await Assert.ThrowsAsync<BudgetCheckFailureException>(() => client.CallAsync("Journey", CancellationToken.None));

        Assert.Equal(503, error.StatusCode);
        Assert.Equal("dependency_unavailable", error.Code);
    }

    [Fact]
    public async Task OversizedMcpCallResponseMapsToBadGateway()
    {
        using var httpClient = CreateClient(new InProcessMcpHandler { OversizedToolResponse = true });
        var client = CreateMcpClient(httpClient);

        var error = await Assert.ThrowsAsync<BudgetCheckFailureException>(() => client.CallAsync("Journey", CancellationToken.None));

        Assert.Equal(502, error.StatusCode);
        Assert.Equal("dependency_response_invalid", error.Code);
    }

    [Fact]
    public async Task CallerCancellationIsPropagated()
    {
        using var httpClient = CreateClient(new InProcessMcpHandler { HangOnToolCall = true });
        var client = CreateMcpClient(httpClient);
        using var cancellation = new CancellationTokenSource(TimeSpan.FromMilliseconds(100));

        await Assert.ThrowsAnyAsync<OperationCanceledException>(() => client.CallAsync("Journey", cancellation.Token));
    }

    [Fact]
    public async Task BoundedTransportRejectsUnknownLengthOversizedBody()
    {
        using var httpClient = CreateClient(new OversizedResponseHandler());

        var error = await Assert.ThrowsAsync<HttpRequestException>(() => httpClient.GetAsync("http://mcp.test/mcp"));
        Assert.IsType<ResponseTooLargeException>(error.InnerException);
    }

    [Fact]
    public async Task BoundedTransportAcceptsExactlyTheResponseLimit()
    {
        using var httpClient = CreateClient(new FixedResponseHandler(new byte[BoundedMcpResponseHandler.MaxResponseBytes]));

        using var response = await httpClient.GetAsync("http://mcp.test/mcp");
        var body = await response.Content.ReadAsByteArrayAsync();

        Assert.Equal(BoundedMcpResponseHandler.MaxResponseBytes, body.Length);
    }

    private static HttpClient CreateClient(HttpMessageHandler handler) =>
        new(new BoundedMcpResponseHandler(handler));

    private static McpBudgetCheckClient CreateMcpClient(HttpClient httpClient) =>
        new(httpClient, McpBudgetCheckSettings.FromUrl("http://localhost:5400/mcp"), NullLoggerFactory.Instance);

    private sealed class InProcessMcpHandler : HttpMessageHandler
    {
        public string ToolResult { get; init; } = "{}";
        public bool IsError { get; init; }
        public bool OmitStructuredContent { get; init; }
        public bool HangOnToolCall { get; init; }
        public bool MalformedToolResponse { get; init; }
        public bool OversizedToolResponse { get; init; }
        public JsonElement? LastToolCall { get; private set; }

        protected override async Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken)
        {
            using var body = JsonDocument.Parse(await request.Content!.ReadAsStringAsync(cancellationToken));
            var root = body.RootElement;
            var method = root.GetProperty("method").GetString();
            if (method == "notifications/initialized") return new HttpResponseMessage(HttpStatusCode.Accepted);

            var id = root.GetProperty("id").Clone();
            if (method == "initialize")
            {
                var protocolVersion = root.GetProperty("params").GetProperty("protocolVersion").GetString();
                return JsonResponse(new
                {
                    jsonrpc = "2.0",
                    id,
                    result = new
                    {
                        protocolVersion,
                        capabilities = new { tools = new { } },
                        serverInfo = new { name = "in-process-test-server", version = "1.0.0" }
                    }
                });
            }

            if (method != "tools/call") return JsonResponse(new { jsonrpc = "2.0", id, error = new { code = -32601, message = "Method not found" } });
            if (HangOnToolCall) await Task.Delay(Timeout.Infinite, cancellationToken);

            LastToolCall = root.Clone();
            if (MalformedToolResponse)
            {
                return new HttpResponseMessage(HttpStatusCode.OK)
                {
                    Content = new StringContent("{", Encoding.UTF8, "application/json")
                };
            }

            if (OversizedToolResponse)
            {
                return new HttpResponseMessage(HttpStatusCode.OK)
                {
                    Content = new UnknownLengthContent(new byte[BoundedMcpResponseHandler.MaxResponseBytes + 1])
                };
            }

            var toolResult = JsonDocument.Parse(ToolResult).RootElement;
            JsonElement? structured = OmitStructuredContent ? null : toolResult;
            return JsonResponse(new
            {
                jsonrpc = "2.0",
                id,
                result = new
                {
                    content = new[] { new { type = "text", text = ToolResult } },
                    structuredContent = structured,
                    isError = IsError
                }
            });
        }

        private static HttpResponseMessage JsonResponse<T>(T value) => new(HttpStatusCode.OK)
        {
            Content = new StringContent(JsonSerializer.Serialize(value), Encoding.UTF8, "application/json")
        };
    }

    private sealed class OversizedResponseHandler : HttpMessageHandler
    {
        protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken)
        {
            var content = new UnknownLengthContent(new byte[BoundedMcpResponseHandler.MaxResponseBytes + 1]);
            return Task.FromResult(new HttpResponseMessage(HttpStatusCode.OK) { Content = content });
        }
    }

    private sealed class ConnectionFailureHandler : HttpMessageHandler
    {
        protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken) =>
            throw new HttpRequestException("test connection failure");
    }

    private sealed class FixedResponseHandler(byte[] bytes) : HttpMessageHandler
    {
        protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken) =>
            Task.FromResult(new HttpResponseMessage(HttpStatusCode.OK) { Content = new UnknownLengthContent(bytes) });
    }

    private sealed class UnknownLengthContent(byte[] content) : HttpContent
    {
        protected override Task SerializeToStreamAsync(Stream stream, System.Net.TransportContext? context) =>
            stream.WriteAsync(content).AsTask();

        protected override bool TryComputeLength(out long length)
        {
            length = 0;
            return false;
        }
    }
}
using System.Text.Json;
using ModelContextProtocol;
using ModelContextProtocol.Client;

namespace BudgetTracker.Backend.Clients;

public interface IMcpBudgetCheckClient
{
    Task<JsonElement> CallAsync(string journeyLabel, CancellationToken cancellationToken);
}

public sealed record McpBudgetCheckSettings(Uri Endpoint)
{
    public static McpBudgetCheckSettings FromUrl(string value)
    {
        if (!Uri.TryCreate(value, UriKind.Absolute, out var endpoint)
            || endpoint.Scheme is not ("http" or "https")
            || string.IsNullOrWhiteSpace(endpoint.Host)
            || !string.IsNullOrEmpty(endpoint.UserInfo))
        {
            throw new InvalidOperationException("MCP_SERVER_URL must be an absolute HTTP URL without user information.");
        }

        return new(endpoint);
    }
}

public sealed class BudgetCheckFailureException(int statusCode, string code, string message, Exception? innerException = null)
    : Exception(message, innerException)
{
    public int StatusCode { get; } = statusCode;
    public string Code { get; } = code;
}

public sealed class McpBudgetCheckClient(
    HttpClient httpClient,
    McpBudgetCheckSettings settings,
    ILoggerFactory loggerFactory) : IMcpBudgetCheckClient
{
    private const string ToolName = "budget.get_summary";
    private static readonly TimeSpan Deadline = TimeSpan.FromSeconds(15);

    public async Task<JsonElement> CallAsync(string journeyLabel, CancellationToken cancellationToken)
    {
        using var deadline = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
        deadline.CancelAfter(Deadline);

        try
        {
            var transport = new HttpClientTransport(
                new HttpClientTransportOptions
                {
                    Endpoint = settings.Endpoint,
                    TransportMode = HttpTransportMode.StreamableHttp,
                    Name = "student4-backend"
                },
                httpClient,
                loggerFactory,
                ownsHttpClient: false);
            await using var client = await McpClient.CreateAsync(
                transport,
                loggerFactory: loggerFactory,
                cancellationToken: deadline.Token);
            var result = await client.CallToolAsync(
                ToolName,
                new Dictionary<string, object?>
                {
                    ["params"] = new Dictionary<string, object?> { ["journey_label"] = journeyLabel }
                },
                cancellationToken: deadline.Token);

            if (result.IsError == true || result.StructuredContent is not { } content)
            {
                throw InvalidResponse();
            }

            var body = JsonSerializer.SerializeToElement(content);
            if (IsToolFailure(body))
            {
                throw MapToolFailure(body);
            }

            if (!HasExactProperties(body, "ok", "summary")
                || body.GetProperty("ok").ValueKind != JsonValueKind.True
                || body.GetProperty("summary").ValueKind != JsonValueKind.Object)
            {
                throw InvalidResponse();
            }

            return body.GetProperty("summary").Clone();
        }
        catch (BudgetCheckFailureException)
        {
            throw;
        }
        catch (OperationCanceledException exception) when (!cancellationToken.IsCancellationRequested)
        {
            throw new BudgetCheckFailureException(504, "dependency_timeout", "The MCP service timed out.", exception);
        }
        catch (HttpRequestException exception)
        {
            if (HasInner<ResponseTooLargeException>(exception))
            {
                throw new BudgetCheckFailureException(502, "dependency_response_too_large", "The MCP service response exceeded the size limit.", exception);
            }

            throw new BudgetCheckFailureException(503, "dependency_unavailable", "The MCP service is unavailable.", exception);
        }
        catch (ResponseTooLargeException exception)
        {
            throw new BudgetCheckFailureException(502, "dependency_response_too_large", "The MCP service response exceeded the size limit.", exception);
        }
        catch (McpException exception)
        {
            if (HasInner<ResponseTooLargeException>(exception))
            {
                throw new BudgetCheckFailureException(502, "dependency_response_too_large", "The MCP service response exceeded the size limit.", exception);
            }

            var statusCode = HasInner<HttpRequestException>(exception) ? 503 : 502;
            var code = statusCode == 503 ? "dependency_unavailable" : "dependency_response_invalid";
            var message = statusCode == 503 ? "The MCP service is unavailable." : "The MCP service returned an unusable response.";
            throw new BudgetCheckFailureException(statusCode, code, message, exception);
        }
        catch (IOException exception)
        {
            throw new BudgetCheckFailureException(503, "dependency_unavailable", "The MCP service is unavailable.", exception);
        }
        catch (JsonException exception)
        {
            throw new BudgetCheckFailureException(502, "dependency_response_invalid", "The MCP service returned an unusable response.", exception);
        }
    }

    private static bool IsToolFailure(JsonElement body) =>
        body.ValueKind == JsonValueKind.Object
        && body.TryGetProperty("ok", out var ok)
        && ok.ValueKind == JsonValueKind.False;

    private static BudgetCheckFailureException MapToolFailure(JsonElement body)
    {
        if (!HasExactProperties(body, "ok", "error")) return InvalidResponse();
        var error = body.GetProperty("error");
        if (!HasExactProperties(error, "code", "message")
            || error.GetProperty("code").ValueKind != JsonValueKind.String
            || error.GetProperty("message").ValueKind != JsonValueKind.String)
        {
            return InvalidResponse();
        }

        return error.GetProperty("code").GetString() switch
        {
            "invalid_input" => new(400, "validation_error", "The journey label is invalid."),
            "journey_not_found" => new(404, "journey_not_found", "The journey was not found."),
            "dependency_timeout" => new(504, "dependency_timeout", "The budget service timed out."),
            "dependency_unavailable" => new(503, "dependency_unavailable", "The budget service is unavailable."),
            "response_too_large" => new(502, "dependency_response_too_large", "The MCP service response exceeded the size limit."),
            _ => InvalidResponse()
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

    private static BudgetCheckFailureException InvalidResponse() =>
        new(502, "dependency_response_invalid", "The MCP service returned an unusable response.");

    private static bool HasInner<TException>(Exception exception) where TException : Exception
    {
        for (var current = exception; current is not null; current = current.InnerException)
        {
            if (current is TException) return true;
        }

        return false;
    }

}

public sealed class BoundedMcpResponseHandler : DelegatingHandler
{
    public const int MaxResponseBytes = 16 * 1024;

    public BoundedMcpResponseHandler() : this(new HttpClientHandler())
    {
    }

    public BoundedMcpResponseHandler(HttpMessageHandler innerHandler) : base(innerHandler)
    {
    }

    protected override async Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken)
    {
        var response = await base.SendAsync(request, cancellationToken);
        if (response.Content.Headers.ContentLength > MaxResponseBytes)
        {
            response.Dispose();
            throw new ResponseTooLargeException();
        }

        var originalContent = response.Content;
        var stream = await originalContent.ReadAsStreamAsync(cancellationToken);
        var headers = originalContent.Headers
            .Where(header => !string.Equals(header.Key, "Content-Length", StringComparison.OrdinalIgnoreCase))
            .ToArray();
        response.Content = new StreamContent(new BoundedMcpResponseStream(stream, originalContent, MaxResponseBytes));
        foreach (var (name, values) in headers) response.Content.Headers.TryAddWithoutValidation(name, values);
        return response;
    }
}

public sealed class ResponseTooLargeException : IOException
{
}

internal sealed class BoundedMcpResponseStream(Stream innerStream, HttpContent owner, int maxBytes) : Stream
{
    private int _bytesRead;

    public override bool CanRead => innerStream.CanRead;
    public override bool CanSeek => false;
    public override bool CanWrite => false;
    public override long Length => throw new NotSupportedException();
    public override long Position { get => throw new NotSupportedException(); set => throw new NotSupportedException(); }

    public override int Read(byte[] buffer, int offset, int count) => RecordRead(innerStream.Read(buffer, offset, count));
    public override int Read(Span<byte> buffer) => RecordRead(innerStream.Read(buffer));

    public override async ValueTask<int> ReadAsync(Memory<byte> buffer, CancellationToken cancellationToken = default) =>
        RecordRead(await innerStream.ReadAsync(buffer, cancellationToken));

    public override Task<int> ReadAsync(byte[] buffer, int offset, int count, CancellationToken cancellationToken) =>
        ReadAsync(buffer.AsMemory(offset, count), cancellationToken).AsTask();

    public override void Flush() => throw new NotSupportedException();
    public override long Seek(long offset, SeekOrigin origin) => throw new NotSupportedException();
    public override void SetLength(long value) => throw new NotSupportedException();
    public override void Write(byte[] buffer, int offset, int count) => throw new NotSupportedException();

    protected override void Dispose(bool disposing)
    {
        if (disposing) owner.Dispose();
        base.Dispose(disposing);
    }

    public override ValueTask DisposeAsync()
    {
        owner.Dispose();
        GC.SuppressFinalize(this);
        return ValueTask.CompletedTask;
    }

    private int RecordRead(int read)
    {
        if (_bytesRead + read > maxBytes)
        {
            throw new ResponseTooLargeException();
        }

        _bytesRead += read;
        return read;
    }
}
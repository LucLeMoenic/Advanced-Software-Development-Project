using System.Text.Json;
using Accommodation.Backend.Api;
using ModelContextProtocol;
using ModelContextProtocol.Client;

namespace Accommodation.Backend.Clients;

public interface IMcpToolClient
{
    Task<JsonElement> CallAsync(LookupCall call, CancellationToken cancellationToken);
}

public sealed record McpSettings(Uri Endpoint);

public sealed class McpToolClient(
    HttpClient httpClient,
    McpSettings settings,
    ILoggerFactory loggerFactory) : IMcpToolClient
{
    private const string Dependency = "mcp";
    private static readonly TimeSpan Deadline = TimeSpan.FromSeconds(5);

    public async Task<JsonElement> CallAsync(LookupCall call, CancellationToken cancellationToken)
    {
        if (!AssistantTools.Allowed.Contains(call.Tool))
        {
            throw new InvalidOperationException($"MCP tool '{call.Tool}' is not allow-listed.");
        }

        using var deadline = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
        deadline.CancelAfter(Deadline);
        try
        {
            var transport = new HttpClientTransport(
                new HttpClientTransportOptions
                {
                    Endpoint = settings.Endpoint,
                    TransportMode = HttpTransportMode.StreamableHttp,
                    Name = "student1-backend"
                },
                httpClient,
                loggerFactory,
                ownsHttpClient: false);
            await using var client = await McpClient.CreateAsync(
                transport,
                loggerFactory: loggerFactory,
                cancellationToken: deadline.Token);
            var result = await client.CallToolAsync(
                call.Tool,
                new Dictionary<string, object?> { ["params"] = call.Arguments },
                cancellationToken: deadline.Token);

            if (result.IsError == true || result.StructuredContent is not { } content)
            {
                throw new AssistantException(AssistantFailure.InvalidResponse, Dependency);
            }

            var body = JsonSerializer.SerializeToElement(content);
            if (body.ValueKind == JsonValueKind.Object
                && body.TryGetProperty("ok", out var ok)
                && ok.ValueKind == JsonValueKind.False)
            {
                throw new AssistantException(DomainFailure(body), Dependency);
            }

            return body;
        }
        catch (AssistantException)
        {
            throw;
        }
        catch (OperationCanceledException exception) when (!cancellationToken.IsCancellationRequested)
        {
            throw new AssistantException(AssistantFailure.Timeout, Dependency, exception);
        }
        catch (Exception exception) when (exception is HttpRequestException or McpException or IOException)
        {
            throw new AssistantException(AssistantFailure.Unavailable, Dependency, exception);
        }
    }

    private static AssistantFailure DomainFailure(JsonElement body)
    {
        var code = body.TryGetProperty("error", out var error)
            && error.ValueKind == JsonValueKind.Object
            && error.TryGetProperty("code", out var value)
            && value.ValueKind == JsonValueKind.String
                ? value.GetString()
                : null;
        return code switch
        {
            "search_not_found" => AssistantFailure.SearchNotFound,
            "dependency_timeout" => AssistantFailure.Timeout,
            "dependency_unavailable" => AssistantFailure.Unavailable,
            _ => AssistantFailure.InvalidResponse
        };
    }
}

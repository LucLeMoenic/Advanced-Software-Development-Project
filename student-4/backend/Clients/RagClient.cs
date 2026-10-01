using System.Net;
using System.Net.Http.Json;
using System.Text.Json;

namespace BudgetTracker.Backend.Clients;

public interface IRagClient
{
    Task<JsonElement> AskAsync(string question, CancellationToken cancellationToken);
}

public sealed record RagSettings(Uri BaseAddress, TimeSpan Deadline)
{
    public static RagSettings FromUrl(string value) =>
        Uri.TryCreate(value, UriKind.Absolute, out var address)
        && address.Scheme is "http" or "https"
        && string.IsNullOrWhiteSpace(address.UserInfo)
            ? new(address, TimeSpan.FromSeconds(30))
            : throw new InvalidOperationException("RAG_SERVER_URL must be an absolute HTTP URL without user information.");
}

public sealed class RagFailureException(int statusCode, string code, string message, Exception? innerException = null)
    : Exception(message, innerException)
{
    public int StatusCode { get; } = statusCode;
    public string Code { get; } = code;
}

public sealed class RagClient(HttpClient client, RagSettings settings) : IRagClient
{
    private const int MaximumResponseBytes = 16 * 1024;

    public async Task<JsonElement> AskAsync(string question, CancellationToken cancellationToken)
    {
        using var deadline = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
        deadline.CancelAfter(settings.Deadline);
        try
        {
            using var request = new HttpRequestMessage(HttpMethod.Post, new Uri(settings.BaseAddress, "/query"))
            {
                Content = JsonContent.Create(new { feature = "student-4", question })
            };
            using var response = await client.SendAsync(request, HttpCompletionOption.ResponseHeadersRead, deadline.Token);
            if (response.StatusCode != HttpStatusCode.OK)
            {
                throw response.StatusCode switch
                {
                    HttpStatusCode.ServiceUnavailable => new RagFailureException(503, "dependency_unavailable", "The RAG service is unavailable."),
                    HttpStatusCode.GatewayTimeout => new RagFailureException(504, "dependency_timeout", "The RAG service timed out."),
                    _ => InvalidResponse()
                };
            }

            await using var stream = await response.Content.ReadAsStreamAsync(deadline.Token);
            using var buffer = new MemoryStream();
            var chunk = new byte[4096];
            int read;
            while ((read = await stream.ReadAsync(chunk, deadline.Token)) > 0)
            {
                if (buffer.Length + read > MaximumResponseBytes)
                {
                    throw new RagFailureException(502, "dependency_response_too_large", "The RAG response exceeded the size limit.");
                }

                buffer.Write(chunk, 0, read);
            }

            using var document = JsonDocument.Parse(buffer.ToArray());
            return document.RootElement.Clone();
        }
        catch (RagFailureException)
        {
            throw;
        }
        catch (OperationCanceledException exception) when (!cancellationToken.IsCancellationRequested)
        {
            throw new RagFailureException(504, "dependency_timeout", "The RAG service timed out.", exception);
        }
        catch (HttpRequestException exception)
        {
            throw new RagFailureException(503, "dependency_unavailable", "The RAG service is unavailable.", exception);
        }
        catch (JsonException exception)
        {
            throw InvalidResponse(exception);
        }
        catch (IOException exception)
        {
            throw new RagFailureException(503, "dependency_unavailable", "The RAG service is unavailable.", exception);
        }
    }

    private static RagFailureException InvalidResponse(Exception? innerException = null) =>
        new(502, "dependency_response_invalid", "The RAG service returned an unusable response.", innerException);
}
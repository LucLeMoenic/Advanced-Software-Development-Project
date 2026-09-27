using System.Net;
using System.Net.Http.Json;
using System.Text.Json;
using Accommodation.Backend.Api;

namespace Accommodation.Backend.Clients;

public interface IRagClient
{
    Task<JsonElement> AskAsync(string question, CancellationToken cancellationToken);
}

public sealed record RagSettings(Uri BaseAddress, TimeSpan Deadline);

public sealed class RagClient(HttpClient client, RagSettings settings) : IRagClient
{
    private const string Dependency = "rag";
    private const int MaximumResponseBytes = 16000;

    public async Task<JsonElement> AskAsync(string question, CancellationToken cancellationToken)
    {
        using var deadline = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
        deadline.CancelAfter(settings.Deadline);
        try
        {
            using var request = new HttpRequestMessage(HttpMethod.Post, new Uri(settings.BaseAddress, "/query"))
            {
                Content = JsonContent.Create(new { feature = "student-1", question })
            };
            using var response = await client.SendAsync(request, HttpCompletionOption.ResponseHeadersRead, deadline.Token);
            if (response.StatusCode != HttpStatusCode.OK)
            {
                throw new AssistantException(
                    response.StatusCode switch
                    {
                        HttpStatusCode.ServiceUnavailable => AssistantFailure.Unavailable,
                        HttpStatusCode.GatewayTimeout => AssistantFailure.Timeout,
                        _ => AssistantFailure.InvalidResponse
                    },
                    Dependency);
            }

            await using var stream = await response.Content.ReadAsStreamAsync(deadline.Token);
            using var buffer = new MemoryStream();
            var chunk = new byte[4096];
            int read;
            while ((read = await stream.ReadAsync(chunk, deadline.Token)) > 0)
            {
                if (buffer.Length + read > MaximumResponseBytes)
                {
                    throw new AssistantException(AssistantFailure.InvalidResponse, Dependency);
                }

                buffer.Write(chunk, 0, read);
            }

            using var document = JsonDocument.Parse(buffer.ToArray());
            return document.RootElement.Clone();
        }
        catch (AssistantException)
        {
            throw;
        }
        catch (OperationCanceledException exception) when (!cancellationToken.IsCancellationRequested)
        {
            throw new AssistantException(AssistantFailure.Timeout, Dependency, exception);
        }
        catch (HttpRequestException exception)
        {
            throw new AssistantException(AssistantFailure.Unavailable, Dependency, exception);
        }
        catch (JsonException exception)
        {
            throw new AssistantException(AssistantFailure.InvalidResponse, Dependency, exception);
        }
    }
}
